# Free deployment

Selected topology: Vercel Hobby frontend, Render Free backend, FalkorDB Cloud
Free database, and Gemini free-tier model access. Do not enable paid upgrades.
No deployment has been created or verified yet.

1. Create a Free FalkorDB Cloud instance. Store its hostname, port, username,
   and password only in the hosting secret settings. Match the TLS setting to
   the instance; the advertised Free plan currently has no TLS or persistence.
2. In Render, create a Blueprint from this repository using `render.yaml`.
   It explicitly selects `plan: free`. Provide database credentials and the
   existing Gemini key. Set CORS_ORIGINS to the eventual Vercel HTTPS origin
   (no trailing slash). The cloud start command initializes only missing
   tenants; existing playbooks and runs are preserved during application restarts.
3. In Vercel, import `varmaleena/AegisGraph`, select Hobby and root directory
   `frontend`, and keep the detected Next.js build settings. Before building,
   set NEXT_PUBLIC_API_URL to the Render HTTPS origin without a trailing slash.
   Never put model or database credentials in NEXT_PUBLIC variables.
4. Confirm the final Vercel origin in Render CORS_ORIGINS. Configure access
   control for the mutating API before enabling public model-backed actions.
5. Verify database health, evidence, SSE investigation, interrupted-run resume,
   warm replay, and stale-policy rejection through the deployed app.

Render Free can take about a minute to wake after 15 minutes idle. Its free
hours are shared across the workspace. FalkorDB Free loses graph state on
database restart, so application checkpoint recovery does not imply database
durability on this tier. Preserve the local Docker instance and live evidence
files as the demo backup. Keep payment methods and automatic upgrades disabled
where available; if a provider requires a paid plan, stop instead of upgrading.

References:
- https://render.com/docs/free
- https://render.com/docs/blueprint-spec
- https://vercel.com/docs/monorepos
- https://www.falkordb.com/plans/
