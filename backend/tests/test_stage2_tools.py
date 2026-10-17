"""Stage 2 integration suite. Resets synthetic tenant_beta before/after tests."""
import json
import time
import pytest
from backend.db import operation, run
from backend.seed_graph import seed, ANCHOR
from backend import mcp_tools as t

TENANT = "tenant_beta"

@pytest.fixture(scope="module",autouse=True)
def fixture_graph():
    seed(TENANT,reset=True)
    yield
    seed(TENANT,reset=True)

def test_root_cause_returns_real_shortest_path_and_owner():
    result=t.trace_root_cause_and_blast_radius("checkout-api",TENANT)
    row=result["data"][0]
    assert row["suspect_pr"]=="PR-409"
    assert row["author_name"]=="Elena Rostova"
    assert row["owning_team"]=="Identity-Platform"
    assert row["dependency_path"]==["checkout-api","token-auth-service"]
    assert row["downstream_blast_radius"]==["web-storefront"]
    assert "PR-409" in result["highlighted_node_ids"]

def test_pagerank_orders_all_eight_services():
    result=t.compute_service_criticality_pagerank(TENANT)
    scores=[r["pagerank_score"] for r in result["data"]]
    assert len(scores)==8
    assert scores==sorted(scores,reverse=True)
    assert result["data"][0]["service_name"]=="redis-session-cluster"
    assert "algo.pageRank" in result["cypher_executed"]

def test_bitemporal_revision_and_idempotent_delivery():
    known_before=int(time.time())-1
    assert t.resolve_bitemporal_policy("token-auth-service",TENANT)["data"][0]["active_decision_id"]=="DEC-01"
    args=("token-auth-service","auth-pool-timeout","Sarah Chen",
          "150ms with strict circuit breaking","SLACK-882","Thread starvation",
          ANCHOR-7200,TENANT,"DEC-02")
    with operation(TENANT):
        result=t.ingest_and_supersede_decision(*args)
        t.ingest_and_supersede_decision(*args)
    assert result["data"][0]["superseded_decision"]=="DEC-01"
    current=t.resolve_bitemporal_policy("token-auth-service",TENANT)["data"][0]
    assert current["active_decision_id"]=="DEC-02"
    assert current["superseded_history"][0]["id"]=="DEC-01"
    past=t.resolve_bitemporal_policy("token-auth-service",TENANT,valid_at=ANCHOR-86400)["data"][0]
    assert past["active_decision_id"]=="DEC-01"
    as_known=t.resolve_bitemporal_policy("token-auth-service",TENANT,
        valid_at=ANCHOR,known_at=known_before)["data"][0]
    assert as_known["current_source"]=="DOC-101"
    assert run(TENANT,"MATCH (d:Decision {id:'DEC-02'}) RETURN count(d) AS total")["data"][0]["total"]==1

def test_playbook_lookup_returns_ordered_persisted_tool_arguments():
    assert t.lookup_procedural_playbook("ERR_AUTH_POOL_EXHAUSTED","checkout-api",TENANT)["data"]==[]
    run(TENANT, """
CREATE (sig:SymptomSignature {id:'TEST-SIG',error_code:'TEST',affected_service:'checkout-api'})
CREATE (pb:Playbook {id:'TEST-PB',name:'Test ordered steps',success_count:2})
CREATE (sig)-[:TRIGGERS_PLAYBOOK]->(pb)
WITH pb
UNWIND [2,1] AS ord
CREATE (s:ActionStep {id:'TEST-STEP-'+toString(ord),step_order:ord,mcp_tool:'remediate_auth_pool',
 tool_args_json:'{"service_name":"token-auth-service"}',expected_outcome:'HEALTHY'})
CREATE (pb)-[:HAS_STEP {order:ord}]->(s) RETURN s.id AS id
""")
    steps=t.lookup_procedural_playbook("TEST","checkout-api",TENANT)["data"]
    assert [s["step_order"] for s in steps]==[1,2]
    assert json.loads(steps[0]["tool_args"])=={"service_name":"token-auth-service"}

def test_shadow_isolation_and_repeated_clone_preserve_production():
    query="MATCH (s:Service {name:'token-auth-service'}) RETURN properties(s) AS props"
    before=run(TENANT,query)["data"]
    with operation(TENANT):
        isolate=t.simulate_action_in_shadow_graph("token-auth-service","isolate",TENANT)
        rollback=t.simulate_action_in_shadow_graph("token-auth-service","rollback",TENANT)
    assert isolate["data"][0]["lost_connectivity"]==["checkout-api","payment-orchestrator","web-storefront"]
    assert not isolate["data"][0]["safe"]
    assert rollback["data"][0]["safe"]
    assert rollback["data"][0]["lost_connectivity"]==[]
    assert run(TENANT,query)["data"]==before
    assert run(TENANT,"MATCH ()-[r:DEPENDS_ON]->() RETURN count(r) AS n")["data"][0]["n"]==8

def test_missing_target_and_unsupported_action_are_rejected():
    with pytest.raises(ValueError,match="does not exist"):
        t.simulate_action_in_shadow_graph("missing","isolate",TENANT)
    with pytest.raises(ValueError):
        t.simulate_action_in_shadow_graph("token-auth-service","delete everything",TENANT)

def test_parameterized_service_name_cannot_inject_cypher():
    assert t.trace_root_cause_and_blast_radius("x'}) DETACH DELETE n //",TENANT)["data"]==[]
    assert run(TENANT,"MATCH (s:Service) RETURN count(s) AS n")["data"][0]["n"]==8
