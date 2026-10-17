"""Stage 1 integration checks: requires the local synthetic FalkorDB fixture."""
import pytest
from backend.db import run
from backend.seed_graph import seed

@pytest.fixture(scope="module",autouse=True)
def clean_fixture():
    seed("tenant_beta",reset=True)
    yield
    seed("tenant_beta",reset=True)

def scalar(tenant, query, key):
    return run(tenant, query)["data"][0][key]

def test_fixture_entities_and_dependency_edges():
    for tenant in ("tenant_beta",):
        counts = {r["label"]: r["total"] for r in run(tenant,
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS total")["data"]}
        for label, total in {"Team":3, "Person":6, "Service":8, "PR":1,
                             "Document":1, "Decision":1, "Runtime":1}.items():
            assert counts[label] == total
        assert scalar(tenant,
            "MATCH (:Service)-[r:DEPENDS_ON]->(:Service) RETURN count(r) AS total","total") == 8
        assert scalar(tenant,
            "MATCH (:Team)-[r:OWNS]->(:Service) RETURN count(r) AS total","total") == 8
        decision = run(tenant, "MATCH (d:Decision {id:'DEC-01'}) RETURN properties(d) AS p")["data"][0]["p"]
        assert decision["status"] == "ACTIVE"
        assert decision["valid_to"] == decision["recorded_to"] == 0

def test_seeding_twice_does_not_duplicate_data():
    for tenant in ("tenant_beta",):
        before = scalar(tenant,"MATCH (n) RETURN count(n) AS total","total")
        seed(tenant)
        seed(tenant)
        assert scalar(tenant,"MATCH (n) RETURN count(n) AS total","total") == before

def test_tenant_graphs_are_isolated():
    marker = "stage1-isolation-check"
    try:
        run("tenant_beta", "CREATE (:Checkpoint {id:$id}) RETURN 1 AS ok", {"id":marker})
        assert run("vortexpay_prod",
            "MATCH (n:Checkpoint {id:$id}) RETURN n.id AS id", {"id":marker})["data"] == []
        assert len(run("tenant_beta",
            "MATCH (n:Checkpoint {id:$id}) RETURN n.id AS id", {"id":marker})["data"]) == 1
    finally:
        run("tenant_beta", "MATCH (n:Checkpoint {id:$id}) DELETE n", {"id":marker})

def test_query_metadata_is_from_database():
    result = run("vortexpay_prod","MATCH (s:Service) RETURN s.id AS id, [s.id] AS highlighted_node_ids")
    assert len(result["data"]) == 8
    assert isinstance(result["execution_time_ms"],float)
    assert result["execution_time_ms"] >= 0
    assert "checkout-api" in result["highlighted_node_ids"]
