# Week 9 run log · 21 – 27 Dec 2026 · S3 fix, sized budgets, attacks A4–A6, Gate G2 evidence, demo slice

**Goal:** close the sharing study on validation for Gate G2:
- the S3 correction and token budgets you chose;
- the last three attacks;
- the G2 evidence page;
- the thin end-to-end demo slice.

**State:** code complete and tested (unit cases, fixture pipelines, stress scale). Your run produces the final validation numbers of the headline study and the G2 evidence.

## Week-8 review (your real-data run, pushed 29 Oct)

Complete and consistent:
- both datasets, 3 seeds, 25 configurations, 11 protocol runs per seed and the audit;
- 63 min and 1.75 GB on HI-Medium;
- no token refusals.

| Validation, linked detection | HI-Medium | LI-Medium |
| --- | --- | --- |
| S0 | 0.174 | 0.154 |
| S1 / S2 / S4 | 0.727 / 0.736 / 0.704 | 0.663 / 0.695 / 0.652 |
| S3, ε 0.5 → 8 | 0.726 → 0.739 | 0.642 → 0.656 |
| PD τ = 2 / 3 / 4 | 0.735 / 0.728 / 0.708 | 0.624 / 0.606 / 0.660 |
| Oracle (preregistered) | 0.672 | 0.703 |
| Oracle + propagation (pooled) | 0.741 | **0.846** |
| Relational oracle (A14 ceiling) | **0.747** | 0.807 |
| H1b: S2 against the relational oracle | 0.98 [0.94, 1.02] | 0.83 [0.74, 0.92] |

Findings:

1. **H1b holds against the new ceiling, with room to spare.**
   - The relational oracle now sits above every sharing level on HI-Medium.
   - On LI-Medium its fixed-rule twin (oracle + propagation) links more, 0.846. Against that, S2 recovers 0.78, still above 0.60.
   - From this week, H1b is also reported against whichever pooled configuration is stronger.
2. **Privacy costs almost no detection.**
   - S3 at every ε and PD at every τ stay within a few points of S2.
   - S1 alone gets 0.98 (HI) and 0.94 (LI) of S2's gain, so H1d passes trivially. The page shows S1 as the reference.
3. **Leakage is where the levels differ.**
   - S2 records give away fan-in almost exactly: TPR 0.88 (HI) and 0.93 (LI) at 1% FPR.
   - PD discloses exactly the suspicious accounts, so it leaks a lot even at high τ.
   - S4 leaks more than S2 on 3 of 4 targets on HI-Medium and 1 of 4 on LI-Medium.
4. **S3 had an existence leak.**
   - Its leakage did not fall with ε (LI fan-in excess 0.077 at ε = 0.5 and 0.083 at ε = 8; AUC 0.89 against 0.72 for S1).
   - The cause: "no record" was answered in the clear, and that reveals a score ≥ 0.01.
   - **Your decision: fix it** (A16).
5. **The 250,000 token budget barely helped.**
   - Hashing re-identified 42% of target tokens, the OPRF 20% (×2).
   - Sized to twice the legitimate peak, the OPRF falls to 3.8% (×11.0) on HI-Medium and 5.2% (×7.8) on LI-Medium.
   - **Your decision: sized budgets** (A16).
6. **S1 itself leaks fan-in beyond the margin on LI-Medium** (upper bound 0.071). Alert flags reveal suspicious-looking behaviour. This is a real H1c finding, not a bug, and it stays in the results.

## Amendment A16

Recorded in `CHANGES.md` and preregistration section 6b. All of it was prompted by validation results; test is sealed.

- **S3 answers every request with a record.**
  - When none exists, it releases a dummy (bucket 0, no deviation, counters missing) through the same randomised response.
  - The time field is always the end of the requested range.
  - Releases are memoised per record *and epoch*. A key rotation brings a fresh release, so the same noisy values can never link an account across epochs. I found this second flaw while building A4.
- **Token budgets:** twice the largest legitimate per-bank, per-epoch use on validation.
  - HI-Medium 74,510; LI-Medium 87,580 (`finmesh/schemas/token_budgets.json`).
  - PT2 is judged at these budgets.
- **A4–A6 specified before results** (below).
- **H1b sensitivity** against the stronger pooled configuration.

## What was built

| Item | Where | Notes |
| --- | --- | --- |
| S3 fix | `finmesh/sharing/node.py`, `finmesh/sharing/ldp.py` | Dummy releases, range-end time field, memo per record and epoch, ledger per account (or token) and epoch |
| Sized token budgets | `finmesh/schemas/token_budgets.json`, `token_budget()` | Used by every protocol run; A1 reports the protocol budget, this run's sized budget, and 250,000 |
| A4 linkability across epochs | `finmesh/training/attacks.py` | Rotation simulated at mid-validation (validation sits inside one 7-day epoch); the true record ranked among up to 99 decoys by similarity; hit@1 against chance; S3 re-released per half |
| A5 membership inference on S4 | same file | Does S4's disclosure (deviations, magnitudes, embedding) reveal the autoencoder's training rows? Strong classifier against chance |
| A6 query leakage | same file | A responder's prediction of its own label: own score, then plus the requests it received |
| Gate G2 evidence | `finmesh/eval/g2.py`, `finmesh g2` | Per dataset: H1a–H1d and PT2 on validation, and the three G2 risk checks from the proposal |
| Thin demo slice | `finmesh/demo/slice.py`, `finmesh demo-slice` | One alert end to end through real tokens, signed requests and S2 responses; noisy-OR fusion; placeholder rule-based typology; incident card and ledger; latency against PT6 (3 s) |
| Tests | `tests/unit/test_week9.py`, `tests/unit/test_privacy.py`, `tests/unit/test_x1.py`, `tests/integration/test_real_data_week9.py` | |

### Design choices to review

- **A4 needs a simulated rotation.** Validation (windows 39–50) lies inside one 7-day epoch (windows 28–55), so no real rotation happens in it. The test split will hold one; A4 at test will use it.
- **A5 targets S4's disclosure, not a global model.** The global DP model arrives in weeks 10–12, and its membership inference is X5.
- **A6 is measured, not prevented.** The requester's bucket travels in the clear by design (PD needs it). A6 shows how much a responder learns about its own account from being asked.
- **The demo slice's typology is a placeholder.** It is a handful of readable rules on the account's own features. The typology catalogue and the supervised attributor are weeks 13–14. The slice proves the path and measures its latency; it makes no attribution claim.

## What I ran here (results)

| Check | Result |
| --- | --- |
| CI mirror | All steps pass, including `finmesh demo-slice` and `finmesh g2` on the fixture |
| S3 | Replies look the same whether or not a record exists; a dummy is memoised and charged once; the time field is the range end |
| A4 on hand-built records | Identical records link perfectly (hit@1 = 1, chance 0.01); fresh releases at ε = 0.5 fall to chance; at ε = 400, near-perfect again |
| A6 on a hand-built case | When peers only ask about positives, requests lift the responder's AUC from 0.5 to above 0.8 |
| Fixture pipeline | All attacks run; A4 at S3 is at chance after the fix (before: 0.12 against 0.04) |
| Demo slice on the fixture (budget raised so it alerts) | 20 sessions, p95 0.014 s |

At stress scale (32 M rows, one seed):

| Measure | Value |
| --- | --- |
| One seed, all 25 configurations, 11 protocol runs and the audit with A1–A6 | 7,164 s (119 min; about 30 min of it shared the two CPUs with a CI run) |
| Protocol time per level | S1 (with the OPRF work) slowed by the CI run; S2, S4 and PD about 320–550 s; S3 about 410 s each (every request now gets a record) |
| S3 answers | 1,479,187 records per level (real or dummy); "no record" only when the ε cap is spent: ε = 2: 27, ε = 4: 1,538, ε = 8: 8,487 |
| A4 at stress | S2 and S4 hit@1 0.46 against chance 0.013; S3 at chance (0.013–0.018) at every ε |
| A5 | 80,000 rows; AUC 0.50 (the stress set's features are random, so chance is expected) |
| Peak memory | 5.4 GB in the S3 runs; after the fix below, the S3 phase peaks at 2.8 GB and the run's peak is evaluation, 3.8 GB as in week 8 |

Three fixes came from these runs:

- **Release speed.** Randomised response ran field by field in Python, 376 µs per S3 release; about 9 minutes per S3 level once every request got a record. It is now vectorised over the 20 fields: 15 µs, with keep rates checked against e^ε/(e^ε + k − 1).
- **S3 memory.** Answers are gathered in chunks of 200,000 and records stored as 16-bit integers. Every field fits, including the embedding, already clipped to that range. Measured again at stress scale with S1, S2 and S3 (ε = 2): the S3 phase falls from 5.4 to 2.8 GB.
- **The first full stress run hit my 2-hour limit** because of the slow releases. The second completed.

Real HI-Medium sends about 6 times fewer requests than this stress set. Expect about 70 minutes per dataset with three seeds, and a peak near 2.5 GB.

## What you run on your machine

About 2.5 hours of machine time, mostly step 2.

### 1. Update and check (5 min)

```bash
cd ~/FinMesh
git pull
uv sync
bash scripts/ci_local.sh
```

### 2. Rerun X1–X3 and the full audit (about 65 min per dataset)

```bash
uv run finmesh x1 --dataset HI-Medium
uv run finmesh x1 --dataset LI-Medium
```

This overwrites `docs/eval/x1_*`, `x3_*`, `audit_*` and the figures. The week-8 artifacts stay in `data/artifacts/week08/`; the new ones go to `week09/`.

### 3. Demo slice (about 5 min per dataset, mostly setup)

```bash
uv run finmesh demo-slice --dataset HI-Medium
uv run finmesh demo-slice --dataset LI-Medium
```

Writes `docs/eval/demo_slice_<ds>.md` with the latency and an example incident card.

### 4. Gate G2 evidence (seconds)

```bash
uv run finmesh g2
```

Writes `docs/gates/G2_evidence.md`. I will write the G2 decision note from it.

### 5. Tests and push

```bash
uv run pytest -m real_data -v
git add docs/eval/ docs/gates/
git commit -m "Week 9: G2 evidence, attacks A4-A6, demo slice on real data"
git push
```

**What to look for:**

- **S3:** leakage should now fall toward S1's as ε shrinks, and A4 at S3 should be near chance.
- **A1:** hashing ÷ OPRF at the protocol budget. Expect about 11 on HI-Medium and about 8 on LI-Medium, so PT2 may fail on LI-Medium. That is a result; it says how tight budgets must be.
- **A4 at S2, S4 and PD:** expect well above chance. Deterministic records link an account across a rotation.
- **Demo slice:** p95 well under 3 s.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `service_refused` above 0 | A bank's legitimate use exceeded its sized budget | Send me the page; the sizing rule may need more headroom |
| `G2 page left unchanged` | No week-8 or week-9 artifact for HI- or LI-Medium | Run step 2 first |
| Demo slice reports no sessions | No alert with a counterparty at another member | Only expected on the fixture |

## Week-9 checklist against the plan

- [x] S3 existence fix and per-epoch releases (A16)
- [x] Token budgets sized to legitimate use (A16)
- [x] Attacks A4 (linkability across epochs), A5 (membership inference on S4), A6 (query leakage)
- [x] H1b sensitivity against the strongest pooled configuration
- [x] Gate G2 evidence page
- [x] Thin demo slice: one node, one alert, one request, one attribution, with latency
- [ ] Done when: X1–X3 and A1–A6 on validation for HI- and LI-Medium, demo slice timed, G2 evidence pushed (your steps 2–5); then the G2 decision note
- Week 10: the federated DP neural scorer (G3 track)
