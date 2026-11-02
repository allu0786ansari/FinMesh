# X7 · demo path under load and faults · HI-Medium

200 alerts, 8 member nodes and the token service as separate processes on 127.0.0.1; one orchestrator per member, over HTTP. Client timeout 2 s, 1 retry. Phases: baseline, node 4 killed and restarted, token service killed and restarted, node 7 slower than the timeout, recovered. Total 97 s.

## Engineering acceptance

| Criterion | Result | Detail |
| --- | --- | --- |
| PT6: p95 from session opened to action recorded ≤ 3 s (normal phases) | pass | p95 0.1793 s over 130 alerts |
| Every session ends closed or failed, under every fault | pass | {'closed': 200} |
| A replayed alert never dispatches twice | pass | {'requests_before': 733, 'requests_after': 733, 'node_answers_before': 710, 'node_answers_after': 710} |
| Unauthenticated, expired, replayed, over-budget and out-of-scope requests are rejected | pass | 10 of 10 |
| No high-impact action runs without a second person's approval | pass | self-approval refused: True; high-impact actions 1, run without approval 0, self-approved 0 |
| Each action links to its session, evidence and card | pass | actions → sessions → requests and card |
| An unreachable member gives a flagged partial case, not a failure | pass | 22 cases flagged incomplete |
| Each fault scenario was really exercised | pass | node_down: requests to the killed node recorded unavailable = 23; token_down: sessions stopped by the outage and resumed after = 18; slow_node: requests to the slow node timed out = 9 |
| Harness and demo path emit identical messages | pass | contract tests in tests/unit/test_week15*.py (CI) |

## Latency: session opened to action recorded (seconds)

PT6 (p95 ≤ 3 s) on the normal phases: p95 **0.179 s**, p50 0.069 s → **met**.

| Phase | Closed | p50 | p95 | max | Session states |
| --- | --- | --- | --- | --- | --- |
| baseline | 100 | 0.064 | 0.177 | 0.311 | closed 100 |
| node_down | 30 | 0.107 | 0.862 | 1.091 | closed 30 |
| token_down | 20 | 0.066 | 0.178 | 0.182 | closed 20 |
| slow_node | 20 | 0.089 | 4.318 | 4.328 | closed 20 |
| recovered | 30 | 0.082 | 0.211 | 0.217 | closed 30 |

Final session states: {'closed': 200}. Evidence request outcomes: {'no_record': 409, 'ok': 292, 'unavailable': 32}.

## Security probes over real HTTP

| Probe | Expected | Observed |
| --- | --- | --- |
| token service, no authentication | 401 | 401 |
| token service, bank 0 asking for bank 1 | 403 | 403 |
| token service, replayed call | 401 | 401 |
| token service, over budget | refused (429) | refused (429) |
| evidence, replayed request (after the node was restarted) | refused | refused |
| evidence, tampered after signing | refused | refused |
| evidence, expired request | refused | refused |
| evidence, sent to a node it is not addressed to | refused | refused |
| evidence, undeclared purpose | 400 | 400 |
| node clock, no admin key | 401 | 401 |

## Resources

| Process | Peak memory (MB) | CPU (s) | Start-up (s) |
| --- | --- | --- | --- |
| token | 102.200 | 1.750 | 0.550 |
| node0 | 225.500 | 3.340 | 3.140 |
| node1 | 225.900 | 3.310 | 3.140 |
| node2 | 225.200 | 3.190 | 3.030 |
| node3 | 223.200 | 3.010 | 2.730 |
| node4 | 224.900 | 3.110 | 2.830 |
| node5 | 226.500 | 3.420 | 3.340 |
| node6 | 225.100 | 3.300 | 3.140 |
| node7 | 225.900 | 3.050 | 3.140 |
| orchestration (this process) | 213.300 | 4.320 | — |

Replay of every alert: requests 733 → 733, node answers 710 → 710.
