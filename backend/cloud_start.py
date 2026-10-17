"""Seed missing demo tenants, then start the cloud HTTP service."""
import os
import uvicorn
from backend.db import TENANTS, run
from backend.seed_graph import seed


def initialize():
    # Preserve learned playbooks, telemetry, and interrupted runs on redeploy.
    for tenant in TENANTS:
        existing = run(tenant, "MATCH (r:Runtime {id:'runtime'}) RETURN r.id AS id")
        if not existing["data"]:
            seed(tenant)


if __name__ == "__main__":
    initialize()
    uvicorn.run("backend.main:app", host="0.0.0.0",
                port=int(os.getenv("PORT", "8000")))
