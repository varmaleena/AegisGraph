# Demo and participant walkthrough
Suggested three-minute recording; this duration is a presentation plan, not a verified event limit.

1. Start with a fresh seed and the command center. Explain the checkout failure and synthetic data.
2. Inject the Slack decision. Show DEC-02 SUPERSEDES DEC-01; inspect the policy query and lineage.
3. Trigger the incident. Show PR-409, its author, ownership, shortest path and PageRank evidence.
4. Show the shadow configuration fix, then Commander remediation and green procedural nodes.
5. Create a new session and replay. Show that Scribe/Navigator investigation is skipped and success_count grows.
6. Explain that every handoff, event and procedure is persisted in FalkorDB. Briefly show database-stop evidence.

## Understand before submitting
- db.py converts server results to structured tool traces and stores a mutation lease in a graph Runtime node.
- seed_graph.py creates the synthetic topology in one write and skips a tenant already seeded.
- mcp_tools.py contains parameterized Cypher. shortestPath must be in WITH/RETURN for this FalkorDB version.
- valid time answers when a decision applied; recorded time answers what the system knew at a date.
- GRAPH.COPY creates a separate graph; isolation deletes relationships only in the copy.
- agents.py writes hypotheses/tasks/events. Commander retrieves its approval from Task nodes.
- compile_playbook stores one allowlisted synthetic remediation step. Replay validates stored arguments.
- main.py streams SSE step events; frontend page.tsx parses incremental frames and refreshes graph evidence.
- Real monitoring and deployment tools are not integrated. HEALTHY is verified synthetic graph state.
- These agents are deterministic specialist components; LLM orchestration is future work.

## Submission items
- [ ] Participant has reviewed and explained every core query and the demo behavior.
- [ ] Author/team name is correct in the README.
- [ ] Public GitHub repository exists and contains the final source.
- [ ] Working demo video recorded and linked.
- [ ] Live URL added, or complete local Docker setup independently verified.
- [ ] Tracks 01, 02 and 03 declared.
- [ ] AI assistance disclosed accurately.
- [ ] Submit through WeMakeDevs before the official deadline.

## V2 recording
Use docs/V2_WORKFLOW.md for the five-part V2 sequence.
After configuring a real provider key and resetting beta, run:
node scripts/check-ui.cjs --live
This makes actual model calls subject to account quota. It does not use test-fixture responses.
