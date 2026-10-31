# Week 14 run log · 25 – 31 Jan 2027 · Coverage curve and the constrained narrative (H3b)

**Goal:**
- RQ3, part 2: give the analyst a short, grounded narrative for each detected case, written by a local model that cannot change the decision, and measure how often its raw output is grounded (H3b).
- External validity of the headline: replace the single real-bank point (A64) with a **coverage curve**, the sharing gain as the federation grows from 10% to 100% of accounts.

**State:** code complete and tested (unit cases with a scripted model, fixture pipeline, stress scale). One script runs every real-data step: `bash scripts/week14.sh`. It needs Ollama with llama3.2:3b on your machine.

## Week-13 review (your run, pushed 31 Oct)

### X6: attribution by sharing level

| | HI-Medium (551 schemes) | LI-Medium (93 schemes) |
| --- | --- | --- |
| Attributor accuracy, end to end: S0 → S1 → S2 → S3 (ε = 2) | 0.146 → 0.187 → 0.189 → 0.192 | 0.122 → 0.108 → 0.151 → 0.104 |
| Oracle (all data pooled) | 0.179 | 0.161 |
| Majority / rules / catalogue at S2 | 0.111 / 0.102 / 0.110 | 0.136 / 0.065 / 0.122 |
| S2 − S0 [95% CI] | **+0.042 [0.016, 0.068]** | +0.029 [−0.032, 0.090] |
| H3a on validation | **met** | not met |

What it means:

1. **H3a holds on HI-Medium.** Sharing helps name the pattern, and S2's attributor beats every baseline.
2. **The gain arrives at S1** (cross-bank structure: how many accounts and banks, over what span). Other banks' record counters (S2) and their noisy version (S3) add almost nothing more. That is the same lesson as RQ1: the link is what matters.
3. **The oracle is no better than S2**, so more data about the same incident does not help. The limit is the incident evidence itself: a 3-member incident at the primary budget shows only a few rows of an 8-pattern problem.
4. **Absolute accuracy is low** (about 0.19 end to end, 0.22 on detected schemes, against 0.125 for chance over 8 patterns). An unqualified label would mislead the analyst. This is why A21 shows the label **only above a confidence threshold τ**, and otherwise says UNATTRIBUTED with three candidates.
5. **LI-Medium is underpowered** (93 schemes); its intervals cover 0.

### A64: the real-bank federation

The 64 largest banks hold **4.7% of accounts**, only 95 validation schemes touch two members (522 under B8), and linked detection is near zero at every level (HI 0.002–0.006, LI 0). This is a property of AMLworld: its account mass sits in tens of thousands of small bank ids, which no realistic consortium would contain. One point at 4.7% says little. Real partnerships recruit the largest banks first (TMNL: the five largest Dutch banks; the top three hold about 90% of Dutch current accounts), so the useful question is **how the gain grows with coverage**. A21 answers it with the curve below.

### Your decision (31 Oct)

Proceed with both recommendations: the coverage curve, and the constrained narrative with abstention.

## Amendment A21 (pre-registered and pushed before any week-14 code: commit `77c5320`)

- **Coverage curve (secondary, no hypothesis):** federations `B8c{p}`, p ∈ {10, 25, 50, 75, 90}% of accounts. Banks are ranked by accounts and added largest first until the share reaches p, then grouped into 8 members by the B8 balancing rule. X1 as for A64 (S0–S4, propagation, oracles; seeds 0–2; no sweeps or audit). End points: A64 (4.7%) and B8 (100%).
- **Narrative sample:** S2, seed 0, up to 200 detected validation schemes, up to 25 per pattern.
- **Abstention:** τ is the smallest value in {0.30, 0.35, …, 0.95} whose selective accuracy on all detected validation schemes is at least 0.5 with coverage at least 10% (selective classification, Geifman and El-Yaniv 2017). Below τ the case is UNATTRIBUTED with its top three candidates.
- **Model call:** llama3.2:3b, JSON-only, temperature 0; a reply that fails the check gets one schema-constrained retry, then a template narrative.
- **H3b:** grounding rate of the raw first replies ≥ 0.95. Grounded = valid JSON, typology equal to the one shown (or UNATTRIBUTED), every cited field present in the evidence. Numeric grounding, retry and fallback rates and latency are reported alongside.

### What the research said, and how it shaped the design

| Source | Finding | Design choice |
| --- | --- | --- |
| Co-Investigator AI (2025), SAR drafting | Narratives must be checked against source data; models invent amounts and identities | The model gets only a fixed evidence template; every cited field and every number is checked against it |
| SumUp narrative study (2025) | ROUGE scores are poor proxies, and LLM judges are biased | Grounding is checked by rules, not by another model |
| Ollama structured outputs | Schema-constrained decoding plus temperature 0 is reliable, but outputs should still be validated | JSON-only first (so H3b measures the model, A7), schema retry only as repair |
| Geifman and El-Yaniv (2017) | Selective classification: trade coverage for accuracy with a confidence threshold | τ chosen by a fixed rule, before the narrative run |
| FATF guidance | All rights reserved | Context text is our own catalogue, not FATF passages |
| TMNL, U4 | Real partnerships start from the largest banks | Coverage curve adds banks largest first |

## What was built

| Item | Where | Notes |
| --- | --- | --- |
| Coverage federations | `finmesh/data/consortium.py` (`B8c50` etc.), `finmesh federation --option B8c50` | Largest banks first until the share is reached, then the B8 grouping; every later step takes the option as before |
| Coverage curve | `finmesh/eval/coverage.py`, `finmesh coverage` | Reads each point's X1 artifact and universe counts; table, gain table and figure. Missing points are listed, never invented |
| X6 hooks | `finmesh/training/x6.py` (`levels`, `keep_tables`, `proba_out`) | Defaults unchanged; the narrative reuses the exact S2 attributor (same seed, same cross-fitting) |
| Narrative | `finmesh/attribution/narrative.py`, `finmesh narrative` | Abstention, stratified sample, evidence template, prompt, JSON-only call, schema retry, template fallback, checks, latency; localhost only |
| Narrative page | `finmesh/attribution/narrative_report.py` | H3b, reply quality, latency, risk-coverage table, per pattern, three example cases; every case in a `.jsonl` file |
| Runner | `scripts/week14.sh` | Resumable; checks Ollama first so it never fails after hours of coverage runs |
| Tests | `tests/unit/test_week14.py` (16), `tests/integration/test_real_data_week14.py` | A scripted fake model replaces Ollama in tests and CI |

### Design choices to review

- **The model never decides.** Typology from the attributor (only above τ); evidence from a template; review actions from the catalogue. The model only writes sentences, and its output is checked before anyone sees it.
- **What the evidence holds.** Exactly what S2 reveals to the case owner: 13 fields about its own accounts, 4 about the linked case (accounts, members, account-windows, hours), and 10 bucketed counters from other members, shown as ranges ("at least 5, below 10"). No account ids, names or raw transactions.
- **H3b is measured on the first reply, unrepaired.** The schema retry and the template make the delivered text safe, but they are not counted as grounded first replies.
- **Numeric grounding is reported, not part of H3b.** A21 defined H3b without it; it is the strictest check (a model writing "about 10" when the evidence says 12 fails it).
- **Smaller samples.** If fewer than 200 detected schemes exist, all are used; with `--n` smaller than 200 the per-pattern cap shrinks evenly so no pattern is crowded out.

## What I ran here (results)

| Check | Result |
| --- | --- |
| Coverage spec | `B8c50` parses; A-options, 0%, 100% and malformed specs are refused; banks are taken largest first and the last one crosses the target |
| Coverage curve | Points sorted by measured coverage; table, gain table and figure; missing points listed |
| Abstention | τ is the smallest qualifying value; none when no threshold reaches 50% accuracy or 10% coverage |
| Sample | Per-pattern cap, fill, deterministic, all schemes when fewer than n |
| Evidence and prompt | Spans in hours, NaN-safe maxima, bucket ranges; only fields with a value are shown and citable; only the assigned entry as context (three candidates when unattributed); 2,800–3,500 characters (about 700–900 tokens), inside the 2,048-token context; replies capped at 320 tokens |
| Checks | Wrong typology, invented field, bad JSON and stray numbers are each caught |
| Retry and fallback | Bad first reply → schema retry restricted to the assigned typology and real fields; transport errors → template, which is numerically grounded by construction |
| Attributor probabilities | Rows sum to 1 for detected schemes, NaN otherwise; their argmax equals the attributor's predictions, which are unchanged |
| Driver | End to end with a scripted model; fails fast with a clear message when Ollama is down; refuses non-local endpoints |
| Fixture pipeline | `federation --option B8c50`, labels, both feature views, X1, `coverage` |
| Stress scale (SCALE-Tail, 32 M rows, scripted model) | S2 attributor alone: 18 min, peak memory 3.2 GB (sharing the 2 cores with the CI run); the signal-free set detects 1 of its 40 schemes, which is narrated, checked and rendered end to end. Confirms the real path at Medium scale; its rates mean nothing |
| CI mirror | All steps pass |

There is no Ollama or model download in this environment, so **llama3.2:3b itself has not been run here**; your run is the first real measurement of H3b. On your machine the G0 probe took 19.5 s per call (p50) with a much shorter prompt, so **the 30 s latency target is at risk**; latency is reported, not a hypothesis.

## What you run on your machine

### 1. Update and check (about 15 min)

```bash
cd ~/FinMesh
git pull
uv sync
bash scripts/ci_local.sh
```

### 2. Start the model (once)

```bash
ollama serve            # in a second terminal, if it is not already running
ollama pull llama3.2:3b
```

### 3. Run everything (unattended)

```bash
bash scripts/week14.sh 2>&1 | tee week14.log
```

For each of HI-Medium and LI-Medium it runs:

1. The coverage curve: for each of `B8c10`, `B8c25`, `B8c50`, `B8c75`, `B8c90`: membership, labels, both feature views, X1 without sweeps or audit. Then `finmesh coverage`, writing `docs/eval/coverage_<ds>.md` and `.png`.
2. The narrative: `finmesh narrative`, writing `docs/eval/narrative_<ds>.md` and `narrative_<ds>_cases.jsonl`.
3. Finally, `pytest -m real_data`.

Expected time, from your week-13 timings: each coverage point takes about 10–35 min (bigger federations take longer), so about **4–5 hours** for both datasets; each narrative takes the S2 attributor (about 6 min) plus 200 model calls at about 20–40 s each (**about 1.5–2 hours**). Total **about 8 hours**; run it overnight.

Interrupted? Run the same command again. Ollama not running? The script stops at the start with instructions. To run only the coverage curve: `SKIP_NARRATIVE=1 bash scripts/week14.sh`.

**What to look for:**

- **Coverage:** where S2 − S0 becomes clearly positive, and whether S2 keeps most of the relational-oracle gain at partial coverage.
- **Narrative:** H3b against 0.95; the fallback rate; latency p95 against 30 s; τ and how many cases get a label.
- **Read 10–20 cases** in `narrative_HI-Medium_cases.jsonl`. Are they useful to an analyst? Your judgement here goes into the paper's qualitative section.

### 4. Push

```bash
git add docs/eval/ docs/protocol/ week14.log
git commit -m "Week 14: coverage curve and the constrained narrative on real data"
git push
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `Ollama is not reachable` at the start | `ollama serve` not running, or the model not pulled | Start it and `ollama pull llama3.2:3b`; or `SKIP_NARRATIVE=1` |
| Narrative latency far above 30 s | Another heavy process, or the model on CPU while X1 runs | Let the coverage steps finish first (the script already orders them so) |
| Many template fallbacks | The model ignores the format | Report as is; it is a finding about 3B models. Do not change the prompt after seeing results |
| `membership_B8c50.parquet missing` | Federation step skipped | `uv run finmesh federation --dataset <ds> --option B8c50` |
| Out of memory on `B8c90` | Close to full scale, like B8 | Close other programs; the step resumes |

## Week-14 checklist against the plan

- [x] Week-13 review; A21 pre-registered from research
- [x] Coverage federations and the coverage curve
- [x] Abstention threshold, evidence template, constrained narrative with retry and fallback
- [x] H3b, numeric grounding, latency; example cases for the paper
- [ ] Real-data run (your machine, with Ollama)
- Weeks 15–17: the demo path and analyst console (incident card with the narrative)
