"""Deterministic synthetic DAG physics. Only this module derives telemetry."""
import math
from backend.db import run

TOPOLOGY = """
MATCH (s:Service)
OPTIONAL MATCH (s)-[:DEPENDS_ON]->(d:Service)
RETURN properties(s) AS config, collect(d.name) AS dependencies
"""
def calculate(configs):
    configs={r["config"]["name"]:r for r in configs}
    computed={}
    visiting=set()
    def visit(name):
        if name in computed:return computed[name]
        if name in visiting:raise ValueError("Dependency cycle detected; telemetry was not written")
        visiting.add(name)
        item=configs[name]; s=item["config"]
        children=[visit(n) for n in item["dependencies"]]
        pool=int(s["max_pool_size"]); timeout=int(s["timeout_ms"])
        if pool<1 or timeout<1:raise ValueError("Pool size and timeout must be positive")
        pressure=float(s["current_load_rps"])/pool
        queue=0 if s["circuit_breaker"] else max(0,pressure-25)*4
        child_latency=max((c["p99_latency_ms"] for c in children),default=0)
        latency=float(s["base_processing_ms"])+queue+child_latency
        timeout_error=0.0
        for child in children:
            if timeout<child["p99_latency_ms"]:
                timeout_error=max(timeout_error,0.004 if s["circuit_breaker"] and pool>=80
                    else min(.95,(child["p99_latency_ms"]-timeout)/child["p99_latency_ms"]+.35))
        starvation=0 if s["circuit_breaker"] else min(.85,max(0,pressure-25)/52)
        local=max(.999 if s.get("isolated") or s.get("dependency_unavailable") else .002,starvation,timeout_error)
        # Critical dependency errors propagate with 0.85 coupling per service hop.
        inherited=max((c["error_rate"]*.85 for c in children),default=0)
        error=min(.999,max(local,inherited))
        result=dict(name=name,p99_latency_ms=round(latency,4),error_rate=round(error,6),
                    status="HEALTHY" if error<.01 else "DEGRADED" if error<.15 else "CRITICAL")
        visiting.remove(name);computed[name]=result
        return result
    for name in configs:visit(name)
    return list(computed.values())

def recalculate_graph_telemetry(graph_name="vortexpay_prod"):
    source=run(graph_name,TOPOLOGY)
    rows=calculate(source["data"])
    result=run(graph_name,"""
UNWIND $rows AS row MATCH (s:Service {name:row.name})
SET s.p99_latency_ms=row.p99_latency_ms, s.error_rate=row.error_rate, s.status=row.status
RETURN s.name AS name, s.error_rate AS error_rate, s.p99_latency_ms AS p99_latency_ms,
 s.status AS status, [s.id] AS highlighted_node_ids
""",dict(rows=rows))
    result["execution_time_ms"]+=source["execution_time_ms"]
    result["cypher_executed"]=TOPOLOGY+"\n"+result["cypher_executed"]
    return result

def migrate_physics(tenant):
    result=run(tenant,"""
MATCH (s:Service) WHERE s.max_pool_size IS NULL
SET s.timeout_ms=2000, s.max_pool_size=200, s.circuit_breaker=false,
 s.base_processing_ms=15, s.current_load_rps=1200
RETURN s.name AS name
""")
    if result["data"]:
        run(tenant,"""
MATCH (s:Service {name:'redis-session-cluster'})
SET s.base_processing_ms=190, s.max_pool_size=500
WITH s MATCH (a:Service {name:'token-auth-service'})
SET a.timeout_ms=150, a.max_pool_size=20, a.base_processing_ms=20
RETURN a.id AS id
""")
    run(tenant,"MATCH (p:PR {id:'PR-409'}) SET p.config_diff=$diff RETURN p.id AS id",
        dict(diff='{"timeout_ms":{"before":5000,"after":150},"max_pool_size":{"before":100,"after":20},"circuit_breaker":{"after":false}}'))
    return recalculate_graph_telemetry(tenant)

def inject_fault(tenant):
    run(tenant,"""
MATCH (a:Service {name:'token-auth-service'}), (r:Service {name:'redis-session-cluster'})
SET a.timeout_ms=150, a.max_pool_size=20, a.circuit_breaker=false,
 a.current_load_rps=1200, r.base_processing_ms=190
RETURN a.id AS id
""")
    return recalculate_graph_telemetry(tenant)
