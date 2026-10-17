"""Versioned memory compiled from verified production ToolTrace records."""
import json
import time
import uuid
from backend.db import run

GATE="""
MATCH (sig:SymptomSignature {error_code:$error_code,entry_service:$entry_service})
 -[:HAS_PLAYBOOK]->(pb:Playbook {status:'ACTIVE'})
OPTIONAL MATCH (dec:Decision {id:pb.required_decision_id})
OPTIONAL MATCH (s:Service {name:$entry_service})-[:DEPENDS_ON*1..4]->(dep:Service)
WITH pb,dec,collect(DISTINCT dep.name) AS raw_deps
RETURN pb.id AS playbook_id,pb.version AS version,
 pb.required_decision_id AS required_decision_id,dec.status AS decision_status,
 pb.topology_hash AS expected_topology_hash,raw_deps AS live_dependencies,
 pb.required_config_bounds AS required_config_bounds
"""
def topology_hash(tenant,entry):
    rows=run(tenant,"""
MATCH (:Service {name:$name})-[:DEPENDS_ON*1..4]->(dep:Service)
RETURN collect(DISTINCT dep.name) AS names
""",dict(name=entry))["data"]
    return "|".join(sorted(rows[0]["names"]))

def edge_hash(tenant,entry):
    result=run(tenant,"""
MATCH p=(:Service {name:$name})-[:DEPENDS_ON*1..4]->(:Service)
UNWIND relationships(p) AS e
RETURN DISTINCT startNode(e).name AS source,endNode(e).name AS target
ORDER BY source,target
""",dict(name=entry))
    return "|".join(r["source"]+">"+r["target"] for r in result["data"])

def gate(tenant,entry,error):
    rows=run(tenant,GATE,dict(entry_service=entry,error_code=error))["data"]
    if not rows:return dict(verdict="NO_PLAYBOOK",reason="",playbook_id="")
    if len(rows)!=1:raise ValueError("Multiple active playbooks; memory requires repair")
    row=rows[0]
    if row["decision_status"]!="ACTIVE":
        verdict="REJECTED_STALE_POLICY"
        reason=f"Playbook {row['playbook_id']} relies on Decision {row['required_decision_id']}, which is no longer ACTIVE."
    elif "|".join(sorted(row["live_dependencies"]))!=row["expected_topology_hash"]:
        verdict="REJECTED_TOPOLOGY_DRIFT";reason="Upstream dependencies changed."
    else:
        details=run(tenant,"MATCH (p:Playbook {id:$id}) RETURN p.topology_edges_hash AS edges",dict(id=row["playbook_id"]))["data"][0]
        verdict="VALID_REPLAY" if details["edges"]==edge_hash(tenant,entry) else "REJECTED_TOPOLOGY_DRIFT"
        reason="" if verdict=="VALID_REPLAY" else "Dependency edges changed, even though reachable names match."
    if verdict=="VALID_REPLAY":
        bounds=run(tenant,"MATCH (d:Decision {id:$id}) RETURN d.config_bounds_json AS bounds",
                   dict(id=row["required_decision_id"]))["data"][0]["bounds"]
        if bounds!=row["required_config_bounds"]:
            verdict="REJECTED_CONFIG_BOUNDS";reason="Structured policy bounds changed."
    return dict(row,verdict=verdict,reason=reason)

def steps(tenant,pbid):
    return run(tenant,"""
MATCH (:Playbook {id:$id})-[r:HAS_STEP]->(s:ActionStep)
RETURN s.tool_args_json AS args,s.mcp_tool AS tool,s.post_error_rate AS post_error_rate
ORDER BY r.order
""",dict(id=pbid))["data"]

def compile_verified_playbook(tenant,rid):
    state=run(tenant,"MATCH (r:InvestigationRun {run_id:$id}) RETURN properties(r) AS r",dict(id=rid))["data"][0]["r"]
    if state["post_incident_error_rate"]>=.01:raise ValueError("Cannot compile an unverified run")
    existing=run(tenant,"MATCH (p:Playbook {compiled_from_run:$id}) RETURN p.id AS id",dict(id=rid))["data"]
    if existing:return existing[0]["id"]
    rows=run(tenant,"""
MATCH (:InvestigationRun {run_id:$id})-[:EXECUTED_STEP]->(t:ToolTrace {tool_name:'apply_verified_mutation_to_prod'})
WHERE t.verified=true RETURN t.tool_args_json AS args,t.result_json AS result
ORDER BY t.step_num
""",dict(id=rid))["data"]
    actions=[]
    for row in rows:
        result=json.loads(row["result"])["data"][0]
        if result["post_error_rate"]<.01 and result["post_error_rate"]<result["pre_error_rate"]:
            actions.append(dict(args=row["args"],pre=result["pre_error_rate"],post=result["post_error_rate"]))
    if not actions:raise ValueError("No exact successful production mutations to compile")
    args=json.loads(actions[-1]["args"]);decision=args["justifying_decision_id"]
    bounds=run(tenant,"MATCH (d:Decision {id:$id,status:'ACTIVE'}) RETURN d.config_bounds_json AS bounds",dict(id=decision))["data"]
    if not bounds:raise ValueError("Governing policy changed before compilation")
    old=gate(tenant,state["entry_service"],state["error_code"])
    old_id=old["playbook_id"];version=int(old.get("version",0))+1
    pbid="PB-"+str(uuid.uuid4())+f"-v{version}"
    entries=[dict(id=pbid+f"-STEP-{i}",order=i,args=a["args"],pre=a["pre"],post=a["post"])
             for i,a in enumerate(actions,1)]
    run(tenant,"""
MATCH (r:InvestigationRun {run_id:$rid})
MERGE (sig:SymptomSignature {id:$sig,error_code:$error,entry_service:$entry})
CREATE (pb:Playbook {id:$id,version:$version,status:'ACTIVE',required_decision_id:$decision,
 topology_hash:$hash,topology_edges_hash:$edges,required_config_bounds:$bounds,
 postcondition_expr:'error_rate < 0.01 AND p99_latency_ms < 500',
 created_at:$now,verified_runs:1,compiled_from_run:$rid})
CREATE (sig)-[:HAS_PLAYBOOK]->(pb)
SET r.playbook_used_or_created=$id
WITH pb
UNWIND $steps AS step
CREATE (a:ActionStep {id:step.id,step_order:step.order,
 mcp_tool:'apply_verified_mutation_to_prod',tool_args_json:step.args,
 evidence_node_id:$decision,pre_error_rate:step.pre,post_error_rate:step.post})
CREATE (pb)-[:HAS_STEP {order:step.order}]->(a)
WITH DISTINCT pb
""" + ("""
MATCH (old:Playbook {id:$old})
SET old.status='SUPERSEDED'
CREATE (pb)-[:SUPERSEDES_PLAYBOOK {reason:$reason,timestamp:$now}]->(old)
RETURN pb.id AS id
""" if old_id else "RETURN pb.id AS id"),dict(rid=rid,id=pbid,version=version,decision=decision,hash=topology_hash(tenant,state["entry_service"]),
         edges=edge_hash(tenant,state["entry_service"]),bounds=bounds[0]["bounds"],now=int(time.time()),
         sig="SIG-V2-"+state["entry_service"]+"-"+state["error_code"],error=state["error_code"],
         entry=state["entry_service"],steps=entries,old=old_id,
         reason=state.get("rejection_reason") or "New verified procedure"))
    return pbid