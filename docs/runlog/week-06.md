# Week 6 run log · 30 Nov – 6 Dec 2026 · Token service and evidence records

**Goal:** banks can match accounts through OPRF tokens and exchange S1 and S2 evidence in the harness.

**State:** code complete and tested (hand-built protocol cases, contract tests, fixture, stress scale). Your run produces the first real cross-bank incidents. It also reruns the baselines, so the G1 additions (ablation, decomposition) get real numbers.

## Gate G1 closed (26 Oct)

- **Criterion met.** Oracle − S0 linked detection on HI-Medium validation is 0.508 [0.465, 0.550]; on LI-Medium 0.538.
- **The gain is linking, not detection.** S0 already alerts on 86% of schemes, against the oracle's 89%. Of the oracle's 0.68 linked detection, 0.64 is schemes linked across members, which S0 cannot do. So this phase centres on whether tokens and evidence let banks join their alerts.
- **Your decisions:**
  - provisional thresholds unchanged;
  - an artefact ablation added (S0 and the oracle without payment-format shares and `self_tx`);
  - a linking decomposition added (S0 alerts linked with the pooled rule).

  Both additions are amendment A12.
- **Preregistration:** frozen in commit `ca482c1`, decision note `docs/gates/G1.md`.
- **Tag:** the cloud session cannot push tags, so please create `g1` yourself (step 1).

## What was built

| Item | Where | Notes |
| --- | --- | --- |
| Token service | `finmesh/matching/tokens.py` | One OPRF key per 7-day epoch, derived from a seed only the service holds. Blind evaluation for banks, a budget per bank and epoch (250,000), and a log of counts only. The key is never readable: no getter, no repr, no pickling |
| Token client | same file | Blinds, sends blinded points through a transport callable, unblinds; about 0.2 ms per token |
| Shared-key hashing control | `HashTokenClient` | The scheme the OPRF replaces; used only by the A1 audit (week 8) |
| CC5 contract tests | `tests/contract/test_token_key_isolation.py`, `tests/unit/test_sharing.py` | Bank-side modules never name the service or key functions; the token client only blinds and unblinds; no public attribute, repr or pickle exposes a key |
| Local autoencoder | `finmesh/models/autoencoder.py` | Per member: 47 → 24 → 8 → 24 → 47 on robust-scaled features. Top-3 deviating features (index, direction, magnitude bucket); the 8-unit bottleneck is the S4 embedding for week 7 |
| Evidence schema and records | `finmesh/schemas/evidence_v1.json`, `finmesh/sharing/evidence.py` | Probability bucket, top-3 deviations, 10 bucketed behaviour counters. Records exist for account-windows with calibrated probability ≥ 0.01, or alerted. The account itself never leaves the node |
| Requests | `finmesh/sharing/requests.py` | Ed25519-signed by the issuer (nodes verify, never sign); expiring, one-time, purpose-bound, hop limit 1; at most 20 answers per token and epoch; received evidence dropped after 72 h |
| Messages and bus | `finmesh/sharing/messages.py` | Five allowlisted message types with primitive fields only. The bus rejects anything else, an S0 response, and an S1 response carrying a record |
| Bank node and S0/S1/S2 responses | `finmesh/sharing/node.py` | S1: alert flag and time bucket. S2: the latest record in range plus the alert flag |
| Protocol run | `finmesh/sharing/simulate.py`, `finmesh/training/sharing_run.py`, `finmesh share` | For each alert, requests about cross-member counterparties within 72 h; positive answers become cross-bank links; incidents are scored by the harness |
| Baselines rerun | `finmesh baselines` | Adds the G1 artefact ablation and the linking decomposition |

### Design choices to review

- **Requests are causal.** At window w a bank asks only about windows up to w, so a link is found from the side whose alert comes later. Nothing is learned from the future, matching how a real exchange would work.
- **Epoch of 7 days.** A shorter epoch makes tokens harder to link over time (attack A4, week 9) but splits more requests across epoch boundaries. Each request covers at most two epochs.
- **Budget 250,000 evaluations per bank and epoch, and 20 answers per token.** Large enough for normal triage. The rate limit is what stops a peer from probing one account repeatedly; attacks A1 and A6 will test both.
- **Week 6 links on alert flags only**, so S1 and S2 produce the same incidents. S2's records start to matter in week 7, when fusion and triage use them to re-rank each bank's queue within its budget, and when they become the input to S3's randomised response.
- **Ed25519 for request signatures** (new dependency: `cryptography`). The issuer holds the only signing key, so a node cannot forge a request.

## What I ran here (results)

| Check | Result |
| --- | --- |
| CI mirror | All steps pass, including `finmesh share` on the fixture |
| Tokens | Same token for the same account at any bank within an epoch; different across epochs; equal to direct evaluation; budgets refuse whole batches and log counts only |
| Requests | Refuses replay, forged fields, an unknown issuer, expiry, the wrong responder, and the 21st answer for a token |
| Responses | S1 never carries a record; S2 returns the latest record in range; out-of-range alerts are not reported |
| Protocol (hand-built two-bank case) | S0 sends nothing; S1 and S2 link exactly the alert pair that transacted, from the later side; only allowlisted messages cross |
| CC1 and CC5 contract tests | Pass |

At stress scale (32 M rows, heavy-tailed, random labels):

| Measure | Value |
| --- | --- |
| Whole run (S0, S1, S2, reference) | 637 s, peak 2.7 GB (first attempt 4.0 GB) |
| Requests per level | 554,743, about 250 s per level |
| Token evaluations | 444,953 (index and requests); at most 42,296 per bank and epoch against the 250,000 budget; none refused |
| Rate limit | 331 requests refused (busy hub accounts asked about more than 20 times) |
| Messages | All allowlisted; the bus would have raised otherwise |

The stress set's labels and schemes are synthetic, so its linked detection is 0 by construction; only the protocol volumes and costs carry over. Real data has far fewer busy alerted hubs, so expect fewer requests.

One fix came from this run. The table of transactions between members was built for every account pair in the validation span. It is now cut to transactions touching an alerted account while streaming, which is exact because requests and incidents only ever start from alerts, and brought the peak from 4.0 to 2.7 GB. The page now reports peak memory per phase.

## What you run on your machine

About 1 hour.

### 1. Update, check and tag G1 (5 min)

```bash
cd ~/FinMesh
git pull
uv sync                      # adds cryptography (Ed25519)
bash scripts/ci_local.sh
git tag -a g1 ca482c1 -m "Gate G1: preregistration frozen"
git push origin g1
```

### 2. Rerun the baselines with the G1 additions (10–15 min per dataset)

```bash
uv run finmesh baselines --dataset HI-Medium
uv run finmesh baselines --dataset LI-Medium
uv run finmesh g1
```

The pages gain three rows: S0 alerts linked across members (the decomposition) and the two ablation models. `docs/gates/G1_evidence.md` gains the ablation gap. The G1 numbers themselves do not change: same seed, same models.

### 3. Run the sharing protocol (10–20 min per dataset)

```bash
uv run finmesh share --dataset HI-Medium
uv run finmesh share --dataset LI-Medium
```

Writes `docs/eval/sharing_<ds>.md`.

**What to look for:**
- **Cross-member incidents** above 0 for S1 and S2. This is the week's done-when.
- **S1 linked detection** above S0, and close to the `S0+pooled-link` row. That row is the most S1 can reach: if the gap is large, requests are missing links (epoch splits, rate limits) and I will look at why.
- **No token-service refusals.**

### 4. Tests and push

```bash
uv run pytest -m real_data -v
git add docs/eval/ docs/gates/
git commit -m "Week 6: G1 additions and sharing protocol on real data"
git push
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `No module named 'cryptography'` | `uv sync` not run | `uv sync` |
| `features_w6_B8_pooled_v3 ... missing` | Pooled view not built | `finmesh features --dataset <ds> --view pooled` |
| `refused` with `rate_limited` | A counterparty touched by very many alerts | Expected for hubs; listed in the page |
| `BudgetExceeded` | A bank exceeded 250,000 evaluations in an epoch | Send me the page; the budget is a parameter |

## Week-6 checklist against the plan

- [x] Token service: per-epoch keys, blind–evaluate–unblind, per-bank query budgets, evaluation log
- [x] Contract test: no bank process ever holds the OPRF key (CC5)
- [x] Shared-key hashing control (leakage audit only)
- [x] Local autoencoder per bank; per-feature deviation vector for the top-three features
- [x] Evidence record: token, time bucket, probability bucket, top-three deviations with direction and magnitude bucket, bucketed behaviour counters
- [x] Evidence requests: purpose, hop limit, requester score bucket, signed one-time token, per-token rate limit, retention
- [x] S0, S1 and S2 responses; allowlisted-message contract test
- [ ] Done when: an in-process run on validation produces cross-bank incidents at S1 and S2 (your step 3)
