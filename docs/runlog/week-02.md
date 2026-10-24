# Week 2 run log · 2 – 8 Nov 2026 · Visibility model, federation, splits, Gate G0

**Goal:** the bank federation is chosen, splits are drafted, and the go/no-go count is known.

**State:** code complete and tested here on the synthetic fixture and on HI-Medium-sized synthetic data. The G0 numbers come from the real data, so steps 3–9 below run on your machine. Week 2 is done when the evidence files in `docs/gates/` are pushed; I then write the G0 decision note (`docs/gates/G0.md`).

## Why CI was failing (fixed)

All three week-1 pushes failed CI at the **lint** step. A last-minute edit to `finmesh/data/patterns.py` (adding `explode(empty_as_null=False)` to silence a polars deprecation warning) made two lines longer than 100 characters. I re-ran the tests and type checks after that edit but not the linter, so the failure was only caught by GitHub. Nothing was wrong with the code's behaviour; the remaining CI steps passed when reproduced on a fresh clone.

Fixes:

- Reformatted the lines.
- Added `scripts/ci_local.sh` (`make ci`), which runs exactly the CI steps in order. I run it before every push from now on.
- Bumped `actions/checkout` to v5 (GitHub warned that v4 runs on deprecated Node 20). `astral-sh/setup-uv@v6` and `gitleaks-action@v2` still show that warning; it does not fail the build.

## Decisions applied this week (approved 24 Oct)

| Finding | Decision | Where |
| --- | --- | --- |
| 1 · sparse tail | Model and evaluate on the dense period only; found by a label-free rule (longest run of days with at least 5% of the median daily rows) | `finmesh/data/splits.py` |
| 4 · hub bank 70 | Rank banks by number of accounts, not transaction volume | `finmesh/data/consortium.py` |

Both are recorded as amendments A1 and A2 in `docs/proposal/CHANGES.md` and marked in the proposal text, together with the A3 correction (pattern-labelled share) and the A4 federation rule (final choice at G0).

## What was built

| Item | Where | Notes |
| --- | --- | --- |
| Observation window | `finmesh/data/splits.py` | Label-free dense-period rule; counts rows and laundering rows excluded |
| Window length rule | `splits.choose_window_hours` | Largest of {4, 6, 12} h with at least 8 test windows; gives **6 h** for a 10-day window |
| Time splits | `splits.plan_split` | 60/20/20 of whole windows, one-window gaps; train 132 h, val 48 h, test 48 h |
| Scheme assignment and masking | `splits.assign_schemes`, `transaction_split` | Scheme belongs to the partition of its first in-window row; its rows elsewhere are masked; truncated schemes counted |
| Visibility model | `finmesh/data/visibility.py` | Member view with full records incl. counterparty; leg kinds internal / cross-member / boundary / invisible |
| Federation options | `finmesh/data/consortium.py` | A: top-*k* real banks by accounts; B: all bank IDs grouped into *k* balanced institutions |
| G0 evidence and selection rule | `finmesh/eval/g0.py` | Option chosen on train + val only; test counted for the chosen option only; bands 100 / 40 |
| Memory-safe data layer | `finmesh/data/ingest.py`, `lowmem.py` | HI-Medium-size ingest 929 MB, G0 1.2 GB (see below) |
| OPRF (RFC 9497) | `finmesh/matching/oprf.py` | ristretto255-SHA512 on `rbcl`; byte-identical to Cloudflare's voprf-ts |
| Feature timing spike | `finmesh/features/prototype.py` | One member, one day, ten features |
| Local LLM probe | `finmesh/attribution/llm_probe.py` | Latency, JSON and schema validity through Ollama; localhost only |
| CLI | `finmesh g0`, `feature-timing`, `llm-probe` | |
| Tests | `tests/unit/test_splits.py`, `test_consortium_visibility.py`, `test_g0.py`, `test_oprf.py`, `test_llm_probe_and_ingest_scale.py`, `tests/integration/test_real_data_week2.py` | 52 unit tests; 8 real-data tests skip here |

### The G0 selection rule (fixed before any real numbers)

1. For each candidate (A8, A16, A32, A64, B4, B8, B16), count **multi-member** schemes, meaning schemes visible to two or more members within their own partition, in **train and validation only**. Project to the test period by time share.
2. Choose the smallest real-bank option (A) whose projection reaches 100. If none does, choose **B8** (eight grouped institutions, the proposal's "four to eight").
3. Only then count test schemes, for the chosen option alone, and apply the bands: 100 or more proceed; 40–99 proceed with pooled federations, RQ1 as a case study; under 40 fall back.

This keeps the federation choice from seeing the test set. The rule is coded in `select_option` and tested.

### Memory: what changed and why it matters for you

WSL2 gets **half of Windows' RAM by default**, so on an 8 GB laptop it may have only about 4 GB. Measured peak *real* memory (anonymous memory; peak RSS also counts memory-mapped file pages the OS can drop):

| Run | Before | After |
| --- | --- | --- |
| Ingest, 32 M synthetic rows (HI-Medium size) | 5.3 GB | **0.93 GB** |
| G0, 32 M synthetic rows | 3.7 GB, 130 s | **1.2 GB, 78 s** |
| Profile queries, 32 M rows | — | 1.3 GB |

Causes found and fixed:

- `is_in` is not supported by polars' streaming engine; inside a larger query it silently moved the whole query into memory (5.3 GB). Replaced by a range test, with a regression test.
- Distinct-account counts per bank (`n_unique` inside `group_by`) do not stream. They now run on 64-bit key hashes in hash-partitioned slices (`finmesh/data/lowmem.py`); a test checks the result equals the exact count.
- Duplicate-row detection now hashes rows and runs in slices of about 4 M rows.
- Federation account coverage is derived from per-bank account counts instead of re-scanning transactions (each account belongs to exactly one bank).

## What I ran here (results)

| Check | Command | Result |
| --- | --- | --- |
| Full CI mirror | `bash scripts/ci_local.sh` | All steps passed |
| Lint / types | Ruff, mypy strict | Clean; 34 source files |
| Tests | `pytest --cov` | 52 passed, 8 skipped (real data), coverage 90.5% |
| OPRF cross-check | `tests/unit/test_oprf.py` | Matches Cloudflare voprf-ts on 3 keys × 4 inputs and the full blind protocol; reproduces the RFC 9497 A.1.1 key `5ebcea5e…063b0e` |
| Ingest at HI-Medium size | `scripts/scale_check.py --rows 32000000` | 32 M rows in 77 s, 929 MB |
| G0 at HI-Medium size | synthetic 32 M rows + 1,500 schemes | 78 s, 1.2 GB |

Fixture G0 output (synthetic; not a finding):

```
window 6 h  schemes 24  option B8  multi-member test schemes 1  band fallback  peak memory 30.5 MB
```

The fixture plants a 16-row tail (10 laundering), one scheme that runs past the window end, and 24 small banks so the real-bank and grouped options differ. The tests check that the window rule drops exactly the tail, the window length is 6 h, every scheme's partition is that of its first in-window row, the mask is exactly gaps plus out-of-partition scheme rows, and no test count is computed for options that were not chosen.

## What you run on your machine

Times are estimates for an 8 GB laptop.

### 1. Update and check (2 min)

```bash
cd ~/FinMesh
git pull
uv sync
bash scripts/ci_local.sh
```

Expected: ends with `local CI: all steps passed`.

### 2. Check how much memory WSL has (1 min)

```bash
free -h
```

Look at the `total` of the `Mem:` row. With 4 GB or more, every step below fits (the heaviest is about 1.3 GB). If it shows less than 4 GB, or a step is killed, give WSL more memory: create `C:\Users\<you>\.wslconfig` containing

```
[wsl2]
memory=6GB
```

then run `wsl --shutdown` in PowerShell and reopen the terminal.

### 3. Re-ingest the Small sets with the new counting code (2 min)

This confirms on real data that the hash-based counts equal last week's exact counts.

```bash
uv run finmesh week1 --dataset HI-Small
uv run finmesh week1 --dataset LI-Small
```

Expected: the same numbers as week 1 (`rows 5,078,345 ... accounts 515,088`, `duplicate extra rows 9`; LI-Small `accounts 705,907`, `duplicate extra rows 8`), now with `peak memory` well below last week's figure.

### 4. Add HI-Medium, the G0 fallback (5–10 min)

Put the three HI-Medium files in `data/raw/HI-Medium/` with their names unchanged (`HI-Medium_Trans.csv`, `HI-Medium_Patterns.txt`, `HI-Medium_accounts.csv`), delete any `Zone.Identifier` files, then:

```bash
find data/raw -name '*Zone.Identifier' -delete
uv run finmesh week1 --dataset HI-Medium
```

This writes `docs/data_profile/HI-Medium.md`.

### 5. Gate G0 evidence (3–6 min)

```bash
uv run finmesh g0 --dataset HI-Small --dataset LI-Small
uv run finmesh g0 --dataset HI-Medium
```

Writes `docs/gates/G0_evidence_HI-Small.md`, `G0_evidence_LI-Small.md`, `G0_evidence_HI-Medium.md` and `G0_evidence_summary.md` (pooled HI + LI). Each page starts with the outcome line. Copy the three printed `option ... band ...` lines into your reply if you like; the pages hold everything.

Note on HI-Medium: the dense-period rule is applied to it as to the others. HI-Medium is described as spanning 16 days, so its observation window and split dates will differ from the Small sets; the evidence page shows them.

### 6. Feature timing (1 min)

```bash
uv run finmesh feature-timing --dataset HI-Small
```

Writes `docs/gates/feature_timing_HI-Small.json` (rows per second and peak memory for the largest member's first day).

### 7. Local language model check (20–40 min, mostly download)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
ollama pull qwen2.5:3b
uv run finmesh llm-probe --model llama3.2:3b --save
uv run finmesh llm-probe --model qwen2.5:3b --save
```

If `llm-probe` says it cannot reach Ollama, start the server in a second terminal with `ollama serve` and rerun. Each probe makes 20 calls and writes `docs/gates/llm_probe_<model>.json` with p50/p95 latency and JSON, schema and grounding rates. The prompts contain only synthetic, bucketed evidence. On CPU, expect a few seconds to tens of seconds per call.

### 8. Real-data regression tests (seconds)

```bash
uv run pytest -m real_data -v
```

Expected: all pass, including the new week-2 anchors (tail of 1,108 rows with 655 laundering in HI-Small, 223 with 134 in LI-Small; 6 h windows; 370 and 117 schemes).

### 9. Push the evidence

```bash
git add docs/gates/ docs/data_profile/
git commit -m "Week 2: G0 evidence on real data"
git push
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| A step ends with `Killed` | WSL memory cap | Step 2: raise `memory=` in `.wslconfig` |
| `HI-Medium: not ingested` | Step 4 skipped or files misnamed | Check `uv run finmesh check` |
| `run finmesh g0 first, or pass --option` | Feature timing before G0 | Run step 5 first |
| `cannot reach Ollama` | Server not running | `ollama serve` in another terminal |
| `ollama: command not found` after install | New shell needed | Open a new terminal |
| Real-data test fails on accounts or duplicates | Hash-count change behaves differently on your data | Send me the test output; the old exact code is in commit `6a264c5` |

## Week-2 checklist against the plan

- [x] Visibility model: full record of every transaction touching a member's accounts
- [x] Federation choice by a label-free rule (ranking by accounts; options A and B; rule fixed in code)
- [x] Window length from {4, 6, 12} h by a stated rule (6 h)
- [x] Time split with one-window gaps; schemes assigned to the partition where they start; masking
- [x] Counts for G0 (code done; real numbers in step 5)
- [x] Graph-feature timing (code done; real numbers in step 6)
- [x] Local model latency and JSON validity (code done; real numbers in step 7)
- [x] OPRF spike: RFC 9497 round trip works and matches an independent implementation
- [ ] G0 gate note: written by me from the evidence you push

## Open items for you

1. Run steps 1–9 and push `docs/gates/` and `docs/data_profile/HI-Medium.md`.
2. Code licence (Apache-2.0 or MIT) and the dataset licence variant in `docs/data_card.md`, both still open from week 1.
