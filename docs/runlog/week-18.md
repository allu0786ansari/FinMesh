# Week 18 run log · 22 – 28 Feb 2027 · The sealed test: freeze, test mode, dry run, sign-off

**Goal (proposal: week 18):** open the sealed test once, for the frozen configurations, and decide every pre-registered hypothesis on it.

**State (2 Nov, evening):** **ready for your sign-off; the seal is still closed.** As agreed (freeze, build, dry-run, sign-off), validation work is closed and every runner now has a test path. The whole test plan has been dry-run on the fixture, including the access log and the refusal of a second opening. **Nothing opens the test until you sign `docs/protocol/test_plan.md`.**

## What you decide now

1. **Read and sign the test plan** (`docs/protocol/test_plan.md`, 10 min). It lists every opening, its seeds, metrics and decision rule, and amendment **A24**: how each parameter fitted on validation is carried to the test. A24 changes no model, feature, fusion rule, threshold, prompt or hypothesis. Three choices in it are mine and need your yes:
   - **Seeds.** At test, the headline configurations of X1 run seeds 0–4 and the others seeds 0–2 (preregistration section 7). I count the **relational oracle** as headline, because A14 made it H1b's ceiling. Each comparison averages both sides over the seeds both ran.
   - **The Holm family** is every sharing configuration's stacker compared with S0: S1, S2 and S4, S3 at five ε, and PD at three τ. That is 11 comparisons, the most conservative reading of "across the sharing levels". H1a's S2 gain was +0.56 on validation, so this choice cannot decide it.
   - **X5 is not retrained.** The test scores the DP models saved in week 12, so no privacy budget is spent twice. Only the non-private local-only MLPs, which were not saved, are retrained, with the same seed, data and steps.
2. **The blind review, both of us, after the test** (about 45 min each; your choice, 3 Nov). Rate before either of you reads the narrative test results (`docs/eval/test/narrative_*`, `RESULTS.md`, the night-3 log); X1, X5 and baseline results are fine to read. Your copy is `docs/eval/narrative_HI-Medium_A23_review_allaudin.csv`; Ravi's is `..._ravi.csv`. The instructions are in section 3 below.

## What changed in the code

| Change | Why | Effect on validation results |
| --- | --- | --- |
| **Test mode for X1–X3 and the audit, with X6 on the same scores** (`finmesh test-x1`) | Each seed trains as on validation and re-runs the frozen validation side to fit the frozen parameters. It then scores test from features only, logs one opening with a SHA-256 of every score, and only then reads labels | None: one seed is now train → score a partition → evaluate. Validation X1 and X6 outputs are identical to before, number for number (fixture check) |
| **Baselines** (`test-baselines`): FPR points with validation thresholds, touch label, artefact ablation, decomposition, PT4b | Section 8 secondary analyses | Identical (fixture check) |
| **X5 and the ensemble** (`test-x5`, `test-ensemble`) | H2a, H2b and the G3 rule on test, from the saved week-12 models | No change on validation |
| **Narrative on test** (`narrative --test`) | H3b and top-k on test. It uses τ from validation and the X6 test attributor (seed 0). It saves every case, so if Ollama stops the same command resumes without a second opening | No change on validation |
| **The seal tightened** | `slices` refuses the test partition unless it has been opened. A runner refuses a second opening **before** hours of scoring, not at the end. Each opening logs the scores' digest | — |
| **Two determinism fixes** | The A4 audit grouped records in a thread-dependent order. The relational oracle summed probabilities in a thread-dependent order, which moved results by 1e-16. A rerun now gives bit-identical scores, so the digest means something | A4 numbers move by a few points between runs of the old code. Every other number is unchanged |
| **`finmesh test-preflight`** | Checks everything without reading a label: the code is unchanged since the signed commit, inputs exist, which seeds have already opened the test, Ollama, disk | — |
| **`finmesh test-report`** | `docs/eval/test/RESULTS.md`: every rule of the plan applied mechanically | — |
| **Two raters** (`narrative-review --prepare`, then `narrative-review`) | Each rater is scored alone. Their agreement uses Cohen's kappa (linear-weighted for faithfulness and usefulness), and the claim check is compared with the cases both call faithful | — |

## Checks done here

| Check | Result |
| --- | --- |
| Validation outputs before and after the refactor (fixture; X1 with sweeps and audit, 2 seeds; X6; baselines) | **Identical**, except A4, which differed between runs of the *old* code too; it is now deterministic |
| Two identical test runs | Bit-identical scores (same SHA-256) |
| Full test plan on the fixture (`test-x1`, `test-baselines`, `test-x5`, `test-ensemble`, `test-report`) | Runs end to end; 6 openings logged, one per experiment, seed and label variant |
| A rerun after a finished seed | Keeps the saved seed; no new opening |
| A lost result after an opening | Refused before any work; with `--allow-repeat` it reruns, gives the same digest, and is logged as a repeat |
| Narrative stopped mid-run (scripted model) | The rerun resumes at the next case with no second opening |
| Scale stress (SCALE-Tail, 32 M rows, one full test seed with sweeps, audit and X6) | **Not finished here.** It was stopped at the sandbox's 2 h limit while sharing both cores with the test suite. Resident memory stayed between 1.5 and 2.4 GB through the validation half. The test half frees the validation half first, so its peak should match: X1 on HI-Medium validation peaked at 1.75 GB. Your first night will give the real figure |
| New unit tests (`tests/unit/test_week18.py`, 10 tests) | All pass. The fixture budget is raised so there are real gains: per-configuration seeds, Holm, A6 after the opening, X6 on test, the narrative's inputs, resume, refusal and a logged repeat with an identical digest |
| Unit tests, coverage, lint, types, local CI mirror, gitleaks | 294 passed, coverage 81.67%; lint, types and gitleaks clean; the fixture dry run of every test command runs in CI (`test-x1` 88 s + 14 s) |

The fixture's budget yields almost no alerts, so its numbers are zeros. It tests the mechanics, not the science; the unit test raises the budget and checks real gains.

## Steps for you

### 1. Update and check (15 min)

```bash
git pull && uv sync --locked
bash scripts/ci_local.sh            # includes the fixture dry run of every test command
uv run finmesh test-preflight --dataset HI-Medium
uv run finmesh test-preflight --dataset LI-Medium
uv run finmesh test-preflight --dataset HI-Small --only x1
uv run finmesh test-preflight --dataset LI-Small --only x1
```

Every line should read `ok`, except `WARN` for "no frozen commit signed" (until step 2) and for Ollama on nights without the narrative. If a Small dataset shows `FAIL` for its features (they may never have been built in the pooled view), build them; this reads no test label:

```bash
uv run finmesh labels --dataset HI-Small && uv run finmesh features --dataset HI-Small \
  && uv run finmesh features --dataset HI-Small --view pooled      # then the same for LI-Small
```

### 2. Sign the plan (10 min)

Read `docs/protocol/test_plan.md`. If you agree, fill in its three header fields:

- **Frozen commit:** the output of `git rev-parse --short HEAD`, taken right after pulling;
- **Signed off by:** your name;
- **Date:** today.

Then commit and push (`git commit -am "Week 18: test plan signed" && git push`). From then on, the preflight fails if any code file differs from that commit. Documents and results can still be committed.

### 3. Blind review, both raters (about 45 min each, after step 4; before reading the narrative results)

Each of you opens **only your own copy** in a spreadsheet:

- Allaudin: `docs/eval/narrative_HI-Medium_A23_review_allaudin.csv`
- Ravi: `docs/eval/narrative_HI-Medium_A23_review_ravi.csv`

Do not open the `KEY_do_not_open` file or each other's copy, and do not discuss cases until both are done. For each of the 30 rows, use the evidence column only:

- **faithful A / faithful B:** `yes` if every claim in that narrative is supported by the evidence and its readings; `partly` if some claim is unsupported but none is contradicted; `no` if any claim contradicts the evidence.
- **useful A / useful B:** `1` no help to an analyst, `2` some help, `3` clearly helps decide what to check first.
- **prefer:** `A`, `B` or `same`.
- **notes:** anything that surprised you (optional).

Save as CSV with the same name, commit and push both files. Then:

```bash
uv run finmesh narrative-review --dataset HI-Medium
```

This writes `docs/eval/narrative_HI-Medium_A23_review_result.md` (each rater, agreement, claim check against both).

### 4. The test (three or four nights; plan section 5)

```bash
bash scripts/week18.sh HI-Medium 2>&1 | tee week18_HI-Medium.log   # night 1, about 7–8 h
bash scripts/week18.sh LI-Medium 2>&1 | tee week18_LI-Medium.log   # night 2, about 8–9 h
bash scripts/week18.sh narrative 2>&1 | tee week18_narrative.log   # night 3, Ollama on, 10–12 h
bash scripts/week18.sh small     2>&1 | tee week18_small.log       # about 1 h, then the results page
```

Each script runs the preflight first and stops if anything fails. If a script stops (power cut, Ollama stopped), run the same command again: finished steps are skipped, X1 continues from its next seed, and the narrative continues from its next case.

**Only if** `test-x1` crashed *after* opening a seed's test and *before* saving it, the rerun is refused with "already opened ... saved result is missing". Then run that one command by hand with `--allow-repeat`. The log marks it as a repeat and we report it. Never delete anything under `data/sealed/` or `data/test/`.

### 5. Push

```bash
git add docs/eval/test week18_*.log && git commit -m "Week 18: test results" && git push
```

I then write the results into this log and the paper tables.

## Machine-time estimate

| Run | Per Medium dataset | Note |
| --- | --- | --- |
| `test-x1` (5 seeds, sweeps, audit, X6) | 3–4 h | Each seed re-runs its validation side to fit the frozen parameters, then scores test. 1,000 account replicates at test |
| `test-baselines` | 0.5–1 h | |
| `test-x5` | 1–1.5 h | Scoring only, plus the local-only MLPs |
| `test-ensemble` | 1–1.5 h | |
| `narrative --test` | HI about 10 h, LI 2–4 h | As the A23 validation run |
| Small replication (`test-x1 --no-x6 --no-audit`) | about 30 min each | |
