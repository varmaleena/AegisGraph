"""Stage 4 HTTP contract checks against real FalkorDB; beta is disposable."""
import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.db import operation
from backend.seed_graph import seed
api=TestClient(app)
@pytest.fixture(autouse=True)
def reset_beta():
    seed("tenant_beta",reset=True)
    yield
    seed("tenant_beta",reset=True)
def post(path,**kw):
    return api.post(path,json={"tenant":"tenant_beta",**kw})
def packets(response):
    return [(part.splitlines()[0][7:],json.loads(part.splitlines()[1][6:]))
            for part in response.text.strip().split("\n\n")]
def test_session_reload_reset_and_full_stream():
    old=api.get("/session?tenant=tenant_beta").json()["session_id"]
    assert post("/ingest-contradiction").status_code==200
    r=post("/chat")
    assert r.status_code==200
    events=packets(r)
    assert events[0][0]=="session" and events[-1][0]=="done"
    assert any("compiled" in data.get("summary","") for kind,data in events)
    saved=api.get("/session?tenant=tenant_beta").json()
    assert saved["session_id"]==old
    assert len(saved["events"])==len([1 for k,d in events if k=="step"])+1
    assert post("/reset-session").json()["session_id"]!=old
    replay=packets(post("/chat"))
    assert [d["agent"] for k,d in replay if k=="step"]==["User","Commander","Commander","System"]
def test_error_stream_has_no_done_and_lock_releases():
    events=packets(post("/chat"))
    assert events[-1][0]=="error"
    assert not any(k=="done" for k,d in events)
    assert post("/reset-session").status_code==200
def test_invalid_tenants_actions_targets_and_busy():
    assert api.get("/graph?tenant=unknown").status_code==400
    assert post("/simulate",action="destroy").status_code==422
    assert post("/simulate",target_service="missing").status_code==400
    assert api.post("/chat",json={"tenant":"vortexpay_sandbox"}).status_code==422
    with operation("tenant_beta"):
        assert post("/reset-session").status_code==409
def test_graph_shadow_and_cors():
    graph=api.get("/graph?tenant=tenant_beta").json()
    assert len(graph["nodes"])==21 and len(graph["links"])==27
    r=post("/simulate",action="isolate")
    assert r.json()["trace"]["data"][0]["impacted_tier1_services"]==3
    shadow=api.get("/graph?tenant=tenant_beta_sandbox")
    assert shadow.status_code==200
    r=api.options("/chat",headers={"Origin":"http://localhost:3001","Access-Control-Request-Method":"POST"})
    assert r.headers["access-control-allow-origin"]=="http://localhost:3001"
