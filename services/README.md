# services/

The demo-path services live in the package, under [`finmesh/services/`](../finmesh/services/): the token service and bank nodes over HTTP, authentication, durable orchestration, the analyst console and the privacy ledger, and X7 (latency, faults and security probes). Run them with `uv run finmesh demo-build`, `demo-run`, `console` and `x7`, or with `docker compose` (see the main README).

Experiments never run through these services; they use the in-process harness in `finmesh/`. Run logs: [`docs/runlog/week-15.md`](../docs/runlog/week-15.md) to [`week-17.md`](../docs/runlog/week-17.md).
