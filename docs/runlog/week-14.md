# Week 14 run log · 25 – 31 Jan 2027 · Coverage curve and the constrained narrative (H3b)

**Goal:**
- RQ3, part 2: give the analyst a short, grounded narrative for each detected case, written by a local model that cannot change the decision, and measure how often its raw output is grounded (H3b).
- External validity of the headline: replace the single real-bank point (A64) with a **coverage curve**, the sharing gain as the federation grows from 10% to 100% of accounts.

**State (1 Nov):** first run done on your machine (31 Oct – 1 Nov). The coverage curve is final; the narrative failed H3b, mostly for reasons in my prompt, so A22 fixes it and a rerun is needed: `bash scripts/week14_rerun.sh`. The original plan for the first run is kept below for the record.

## Update 1 Nov: what the first run showed, and the A22 rerun

### Coverage curve (final)

| Federation (share of all accounts held) | HI S2 − S0 linked [95% CI] | Share of the B8 gain | S2 / relational oracle |
| --- | --- | --- | --- |
| A64 (4.7%) | 0.002 [−0.002, 0.007] | 0% | — |
| B8c10 | 0.056 [0.040, 0.074] | 10% | 1.21 [0.96, 1.55] |
| B8c25 | 0.148 [0.122, 0.176] | 26% | 0.95 [0.84, 1.09] |
| B8c50 | 0.354 [0.313, 0.393] | 63% | 1.05 [0.98, 1.14] |
| B8c75 | 0.485 [0.442, 0.528] | 86% | 0.96 [0.91, 1.00] |
| B8c90 | 0.531 [0.488, 0.571] | 94% | 0.96 [0.92, 1.01] |
| B8 (100%) | 0.562 [0.523, 0.603] | 100% | 0.98 [0.94, 1.02] |

- **The gain grows steadily with coverage.** There is no threshold to cross. LI-Medium has the same shape (39% of the gain at 25%, 80% at 50%).
- **The protocol keeps pace with pooling at every size.** S2 recovers 0.95–1.05 of the relational-oracle gain on HI-Medium at every point, and 0.68–0.84 on LI-Medium. H1b does not depend on who joins.
- **Presentation fixes (no rerun of X1).**
  - The x-axis is now the share of all accounts held. The first figure used validation-account share, which saturates: B8c75, B8c90 and B8 all sat at about 100%.
  - The page now says that the alert budget scales with accounts held. From about 75% held, almost every account active in validation is covered, so the rest of the gain to B8 comes mainly from the larger budget (and the different grouping), not from reach.

### Narrative, first run (A21): H3b failed

| | HI-Medium | LI-Medium |
| --- | --- | --- |
| H3b, grounded first replies (target 0.95) | 0.105 [0.070, 0.155] | 0.182 [0.112, 0.282] |
| First calls that timed out (120 s) | 59% | 36% |
| H3b among replies that arrived | 0.26 | 0.30 |
| Template fallback | 65% | 45% |
| τ (abstention threshold) | none | none |
| True pattern among the 3 candidates shown | 53.5% (chance 37.5%) | 50.6% |

Causes, from the raw replies:

1. **Every field cited.** The median reply cited 26 fields. That used most of the 320-token cap and caused both the timeouts and the cut-off JSON. This came from my prompt.
2. **Brackets copied.** 36 of 57 JSON replies wrote `"[own_accounts]"` because my prompt marked field names with brackets. This also came from my prompt.
3. **Reference read as facts.** The model restated the catalogue's red flags as observations ("funds returning to the originating account") and named typologies outside the candidates. H3b as defined does not catch this.
4. **CPU speed.** Your machine runs Ollama on CPU only (about 5.8 GB available). Good replies took 50–95 s. By your decision on 1 Nov, latency is reported, not judged.
5. **No τ qualifies.** The attributor is overconfident: on HI-Medium it is right only 30% of the time even at confidence 0.95 or more. So every case is UNATTRIBUTED with three candidates, as A21 intended. You decided to keep this rule.

### Amendment A22 (pre-registered and pushed before any code: commit `068ae49`)

Research behind it:

- **Explicit rules for small models.** In tests of 2–9B models, one rule did most of the work: telling the model not to confuse definitions with the actual data. Without it, small models hallucinated fields in 38–70% of replies. ([source](https://aiexplorer-blog.vercel.app/post/structured-json-output-small-llms))
- **Key order.** When structured output puts the constrained field before the free text, quality drops. Writing the free text first avoids this. ([source](https://dylancastillo.co/posts/gemini-structured-outputs.html))

| Change | Why |
| --- | --- |
| Evidence as `field_name = value (meaning)`; no brackets | Fixes cause 2 |
| Reply order: narrative, then cited_fields, then typology_id; cite 1 to 4 fields | Fixes cause 1; free text first |
| One worked example reply, with no digits | Small models copy the format; no number can leak from the example |
| Candidates as one-line descriptions under "general reference, not observations"; no red flags | Fixes cause 3 |
| Timeout 600 s, cap 400 tokens | Cause 4: no case is lost to speed |
| **Strict grounding** = H3b + 1 to 4 citations + numbers only from the evidence + no typology named outside the candidates. It triggers the retry and the fallback | The analyst only sees strictly checked text. H3b itself is unchanged, so A21 and A22 compare directly |
| Top-1 and top-3 accuracy at S0 and S2, end to end, with CIs, against the three most frequent patterns and chance | The top-3 list is what the analyst sees, so it needs a measured value |
| Blind review sheet: 30 HI cases, rated for faithfulness and usefulness | A human check of what the rules cannot see |

The A21 pages stay unchanged; A22 writes `*_A22*` files, and its page compares the two runs on the same 200 cases.

### Fix 1 Nov afternoon: generation slowed 25-fold during the rerun

The `ollama serve` log from your first rerun attempt showed the model answering, but generation fell from **5.5 tokens/s** on the first case to **0.2–0.3 tokens/s**. A reply then took 9–10 min and hit the 600 s limit. Prompt reading stayed normal (26–44 tokens/s).

The cause is recent Ollama's built-in llama.cpp server. It keeps every finished prompt's state in RAM as a prompt cache, about 110 MB per prompt and up to 8 GB in total. The log showed 32 prompts and 3.5 GB. With about 5.8 GB available, that cache pushed the model's own weights out of memory, so each generated token waited on the disk. Ollama has no setting for this cache's size.

The fix is in the client: every call now sends `keep_alive: 0`. The model unloads after each reply, which frees its cache, and reloads from the disk cache in a few seconds. Replies are unchanged; only memory use differs.

If you have already started the rerun: stop it (Ctrl+C), stop `ollama serve` (Ctrl+C) and start it again. Then follow the steps below. The narrative step restarts from case 1, because nothing was saved yet.

Optional, if Windows (WSL) has more RAM than Linux sees: in `C:\Users\<you>\.wslconfig`, set

```
[wsl2]
memory=10GB
```

then run `wsl --shutdown` in PowerShell and reopen the terminal. A machine with 16 GB can give WSL 10–12 GB.

### Fix 1 Nov evening: HI-Medium skipped after a restart

If `ollama serve` is stopped while the script is still running, every remaining call fails at once with "connection refused". Each case then falls back to the template in milliseconds, so the step "finishes" and saves a result made of failed calls. On the next run the script saw that file and skipped HI-Medium.

- **Now:** a refused or reset connection stops the narrative at once and saves nothing. The script also checks each saved A22 narrative and removes any made while the server was down, so that dataset runs again from case 1.
- **Always stop the script first** (Ctrl+C), then `ollama serve`.
- **To restart both narratives from case 1 on purpose,** use `FRESH=1` once. Don't use it when resuming, or it also removes a finished one.

### What you run now

```bash
cd ~/FinMesh
git pull
uv sync
bash scripts/ci_local.sh
ollama serve            # second terminal, if not running
bash scripts/week14_rerun.sh 2>&1 | tee week14_rerun.log
```

It re-renders both coverage pages (seconds), runs the A22 narrative on HI-Medium (200 cases) and LI-Medium (77 cases), then `pytest -m real_data`. With CPU inference, expect about **60–120 s per case**, so about **5–7 h** for HI and **2–3 h** for LI. Run it overnight with the laptop plugged in and kept awake. It resumes if interrupted.

**Then the blind review (about 30 min):** open `docs/eval/narrative_HI-Medium_A22_review.csv` in a spreadsheet. For each of the 30 cases, compare the narrative with the evidence column only:

- **faithful:** `yes` if every statement is in the evidence; `partly` if one statement goes beyond it; `no` if it misstates the evidence or presents a pattern as fact;
- **useful:** `1` = no help; `2` = saves some reading; `3` = a clear, correct summary.

Don't look at the true patterns first. Save the file as is.

```bash
git add docs/eval/ week14_rerun.log
git commit -m "Week 14 rerun: A22 narrative, coverage pages, blind review"
git push
```

**What to look for:** strict grounding and H3b against 0.95; the A21 → A22 table; S2 top-3 against S0 and the frequency baseline; and your own faithfulness ratings.

## First-run plan (31 Oct, kept for the record)

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
