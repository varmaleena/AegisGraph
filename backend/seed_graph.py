"""Deterministic synthetic fixture; safe to run repeatedly, reset is explicit."""
import argparse
from backend.db import graph, run, TENANTS

ANCHOR = 1792022400  # fixed synthetic timeline, 2026-10-15 UTC

def seed(tenant="vortexpay_prod", reset=False):
    if tenant not in TENANTS:
        raise ValueError("Invalid tenant")
    if reset:
        graph(tenant).delete()
    if run(tenant, "MATCH (r:Runtime {id:'runtime'}) RETURN r.id AS id")["data"]:
        from backend.simulator import migrate_physics
        migrate_physics(tenant)
        return
    teams = ["Core-Payments", "Identity-Platform", "Checkout-Experience"]
    people = [
        ("Sarah Chen", "Staff Engineer", teams[1]), ("Marcus Vance", "Senior SRE", teams[0]),
        ("Elena Rostova", "Backend Eng", teams[1]), ("Devon Brooks", "Frontend Lead", teams[2]),
        ("Priya Nair", "Security Architect", teams[1]), ("Alex Rivera", "DevOps", teams[0])]
    services = [
        ("web-storefront",1,teams[2]), ("checkout-api",1,teams[2]),
        ("payment-orchestrator",1,teams[0]), ("fraud-engine",2,teams[0]),
        ("ledger-db-proxy",1,teams[0]), ("token-auth-service",1,teams[1]),
        ("redis-session-cluster",1,teams[1]), ("notification-worker",2,teams[0])]
    edges = [
        ("web-storefront","checkout-api"), ("checkout-api","payment-orchestrator"),
        ("payment-orchestrator","fraud-engine"), ("payment-orchestrator","ledger-db-proxy"),
        ("payment-orchestrator","token-auth-service"), ("checkout-api","token-auth-service"),
        ("token-auth-service","redis-session-cluster"), ("ledger-db-proxy","notification-worker")]
    # One write means a failed seed cannot leave a partly populated fixture.
    query = """
CREATE (:Runtime {id:'runtime', lock_until:0, lock_token:'', active_session:''})
WITH 1 AS dummy
UNWIND $teams AS t CREATE (:Team {id:t, name:t, oncall_channel:'#oncall-'+t})
WITH DISTINCT dummy
UNWIND $people AS p
MATCH (t:Team {name:p.team})
CREATE (:Person {id:p.id, name:p.name, role:p.role, team:p.team, handle:p.handle})-[:MEMBER_OF]->(t)
WITH DISTINCT dummy
UNWIND $services AS svc
MATCH (t:Team {name:svc.team})
CREATE (s:Service {id:svc.name, name:svc.name, tier:svc.tier, language:'Python',
 status:'PENDING_TELEMETRY', timeout_ms:5000, circuit_breaker:false})
CREATE (t)-[:OWNS]->(s)
WITH DISTINCT dummy
UNWIND $edges AS e
MATCH (a:Service {name:e.a}), (b:Service {name:e.b})
CREATE (a)-[:DEPENDS_ON {criticality:'critical', call_type:'sync'}]->(b)
WITH DISTINCT dummy
MATCH (auth:Service {name:'token-auth-service'}), (elena:Person {name:'Elena Rostova'}),
      (sarah:Person {name:'Sarah Chen'})
CREATE (doc:Document {id:'DOC-101', title:'Auth pool configuration', doc_type:'confluence',
 url:'https://example.invalid/DOC-101', updated_at:$old})
CREATE (d:Decision {id:'DEC-01', topic:'auth-pool-timeout', summary:'Use a 5000ms connection pool timeout.',
 source:'DOC-101', valid_from:$old, valid_to:0, recorded_from:$old, recorded_to:0, status:'ACTIVE'})
CREATE (d)-[:GOVERNS]->(auth), (d)-[:DOCUMENTED_IN]->(doc), (d)-[:DECIDED_BY]->(sarah)
CREATE (pr:PR {id:'PR-409', title:'Reduce auth pool timeout to 150ms', commit_sha:'synthetic409',
 timestamp:$recent, files_changed:'auth/pool.py', applied:true})
CREATE (elena)-[:AUTHORED]->(pr), (pr)-[:MODIFIED]->(auth)
SET auth.timeout_ms=150
RETURN d.id AS seeded_decision
"""
    run(tenant, query, dict(teams=teams,
        people=[dict(id=n,name=n,role=r,team=t,handle="@"+n.lower().replace(" ",".")) for n,r,t in people],
        services=[dict(name=n,tier=t,team=team) for n,t,team in services],
        edges=[dict(a=a,b=b) for a,b in edges], old=ANCHOR-30*86400, recent=ANCHOR-2700))

    from backend.simulator import migrate_physics
    migrate_physics(tenant)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--tenant", choices=TENANTS)
    args = parser.parse_args()
    for name in ([args.tenant] if args.tenant else TENANTS):
        seed(name, args.reset)
        print("Seeded", name)