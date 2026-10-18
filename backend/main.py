import json
import logging
import os
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from redis.exceptions import RedisError
from backend.db import run, operation, BusyError, GRAPHS
from backend import agents
from backend import mcp_tools as tools

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="AegisGraph", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS","http://localhost:3001").split(","),
                  allow_methods=["GET","POST"], allow_headers=["Content-Type"])
Tenant = Literal["vortexpay_prod","tenant_beta"]

class Request(BaseModel):
    tenant: Tenant = "vortexpay_prod"
class ChatRequest(Request):
    message: str = Field(default="Investigate ERR_AUTH_POOL_EXHAUSTED in checkout-api", max_length=2000)
class SimRequest(Request):
    target_service: str = "token-auth-service"
    action: Literal["isolate","rollback"] = "isolate"

@app.exception_handler(RedisError)
async def database_unavailable(request, exc):
    logging.error("Database request failed: %s",type(exc).__name__)
    return JSONResponse(status_code=503,content={"detail":"FalkorDB unavailable. No offline state is available."})

@app.exception_handler(BusyError)
async def busy(request, exc):
    return JSONResponse(status_code=409,content={"detail":str(exc)})

@app.exception_handler(ValueError)
async def invalid(request, exc):
    return JSONResponse(status_code=400,content={"detail":str(exc)})

@app.get("/health")
def health():
    return run("vortexpay_prod","MATCH (r:Runtime {id:'runtime'}) RETURN r.id AS id")

@app.get("/graph")
def get_graph(tenant: str = "vortexpay_prod"):
    if tenant not in GRAPHS:
        raise HTTPException(400,"Unknown graph")
    nodes = run(tenant,"MATCH (n) RETURN n.id AS id, labels(n)[0] AS label, properties(n) AS properties")
    links = run(tenant,"MATCH (a)-[r]->(b) RETURN a.id AS source, b.id AS target, type(r) AS type")
    return dict(nodes=nodes["data"],links=links["data"],graph=tenant)

@app.get("/session")
def get_session(tenant: Tenant = "vortexpay_prod"):
    with operation(tenant):
        sid=agents.active_session(tenant)
        return dict(session_id=sid,events=agents.events(tenant,sid))

@app.post("/reset-session")
def reset_session(req: Request):
    with operation(req.tenant):
        from backend.v2_api import cleanup_failed_runs
        cleanup_failed_runs(req.tenant)
        return dict(session_id=agents.new_session(req.tenant),events=[])

@app.post("/ingest-contradiction")
def ingest(req: Request):
    with operation(req.tenant):
        return agents.inject_policy(req.tenant)

@app.post("/simulate")
def simulate(req: SimRequest):
    with operation(req.tenant):
        trace=tools.simulate_action_in_shadow_graph(req.target_service,req.action,req.tenant)
        return agents.event(req.tenant,agents.active_session(req.tenant),"Navigator",
            f"Shadow {req.action}: {trace['data'][0]['impacted_tier1_services']} Tier-1 services lose connectivity.",trace)

@app.post("/chat")
def chat(req: ChatRequest):
    # Fail before HTTP headers if FalkorDB cannot be reached.
    run(req.tenant,"MATCH (r:Runtime {id:'runtime'}) RETURN r.id AS id")
    def stream():
        try:
            with operation(req.tenant):
                sid=agents.active_session(req.tenant)
                yield "event: session\ndata: "+json.dumps({"session_id":sid})+"\n\n"
                yield "event: step\ndata: "+json.dumps(agents.event(req.tenant,sid,"User",req.message))+"\n\n"
                # Bounded incident agent, not a general-purpose chat assistant.
                for item in agents.investigate(req.tenant,sid):
                    yield "event: step\ndata: "+json.dumps(item)+"\n\n"
                yield "event: done\ndata: {}\n\n"
        except Exception as exc:
            yield "event: error\ndata: "+json.dumps({"detail":str(exc)})+"\n\n"
    return StreamingResponse(stream(),media_type="text/event-stream",
        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})
# V2 endpoints coexist with legacy routes; the upgraded UI uses /api/runs.
from backend.v2_api import router as v2_router
app.include_router(v2_router)
