"""Seven MCP operations. Caller binds tenant/run identity outside model arguments."""
import hashlib
import json
import os
import uuid
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from backend.db import run, graph
from backend.simulator import recalculate_graph_telemetry
from backend.v2_policy import active_policy, validate_config
from backend import mcp_tools as legacy

def tenant():return os.getenv("AEGIS_TENANT","vortexpay_prod")
def run_id():return os.getenv("AEGIS_RUN_ID","manual")

def merge(*traces):
    return dict(data=traces[-1]["data"],graph=traces[-1]["graph"],
        cypher_executed=chr(10).join(t["cypher_executed"] for t in traces),
        execution_time_ms=sum(t["execution_time_ms"] for t in traces),
        highlighted_node_ids=sorted({n for t in traces for n in t["highlighted_node_ids"]}))

def snapshot(name):
    return run(name,"""
MATCH (s:Service) OPTIONAL MATCH (s)-[:DEPENDS_ON]->(d:Service)
RETURN s.name AS name, s.timeout_ms AS timeout_ms,s.max_pool_size AS max_pool_size,
 s.circuit_breaker AS circuit_breaker,s.base_processing_ms AS base_processing_ms,
 s.current_load_rps AS current_load_rps, collect(d.name) AS dependencies
ORDER BY name
""")

def fingerprint(name):
    rows=snapshot(name)["data"]
    for row in rows:row["dependencies"]=sorted(row["dependencies"])
    return hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()

def telemetry(name):
    return run(name,"""
MATCH (s:Service) RETURN s.name AS name,s.error_rate AS error_rate,
 s.p99_latency_ms AS p99_latency_ms,s.status AS status,
 s.timeout_ms AS timeout_ms,s.max_pool_size AS max_pool_size,s.circuit_breaker AS circuit_breaker
ORDER BY name
""")

def inspect_service_telemetry_and_frontier(service_name: str):
    """Inspect measured service health and unexplored dependency, PR, and policy frontiers."""
    result=run(tenant(),"""
MATCH (s:Service {name:$name})
OPTIONAL MATCH (s)-[:DEPENDS_ON]->(d:Service)
WITH s,collect(DISTINCT d.name) AS deps
OPTIONAL MATCH (p:PR)-[:MODIFIED]->(s)
WITH s,deps,collect(DISTINCT p.id) AS prs
OPTIONAL MATCH (dec:Decision {status:'ACTIVE'})-[:GOVERNS]->(s)
RETURN properties(s) AS telemetry, deps AS dependencies, prs AS recent_prs,
 collect(DISTINCT dec.id) AS decisions,
 size(deps) AS upstream_dependencies_count,size(prs) AS recent_prs_count,
 count(DISTINCT dec) AS governing_decisions_count,[s.id] AS highlighted_node_ids
""",dict(name=service_name))
    if not result["data"]:raise ValueError("Unknown service")
    result["unexplored_edges"]={k:result["data"][0][k] for k in ("dependencies","recent_prs","decisions")}
    return result

def traverse_dependency_SingleOrMultiHop(service_name: str,max_hops: int=3):
    """Traverse upstream dependencies and identify where measured errors originate; max_hops is 1..5."""
    if not 1<=max_hops<=5:raise ValueError("max_hops must be 1..5")
    return run(tenant(),f"""
MATCH p=(s:Service {{name:$name}})-[:DEPENDS_ON*1..{max_hops}]->(dep:Service)
RETURN [n IN nodes(p)|n.name] AS path, dep.name AS dependency,
 dep.error_rate AS error_rate,dep.p99_latency_ms AS p99_latency_ms,
 [n IN nodes(p)|n.id] AS highlighted_node_ids
ORDER BY error_rate DESC
""",dict(name=service_name))

def inspect_recent_prs_and_authors(service_name: str):
    """Read recent modifying PRs, exact configuration diffs, and author provenance for this service."""
    return run(tenant(),"""
MATCH (person:Person)-[:AUTHORED]->(p:PR)-[:MODIFIED]->(s:Service {name:$name})
RETURN p.id AS pr_id,p.title AS title,p.config_diff AS config_diff,
 person.name AS author,p.timestamp AS timestamp,[person.id,p.id,s.id] AS highlighted_node_ids
ORDER BY timestamp DESC
""",dict(name=service_name))

def query_bitemporal_policies(service_name: str):
    """Read active policy constraints and supersession history. Structured bounds must be followed."""
    history=legacy.resolve_bitemporal_policy(service_name,tenant())
    current=active_policy(tenant(),service_name)
    history["policy"]=dict(id=current["id"],summary=current["summary"],bounds=json.loads(current["bounds"]))
    history["unexplored_edges"]={"supersession_lineage":True}
    return history

def compute_blast_radius_pagerank():
    """Rank service bottlenecks with native FalkorDB PageRank before choosing impactful actions."""
    return legacy.compute_service_criticality_pagerank(tenant())

class Mutation(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    service_name: str
    timeout_ms: int=Field(ge=1,le=10000)
    max_pool_size: int=Field(ge=1,le=1000)
    circuit_breaker: StrictBool

def mutate(name,params):
    return run(name,"""
MATCH (s:Service {name:$service_name})
SET s.timeout_ms=$timeout_ms,s.max_pool_size=$max_pool_size,s.circuit_breaker=$circuit_breaker
RETURN s.name AS name,[s.id] AS highlighted_node_ids
""",params)

def clone_services(source,dest):
    names=graph(source).client.execute_command("GRAPH.LIST")
    if dest in [n.decode() if isinstance(n,bytes) else n for n in names]:graph(dest).delete()
    snap=run(source,"MATCH (s:Service) RETURN properties(s) AS properties")
    edges=run(source,"MATCH (a:Service)-[r:DEPENDS_ON]->(b:Service) RETURN a.id AS a,b.id AS b,properties(r) AS properties")
    a=run(dest,"UNWIND $nodes AS n CREATE (s:Service) SET s=n.properties RETURN s.id AS id",
          dict(nodes=snap["data"]))
    b=run(dest,"""UNWIND $edges AS e MATCH (a:Service {id:e.a}),(b:Service {id:e.b})
CREATE (a)-[r:DEPENDS_ON]->(b) SET r=e.properties RETURN a.id AS id""",dict(edges=edges["data"]))
    return merge(snap,edges,a,b)

def simulate_config_mutation_in_sandbox(service_name: str,timeout_ms: int,max_pool_size: int,circuit_breaker: bool):
    """Test a policy-compliant configuration on an isolated service graph and store a measured safety receipt."""
    args=Mutation(service_name=service_name,timeout_ms=timeout_ms,max_pool_size=max_pool_size,circuit_breaker=circuit_breaker).model_dump()
    policy=active_policy(tenant(),service_name);validate_config(policy,args)
    shadow="vortexpay_sandbox" if tenant()=="vortexpay_prod" else "tenant_beta_sandbox"
    before=telemetry(tenant()); fp=fingerprint(tenant())
    clone=clone_services(tenant(),shadow)
    mutation=mutate(shadow,args)
    physics=recalculate_graph_telemetry(shadow);after=telemetry(shadow)
    target={r["name"]:r for r in after["data"]}
    safe=target["checkout-api"]["error_rate"]<.01 and target[service_name]["error_rate"]<.01 and target["checkout-api"]["p99_latency_ms"]<500
    receipt=run(tenant(),"""
CREATE (s:Simulation {id:$id,run_id:$run_id,config_json:$config,input_hash:$fp,
 decision_id:$decision,safe:$safe})
RETURN s.id AS id
""",dict(id="SIM-"+str(uuid.uuid4()),run_id=run_id(),config=json.dumps(args,sort_keys=True),fp=fp,decision=policy["id"],safe=safe))
    result=merge(clone,mutation,physics,after,receipt)
    result["data"]=[dict(safe=safe,before=before["data"],after=after["data"],decision_id=policy["id"])]
    result["graph"]=shadow
    return result

def apply_verified_mutation_to_prod(service_name: str,timeout_ms: int,max_pool_size: int,
        circuit_breaker: bool,justifying_decision_id: str,justifying_pr_id: str):
    """Apply exactly the sandbox-verified configuration with current policy/PR evidence; verify derived recovery."""
    args=Mutation(service_name=service_name,timeout_ms=timeout_ms,max_pool_size=max_pool_size,circuit_breaker=circuit_breaker).model_dump()
    policy=active_policy(tenant(),service_name);validate_config(policy,args)
    if policy["id"]!=justifying_decision_id:raise ValueError("Stale justifying policy")
    request_args=dict(args,justifying_decision_id=justifying_decision_id,justifying_pr_id=justifying_pr_id)
    request_key=json.dumps(request_args,sort_keys=True)
    cached=run(tenant(),"""
MATCH (a:AppliedMutation {run_id:$rid,args_json:$args})
RETURN a.result_json AS result,a.post_fingerprint AS fp
""",dict(rid=run_id(),args=request_key))["data"]
    if cached and cached[0]["fp"]==fingerprint(tenant()):
        result=json.loads(cached[0]["result"]);result["idempotent_replay"]=True
        return result
    pr=run(tenant(),"MATCH (p:PR {id:$id})-[:MODIFIED]->(:Service {name:$name}) RETURN p.id AS id",
        dict(id=justifying_pr_id,name=service_name))
    if not pr["data"]:raise ValueError("PR does not justify this service")
    receipt=run(tenant(),"""
MATCH (s:Simulation {run_id:$run_id,config_json:$config,input_hash:$fp,decision_id:$decision,safe:true})
RETURN s.id AS id LIMIT 1
""",dict(run_id=run_id(),config=json.dumps(args,sort_keys=True),fp=fingerprint(tenant()),decision=policy["id"]))
    if not receipt["data"]:raise ValueError("Verified sandbox receipt missing or stale; simulate this exact configuration first")
    before=telemetry(tenant())
    mutation=mutate(tenant(),args);physics=recalculate_graph_telemetry(tenant());after=telemetry(tenant())
    a={r["name"]:r for r in after["data"]};b={r["name"]:r for r in before["data"]}
    verified=a["checkout-api"]["error_rate"]<.01 and a["checkout-api"]["p99_latency_ms"]<500 and a[service_name]["error_rate"]<.01
    result=merge(pr,receipt,before,mutation,physics,after)
    result["data"]=[dict(verified=verified,pre_error_rate=b["checkout-api"]["error_rate"],
        post_error_rate=a["checkout-api"]["error_rate"],p99_latency_ms=a["checkout-api"]["p99_latency_ms"],
        decision_id=policy["id"],before=before["data"],after=after["data"])]
    if not verified:raise ValueError("Measured production postcondition failed")
    run(tenant(),"""
CREATE (:AppliedMutation {id:$id,run_id:$rid,args_json:$args,result_json:$result,post_fingerprint:$fp})
RETURN 1 AS saved
""",dict(id="APPLIED-"+str(uuid.uuid4()),rid=run_id(),args=request_key,result=json.dumps(result),fp=fingerprint(tenant())))
    return result

TOOLS=(inspect_service_telemetry_and_frontier,traverse_dependency_SingleOrMultiHop,
 inspect_recent_prs_and_authors,query_bitemporal_policies,compute_blast_radius_pagerank,
 simulate_config_mutation_in_sandbox,apply_verified_mutation_to_prod)