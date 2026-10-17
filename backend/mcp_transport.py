"""Actual MCP ClientSession over subprocess stdio; no direct tool dispatch."""
import os
import sys
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

@asynccontextmanager
async def connect(tenant,rid):
    env={k:v for k,v in os.environ.items() if k not in ("GEMINI_API_KEY","GROQ_API_KEY","OPENAI_API_KEY")}
    env.update(AEGIS_TENANT=tenant,AEGIS_RUN_ID=rid,PYTHONIOENCODING="utf-8")
    params=StdioServerParameters(command=sys.executable,args=["-m","backend.v2_mcp_server"],env=env)
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            yield session