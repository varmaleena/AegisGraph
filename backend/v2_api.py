import asyncio
import json
import time
from typing import Literal
from fastapi import APIRouter,HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel,Field
from backend.db import run,operation,collect_queries
from backend import orchestrator
from backend.model_client import public_settings
from backend.simulator import migrate_physics
from backend.v2_policy import ensure_policy
from backend.v2_tools import telemetry
from backend import agents, playbook_engine
from backend.mcp_tools import simulate_action_in_shadow_graph

router=APIRouter(prefix="/api")
Tenant=Literal["vortexpay_prod","tenant_beta"]
class IncidentRequest(BaseModel):
    tenant:Tenant="vortexpay_prod"
    message:str=Field(default="ERR_AUTH_POOL_EXHAUSTED in checkout-api",max_length=2000)
    entry_service:Literal["checkout-api","payment-orchestrator","web-storefront"]="checkout-api"
    error_code:str=Field(default="ERR_AUTH_POOL_EXHAUSTED",max_length=100)
    interrupt_at_step:int|None=Field(default=None,ge=1,le=15)

async def events(tenant,rid):
    yield "event: run"+chr(10)+"data: "+json.dumps(dict(run_id=rid))+chr(10)*2
    async for item in orchestrator.execute(tenant,rid):
        yield "event: "+item["kind"]+chr(10)+"data: "+json.dumps(item)+chr(10)*2

def stream(tenant,rid):
    return StreamingResponse(events(tenant,rid),media_type="text/event-stream",
        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@router.post("/runs")
async def start(req:IncidentRequest):
    rid=await asyncio.to_thread(orchestrator.begin,req.tenant,req.message,req.entry_service,
                                req.error_code,req.interrupt_at_step)
    return stream(req.tenant,rid)

@router.post("/runs/{rid}/resume")
def resume(rid:str,tenant:Tenant="vortexpay_prod"):
    state=orchestrator.load(tenant,rid)
    if state["status"] not in ("IN_PROGRESS","INTERRUPTED_CRASH","INTERRUPTED_ERROR"):raise HTTPException(409,"Run cannot resume")
    if not public_settings()["configured"]:raise HTTPException(400,"Configure your model API key first")
    return stream(tenant,rid)

@router.post("/runs/{rid}/cancel")
def cancel(rid:str,tenant:Tenant="vortexpay_prod"):
    with operation(tenant):
        state=orchestrator.load(tenant,rid)
        if state["status"] not in ("INTERRUPTED_CRASH","INTERRUPTED_ERROR"):raise HTTPException(409,"Only interrupted runs can be cancelled")
        orchestrator.update(tenant,rid,status="CANCELLED")
        cleanup_failed_runs(tenant)
        return dict(status="CANCELLED")

def cleanup_failed_runs(tenant):
    """Caller holds tenant lease. Never remove an active worker or useful checkpoint."""
    return run(tenant,"""
MATCH (r:InvestigationRun)
WHERE r.current_step=0 AND r.status IN ['CANCELLED','INTERRUPTED_CRASH','INTERRUPTED_ERROR']
 AND coalesce(r.worker_until,0)<$now
DETACH DELETE r
""",dict(now=int(time.time()*1000)))

class ScenarioRequest(BaseModel):
    tenant:Tenant="vortexpay_prod"
    security:bool=False

def scenario_stream(req,action):
    def generate():
        with operation(req.tenant):
            sid=agents.active_session(req.tenant)
            if action=="policy":
                with collect_queries() as queries:
                    migrate_physics(req.tenant)
                    ensure_policy(req.tenant,security=req.security)
                    gate=playbook_engine.gate(req.tenant,"checkout-api","ERR_AUTH_POOL_EXHAUSTED")
                trace=dict(data=[gate],graph=req.tenant,traces=queries,
                           cypher_executed="\n".join(q["cypher_executed"] for q in queries),
                           execution_time_ms=sum(q["execution_time_ms"] for q in queries),
                           highlighted_node_ids=["DEC-03" if req.security else "DEC-02"])
                traces=[trace]
            else:
                # V2 physics runs before the native snapshot, then again after isolation.
                migrate_physics(req.tenant)
                result=simulate_action_in_shadow_graph("token-auth-service","isolate",req.tenant)
                traces=result["traces"]
            for trace in traces:
                item=agents.event(req.tenant,sid,"Scribe" if action=="policy" else "Navigator",
                    ("Policy supersession and live playbook gate refreshed." if action=="policy" else
                     "Shadow isolation: "+trace["cypher_executed"].strip().splitlines()[0]),trace)
                yield "event: step\ndata: "+json.dumps(item)+"\n\n"
            yield "event: done\ndata: {}\n\n"
    return StreamingResponse(generate(),media_type="text/event-stream",
                             headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@router.post("/scenarios/policy")
def scenario_policy(req:ScenarioRequest):
    return scenario_stream(req,"policy")

@router.post("/scenarios/isolation")
def scenario_isolation(req:ScenarioRequest):
    return scenario_stream(req,"isolation")

@router.post("/security-policy")
def security(tenant:Tenant="vortexpay_prod"):
    with operation(tenant):
        migrate_physics(tenant)
        return ensure_policy(tenant,security=True)

@router.get("/evidence")
def evidence(tenant:Tenant="vortexpay_prod",sandbox:bool=False):
    rows=run(tenant,"""
MATCH (r:InvestigationRun)
RETURN r.run_id AS run_id,r.execution_mode AS execution_mode,r.status AS status,
 r.current_step AS current_step,r.llm_calls AS llm_calls,r.mcp_tool_calls AS mcp_tool_calls,
 r.total_tokens AS total_tokens,r.falkordb_compute_ms AS falkordb_compute_ms,
 r.wall_clock_ms AS wall_clock_ms,r.pre_incident_error_rate AS pre_incident_error_rate,
 r.post_incident_error_rate AS post_incident_error_rate,r.playbook_used_or_created AS playbook,
 r.precondition_verdict AS precondition_verdict,r.rejection_reason AS rejection_reason,
 r.last_error AS last_error,r.provider AS provider,r.model AS model,r.measurement_source AS measurement_source,
 r.provider_history_json AS provider_history_json,r.last_provider_attempts_json AS last_provider_attempts_json
ORDER BY r.created_at
""")
    graph_name=("vortexpay_sandbox" if tenant=="vortexpay_prod" else "tenant_beta_sandbox") if sandbox else tenant
    return dict(runs=rows["data"],services=telemetry(graph_name)["data"],model=public_settings(),
                graph=graph_name,gate=playbook_engine.gate(tenant,"checkout-api","ERR_AUTH_POOL_EXHAUSTED"))
