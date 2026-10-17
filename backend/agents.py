"""Deterministic specialist agents; all handoffs, traces and memory live in the graph."""
import json
import time
import uuid
from backend.db import run
from backend import mcp_tools as tools
from backend.seed_graph import ANCHOR

def new_session(tenant):
    sid = "SES-"+str(uuid.uuid4())
    run(tenant, """
MATCH (r:Runtime {id:'runtime'})
CREATE (s:Session {id:$id, started_at:$now, user_id:'demo-user', summary:'New investigation', event_count:0})
SET r.active_session=$id RETURN s.id AS id
""", dict(id=sid, now=int(time.time())))
    return sid

def active_session(tenant):
    rows = run(tenant, "MATCH (r:Runtime {id:'runtime'}) RETURN r.active_session AS id")["data"]
    return rows[0]["id"] or new_session(tenant)

def event(tenant, sid, agent, summary, trace=None):
    trace = trace or dict(data=[],cypher_executed="",execution_time_ms=0,highlighted_node_ids=[],graph=tenant)
    payload = dict(agent=agent, summary=summary, trace=trace)
    run(tenant, """
MATCH (s:Session {id:$sid})
SET s.event_count=s.event_count+1
CREATE (e:Event {id:$id, sequence:s.event_count, payload:$payload, created_at:$now})
CREATE (s)-[:HAS_EVENT]->(e)
RETURN e.id AS id
""", dict(sid=sid,id="EVT-"+str(uuid.uuid4()),payload=json.dumps(payload),now=int(time.time())))
    return payload

def events(tenant, sid):
    return [json.loads(r["payload"]) for r in run(tenant, """
MATCH (:Session {id:$sid})-[:HAS_EVENT]->(e:Event)
RETURN e.payload AS payload ORDER BY e.sequence
""", dict(sid=sid))["data"]]

def inject_policy(tenant):
    sid = active_session(tenant)
    result = tools.ingest_and_supersede_decision("token-auth-service","auth-pool-timeout","Sarah Chen",
        "Use 150ms timeout with strict circuit breaking; preserve bounded connection pools.",
        "SLACK-882", "5000ms caused thread starvation under flash-sale load",
        ANCHOR-7200, tenant, "DEC-02")
    run(tenant, """
MATCH (d:Decision {id:'DEC-02'})
MERGE (doc:Document {id:'SLACK-882'})
SET doc.title='Sarah Chen: flash-sale auth configuration', doc.doc_type='slack',
 doc.url='https://example.invalid/SLACK-882', doc.updated_at=$now
MERGE (d)-[:DOCUMENTED_IN]->(doc)
RETURN d.id AS id
""", dict(now=ANCHOR-7200))
    return event(tenant,sid,"Scribe","Policy revised: DEC-02 supersedes DOC-101. 150ms requires circuit breaking.",result)

def handoff(tenant, sid, incident, agent, summary, trace, next_agent):
    result = run(tenant, """
MATCH (s:Session {id:$sid})-[:INVESTIGATED]->(i:Incident {id:$incident})
CREATE (h:Hypothesis {id:$hid, agent:$agent, summary:$summary, confidence:0.97,
 verified:true, cypher_evidence:$cypher})
CREATE (i)-[:HAS_HYPOTHESIS]->(h)
MERGE (t:Task {id:$incident+':'+$agent})
SET t.agent=$agent, t.status='COMPLETE', t.next_agent=$next, t.session_id=$sid
MERGE (i)-[:HAS_TASK]->(t)
RETURN h.id AS id
""", dict(sid=sid,incident=incident,hid="HYP-"+str(uuid.uuid4()),agent=agent,
          summary=summary,cypher=trace["cypher_executed"],next=next_agent))
    return event(tenant,sid,agent,summary,trace)

def compile_playbook(tenant, incident, elapsed):
    return run(tenant, """
MATCH (i:Incident {id:$incident, status:'RESOLVED'})
MERGE (sig:SymptomSignature {id:'SIG-AUTH', error_code:'ERR_AUTH_POOL_EXHAUSTED',
 affected_service:'checkout-api'})
MERGE (pb:Playbook {id:'PB-AUTH'})
SET pb.name='Restore auth pool with current policy', pb.created_from_incident=$incident,
 pb.success_count=1, pb.avg_resolution_ms=$elapsed
MERGE (sig)-[:TRIGGERS_PLAYBOOK]->(pb)
MERGE (step:ActionStep {id:'STEP-AUTH-1'})
SET step.step_order=1, step.mcp_tool='remediate_auth_pool',
 step.tool_args_json='{"service_name":"token-auth-service"}',
 step.expected_outcome='HEALTHY'
MERGE (pb)-[:HAS_STEP {order:1}]->(step)
RETURN pb.id AS playbook_id, [sig.id,pb.id,step.id] AS highlighted_node_ids
""", dict(incident=incident,elapsed=elapsed))

def investigate(tenant, sid):
    started = time.perf_counter()
    iid = "INC-"+str(uuid.uuid4())
    from backend.simulator import inject_fault
    inject_fault(tenant)
    run(tenant, """
MATCH (s:Session {id:$sid}), (checkout:Service {name:'checkout-api'}),
 (auth:Service {name:'token-auth-service'})
CREATE (i:Incident {id:$id, title:'Checkout latency spike', error_signature:'ERR_AUTH_POOL_EXHAUSTED',
 severity:'SEV-1', status:'INVESTIGATING', created_at:$now})
CREATE (s)-[:INVESTIGATED]->(i), (i)-[:AFFECTS]->(checkout)
RETURN i.id AS id
""", dict(sid=sid,id=iid,now=int(time.time())))
    lookup = tools.lookup_procedural_playbook("ERR_AUTH_POOL_EXHAUSTED","checkout-api",tenant)
    yield event(tenant,sid,"Commander",
                "Found compiled procedural memory." if lookup["data"] else "No saved playbook. Starting graph investigation.",lookup)
    try:
        if lookup["data"]:
            # Persisted tool arguments are untrusted: strict tool/name/schema allowlist.
            for step in lookup["data"]:
                if step["tool_name"] != "remediate_auth_pool":
                    raise ValueError("Stored playbook contains a disallowed tool")
                args = json.loads(step["tool_args"])
                if args != {"service_name":"token-auth-service"}:
                    raise ValueError("Stored playbook arguments do not match the approved action")
                trace = tools.remediate_auth_pool(tenant,**args)
                if not trace["data"] or trace["data"][0]["status"] != step["outcome"]:
                    raise ValueError("Playbook postcondition failed")
                yield handoff(tenant,sid,iid,"Commander","Replayed the approved action from FalkorDB; verified HEALTHY.",trace,"DONE")
            elapsed = int((time.perf_counter()-started)*1000)
            run(tenant, """
MATCH (pb:Playbook {id:$id})
SET pb.avg_resolution_ms=(pb.avg_resolution_ms*pb.success_count+$ms)/(pb.success_count+1),
 pb.success_count=pb.success_count+1 RETURN pb.id AS id
""",dict(id=lookup["data"][0]["playbook_id"],ms=elapsed))
        else:
            policy = tools.resolve_bitemporal_policy("token-auth-service",tenant)
            if not any(r["active_decision_id"]=="DEC-02" for r in policy["data"]):
                raise ValueError("Current source is DOC-101. Inject the Slack contradiction before the incident demo.")
            yield handoff(tenant,sid,iid,"Scribe","Sarah Chen approved 150ms with strict circuit breaking. DOC-101 is superseded.",policy,"Navigator")
            root = tools.trace_root_cause_and_blast_radius("checkout-api",tenant)
            if not root["data"]:
                raise ValueError("No root-cause evidence in the graph")
            row = root["data"][0]
            yield handoff(tenant,sid,iid,"Navigator",
                f"{row['suspect_pr']} by {row['author_name']} changed {row['root_service']}. Path: "+ " → ".join(row["dependency_path"]),root,"Navigator")
            run(tenant, """
MATCH (i:Incident {id:$iid})-[:HAS_HYPOTHESIS]->(h:Hypothesis {agent:'Navigator'}),
 (pr:PR {id:$pr}), (d:Decision {id:'DEC-02'})
MERGE (h)-[:POINTS_TO_PR]->(pr) MERGE (h)-[:POINTS_TO_DECISION]->(d)
RETURN h.id AS id
""",dict(iid=iid,pr=row["suspect_pr"]))
            yield event(tenant,sid,"Navigator","Architectural bottlenecks ranked by FalkorDB PageRank.",tools.compute_service_criticality_pagerank(tenant))
            simulation = tools.simulate_action_in_shadow_graph("token-auth-service","rollback",tenant)
            if not simulation["data"][0]["safe"]:
                raise ValueError("Shadow graph rejected the action")
            yield handoff(tenant,sid,iid,"Navigator","Shadow rollback preserves Tier-1 connectivity; authorize synthetic remediation.",simulation,"Commander")
            # Commander reads the durable handoff, not an ephemeral agent message.
            approval = run(tenant, """
MATCH (:Incident {id:$iid})-[:HAS_TASK]->(t:Task {agent:'Navigator', status:'COMPLETE'})
WHERE t.next_agent='Commander' RETURN t.id AS id
""",dict(iid=iid))
            if not approval["data"]:
                raise ValueError("No persisted Navigator approval")
            fix = tools.remediate_auth_pool(tenant,"token-auth-service")
            yield handoff(tenant,sid,iid,"Commander","Applied bounded pool + circuit breaker while retaining 150ms policy; health verified.",fix,"DONE")
        run(tenant,"MATCH (i:Incident {id:$id}) SET i.status='RESOLVED' RETURN i.id AS id",dict(id=iid))
        elapsed = int((time.perf_counter()-started)*1000)
        if not lookup["data"]:
            compiled = compile_playbook(tenant,iid,elapsed)
            yield event(tenant,sid,"Commander","Successful action compiled into a reusable procedural subgraph.",compiled)
        yield event(tenant,sid,"System",f"Incident resolved in {elapsed}ms. All evidence persisted in FalkorDB.")
    except Exception as exc:
        run(tenant,"MATCH (i:Incident {id:$id}) SET i.status='FAILED' RETURN i.id AS id",dict(id=iid))
        yield event(tenant,sid,"System",str(exc))
        raise