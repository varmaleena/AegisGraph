import asyncio
import json
import subprocess
import sys
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.seed_graph import seed
from backend import orchestrator as o, v2_tools as tools
from backend.v2_policy import ensure_policy
from backend.db import run
from backend.tests.test_v2_workflow import FixtureModel
api=TestClient(app)
T="tenant_beta"
@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER","gemini")
    monkeypatch.setenv("AEGIS_TENANT",T)
    seed(T,reset=True)
    yield
    seed(T,reset=True)

def test_placeholder_key_is_not_reported_as_configured(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY","dummy")
    assert api.get("/api/evidence?tenant="+T).json()["model"]["configured"] is False

def test_no_key_rejects_without_creating_run(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY",raising=False)
    response=api.post("/api/runs",json={"tenant":T})
    assert response.status_code==400
    assert api.get("/api/evidence?tenant="+T).json()["runs"]==[]
    assert api.get("/api/evidence?tenant="+T).json()["model"]["configured"] is False

def test_http_stream_and_resume_are_graph_backed(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY","test-fixture-not-live")
    import backend.model_client
    monkeypatch.setattr(o,"ModelClient",FixtureModel)
    response=api.post("/api/runs",json={"tenant":T,"interrupt_at_step":3})
    assert "event: CRASH_SIMULATED" in response.text
    evidence=api.get("/api/evidence?tenant="+T).json()
    rid=evidence["runs"][0]["run_id"]
    result=api.post(f"/api/runs/{rid}/resume?tenant="+T)
    assert "event: done" in result.text
    assert o.load(T,rid)["status"]=="COMPLETED"

def test_fresh_process_rehydrates_step_four(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY","test-fixture-not-live")
    rid=o.begin(T,"Restart proof",interrupt_at_step=3)
    async def start():return [e async for e in o.execute(T,rid,model=FixtureModel())]
    asyncio.run(start())
    code="""
import asyncio,json,sys
from backend import orchestrator as o
from backend.tests.test_v2_workflow import FixtureModel
async def execute():
 return [e async for e in o.execute('tenant_beta',sys.argv[1],model=FixtureModel())]
print(json.dumps(asyncio.run(execute())))
"""
    result=subprocess.run([sys.executable,"-X","utf8","-c",code,rid],capture_output=True,
                          text=True,encoding="utf-8",timeout=60,check=True)
    assert json.loads(result.stdout)[-1]["kind"]=="done"
    state=o.load(T,rid)
    assert state["current_step"]==6 and state["llm_calls"]==6

def test_verified_mutation_response_is_repeatable_and_telemetry_stays_derived():
    ensure_policy(T)
    args=dict(service_name="token-auth-service",timeout_ms=150,max_pool_size=120,circuit_breaker=True)
    tools.simulate_config_mutation_in_sandbox(**args)
    a=tools.apply_verified_mutation_to_prod(**args,justifying_decision_id="DEC-02",justifying_pr_id="PR-409")
    b=tools.apply_verified_mutation_to_prod(**args,justifying_decision_id="DEC-02",justifying_pr_id="PR-409")
    assert b["idempotent_replay"]
    assert a["data"]==b["data"]

def test_api_rejects_bad_crash_step_and_cross_tenant_resume():
    assert api.post("/api/runs",json={"tenant":T,"interrupt_at_step":0}).status_code==422
    assert api.post("/api/runs/missing/resume?tenant=vortexpay_prod").status_code==400

def test_resume_after_verified_mutation_only_finishes_compilation(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY","test-fixture-not-live")
    rid=o.begin(T,"Interrupt after apply",interrupt_at_step=6)
    async def execute():return [e async for e in o.execute(T,rid,model=FixtureModel())]
    assert asyncio.run(execute())[-1]["kind"]=="CRASH_SIMULATED"
    assert o.load(T,rid)["post_incident_error_rate"]<.01
    assert asyncio.run(execute())[-1]["kind"]=="done"
    state=o.load(T,rid)
    assert state["current_step"]==6 and state["llm_calls"]==6


def test_nested_provider_error_is_reported_without_secret(monkeypatch):
    from openai import RateLimitError
    import httpx
    monkeypatch.setenv("GEMINI_API_KEY","test-fixture-not-live")
    class Limited(FixtureModel):
        async def choose(self,messages,schemas):
            response=httpx.Response(429,request=httpx.Request("POST","https://provider.invalid"))
            raise ExceptionGroup("MCP wrapper",[RateLimitError("never-log-this-fixture-secret",response=response,body={})])
    rid=o.begin(T,"Quota interruption")
    async def execute():return [e async for e in o.execute(T,rid,model=Limited())]
    assert asyncio.run(execute())[-1]["kind"]=="error"
    state=o.load(T,rid)
    assert "HTTP 429" in state["last_error"]
    assert "never-log-this-fixture-secret" not in state["last_error"]
    assert state["current_step"]==0 and state["status"]=="INTERRUPTED_CRASH"
