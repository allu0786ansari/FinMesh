# Week 13 run log · 18 – 24 Jan 2027 · Attribution by sharing level (X6) and the real-bank check

**Goal:**
- RQ3, part 1: does what banks share help an analyst name the laundering pattern of a case? Build the typology catalogue, the supervised attributor and three baselines, and run X6 by sharing level.
- External validity of the headline: rerun X1 on a federation of real banks only (A64), as the proposal's secondary partial-participation analysis.

**State:** code complete and tested (unit cases, fixture pipelines, stress scale). One script runs every real-data step: `bash scripts/week13.sh`.

## Week-12 review (your run, pushed 31 Oct)

Gate G3 passed; the full note is `docs/gates/G3.md`. In short:

| Result | HI-Medium | LI-Medium |
| --- | --- | --- |
| A19 retune (proxy AUPRC at ε = 3) | 0.42 → 0.65 | 0.15 → 0.30 |
| DP window unit at ε = 10, share of centralised | 0.49 → **0.78** | 0.38 → **0.96** |
| H2a / H2b on validation | no / no | yes / yes |
| Membership attack AUC | 0.50 (even non-private) | 0.50 |
| DP scorer added to the local detectors | +0.0006 (CI includes 0) | +0.006 at ε = 10 |

The rule applied on HI-Medium: **the detector stays local**, and the DP scorer is reported as a finding. Paper message: collaborate on cases (RQ1), not on models (RQ2).

### Your decisions (31 Oct)

- Week 13: the attributor and baselines; week 14: the language-model narrative.
- Add the real-bank (A64) X1 check this week.
- The sealed test stays closed until week 18.

## Amendment A20 (pre-registered and pushed before any week-13 code: commit `7855812`)

- **Levels:** S0, S1, S2, S3 (ε = 2) and the pooled oracle (ceiling), each with its frozen G2 fusion and linking rule.
- **Unit:** every pattern-labelled validation scheme, attributed through the incident holding most of its alerted accounts within 72 h; undetected schemes count as wrong.
- **What each level reveals to the incident's owner:**
  - S0: its own account-windows' features.
  - S1: adds the case's cross-bank structure (accounts, banks, span).
  - S2: adds other banks' record counters.
  - S3: the same counters through local DP.
  - Oracle: every row's pooled features.
- **Attributor:** multinomial LightGBM, cross-fitted on the two time halves of validation.
- **Baselines:** majority class; a rule-based shape detector; catalogue signature matching.
- **H3a (validation):** S2 − S0 attributor accuracy, 95% CI above 0, and S2's attributor above the majority and rule baselines.
- **Real-bank check:** X1 on A64, S0–S4 + oracles, seeds 0–2, no sweeps, no audit. Secondary; decides no hypothesis.

## What was built

| Item | Where | Notes |
| --- | --- | --- |
| Typology catalogue | `finmesh/schemas/typology_catalogue.json` | 8 AMLworld patterns: description, stage, shape signature, red flags, review actions; the rule list |
| Mapping protocol | `docs/protocol/attribution_mapping.md` | **Needs your review (pass 2) before the run**, see step 1 below |
| X1 hooks | `finmesh/training/x1.py` (`only`, `return_scores`, `evaluate_configs`) | Defaults are the frozen X1; X6 reuses the frozen levels exactly |
| X6 | `finmesh/training/x6.py`, `finmesh x6` | Incidents per level, level-limited features, attributor, baselines, scheme bootstrap, H3a |
| Real-bank path | `finmesh federation --option A64`; option-aware names in `labels`, `features`, `x1` | B8 outputs keep their exact names, so the frozen G2 pages are untouched |
| Runner | `scripts/week13.sh` | Resumable |
| Tests | `tests/unit/test_week13.py`, `tests/integration/test_real_data_week13.py` | |

### Design choices to review

- **The owner's view.** An incident is attributed by the bank holding most of its rows, because that bank's analyst opens the case. Its own features are always available; other banks' information arrives only through the level's channel.
- **Records carry counters, not shape counts.** The S2 record holds 10 bucketed counters (fan-in, fan-out, amounts, pass-through, ...) but not the neighbourhood counts (cycles, scatter-gather). So the rule and catalogue baselines read the shape from the owner's own features at every level. This is deliberate: it matches what the protocol actually shares.
- **No text retrieval.** The proposal's "retrieval-only" baseline becomes catalogue signature matching, because incident evidence is numeric. Text retrieval returns in week 14 for the narrative's context passages.
- **Stage accuracy is not reported.** Every AMLworld pattern is a layering structure, so the stage distribution is degenerate, as the proposal anticipated.

## What I ran here (results)

| Check | Result |
| --- | --- |
| Catalogue | 8 entries; every signature uses the declared shape features; rules only name catalogue patterns |
| Scheme → incident | Most accounts, then most rows, then lowest id |
| Information per level | S0 has only own features; S1 adds structure; S2 adds 20 record aggregates from other banks only; S3 the same through k-RR; oracle the pooled features |
| Rules and catalogue matching | Each rule fires in order; missing evidence falls through to RANDOM; signature matching finds FAN-OUT and CYCLE prototypes |
| Attributor | On separable synthetic cases: accuracy > 0.9 and above the majority class; undetected schemes get no prediction |
| H3a logic | Holds for a 0.55 → 0.85 improvement; not for equal accuracy |
| Fixture pipelines | X6 end to end; the A8 real-bank path (membership, labels, both feature views, X1) with `_A8` names, B8 files untouched |
| Fixture limitation | The fixture's alert budget rounds to 0 alerts (about 360 accounts), so the fixture checks plumbing only; the stress run below exercises attribution |
| CI mirror | All steps pass |

At stress scale (SCALE-Tail, 32 M rows):

| Step (one seed) | Time | Peak memory | Notes |
| --- | --- | --- | --- |
| X6: the frozen levels (S0, S1, S2, S3 at ε = 2, oracle) | 32 min | 3.5 GB | Shared the 2 cores with the CI run; most of it is the X1 core (detector, oracle, relational oracle, records, three protocol runs) |
| X6: incidents, level features, attribution, metrics | 1.2 min | | 2,302 incidents at S0, 534–641 at S1–S3, 118 at the oracle |

The stress set is signal-free and all 40 of its validation schemes are CYCLE, so its accuracies mean nothing; it confirms the full path runs at Medium scale. On your machine expect **about 1–1.5 hours of X6 per dataset** (3 seeds). The A64 check scores only the 64 member banks' accounts, so its labels, features and X1 are lighter than the B8 runs: **about 1–2 hours per dataset**. Total **about 5–7 hours**; run it overnight.

## What you run on your machine

### 1. Update, review the mapping, check (about 15 min)

```bash
cd ~/FinMesh
git pull
uv sync
bash scripts/ci_local.sh
```

Then read `docs/protocol/attribution_mapping.md` and `finmesh/schemas/typology_catalogue.json`. Write "agreed" (or your change) in the **pass 2** row of the review table, and commit before running:

```bash
git add docs/protocol/attribution_mapping.md
git commit -m "Attribution mapping: owner review (pass 2)"
```

### 2. Run everything (unattended)

```bash
bash scripts/week13.sh 2>&1 | tee week13.log
```

For each of HI-Medium and LI-Medium, it runs:

1. `x6`: attribution by sharing level, writing `docs/eval/x6_<ds>.md`.
2. `federation --option A64`, then `labels`, both feature views and `x1` on A64, writing `docs/eval/x1_<ds>_A64.md` and `docs/eval/features_<ds>_A64*.md`.
3. Finally, `pytest -m real_data`.

Interrupted? Run the same command again.

**What to look for:**

- **X6:** attributor accuracy at S0 against S2 (H3a), and how close S2 gets to the oracle.
- **A64:** linked detection at S0 against S1/S2, and how much smaller the gain is when most scheme legs sit at banks outside the federation.

### 3. Push

```bash
git add docs/eval/ docs/protocol/ week13.log
git commit -m "Week 13: X6 attribution and the A64 real-bank check on real data"
git push
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `membership_A64.parquet missing` | The federation step did not run | `uv run finmesh federation --dataset <ds> --option A64` |
| `features_..._A64_v3/meta.json missing` | A64 features not built | Re-run the script; it builds them before X1 |
| X6 or X1 slow | Several levels and seeds per dataset | Expected; leave it running |
| Out of memory | Another heavy process | Close other programs |

## Week-13 checklist against the plan

- [x] Typology catalogue and mapping protocol (pass 1)
- [x] Supervised attributor, rule-based and catalogue baselines, majority class
- [x] X6 by sharing level, with the oracle ceiling
- [x] Real-bank federation path (A64) for the secondary X1 analysis
- [x] Owner's review of the mapping (pass 2), then the real-data run (31 Oct)
- Week 14: the constrained narrative with llama3.2:3b and the grounding test (H3b)
