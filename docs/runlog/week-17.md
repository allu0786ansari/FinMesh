# Week 17 run log · 15 – 21 Feb 2027 · X7: the demo path under load and faults, and packaging

**Goal (proposal: X7 and the engineering acceptance):**
- End-to-end latency on the demo path. PT6: p95 ≤ 3 s from session opened to action recorded.
- Fault and chaos tests, a resource benchmark, and the containerised smoke pipeline.
- A pass or fail for each engineering acceptance criterion.

**State (2 Nov):** code complete and tested here on real processes. The smoke world passes every criterion. One command runs it on your HI-Medium demo world (about 10–20 min). The container image is built and smoke-tested by GitHub CI, because image registries are blocked in this environment.

## How X7 works

The token service and one node per member run as **separate uvicorn processes** on 127.0.0.1. One orchestrator per member talks to them over real HTTP. The demo world's alerts are replayed in window order through five phases:

| Phase | Share of alerts | What happens |
| --- | --- | --- |
| baseline | 50% | Everything up |
| node_down | 15% | The member these alerts ask most is **killed (SIGKILL)**, then restarted |
| token_down | 10% | The token service is **killed**. Sessions it stops are handled again after its restart; its budgets persist in SQLite |
| slow_node | 10% | The member these alerts ask most **answers slower than the client's timeout** |
| recovered | 15% | Everything up again |

After the phases:
- **Replay:** every alert is sent again.
- **Security probes:** 10 probes over real HTTP.
- **Four-eyes rule:** exercised on a closed case.
- **Resources:** each process's peak memory and CPU time, read from `/proc`.

## What was built

| Item | Where | Notes |
| --- | --- | --- |
| Process manager | `finmesh/services/cluster.py` | Start, wait for health, kill (SIGKILL, like a crash), restart, peak memory and CPU from `/proc` |
| Node process | `node_app_from_env` in `finmesh/services/run.py` | A node loads its member's records from the demo world, builds its token index through the token service, and answers over HTTP. Secrets come from the environment only |
| **Nonces kept across restarts** | `finmesh/services/nonces.py` | A restarted node must still refuse a replayed request. The guard's nonce set is replaced by a SQLite-backed one; bank-side code is unchanged |
| X7 | `finmesh/services/x7.py`, `finmesh x7 --dataset <ds>` or `--smoke` | Phases, replay, probes, approvals, resources, acceptance table, report |
| Smoke world | `build_smoke_world` | Synthetic: 4 members, 24 alerts, built so that every fault really happens |
| Container | `Dockerfile`, `compose.yaml`, `.dockerignore` | Python 3.12 slim, locked production dependencies only, an unprivileged user, data at `/data`. Profiles `smoke` and `console`; the console is published on the host's 127.0.0.1 only |
| CI | `.github/workflows/ci.yml`, job `container` | Builds the image and runs X7 smoke inside it |
| Tests | `tests/unit/test_week17.py` (4) | Includes the whole X7 smoke run on real processes |

### Two things the first smoke runs taught

- **A check must prove its fault happened.** The first run passed every criterion, but the slow-node phase had asked only the slowed member's own alerts, so nothing timed out. The cached tokens might also have hidden the token outage. X7 now has a criterion **"each fault scenario was really exercised"**. It counts the requests lost to the killed node, the sessions the token outage stopped and resumed, and the requests that timed out. Each fault's target is chosen from that phase's alerts.
- **Rounding can empty a phase.** With very few alerts, "recovered" got none. Every phase now gets at least one alert.

## What I ran here (results)

X7 on the smoke world (4 members, 24 alerts, 1 s timeout), all as real processes:

| Criterion | Result |
| --- | --- |
| PT6: p95 opened → action recorded ≤ 3 s (normal phases) | pass: p95 0.05 s |
| Every session ends closed or failed, under every fault | pass: 24 of 24 closed |
| A replayed alert never dispatches twice | pass: requests 144 → 144, node answers 136 → 136 |
| Unauthenticated, expired, replayed, over-budget, out-of-scope rejected | pass: 10 of 10 probes |
| No high-impact action without a second person's approval | pass |
| Each action links to its session, evidence and card | pass |
| An unreachable member gives a flagged partial case | pass: 4 cases flagged |
| **Each fault really exercised** | pass: 8 requests lost to the killed node, 2 sessions stopped and resumed, 4 timeouts |
| Harness and demo path emit identical messages | pass (contract tests in CI) |

- **Slow phase:** p95 4.4 s, as expected (2 requests × 2 attempts × 1 s timeout). PT6 is judged on the normal phases only; with a member down or slow, cases still close, flagged as partial.
- **Resources:** token service about 96 MB; each node about 207 MB; orchestration about 215 MB.
- **The 10 probes, all refused as expected:**
  - token service: no authentication, a bank asking for another bank, a replayed call, over budget;
  - evidence: a request replayed after its node restarted, tampered after signing, expired, sent to the wrong node, an undeclared purpose;
  - node clock: changed without the admin key.

The same run with **production dependencies only** (no dev tools, outside the repo, as in the image) passes every criterion; that is the image's install step without Docker. The CI mirror passes all steps.

## What you run on your machine

### 1. Update and check (about 15 min)

```bash
cd ~/FinMesh
git pull
uv sync
bash scripts/ci_local.sh
```

### 2. X7 on your HI-Medium demo world (about 10–20 min)

The demo world from week 16 is reused; there is no need to rebuild it.

```bash
uv run finmesh x7 --dataset HI-Medium 2>&1 | tee week17.log
```

It starts the token service and 8 node processes. Each node builds its token index, which takes a little while. It then runs the five phases, the replay, the probes and the approvals. It prints a pass or fail for each criterion and writes `docs/eval/x7_HI-Medium.md`.

**What to look for:**
- PT6 p95 on the normal phases against 3 s;
- every criterion `pass`;
- each node's peak memory (8 nodes plus the orchestration must fit your about 5.8 GB).

### 3. Optional: the container (if Docker is installed)

```bash
docker compose --profile smoke up --build
```

This builds the image and runs X7 smoke inside it; GitHub CI does the same on every push.

### 4. Push

```bash
git add docs/eval/x7_HI-Medium.md week17.log
git commit -m "Week 17: X7 on HI-Medium"
git push
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `no demo world` | Week-16 `demo-build` not run, or `data/demo/HI-Medium` removed | `uv run finmesh demo-build --dataset HI-Medium --alerts 200` |
| A node "exited at start" | See `data/demo/HI-Medium_x7/node<m>.log` | Usually memory; close other programs |
| Out of memory | 8 nodes plus the orchestration at once | Close other programs. Each node holds only its member's records |
| PT6 fails on the normal phases | A busy machine, or WSL's memory limit | Rerun with nothing else running; report the numbers as they are |

## Week-17 checklist against the plan

- [x] End-to-end latency on the demo path (PT6)
- [x] Fault and chaos tests: node killed, token service killed, slow node, replay, security probes
- [x] Resource benchmark per process
- [x] Container image and compose profiles; container smoke in CI
- [ ] Your X7 run on HI-Medium
- Week 18: open the sealed test (G4) with the frozen configurations, once each
