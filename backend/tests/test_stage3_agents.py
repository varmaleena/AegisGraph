"""Stage 3: real graph-backed coordination and procedural replay.
Resets only synthetic tenant_beta before and after each test.
"""
import json
import subprocess
import sys
import pytest
from backend import agents
from backend.db import run, operation, BusyError
from backend.seed_graph import seed

T="tenant_beta"

@pytest.fixture(autouse=True)
def clean_tenant():
    seed(T,reset=True)
    yield
    seed(T,reset=True)

def first_session():
    with operation(T):
        agents.inject_policy(T)
        sid=agents.new_session(T)
        output=list(agents.investigate(T,sid))
    return sid,output

def incident_status(sid):
    return run(T,"MATCH (:Session {id:$sid})-[:INVESTIGATED]->(i:Incident) RETURN i.status AS status",
               dict(sid=sid))["data"][0]["status"]

def test_session_one_persists_handoffs_verified_fix_and_playbook():
    sid,output=first_session()
    assert incident_status(sid)=="RESOLVED"
    assert {e["agent"] for e in output}>={"Scribe","Navigator","Commander"}
    assert agents.events(T,sid)==output
    health=run(T,"MATCH (s:Service {name:'token-auth-service'}) RETURN properties(s) AS p")["data"][0]["p"]
    assert health["status"]=="HEALTHY"
    assert health["timeout_ms"]==150 and health["circuit_breaker"] and health["max_pool_size"]>=100
    tasks=run(T, """
MATCH (:Session {id:$sid})-[:INVESTIGATED]->(i)-[r:HAS_TASK]->(t)
RETURN count(r) AS links, count(DISTINCT t) AS tasks
""",dict(sid=sid))["data"][0]
    assert tasks=={"links":3,"tasks":3}
    evidence=run(T, """
MATCH (:Session {id:$sid})-[:INVESTIGATED]->(:Incident)-[:HAS_HYPOTHESIS]->
 (h:Hypothesis {agent:'Navigator'})-[:POINTS_TO_PR]->(pr:PR)
RETURN pr.id AS id
""",dict(sid=sid))["data"]
    assert evidence==[{"id":"PR-409"}]
    playbook=agents.tools.lookup_procedural_playbook("ERR_AUTH_POOL_EXHAUSTED","checkout-api",T)["data"]
    assert len(playbook)==1 and playbook[0]["tool_name"]=="remediate_auth_pool"
    assert playbook[0]["prior_successes"]==1

def test_second_session_replays_memory_in_a_fresh_process():
    sid,_=first_session()
    # A different interpreter cannot use previous agent variables or module caches.
    code="""
import json
from backend.db import operation
from backend import agents
with operation('tenant_beta'):
    sid=agents.new_session('tenant_beta')
    events=list(agents.investigate('tenant_beta',sid))
print(json.dumps({'sid':sid,'events':events}))
"""
    proc=subprocess.run([sys.executable,"-X","utf8","-c",code],capture_output=True,text=True,
                        encoding="utf-8",check=True,timeout=30)
    result=json.loads(proc.stdout)
    assert result["sid"]!=sid
    assert incident_status(result["sid"])=="RESOLVED"
    assert [e["agent"] for e in result["events"]]==["Commander","Commander","System"]
    assert agents.events(T,sid)  # resetting chat did not erase historical session
    assert agents.tools.lookup_procedural_playbook("ERR_AUTH_POOL_EXHAUSTED","checkout-api",T)["data"][0]["prior_successes"]==2

def test_missing_policy_fails_and_never_compiles_memory():
    with operation(T):
        sid=agents.new_session(T)
        with pytest.raises(ValueError,match="Inject the Slack"):
            list(agents.investigate(T,sid))
    assert incident_status(sid)=="FAILED"
    assert agents.tools.lookup_procedural_playbook("ERR_AUTH_POOL_EXHAUSTED","checkout-api",T)["data"]==[]
    assert "Inject the Slack" in agents.events(T,sid)[-1]["summary"]

@pytest.mark.parametrize("field,value,expected",[
    ("mcp_tool","execute_shell","disallowed tool"),
    ("tool_args_json",'{"service_name":"ledger-db-proxy"}',"arguments"),
    ("expected_outcome","UNEXPECTED","postcondition"),
])
def test_untrusted_playbook_is_rejected_without_counting_success(field,value,expected):
    first_session()
    # Field comes only from the above fixed test cases, never user input.
    run(T,f"MATCH (s:ActionStep {{id:'STEP-AUTH-1'}}) SET s.{field}=$value RETURN s.id AS id",
        dict(value=value))
    with operation(T):
        sid=agents.new_session(T)
        with pytest.raises(ValueError,match=expected):
            list(agents.investigate(T,sid))
    assert incident_status(sid)=="FAILED"
    assert agents.tools.lookup_procedural_playbook("ERR_AUTH_POOL_EXHAUSTED","checkout-api",T)["data"][0]["prior_successes"]==1
    if field!="expected_outcome":
        state=run(T,"MATCH (s:Service {name:'token-auth-service'}) RETURN s.circuit_breaker AS cb")["data"][0]
        assert not state["cb"]

def test_graph_lease_rejects_competing_operation_and_releases_after_failure():
    with pytest.raises(RuntimeError):
        with operation(T):
            with pytest.raises(BusyError):
                with operation(T):
                    pass
            raise RuntimeError("Intentional failure")
    with operation(T):
        assert agents.active_session(T).startswith("SES-")
