"""Real graph + real MCP tests; model responses below are explicit test fixtures."""
import asyncio
import json
import pytest
from backend.seed_graph import seed
from backend import orchestrator as o, playbook_engine as memory
from backend.db import run
from backend.simulator import recalculate_graph_telemetry,inject_fault
from backend.v2_policy import ensure_policy
from backend import v2_tools as tools

T="tenant_beta"
@pytest.fixture(autouse=True)
def fixture(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY","fixture-only-never-sent")
    monkeypatch.setenv("LLM_PROVIDER","gemini")
    monkeypatch.setenv("AEGIS_TENANT",T)
    seed(T,reset=True)
    yield
    seed(T,reset=True)

class FixtureModel:
    """Not an agent implementation: canned provider responses for integration tests."""
    measurement_source="TEST_FIXTURE"
    def __init__(self,secure=False):
        config=dict(service_name="token-auth-service",timeout_ms=450 if secure else 150,
                    max_pool_size=120,circuit_breaker=True)
        self.calls=[
          ("inspect_service_telemetry_and_frontier",dict(service_name="checkout-api")),
          ("traverse_dependency_SingleOrMultiHop",dict(service_name="checkout-api",max_hops=3)),
          ("inspect_recent_prs_and_authors",dict(service_name="token-auth-service")),
          ("query_bitemporal_policies",dict(service_name="token-auth-service")),
          ("simulate_config_mutation_in_sandbox",config),
          ("apply_verified_mutation_to_prod",dict(config,justifying_decision_id="DEC-03" if secure else "DEC-02",justifying_pr_id="PR-409"))]
    async def choose(self,messages,schemas):
        completed=sum(m.get("role")=="tool" for m in messages)
        name,args=self.calls[completed]
        return dict(role="assistant",tool_calls=[dict(id=f"fixture-{completed}",type="function",
                    function=dict(name=name,arguments=json.dumps(args)))]),0
    async def close(self):pass

def execute(rid,secure=False):
    async def collect():return [e async for e in o.execute(T,rid,model=FixtureModel(secure))]
    return asyncio.run(collect())

def test_physics_rejects_direct_status_fix_and_requires_safe_receipt(monkeypatch):
    ensure_policy(T)
    initial=tools.telemetry(T)["data"]
    checkout=next(s for s in initial if s["name"]=="checkout-api")
    assert .5<checkout["error_rate"]<.65
    with pytest.raises(ValueError,match="receipt"):
        tools.apply_verified_mutation_to_prod("token-auth-service",150,120,True,"DEC-02","PR-409")
    with pytest.raises(ValueError,match="POLICY"):
        tools.simulate_config_mutation_in_sandbox("token-auth-service",5000,120,True)
    tools.simulate_config_mutation_in_sandbox("token-auth-service",150,120,True)
    result=tools.apply_verified_mutation_to_prod("token-auth-service",150,120,True,"DEC-02","PR-409")
    assert result["data"][0]["post_error_rate"]<.01
    before=tools.telemetry(T)["data"]
    recalculate_graph_telemetry(T)
    assert tools.telemetry(T)["data"]==before

def test_crash_resume_replay_then_stale_policy_recompilation():
    rid=o.begin(T,"Checkout authentication pool exhausted",interrupt_at_step=3)
    assert execute(rid)[-1]["kind"]=="CRASH_SIMULATED"
    state=o.load(T,rid)
    assert state["status"]=="INTERRUPTED_CRASH" and state["current_step"]==3
    assert len(json.loads(state["messages_checkpoint_json"]))==8
    assert execute(rid)[-1]["kind"]=="done"
    state=o.load(T,rid)
    assert state["status"]=="COMPLETED" and state["current_step"]==6
    pb1=state["playbook_used_or_created"]
    gate=memory.gate(T,"checkout-api","ERR_AUTH_POOL_EXHAUSTED")
    assert gate["verdict"]=="VALID_REPLAY"
    rid2=o.begin(T,"Recurrence")
    assert o.load(T,rid2)["execution_mode"]=="WARM_REPLAY"
    assert execute(rid2)[-1]["kind"]=="done"
    warm=o.load(T,rid2)
    assert warm["llm_calls"]==0 and warm["mcp_tool_calls"]==1
    ensure_policy(T,security=True)
    rid3=o.begin(T,"Incident after security directive")
    assert o.load(T,rid3)["precondition_verdict"]=="REJECTED_STALE_POLICY"
    assert execute(rid3,secure=True)[-1]["kind"]=="done"
    pb2=o.load(T,rid3)["playbook_used_or_created"]
    link=run(T,"MATCH (n:Playbook {id:$new})-[:SUPERSEDES_PLAYBOOK]->(old:Playbook {id:$old}) RETURN n.version AS v,old.status AS status",
             dict(new=pb2,old=pb1))["data"][0]
    assert link==dict(v=2,status="SUPERSEDED")
    assert memory.gate(T,"checkout-api","ERR_AUTH_POOL_EXHAUSTED")["verdict"]=="VALID_REPLAY"

def test_topology_rewire_with_same_reachable_names_rejects_playbook():
    rid=o.begin(T,"Original");execute(rid)
    run(T,"""MATCH (c:Service {name:'checkout-api'})-[r:DEPENDS_ON]->(a:Service {name:'token-auth-service'})
DELETE r""")
    assert memory.gate(T,"checkout-api","ERR_AUTH_POOL_EXHAUSTED")["verdict"]=="REJECTED_TOPOLOGY_DRIFT"

def test_cyclic_topology_does_not_write_partial_telemetry():
    before=tools.telemetry(T)["data"]
    run(T,"MATCH (a:Service {name:'redis-session-cluster'}),(b:Service {name:'checkout-api'}) CREATE (a)-[:DEPENDS_ON]->(b)")
    with pytest.raises(ValueError,match="cycle"):recalculate_graph_telemetry(T)
    assert tools.telemetry(T)["data"]==before