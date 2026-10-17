import json
import time
from backend.db import run
from backend.mcp_tools import ingest_and_supersede_decision
from backend.seed_graph import ANCHOR

def ensure_policy(tenant, security=False):
    decision="DEC-03" if security else "DEC-02"
    if security:
        ensure_policy(tenant)
    current=run(tenant,"MATCH (d:Decision {id:$id}) RETURN d.id AS id",dict(id=decision))
    if not current["data"]:
        ingest_and_supersede_decision("token-auth-service","auth-pool-timeout",
            "Priya Nair" if security else "Sarah Chen",
            "Security directive: circuit breaker requires timeout >=450ms, pool >=100."
            if security else "Never raise auth timeout above 300ms; use pool >=100 with circuit breaking.",
            "SLACK-SEC-03" if security else "SLACK-882",
            "Security policy revision" if security else "Bound pool starvation",
            int(time.time())-1 if security else ANCHOR-7200,tenant,decision)
    bounds=dict(min_timeout_ms=450,max_timeout_ms=1000,min_pool_size=100,require_circuit_breaker=True) if security else dict(min_timeout_ms=1,max_timeout_ms=300,min_pool_size=100,require_circuit_breaker=True)
    return run(tenant,"""
MATCH (d:Decision {id:$id}) SET d.config_bounds_json=$bounds
RETURN d.id AS id, d.summary AS summary, [d.id] AS highlighted_node_ids
""",dict(id=decision,bounds=json.dumps(bounds)))

def active_policy(tenant,service):
    rows=run(tenant,"""
MATCH (d:Decision {status:'ACTIVE'})-[:GOVERNS]->(:Service {name:$name})
RETURN d.id AS id, d.config_bounds_json AS bounds, d.summary AS summary
""",dict(name=service))["data"]
    if len(rows)!=1 or not rows[0].get("bounds"):raise ValueError("Exactly one structured active policy is required")
    return rows[0]

def validate_config(policy, args):
    b=json.loads(policy["bounds"])
    if not b["min_timeout_ms"]<=args["timeout_ms"]<=b["max_timeout_ms"]:
        raise ValueError("POLICY_REJECTED: timeout outside active decision bounds")
    if args["max_pool_size"]<b["min_pool_size"] or not args["circuit_breaker"]:
        raise ValueError("POLICY_REJECTED: bounded pool and circuit breaker required")