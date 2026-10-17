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

The local Compose stack is the tested baseline; cloud configuration has not been deployed or verified.
