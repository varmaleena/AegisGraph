# Final audit fixes

## Implemented

- Gemini default: gemini-2.5-flash. Configurable key pool and model alternatives,
  bounded attempts/backoff, Retry-After handling, and explicit Groq fallback.
- Groq default remains cloud-verified openai/gpt-oss-120b; Enterprise-only Llama
  and retired Gemini 2.0 are not selected automatically. Their IDs can be supplied
  explicitly through GROQ_MODEL or GEMINI_FALLBACK_MODELS if an account supports them.
- Per-step successful provider/model and sanitized failed-attempt history persist
  alongside usage. Missing usage is never fabricated. All model keys are excluded
  from the MCP subprocess environment and Docker build context.
- Scenario 01 and the security directive stream V2 policy queries and live gate status.
- Scenario 04 streams GRAPH.COPY, reachability, isolation and DAG telemetry through
  the trace inspector, switches to shadow view, and preserves production configuration.
- Cancel/reset-session cleans expired failed step-zero runs while retaining useful
  checkpoints and active workers. Graph reset already clears graph-contained state.
- README describes the deployed V2 architecture and AI assistance disclosure.

## Verification

- pytest backend/tests -q: **41 passed**; one upstream Starlette deprecation warning.
- npm run typecheck: **passed**.
- npm run build: **passed**.
- Browser checkpoint: policy/isolation SSE, live gate, sandbox telemetry, security
  action, mobile overflow and zero page errors: **passed**.
- Local beta graph was backed up and restored around the destructive pytest suite.
- Provider failure scenarios use mocks: 429, 500, 503, timeouts, exhausted routes,
  Retry-After, unavailable models, key deduplication and secret redaction. No paid
  provider or new live inference was used to validate retry behavior.

Historical raw measurements retain their original model IDs rather than rewriting
past executions. Deployed Groq evidence is in DEPLOYED_GROQ_OSS_VERIFICATION.json.
Free hosting limits and public API access-control requirements remain documented.
Passing these checks is not a certification of complete production hardening.
