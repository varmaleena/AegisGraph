"""FalkorDB is the sole durable store. No offline or in-memory fallback."""
import logging
import os
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from falkordb import FalkorDB
from redis.backoff import NoBackoff
from redis.retry import Retry

TENANTS = ("vortexpay_prod", "tenant_beta")
GRAPHS = (*TENANTS, "vortexpay_sandbox", "tenant_beta_sandbox")
log = logging.getLogger("aegis.cypher")
_query_traces=ContextVar("aegis_query_traces",default=None)

@contextmanager
def collect_queries():
    traces=[]
    token=_query_traces.set(traces)
    try:yield traces
    finally:_query_traces.reset(token)


class BusyError(Exception):
    pass

@lru_cache
def client():
    options = dict(host=os.getenv("FALKORDB_HOST", "localhost"),
                   port=int(os.getenv("FALKORDB_PORT", "6379")),
                   socket_connect_timeout=3, socket_timeout=15, retry=Retry(NoBackoff(), 0),
                   ssl=os.getenv("FALKORDB_SSL", "false").lower() == "true")
    for env, key in (("FALKORDB_USERNAME", "username"), ("FALKORDB_PASSWORD", "password")):
        if os.getenv(env):
            options[key] = os.environ[env]
    return FalkorDB(**options)

def graph(name):
    if name not in GRAPHS:
        raise ValueError("Unknown graph")
    return client().select_graph(name)

def run(name, cypher, params=None):
    result = graph(name).query(cypher, params or {}, timeout=10000)
    keys = [col[1] for col in result.header]
    rows = [dict(zip(keys, row)) for row in result.result_set]
    elapsed = float(result.run_time_ms)
    highlighted = set()
    for row in rows:
        for key, value in row.items():
            if key == "highlighted_node_ids" and value:
                highlighted.update(str(v) for v in value if v is not None)
    log.info("graph=%s db_ms=%.3f cypher=%s", name, elapsed, cypher)
    result=dict(data=rows, cypher_executed=cypher, execution_time_ms=elapsed,
                highlighted_node_ids=sorted(highlighted), graph=name)
    traces=_query_traces.get()
    if traces is not None:traces.append(dict(result))
    return result

@contextmanager
def operation(tenant):
    """Atomic graph lease serializes mutations across API/MCP processes."""
    if tenant not in TENANTS:
        raise ValueError("Mutations require a production tenant")
    token = str(uuid.uuid4())
    now = int(time.time() * 1000)
    acquired = run(tenant, """
MATCH (r:Runtime {id:'runtime'})
WHERE r.lock_until < $now
SET r.lock_until=$until, r.lock_token=$token
RETURN r.id AS id
""", dict(now=now, until=now+300000, token=token))
    if not acquired["data"]:
        raise BusyError("Tenant is busy or unseeded; retry after seeding/completion")
    try:
        yield
    finally:
        run(tenant, """
MATCH (r:Runtime {id:'runtime', lock_token:$token})
SET r.lock_until=0, r.lock_token='' RETURN r.id AS id
""", dict(token=token))