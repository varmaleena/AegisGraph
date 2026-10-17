"""Dedicated seven-tool server; tenant/run bound by the MCP transport."""
from functools import wraps
from mcp.server.fastmcp import FastMCP
from backend.v2_tools import TOOLS,tenant
from backend.db import collect_queries
mcp=FastMCP("AegisGraph-v2")

def measured(tool):
    @wraps(tool)
    def wrapped(*args,**kwargs):
        with collect_queries() as queries:
            try:result=tool(*args,**kwargs)
            except ValueError as exc:
                result=dict(data=[dict(error=str(exc))],graph=tenant(),highlighted_node_ids=[])
        result["execution_time_ms"]=sum(q["execution_time_ms"] for q in queries)
        result["cypher_executed"]=chr(10).join(q["cypher_executed"] for q in queries)
        result.setdefault("unexplored_edges",dict(next="Inspect dependencies, PRs or active policy based on the evidence; do not assume tool order."))
        return result
    return wrapped

for tool in TOOLS:mcp.tool()(measured(tool))
if __name__=="__main__":mcp.run()
