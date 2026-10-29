# Week 8 run log · 14 – 20 Dec 2026 · Relational oracle, S3, progressive disclosure, audit A1–A3

**Goal:**
- a ceiling for H1b that relational triage cannot beat;
- the formally private evidence level (S3) and progressive disclosure (PD), with their curves (X3);
- the first leakage numbers (A1–A3, part of X2).

**State:** code complete and tested (unit cases, a fixture pipeline test, stress scale). One command, `finmesh x1`, now produces X1, X3 and the audit. Your run produces the first real utility–leakage frontier.

## Week-7 review (your real-data run, pushed 26 Oct)

The run is complete and consistent: 3 seeds on both datasets, no token refusals, 30 min and 1.6 GB on HI-Medium.

| Linked detection, validation | HI-Medium | LI-Medium |
| --- | --- | --- |
| S0 | 0.174 | 0.154 |
| S1 tokens + flags | 0.727 | 0.663 |
| S2 minimised records | **0.736** | **0.695** |
| S4 records + embeddings | 0.704 | 0.652 |
| Score propagation (plaintext) | 0.704 | 0.749 |
| Oracle (pooled, preregistered) | 0.672 | 0.703 |
| H1b: S2 recovery of the oracle gain | 1.13 [1.07, 1.19] | 0.99 [0.87, 1.11] |

Findings:

1. **Sharing beats the pooled oracle.** Plaintext propagation does too, and it uses no labels, so the gain does not come from the stacker fitting on validation. It comes from relational re-ranking: alerting accounts whose counterparties at other banks look suspicious concentrates the alert budget on connected scheme accounts.
   - Any-alert detection dips slightly (0.873 → 0.858) while AUPRC rises (0.334 → 0.376 for S2; 0.403 for propagation), so the gain is real signal, not metric gaming.
   - The preregistered oracle scores each account alone, so it is not a ceiling and H1b would pass trivially.
   - **Your decision (29 Oct): add a relational oracle as H1b's ceiling (amendment A14).**
2. **Records add little over flags.** S2 − S1 is +0.009 on HI-Medium and +0.032 on LI-Medium, both inside the CIs. Most of the value is the token match, the alert flag and being asked about by a suspicious peer. This matters for the frontier: if S1 is nearly as useful as S2 and leaks less, it may be the better operating point.
3. **Embeddings hurt slightly** (S4 below S2 on both datasets). Eight more noisy features in a small per-member stacker cost more than they add. S4 remains the leakage upper reference, as planned.
4. **The fixed rules trail the stacker** (noisy-OR 0.68 and k-of-n 0.65 on HI-Medium, against 0.736), so fitting the fusion matters. That is why A13 fixed the stacker before results.

## Amendments

- **A14 (your decision):** the relational oracle is H1b's ceiling.
  - It is the pooled model given the same re-ranking with full plaintext access: every counterparty's exact oracle probability and alert, and the same stacker and linking.
  - The preregistered oracle ratio is still reported.
  - It was prompted by validation results while test is sealed; this is disclosed in `CHANGES.md`.
- **A15 (please confirm):** S3, PD and the attacks, fixed before any real result.
  - The proposal says "within a stated margin" for H1c but never states one. I set it at **0.05**: the upper 95% bound of (attack − prior) TPR at 1% FPR, on every assessable target.
  - Details are in `CHANGES.md` and section 6b of the preregistration.

## What was built

| Item | Where | Notes |
| --- | --- | --- |
| Relational oracle | `finmesh/training/relational.py` | Calibrated pooled probabilities; features from every federation counterparty in the 72 h lookback; cross-fitted stacker; plus `oracle+propagation` |
| S3 mechanism | `finmesh/sharing/ldp.py` | k-ary randomised response, ε/20 per field over the 20 noised fields; time bucket and alert flag in the clear (S1 content); memoised per record; per-account epoch ledger capped at ε = 8, then the S1 answer |
| PD | `finmesh/sharing/node.py` | S1 answer always; the S2 record when the requester's bucket ≥ τ |
| Disclosure accounting | `finmesh/sharing/simulate.py` | Records and accounts disclosed, LDP withheld, maximum ε spent on one account |
| Faster protocol runs | `TokenEnv` in `simulate.py` | One token service per seed; later levels reuse the OPRF work (tokens are identical across levels) |
| X3 sweeps | `finmesh/training/x1.py` | S3 at ε ∈ {0.5, 1, 2, 4, 8}; PD at τ ∈ {2, 3, 4}; stacker fitted on the released evidence |
| H1b against both ceilings; H1d with the S1 reference | same file | |
| Leakage audit A1–A3 | `finmesh/training/audit.py` | Runs on seed 0 inside `finmesh x1`; strong adversary, prior-only baseline, cluster bootstrap |
| Pages and figures | `finmesh/training/x1_report.py` | `x1_<ds>.md` + `ladder_<ds>.png`; `x3_<ds>.md` + `x3_<ds>.png`; `audit_<ds>.md` + `frontier_<ds>.png` (the utility–leakage frontier) |
| Tests | `tests/unit/test_privacy.py`, `tests/unit/test_x1.py`, `tests/integration/test_real_data_week8.py` | Randomised-response rates, memoisation and ε cap, PD thresholds, the margin rule, relational features, the full pipeline |

### Design choices to review

- **S3 keeps the alert flag in the clear.** S3 is "S2 through LDP"; the flag is S1's content and carries most of the linking value (finding 2). Noising it too would make S3 strictly weaker than S1. As defined, S3 leaks at most S1 plus an ε-LDP record, which is what H1c compares.
- **ε is split evenly over 20 fields.** At ε = 2 each field gets 0.1, so a 47-value deviation index is close to uniform noise. A budget weighted toward the probability bucket would keep more utility; I kept the even split because it is the plain reading of the proposal.
- **Memoised releases.** Without memoisation a peer could ask repeatedly and average the noise away; with it, the ledger counts distinct records only.
- **The attacks use a strong adversary** trained on true attributes of half the queried accounts. A real peer knows less, so these are upper bounds. A shadow-model adversary (trained only on its own customers) is a weaker variant we can add in week 9 if you want both.
- **A1 is computed, not brute-forced.** Re-identification = matches between targets and the adversary's candidate list, limited for the OPRF by the spare budget. The mechanism check confirms on real tokens that a tokenised candidate matches the holder's token under both mechanisms.
  - Expect A1 to show that a generous budget (250,000) gives little protection when candidate lists are smaller than the budget.
  - The OPRF's real advantages are metering, logging and epoch rotation. The page reports the attack's query volume against legitimate use.

## What I ran here (results)

| Check | Result |
| --- | --- |
| CI mirror | All steps pass; `finmesh x1` on the fixture now writes all three pages |
| Unit tests | Randomised response keeps the true value at e^ε/(e^ε+k−1) and spreads the rest uniformly; memoised releases cost no ε; the ledger caps at 8 per account and epoch; PD discloses only at τ; the relational features count exactly the counterparties inside the lookback; the margin rule |
| Fixture pipeline (budget raised so the fixture alerts) | All 25 configurations, 11 protocol runs per seed, audit, three pages and three figures; strict JSON |

At stress scale (32 M rows, heavy-tailed, random labels, one seed):

| Measure | Value |
| --- | --- |
| One seed, all 25 configurations, 11 protocol runs and the audit | 5,161 s (86 min) |
| Time by phase | S0 detector 108 s; oracle 95 s; relational oracle 57 s; records 41 s; S1 protocol 517 s (with the OPRF work); each later level about 305 s (tokens reused); audit 123 s; evaluation 1,039 s |
| Peak memory | 4.1 GB in the first run, in the audit's A1 step; after the fix below, evaluation is the peak at about 3.8 GB |
| Requests per level | 1,491,762; no token refusals; at most 163,858 evaluations per bank and epoch |
| Accounts with records disclosed | S2 5,406; PD τ = 2, 3, 4: 348, 201, 93 |
| S3 records withheld by the ε cap | ε = 2: 23; ε = 4: 1,113; ε = 8: 6,075 |
| Audit targets | 182,904 (test half 91,754); prevalence: A2 0.77, A3 amount 0.10, fan-in 0.08, pass-through 0.03 |
| A1 (synthetic accounts) | hashing 1.00, OPRF deployed budget 0.11, OPRF sized budget 0.16; ratio 6.1 |

The stress set's labels and schemes are synthetic, so its detection and attack numbers mean nothing; only time, memory and volumes carry over.

Two things came from this run:

- **Token reuse across levels** cut each later protocol run from about 520 s to 305 s at this scale.
- **A1 memory.** A1 built every (adversary, counterparty) pair over the whole period at once, and that was the run's 4.1 GB peak. It now makes one streaming pass per adversary and keeps only the counts and the pairs that hit target tokens. Measured alone on the stress data, the step now takes 32 s and peaks about 0.45 GB above its base.

Real HI-Medium sent about 6 times fewer requests than this stress set in week 7 (231,520 against 1.49 M). Expect about 20 minutes and under 2.5 GB per seed, about 1 hour per dataset with three seeds.

## What you run on your machine

About 2 hours of machine time, mostly step 3. You can leave it running.

### 1. Update and check (5 min)

```bash
cd ~/FinMesh
git pull
uv sync
bash scripts/ci_local.sh
```

### 2. Confirm A15

Read the A15 row in `docs/proposal/CHANGES.md`, especially the 0.05 margin. If you want a different margin or attack definition, tell me **before step 3**.

### 3. Run X1–X3 and the audit (about 1 hour per dataset with 3 seeds)

```bash
uv run finmesh x1 --dataset HI-Medium
uv run finmesh x1 --dataset LI-Medium
```

Each run writes to `docs/eval/`:

| File | Contents |
| --- | --- |
| `x1_<ds>.md`, `ladder_<ds>.png` | Ladder with the relational oracle; H1b against both ceilings |
| `x3_<ds>.md`, `x3_<ds>.png` | S3 recall versus ε; PD recall versus disclosure; H1d |
| `audit_<ds>.md`, `frontier_<ds>.png` | Attacks A1–A3; H1c; the utility–leakage frontier |

**What to look for:**

- **The relational oracle above every sharing level.** If a level still beats it, tell me: the ceiling would need more information, not a different rule.
- **H1b against the relational oracle.** This is the number the paper will quote.
- **S3 against ε.** Recall should rise toward S2 as ε grows. Because the flag is in the clear, even ε = 0.5 should stay near S1.
- **PD** at or near S1's linked detection with a fraction of S2's disclosures.
- **The audit:**
  - S4 should leak most;
  - S1 and S3 at ε ≤ 2 should sit within the 0.05 margin;
  - A1 hashing ÷ OPRF (sized budget) against PT2's factor of 10.

### 4. Tests and push

```bash
uv run pytest -m real_data -v
git add docs/eval/
git commit -m "Week 8: X1-X3 and audit on real data"
git push
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Run too long | Three seeds × 11 protocol runs | Run `--seeds 0` first to check; the audit always uses the first seed |
| Out of memory | Another heavy process | Close it; the stress set peaked at about 3.8 GB, about twice real HI-Medium |
| `H1c ... not assessable` targets | Too few positives in the test half | Expected only on small datasets; listed on the page |
| Week-7 test still reads `week07/` artifacts | By design | Week-8 artifacts are in `data/artifacts/week08/` |

## Week-8 checklist against the plan

- [x] Relational oracle as H1b's ceiling (A14)
- [x] S3: k-ary randomised response per field, ε sweep, memoised releases, per-account ε ledger
- [x] Progressive disclosure with a τ sweep and disclosure volume
- [x] Fusion for S3 and PD fitted on released evidence
- [x] Attacks A1 (hashing vs OPRF with budgets), A2 (relationships), A3 (attributes), with prior-only baselines and TPR at low FPR
- [x] Utility–leakage frontier figure
- [ ] Done when: X1–X3 and the audit on HI-Medium and LI-Medium validation (your step 3)
- Week 9: attacks A4–A6, Gate G2 evidence, the thin demo slice
