"""Six typed, parameterized graph tools shared by FastAPI and MCP."""
import time
import uuid
from backend.db import run, graph, TENANTS

ROOT_CAUSE = """
MATCH (failing:Service {name: $service_name})
MATCH (upstream:Service)<-[:MODIFIED]-(pr:PR)<-[:AUTHORED]-(dev:Person)
WITH failing, upstream, pr, dev,
 shortestPath((failing)-[:DEPENDS_ON*0..5]->(upstream)) AS p
WHERE p IS NOT NULL
OPTIONAL MATCH (downstream:Service)-[:DEPENDS_ON*1..4]->(failing)
OPTIONAL MATCH (team:Team)-[:OWNS]->(upstream)
RETURN [n IN nodes(p) | n.name] AS dependency_path,
 upstream.name AS root_service, pr.id AS suspect_pr, pr.title AS pr_title,
 dev.name AS author_name, dev.handle AS author_handle, team.name AS owning_team,
 collect(DISTINCT downstream.name) AS downstream_blast_radius,
 [n IN nodes(p) | n.id] + [pr.id, dev.id, team.id] AS highlighted_node_ids,
 length(p) AS path_hops, pr.timestamp AS pr_timestamp
ORDER BY path_hops ASC, pr_timestamp DESC LIMIT 3
"""
PAGERANK = """
CALL algo.pageRank('Service', 'DEPENDS_ON') YIELD node, score
RETURN node.name AS service_name, node.tier AS tier, node.status AS status,
 score AS pagerank_score, [node.id] AS highlighted_node_ids
ORDER BY pagerank_score DESC LIMIT 10
"""
POLICY = """
MATCH (s:Service {name:$service_name})<-[:GOVERNS]-(active:Decision)
WHERE active.valid_from <= $valid_at AND (active.valid_to=0 OR $valid_at < active.valid_to)
 AND active.recorded_from <= $known_at AND (active.recorded_to=0 OR $known_at < active.recorded_to)
OPTIONAL MATCH (active)-[:DECIDED_BY]->(author:Person)
OPTIONAL MATCH path=(active)-[:SUPERSEDES*1..5]->(old:Decision)
RETURN active.id AS active_decision_id, active.summary AS current_policy,
 active.source AS current_source, active.valid_from AS valid_from,
 author.name AS decided_by,
 CASE WHEN path IS NULL THEN [] ELSE
 [d IN nodes(path) WHERE d <> active |
 {id:d.id, summary:d.summary, source:d.source, valid_to:d.valid_to}] END AS superseded_history,
 [s.id,active.id,author.id] + CASE WHEN path IS NULL THEN [] ELSE [d IN nodes(path)|d.id] END
 AS highlighted_node_ids
"""
SUPERSEDE = """
MATCH (s:Service {name:$service_name})<-[:GOVERNS]-(old:Decision {topic:$topic, status:'ACTIVE'})
MATCH (p:Person {name:$person_name})
WHERE old.valid_from < $timestamp
SET old.status='SUPERSEDED', old.valid_to=$timestamp, old.recorded_to=$recorded_at
CREATE (historical:Decision {id:old.id+'@'+toString($recorded_at), topic:old.topic,
 summary:old.summary, source:old.source, valid_from:old.valid_from, valid_to:0,
 recorded_from:old.recorded_from, recorded_to:$recorded_at, status:'HISTORICAL'})
CREATE (historical)-[:GOVERNS]->(s)
SET old.recorded_from=$recorded_at, old.recorded_to=0
CREATE (new:Decision {id:$new_id, topic:$topic, summary:$new_summary, source:$source,
 valid_from:$timestamp, valid_to:0, recorded_from:$recorded_at, recorded_to:0, status:'ACTIVE'})
CREATE (new)-[:GOVERNS]->(s), (new)-[:DECIDED_BY]->(p),
 (new)-[:SUPERSEDES {reason:$reason, timestamp:$timestamp}]->(old)
RETURN new.id AS created_decision, old.id AS superseded_decision,
 [s.id, p.id, old.id, new.id] AS highlighted_node_ids
"""
PLAYBOOK = """
MATCH (sig:SymptomSignature {error_code:$error_code, affected_service:$service_name})
 -[:TRIGGERS_PLAYBOOK]->(pb:Playbook)
MATCH (pb)-[:HAS_STEP]->(step:ActionStep)
RETURN pb.id AS playbook_id, pb.name AS playbook_name, pb.success_count AS prior_successes,
 step.step_order AS step_order, step.mcp_tool AS tool_name,
 step.tool_args_json AS tool_args, step.expected_outcome AS outcome,
 [sig.id,pb.id,step.id] AS highlighted_node_ids
ORDER BY step.step_order ASC
"""
IMPACT = """
MATCH (target:Service {name:$target_service})
OPTIONAL MATCH (caller:Service)-[:DEPENDS_ON*1..4]->(target)
WHERE caller.tier=1
RETURN count(DISTINCT caller) AS impacted_tier1_services,
 collect(DISTINCT caller.name) AS impacted_names,
 collect(DISTINCT caller.id)+[target.id] AS highlighted_node_ids
"""
CONNECTIVITY = """
MATCH (caller:Service {tier:1}), (dest:Service {name:$target_service})
MATCH p=(caller)-[:DEPENDS_ON*1..5]->(dest)
RETURN collect(DISTINCT caller.name) AS reachable,
 collect(DISTINCT caller.id) AS highlighted_node_ids
"""

def trace_root_cause_and_blast_radius(service_name: str, tenant: str = "vortexpay_prod"):
    return run(tenant, ROOT_CAUSE, dict(service_name=service_name))

def compute_service_criticality_pagerank(tenant: str = "vortexpay_prod"):
    return run(tenant, PAGERANK)

def resolve_bitemporal_policy(service_name: str, tenant: str = "vortexpay_prod",
                              valid_at: int | None = None, known_at: int | None = None):
    now = int(time.time())
    return run(tenant, POLICY, dict(service_name=service_name,
               valid_at=now if valid_at is None else valid_at, known_at=now if known_at is None else known_at))

def ingest_and_supersede_decision(service_name: str, topic: str, person_name: str,
    new_summary: str, source: str, reason: str, timestamp: int,
    tenant: str = "vortexpay_prod", new_id: str | None = None):
    if tenant not in TENANTS:
        raise ValueError("Invalid tenant")
    if timestamp > int(time.time()):
        raise ValueError("Future effective timestamps are unsupported")
    decision_id = new_id or "DEC-"+str(uuid.uuid4())
    existing = run(tenant, "MATCH (d:Decision {id:$id}) RETURN d.id AS id", dict(id=decision_id))
    if existing["data"]:
        return existing
    result = run(tenant, SUPERSEDE, dict(service_name=service_name, topic=topic, person_name=person_name,
        new_summary=new_summary, source=source, reason=reason, timestamp=timestamp,
        recorded_at=int(time.time()), new_id=decision_id))
    if not result["data"]:
        raise ValueError("No matching active policy/author, or invalid effective timestamp")
    return result

def lookup_procedural_playbook(error_code: str, service_name: str, tenant: str = "vortexpay_prod"):
    return run(tenant, PLAYBOOK, dict(error_code=error_code, service_name=service_name))

def simulate_action_in_shadow_graph(target_service: str, action: str, tenant: str = "vortexpay_prod"):
    if tenant not in TENANTS or action not in ("isolate", "rollback"):
        raise ValueError("Choose a production tenant and isolate or rollback")
    target = run(tenant, "MATCH (s:Service {name:$name}) RETURN s.id AS id", dict(name=target_service))
    if not target["data"]:
        raise ValueError("Target service does not exist")
    shadow = "vortexpay_sandbox" if tenant == "vortexpay_prod" else "tenant_beta_sandbox"
    names = graph(tenant).client.execute_command("GRAPH.LIST")
    if shadow in [n.decode() if isinstance(n, bytes) else n for n in names]:
        graph(shadow).delete()
    # GRAPH.COPY is a native FalkorDB snapshot; no Python topology cache.
    graph(tenant).copy(shadow)
    params = dict(target_service=target_service)
    traces = [run(shadow, IMPACT, params), run(shadow, CONNECTIVITY, params)]
    before = set(traces[-1]["data"][0]["reachable"])
    if action == "isolate":
        mutation = """
MATCH (s:Service {name:$target_service})-[r:DEPENDS_ON]-()
DELETE r SET s.status='ISOLATED' RETURN s.id AS id, [s.id] AS highlighted_node_ids
"""
    else:
        # Roll back the unsafe configuration while keeping the current Slack policy.
        mutation = """
MATCH (s:Service {name:$target_service})
SET s.timeout_ms=150, s.circuit_breaker=true, s.max_pool_size=120
RETURN s.id AS id, [s.id] AS highlighted_node_ids
"""
    traces.append(run(shadow, mutation, params))
    if action=="rollback":
        from backend.simulator import recalculate_graph_telemetry
        traces.append(recalculate_graph_telemetry(shadow))
    traces.append(run(shadow, CONNECTIVITY, params))
    after = set(traces[-1]["data"][0]["reachable"])
    lost = sorted(before-after)
    return dict(data=[dict(action=action, target=target_service, lost_connectivity=lost,
                impacted_tier1_services=len(lost), safe=not lost,
                configuration="150ms / circuit breaker / pool 64" if action=="rollback" else "isolated")],
        cypher_executed="\n".join(t["cypher_executed"] for t in traces),
        execution_time_ms=sum(t["execution_time_ms"] for t in traces),
        highlighted_node_ids=sorted(set(n for t in traces for n in t["highlighted_node_ids"])),
        graph=shadow, traces=traces, clone_command=f"GRAPH.COPY {tenant} {shadow}")

def remediate_auth_pool(tenant: str, service_name: str):
    """Allowlisted synthetic tool: never executes shell/real infrastructure actions."""
    if service_name != "token-auth-service":
        raise ValueError("Only the synthetic auth-pool remediation is allowed")
    policy = resolve_bitemporal_policy(service_name, tenant)
    if not any(d["active_decision_id"] == "DEC-02" for d in policy["data"]):
        raise ValueError("Inject and approve DEC-02 before remediation")
    from backend.simulator import recalculate_graph_telemetry
    mutation=run(tenant, """
MATCH (s:Service {name:$service_name})
SET s.timeout_ms=150,s.circuit_breaker=true,s.max_pool_size=120
RETURN s.id AS id
""",dict(service_name=service_name))
    metrics=recalculate_graph_telemetry(tenant)
    result=run(tenant, """
MATCH (s:Service {name:$service_name}), (checkout:Service {name:'checkout-api'})
RETURN s.name AS service,s.status AS status,s.timeout_ms AS timeout_ms,
 s.circuit_breaker AS circuit_breaker,[s.id,checkout.id] AS highlighted_node_ids
""",dict(service_name=service_name))
    result["execution_time_ms"]+=mutation["execution_time_ms"]+metrics["execution_time_ms"]
    result["cypher_executed"]=mutation["cypher_executed"]+chr(10)+metrics["cypher_executed"]+chr(10)+result["cypher_executed"]
    return result
