# Deployment plan
Recommended topology: Next.js frontend and FastAPI backend as separate Railway services,
with FalkorDB Cloud as the only database.

Official references:
- https://docs.railway.com/guides/deploying-a-monorepo
- https://docs.railway.com/guides/docker-compose
- https://www.falkordb.com/try-free/

The Graph Hacks rules allow any hosting platform and accept Docker/self-hosted/Cloud FalkorDB.
Live hosting is preferred, but verified complete local setup is an accepted alternative
if the project cannot be deployed.

## Required account inputs
A public GitHub repository, Railway project/account and a FalkorDB Cloud instance.
No live deployment or provider billing has been initiated.

## Service configuration
Keep the repository root as build context for both Dockerfiles.
- Backend: backend/Dockerfile, target port 8000. Set FALKORDB_HOST, FALKORDB_PORT,
  FALKORDB_USERNAME, FALKORDB_PASSWORD and FALKORDB_SSL according to the cloud instance.
- Frontend: frontend/Dockerfile, target port 3001. Set NEXT_PUBLIC_API_URL to the
  backend HTTPS origin during the build.
- Backend CORS_ORIGINS must equal the frontend HTTPS origin.
- Run python -m backend.seed_graph once against the cloud instance without --reset.
- Verify all six tools, especially GRAPH.COPY, against the chosen Cloud instance/version.
- Add authentication/access control before opening mutating APIs publicly.
- Confirm provider charges and availability in the selected accounts before provisioning.

## Railway repository configuration

The repository includes `deploy/railway-backend.json` and
`deploy/railway-frontend.json`. Select the corresponding config file in each
service's settings and keep the repository root as its build context.
Set the backend public domain target port to 8000 and the frontend target port
to 3001. Frontend `NEXT_PUBLIC_API_URL` must be configured before its build.

FalkorDB can alternatively run as a private Railway image service using
`falkordb/falkordb`, a persistent volume at `/data`, and
`REDIS_ARGS=--appendonly yes`. Expose port 6379 only on the private network;
do not create a public TCP proxy or publish its Browser. Configure the backend
with that service's private hostname. Confirm the account's available credits
and resource limits before provisioning this three-service topology.

Deploy the database first, seed both tenants once with
`python -m backend.seed_graph`, then start the backend and frontend. Seed without
`--reset` to preserve existing graph history. A healthy backend requires a
reachable FalkorDB instance; successful frontend rendering alone does not verify
deployment. Check evidence loading, an SSE investigation, checkpoint resume,
warm replay, and policy invalidation through the deployed frontend.

The local Compose stack is the tested baseline. These cloud configuration files
are prepared, but no cloud resources have been provisioned or verified yet.
