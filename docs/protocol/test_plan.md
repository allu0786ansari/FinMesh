# Sealed-test execution plan (week 18)

**Status: draft for the owner's sign-off. The seal is closed: no test label has been read.**
**Frozen commit:** 05d1714
**Signed off by:** — Allaudin Ansari · **Date:** — 03 November 2026

This page lists every opening of the sealed test, in order, with its seeds, metrics and decision rules, so the test is run exactly once and nothing is chosen after a result is seen. The rules come from `docs/protocol/preregistration.md` (sections 3–8) and amendments A9–A23 in `docs/proposal/CHANGES.md`. Amendment **A24** (below and in `CHANGES.md`) fixes how each validation-fitted parameter is carried to the test; it changes no model, feature, fusion rule, threshold, prompt or hypothesis.

## 1. The freeze

- **Validation work is closed** (owner decision, 2 Nov 2026): no further tuning, retuning or selection on validation. Every configuration below is the one reported on validation in weeks 5–14.
- **Code:** the commit named above, once signed. `finmesh test-preflight` refuses to call a run ready unless the working tree is clean and no code file (`finmesh/`, `scripts/`, `pyproject.toml`, `uv.lock`) differs from that commit; documents and results may be committed between runs.
- **Two code changes since the validation runs, neither tuning:**
  1. *Determinism.* A4 linkability (week 9 audit) grouped records in a thread-dependent order, and the relational oracle summed counterparty probabilities in a thread-dependent order (differences of 1e-16). Both now use a fixed order, so the same command gives the same scores bit for bit; this is what lets the access log carry a digest of the scores. Validation A4 values move by a few points between runs of the old code and are reported from the new one; every other validation number is reproduced exactly (checked on the fixture, `docs/runlog/week-18.md`).
  2. *Test mode.* The runners gained the test path below; on validation they reproduce their frozen outputs exactly (same check).

## 2. How a parameter fitted on validation reaches the test (amendment A24)

| Item | On validation (reported) | On test |
| --- | --- | --- |
| Models (S0 LightGBM per member, oracle, autoencoders, unsupervised floor) | Trained on the training partition | **The same training**, same seeds; nothing is refitted on validation |
| S0 and oracle calibration (isotonic per member) | Held-out end of training | **Fitted on all of validation, applied at test** (section 6) |
| Fusion stacker (A13), every sharing configuration; relational oracle (A14) | Cross-fitted on the two validation halves | **Refitted per member on all validation candidates, frozen.** Its training inputs are the frozen validation run's evidence features (calibration from the end of training, as reported). Within a member and window a shift of the own-logit feature changes only the stacker's intercept, so the alert ranking is unaffected |
| Noisy-OR flag precision (secondary rule) | Member's precision on the other half | Member's precision on all validation candidates |
| FPR thresholds (0.1%, 0.01%) | Held-out end of training | **From validation** (section 3) |
| Token budgets (A16) | Twice the largest legitimate validation use | Unchanged |
| X6 attributor, majority class, catalogue matching | Cross-fitted on the validation halves | **Fitted on all detected validation schemes**, per level and seed, applied to test schemes; the rule baseline needs no fit |
| Narrative τ (A21 rule) | Smallest τ with selective accuracy ≥ 0.5 and coverage ≥ 10% | **The validation value, frozen**; test cases use the X6 test attributor's probabilities (seed 0) |
| Narrative frequency top-3 baseline | Other validation half | All detected validation schemes |
| X5 neural scorers (H2a, H2b) | Trained once (week 12), weights saved | **The saved week-12 weights, scored on test.** No DP model is retrained, so no privacy budget is spent again. The non-private local-only MLPs were not saved; they are retrained identically (same seed, data and steps) |
| Ensemble stackers (G3 rule) | Cross-fitted on the validation halves | Refitted per member on all of validation, frozen |
| Membership audit (A19) | Training accounts only | **Not rerun**: it has no validation or test component |

**The seal.** Each run scores the test partition from features only, computes a SHA-256 digest of every score, and only then opens the seal once per experiment, dataset and seed through `finmesh.eval.sealed.open_sealed_test`; the access log records the time, configuration, seed, git commit and the digest before any label is returned. A second opening of the same experiment and seed is refused before any work starts. Each seed's result is saved as soon as it exists; a rerun continues from the next seed. Only a run that crashed after its opening and before saving may be rerun, with `--allow-repeat`, and the log marks it as a repeat. Every repeat is reported.

## 3. Seeds and statistics (section 7)

- **X1 headline configurations, seeds 0–4:** S0, the oracle, the relational oracle (the H1b ceiling, A14), S2 and PD at τ ∈ {2, 3, 4}. **Every other X1 configuration, seeds 0–2:** S1, S4, S3 at ε ∈ {0.5, 1, 2, 4, 8}, noisy-OR and k-of-n, propagation, oracle + propagation. The leakage audit (A1–A6) runs on seed 0, as on validation.
- **X6:** seeds 0–2 (its frozen design). **Baselines** (secondary analyses): seed 0, as at G1; the headline S0 and oracle seeds are X1's. **X5 and the ensemble:** the seeds of the saved week-12 run (0–2). **Narrative:** seed 0.
- **Bootstrap:** 1,000 scheme replicates; **1,000** account replicates for window metrics at test (200 on validation); bootstrap seeds fixed at 0.
- **Combining seeds:** per-scheme outcomes averaged over a configuration's seeds; every paired comparison averages both sides over the seeds both ran (a 0–2 configuration against S0 uses S0's seeds 0–2).
- **Holm:** across every sharing configuration's primary (stacker) fusion compared with S0 — S1, S2, S4, S3 at five ε and PD at three τ, 11 comparisons — separately for linked and any-alert detection; two-sided, α = 0.05.

## 4. Decision rules (frozen; a missed target is a finding)

| ID | Rule on test | Where |
| --- | --- | --- |
| **H1a (primary)** | On **HI-Medium**, linked detection at the primary budget: S2 − S0 paired 95% CI excludes 0 with Holm-adjusted p < 0.05, and S2 is above the random-alert baseline | `test-x1` |
| H1b | S2 recovers ≥ 0.60 of the relational oracle's gain over S0 (CI reported); assessed only if oracle − S0 meets the G1 criterion (CI excludes 0, estimate ≥ 0.05). The plain-oracle ratio is reported alongside | `test-x1` |
| H1c | S1 and S3 (ε ≤ 2): upper 95% bound of (attack − prior) TPR at 1% FPR ≤ 0.05 on every assessable A2/A3 target (A15); S4 above S2 and S3's monotonicity in ε reported | `test-x1` (seed 0 audit) |
| H1d | PD reaches ≥ 0.80 of S2's gain with records disclosed on < 0.5 of S2's accounts; each τ reported, S1 as the reference | `test-x1` |
| H2a | DP scorer (window unit, member view) at ε ≤ 10 reaches ≥ 0.70 of the centralised MLP's AUPRC and exceeds the local-only MLP; each ε reported | `test-x5` |
| H2b | At the same ε, window − account AUPRC has a 95% CI above 0; each ε reported | `test-x5` |
| PT4b | S0-BG − S0-B AUPRC, paired account bootstrap, CI excludes 0 | `test-baselines` |
| H3a | S2 − S0 attributor accuracy CI above 0, and S2's attributor above the majority and rule baselines (CIs above 0) | `test-x1` (X6) |
| H3b | Raw-reply grounding ≥ 0.95 over the narrated cases (Wilson CI); strict (A23) grounding, claim consistency, top-1/top-3 accuracy reported | `narrative --test` |
| Secondary | LI-Medium (every rule above); any-alert detection; FPR operating points; touch label; time to detect; artefact ablation (oracle − S0 gap with and without the 8 artefact features); decomposition (S0 alerts with pooled linking); ensemble gain at each ε (G3 rule, reported); HI-Small and LI-Small X1 as replication | as listed |

`finmesh test-report` writes `docs/eval/test/RESULTS.md` with every rule above applied mechanically to the artifacts.

## 5. Run order, commands and time

Each block is one evening's run on your machine (CPU, about 5.8 GB). Times scale the validation timings by two (each test seed rebuilds the validation side to fit the frozen parameters, then scores the test side) and are rough; the run logs give the real ones.

**0. Before anything (15 min).** Sign this page (section 7), then:

```bash
git pull && uv sync --locked
bash scripts/ci_local.sh                     # fixture dry run of every test command
uv run finmesh test-preflight --dataset HI-Medium
uv run finmesh test-preflight --dataset LI-Medium
```

Every line must read `ok` except the Ollama line on a night without the narrative.

**1. HI-Medium (about 7–8 h).** `bash scripts/week18.sh HI-Medium`, which runs in order:

| Step | Command | Openings | Estimate |
| --- | --- | --- | --- |
| X1–X3 + audit + X6 | `finmesh test-x1 --dataset HI-Medium` | 5 (seeds 0–4) | 3–4 h |
| Baselines | `finmesh test-baselines --dataset HI-Medium` | 2 (primary and touch label) | 0.5–1 h |
| X5 | `finmesh test-x5 --dataset HI-Medium` | 3 | 1–1.5 h |
| Ensemble | `finmesh test-ensemble --dataset HI-Medium` | 3 | 1–1.5 h |

**2. LI-Medium (about 8–9 h).** `bash scripts/week18.sh LI-Medium` (same four steps; X5 scoring is slower on LI, as on validation).

**3. Narratives (about 10–12 h; Ollama running).** `bash scripts/week18.sh narrative` runs `finmesh narrative --test` for HI-Medium (200 cases) then LI-Medium (up to 200 detected test schemes). It saves every case; if the model server stops, run the same command again and it resumes without a new opening.

**4. Replication and the results page (about 1 h).** `bash scripts/week18.sh small` runs `finmesh test-x1 --no-x6 --no-audit` on HI-Small and LI-Small, then `finmesh test-report`.

Total about 27–30 h of machine time over three or four nights; about 18 openings per Medium dataset including the narrative's, 5 per Small dataset. `finmesh sealed-log --dataset <ds>` lists them.

## 6. The blind review (after the test, before the narrative results are read)

Both of us rate the A23 validation review independently, each on our own copy:

- `docs/eval/narrative_HI-Medium_A23_review_allaudin.csv` (Allaudin)
- `docs/eval/narrative_HI-Medium_A23_review_ravi.csv` (Ravi)

**Order (owner decision, 3 Nov 2026):** the review is done after the test runs, not before. It decides no hypothesis and A23 is frozen whatever it shows, so its timing changes no test result. To keep the ratings blind to the test, neither rater reads the narrative test outputs (`docs/eval/test/narrative_*`, `docs/eval/test/RESULTS.md`, the narrative lines of the night-3 log) until both sheets are pushed; the X1, X5 and baseline results say nothing about the narratives and may be read. The commit times of the two sheets and of the test results record the order.

Neither opens `..._KEY_do_not_open.csv` or the other's copy. `finmesh narrative-review --dataset HI-Medium` then scores each rater, their agreement (linear-weighted Cohen's kappa for faithfulness and usefulness, kappa for preference), and the claim check against the cases both call faithful. The test run writes a fresh 30-case sheet of test narratives; rating it is optional and, if done, follows the same steps.

## 7. Sign-off

By signing, the owner confirms: the configurations, rules and order above; amendment A24; the seed and Holm choices of section 3; and that nothing here changes after the first opening. Fill in the three fields at the top (frozen commit = `git rev-parse --short HEAD` right after pulling this plan, before editing it), commit and push. Any later code change fails the preflight, so a fix found during the test needs a new amendment and a new signature, recorded here.
