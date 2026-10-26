# Week 7 run log · 7 – 13 Dec 2026 · Fusion, triage, S4 and the first frontier

**Goal:** each level's evidence changes *which* accounts a bank alerts on, and X1 measures linked detection per sharing level on validation.

**State:** code complete and tested (unit cases, a fixture pipeline test, stress scale). Your run produces the first real X1 numbers and the first frontier figure.

## Week-6 review (your real-data run, pushed 26 Oct)

Everything is consistent; no fixes needed.

| Check | HI-Medium | LI-Medium |
| --- | --- | --- |
| S0 linked detection | 0.174 | 0.151 |
| S1 = S2 linked detection | 0.604 | 0.516 |
| S0 alerts linked with the pooled rule (the most S1 can reach on these alerts) | 0.604 | 0.516 |
| Oracle | 0.682 | 0.689 |
| Share of the oracle gain recovered by S1 | **0.85** | **0.68** |
| Cross-member incidents | 905 | 461 |
| Requests; rate-limited | 23,323; 130 | 23,955; 70 |
| Token-service refusals | 0 | 0 |
| Run time, peak memory | 174 s, 1.3 GB | 135 s, 1.3 GB |

What this means:

- **The protocol loses nothing.** S1 reaches the pooled-linking bound exactly: epoch splits and the 20-per-token rate limit cost no scheme.
- **S2 cannot beat S1 yet.** Both stand on S0's alerts, so they link the same alerts. The remaining gap to the oracle (0.08 on HI-Medium, 0.17 on LI-Medium) is schemes where S0 alerts on too few accounts, and only re-ranking can close it. That is this week's triage.
- **The artefact ablation holds.** Without the payment-format shares and `self_tx` the oracle − S0 gap is still large (0.456 on HI-Medium), so RQ1 does not rest on simulator quirks.

## Amendment A13 (please confirm)

The fusion rule is fixed before any real-data X1 number exists, as section 4 of the preregistration requires. It is in `docs/proposal/CHANGES.md` and in section 6a of the preregistration.

- **Who asks:** every validation account-window with probability ≥ 0.01 or an S0 alert. In week 6 only alerts asked; triage needs evidence *before* the alert decision.
- **Primary fusion: a triage stacker.**
  - Per member, a logistic regression (standardised features, L2, C = 1) on the level's evidence.
  - Cross-fitted on the two time halves of validation, so no row is scored by a model fitted on it.
  - Each member then cuts its new score at the primary budget.
- **Linking:** S1+ use the pooled rule (week 6 showed the protocol reaches it); S0 keeps the local rule.
- **Secondary rules** are reported but never selected: noisy-OR and k-of-n.
- **Propagation** is plaintext and uses no cryptography: own probability + 0.5 × the strongest cross-member counterparty probability.

Why a fitted stacker: it is the least-tuned rule that can use every level's evidence. The two fixed rules show how much of any gain depends on fitting. If you prefer one of the fixed rules as primary, say so before you run step 3.

## What was built

| Item | Where | Notes |
| --- | --- | --- |
| Evidence features | `finmesh/fusion/triage.py` | Per candidate. **S1:** own logit; requests, refusals and alert flags received; inbound requests and the requester's highest bucket. **S2** adds: counterparty record buckets (probability, deviation, fan-in, fan-out, pass-through). **S4** adds: the mean counterparty embedding |
| Fixed fusion rules | same file | Noisy-OR (flag weight = the member's alert precision on the other half), k-of-n |
| S4 level | `finmesh/sharing/{evidence,messages,node}.py` | S2 record plus the 8-unit autoencoder bottleneck, integer-bucketed (× 100). Allowlist and bus updated |
| Inbound tracking | `finmesh/sharing/node.py` | A node keeps who asked about which of its accounts, and the requester's bucket. This is the S1 leak that week 9's attacks measure; here it is also triage evidence |
| Response capture | `finmesh/sharing/simulate.py` | Every answer is kept per requester for the features. A member with no records now answers "no record" instead of failing |
| Cross-fitted stacker | `finmesh/training/x1.py` | Fold = validation half (windows 39–44, 45–50) |
| Score propagation | same file | Plaintext reference |
| X1 run | `finmesh x1`, `finmesh/training/x1_report.py` | Seeds 0–2. Per-scheme outcomes averaged over seeds, then a scheme bootstrap. Gains over S0 are paired; H1b recovery = (level − S0) / (oracle − S0) |
| First frontier figure | `docs/eval/frontier_<ds>.png` | Linked detection per level with 95% CIs; the random-alert line |
| Tests | `tests/unit/test_x1.py`, `tests/integration/test_real_data_week7.py` | Includes a check that the stacker never scores a row with a model that saw its label |

### Design choices to review

- **Candidates ask before alerting.** Requests rise about 2.7-fold over week 6 at stress scale (1.49 M against 554,743). Rate limits and token budgets still hold at stress scale (below). In week 9, the inbound requests become what attack A6 (membership inference from requests) measures.
- **Inbound requests are evidence at every level, including S1.** Being asked about by a peer with a high bucket is a strong signal, and it is honest: a real node sees its inbound requests. The cost is privacy, which week 9 prices.
- **The stacker fits on validation labels.** This is allowed by CC2 (fusion parameters come from validation only). The cross-fit keeps the validation numbers out-of-sample. At test, the stacker is refitted on all of validation and frozen.
- **The S4 embedding is averaged over a candidate's counterparties.** It is the simplest summary; a richer one (max-similarity to the requester's own embedding) is possible, but I kept the rule minimal before seeing results.

## What I ran here (results)

| Check | Result |
| --- | --- |
| CI mirror | All steps pass, including `finmesh x1` on the fixture |
| Unit tests | Evidence features, both fixed rules, the cross-fit (permuting one half's labels leaves that half's scores unchanged), seed combining and H1b recovery |
| Fixture pipeline (budget raised to 300 per 1,000 per day so the fixture alerts) | All 12 configurations, three levels of protocol, report and figure |
| Fixture at the real budget | 0 alerts, as in weeks 5–6. The page reports recovery as undefined rather than NaN |

At stress scale (32 M rows, heavy-tailed, random labels, one seed):

| Measure | Value |
| --- | --- |
| One seed, all 12 configurations | 2,472 s (41 min), peak 3.6 GB |
| Time by phase | S0 detector 142 s; oracle 62 s; records and embeddings 23 s; protocol about 520 s per level (S1, S2, S4); propagation 2 s; evaluation 607 s |
| Peak memory by phase | detector 2.6 GB; protocol 1.8 GB per level; evaluation 3.6 GB (the harness, as in the week-5 baselines) |
| Candidates asking; requests per level | 12,689 account-windows; 1,491,762 requests |
| Token evaluations | 940,781 per level; at most 163,858 per bank and epoch against the 250,000 budget; none refused |
| Rate limit | 1,809 requests refused (0.12%) |

Three fixes came from this run:

- **Protocol memory.** The first attempt kept every request and every "no record" answer as a Python object, and kept received evidence until the end of the run. Requests now stream in time order. Retention is purged as time advances. Only informative answers (alert, record, refusal) are kept; request counts come from the request plan. Protocol memory fell from about 2.3 to 1.8 GB.
- **Score storage.** Fused scores differ from S0 only on candidate rows, so only those rows are kept per configuration. Peak memory fell from 4.3 to 3.6 GB.
- **Peak reporting.** The memory meter reported the peak since its last lap rather than over the whole run, which understated the week-6 page's headline peak. Its per-phase figures were right.

The fixes also make the order of requests deterministic (time order). In week 6 the order came from a hash group-by, so rerunning `finmesh share` can move the rate-limited count by a few requests.

Real HI-Medium asks far less than this stress set: week 6 sent 23,323 requests against 554,743 at stress scale. Expect about 10–15 minutes and under 2.5 GB per seed.

The stress set's labels are synthetic, so its detection numbers mean nothing; only time, memory and protocol volumes carry over.

## What you run on your machine

About 1.5 hours, mostly step 3.

### 1. Update and check (5 min)

```bash
cd ~/FinMesh
git pull
uv sync                      # adds matplotlib (the frontier figure)
bash scripts/ci_local.sh
```

### 2. Confirm A13

Read the A13 row in `docs/proposal/CHANGES.md`. If you agree, nothing to do. If not, tell me before step 3, because the rule must be fixed before real X1 numbers exist.

### 3. Run X1 (about 30–45 min per dataset with 3 seeds)

```bash
uv run finmesh x1 --dataset HI-Medium
uv run finmesh x1 --dataset LI-Medium
```

Each run writes `docs/eval/x1_<ds>.md` and `docs/eval/frontier_<ds>.png`.

**What to look for:**

- **S1/S2/S4 linked detection at or above week 6** (0.604 on HI-Medium). It can fall slightly if the stacker drops some of S0's alerts, but should not fall much.
- **S2 above S1** is the first sign that records add value beyond flags (H1b is about S2).
- **H1b recovery** for S2. The preregistered target, judged on test, is 0.60.
- **Propagation** is the plaintext reference: if it beats S2, the records add less than a single number would.
- **No token-service refusals** in the protocol table.

### 4. Tests and push

```bash
uv run pytest -m real_data -v
git add docs/eval/
git commit -m "Week 7: X1 on real data"
git push
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `No module named 'matplotlib'` | `uv sync` not run | `uv sync` |
| `features_w6_B8_pooled_v3 ... missing` | Pooled view not built | `finmesh features --dataset <ds> --view pooled` |
| Out of memory | Another heavy process running | Close it; the stress run peaked at 3.6 GB. Or run one seed: `--seeds 0` |
| `BudgetExceeded` | A bank exceeded 250,000 token evaluations in an epoch | Send me the page; the budget is a parameter |
| `S2 recovery undefined` | The oracle shows no linked gain | Only expected on the fixture; send me the page |

## Week-7 checklist against the plan

- [x] Fusion layer: triage stacker (primary), noisy-OR and k-of-n (secondary), fixed by amendment before results (A13)
- [x] S4 level: records with local embeddings
- [x] Plaintext score-propagation reference
- [x] X1 runner with seeds, scheme bootstrap, paired gains and H1b recovery on validation
- [x] First frontier figure (linked detection per level)
- [ ] Done when: X1 numbers on HI-Medium and LI-Medium validation (your step 3)
