import asyncio
import json
from typing import Literal
from fastapi import APIRouter,HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel,Field
from backend.db import run,operation
from backend import orchestrator
from backend.model_client import public_settings
from backend.simulator import migrate_physics
from backend.v2_policy import ensure_policy
from backend.v2_tools import telemetry

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
    if state["status"] not in ("IN_PROGRESS","INTERRUPTED_CRASH"):raise HTTPException(409,"Run cannot resume")
    if not public_settings()["configured"]:raise HTTPException(400,"Configure your model API key first")
    return stream(tenant,rid)

@router.post("/runs/{rid}/cancel")
def cancel(rid:str,tenant:Tenant="vortexpay_prod"):
    with operation(tenant):
        state=orchestrator.load(tenant,rid)
        if state["status"]!="INTERRUPTED_CRASH":raise HTTPException(409,"Only interrupted runs can be cancelled")
        orchestrator.update(tenant,rid,status="CANCELLED")
        return dict(status="CANCELLED")

@router.post("/security-policy")
def security(tenant:Tenant="vortexpay_prod"):
    with operation(tenant):
        migrate_physics(tenant)
        return ensure_policy(tenant,security=True)

@router.get("/evidence")
def evidence(tenant:Tenant="vortexpay_prod"):
    rows=run(tenant,"""
MATCH (r:InvestigationRun)
RETURN r.run_id AS run_id,r.execution_mode AS execution_mode,r.status AS status,
 r.current_step AS current_step,r.llm_calls AS llm_calls,r.mcp_tool_calls AS mcp_tool_calls,
 r.total_tokens AS total_tokens,r.falkordb_compute_ms AS falkordb_compute_ms,
 r.wall_clock_ms AS wall_clock_ms,r.pre_incident_error_rate AS pre_incident_error_rate,
 r.post_incident_error_rate AS post_incident_error_rate,r.playbook_used_or_created AS playbook,
 r.precondition_verdict AS precondition_verdict,r.rejection_reason AS rejection_reason,
 r.last_error AS last_error,r.provider AS provider,r.model AS model,r.measurement_source AS measurement_source
ORDER BY r.created_at
""")
    return dict(runs=rows["data"],services=telemetry(tenant)["data"],model=public_settings())