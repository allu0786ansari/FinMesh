# Week 1 run log · 26 Oct – 1 Nov 2026 · Repository and data

**Goal:** a clean repository with CI, and both datasets loaded, hashed and profiled.

**State: complete.** Code tested on the synthetic fixture here; real-data run done on the owner's machine (WSL2, Python 3.12.15) on 24 Oct 2026 and verified below. Profiles: `docs/data_profile/HI-Small.md`, `docs/data_profile/LI-Small.md`.

## What was built

| Item | Where | Notes |
| --- | --- | --- |
| Repository layout, uv project, locked deps | `pyproject.toml`, `uv.lock` | Python 3.11–3.13; week 1 needs only polars, pyarrow, pyyaml |
| Lint, types, tests, coverage | Ruff, mypy (strict), pytest | 90% coverage; CI fails under 80% |
| CI + secret scan | `.github/workflows/ci.yml` | Lint, types, tests, fixture smoke pipeline; gitleaks |
| Transaction loader | `finmesh/data/ingest.py` | Header check, explicit casts, malformed-cell and duplicate counts, streaming write |
| Pattern parser and scheme linking | `finmesh/data/patterns.py` | Counts unknown names, unclosed blocks, unmatched and ambiguous lines |
| Accounts loader | `finmesh/data/accounts.py` | Optional; entity-across-banks statistics |
| SHA-256 manifest | `finmesh/data/manifest.py` | Hash stamped on every artifact; detects hand edits |
| Provenance stamps + gate guard | `finmesh/eval/provenance.py` | Fixture-based artifacts can never pass a gate (CC3) |
| Synthetic fixture | `finmesh/data/fixture.py` | Exact AMLworld file format, all 8 patterns, known answers |
| Data profile | `finmesh/data/profile.py` | JSON artifact + markdown in `docs/data_profile/` |
| Kaggle download helper | `finmesh/data/download.py` | Optional extra `kaggle` |
| CLI | `finmesh/cli.py` | `check`, `fixture`, `download`, `ingest`, `profile`, `week1` |
| Scale check | `scripts/scale_check.py` | Time and memory at real-dataset size |
| Docs | `docs/` | Proposal, data card, literature matrix, venues, gates, protocol, log |

### Design decisions worth knowing

- **`tx_id` is the CSV row number.** Every later object (scheme links, splits, evidence records) refers to it, so any result traces back to a line of the original file.
- **Account key = `<bank>:<account>`.** AMLworld account strings are unique only within a bank.
- **Bank IDs are integers.** Pattern files and the CSV may pad differently (`010` vs `10`); both normalise to the same bank.
- **Nothing is dropped silently.** Failed casts become nulls and are counted; duplicates are counted, not removed (AMLworld can contain genuine repeats).
- **Fixture results stay out of `docs/`.** Fixture profiles are written under `data/artifacts/`, so they cannot be mistaken for findings.

## What I ran here (results)

Environment: Linux, Python 3.12.3, 7 GB RAM, uv 0.11.

| Check | Command | Result |
| --- | --- | --- |
| Lint | `uv run ruff check . && uv run ruff format --check .` | All checks passed |
| Types | `uv run mypy` | No issues in 25 source files (strict) |
| Tests | `uv run pytest --cov --cov-fail-under=80` | 18 passed, 4 skipped (real-data tests), coverage 90.02% |
| Tests, other Pythons | same, under 3.11 and 3.13 | 18 passed, 4 skipped on both |
| Warnings | `uv run pytest -W error` | Clean |
| Smoke pipeline | `uv run finmesh fixture && uv run finmesh week1 --dataset FIXTURE-Small` | See below |
| Scale | `uv run python scripts/scale_check.py --rows 5000000` | 5,000,000 rows ingested in 20.3 s; peak memory 2.6 GB (includes generating the file in the same process) |

Smoke pipeline output (fixture, seed 7):

```
ingesting FIXTURE-Small from .../data/raw/FIXTURE-Small
  rows 4,081  laundering 80  banks 6  accounts 361
  malformed cells 0  duplicate extra rows 1
  schemes 11  pattern rows 65  unmatched 0  ambiguous 0
  accounts file: loaded
```

The fixture plants 11 schemes (8 crossing banks, 3 within one bank), 15 laundering rows with no pattern label, one duplicate row and zero-padded bank IDs in the pattern file. The tests assert all of these exactly.

## Verification on the real data (24 Oct 2026)

| Check | HI-Small | LI-Small | Published / expected | Verdict |
| --- | --- | --- | --- | --- |
| Rows | 5,078,345 | 6,924,049 | 5,078,345 / about 6.92 M | Exact match |
| Laundering rows | 5,177 (1 in 981) | 3,565 (1 in 1,942) | 1 in 981 / 1 in 1,942 | Exact match |
| Accounts in transactions | 515,088 | 705,907 | 515 K / 705 K | Match |
| Schemes | 370 | 117 | 370 pattern groups reported for HI-Small | Match |
| Pattern lines linked | 3,209 of 3,209 | 1,023 of 1,023 | ≥ 99% | Exact, none ambiguous |
| Malformed cells | 0 | 0 | 0 | Pass |
| Duplicate extra rows | 9 | 8 | small | Kept, reported |
| Peak memory (ingest) | 2.6 GB | 3.6 GB | < 8 GB | Pass |
| `pytest -m real_data` | 4 passed | | | Pass |

### Findings that change the next weeks

1. **The data has a 10-day dense period and a sparse tail.** Both sets run 1–10 Sep 2022 at 200 K–1.5 M rows a day, then 11–18 Sep with a few hundred rows a day of which about 60% are laundering (HI: 655 laundering of 1,108 tail rows; LI: 134 of 223). These are scheme legs continuing after licit traffic stops. A test split that includes the tail would inflate precision badly. **Week 2 proposal:** model and evaluate on 1–10 Sep only; schemes that run into the tail are scored on their in-window part, and the number truncated is reported.
2. **Scheme counts are below the G0 thresholds even before restricting to a federation.** With schemes split by start time, a last-fifth test period holds roughly 70 HI-Small schemes and 23 LI-Small schemes across *all* banks. Gate G0 counts only schemes touching two or more *federation* banks, so the small sets alone cannot reach 100, and LI-Small cannot reach 40.
3. **"Four to eight real banks" will not work as a federation.** AMLworld has 30,470 (HI) and 41,815 (LI) bank IDs; the eight largest by accounts (excluding bank 70, below) hold about 3.6% of HI-Small accounts (estimate from the top-25 table). Very few schemes would touch two of them. Week 2 measures this exactly and compares label-free alternatives (Section "Open items").
4. **Bank 70 is a hub, not a typical bank:** 15 accounts, 452,751 transactions (9% of HI-Small), all cross-bank, 633 laundering rows. A volume-ranked rule would pick it first. Ranking by number of accounts is a better proxy for bank size.
5. **Pattern-labelled share differs by regime:** 62% of HI-Small laundering rows carry a pattern label, but only 29% in LI-Small. The proposal's "most laundering transactions carry no pattern label" holds for LI only; Section 7.1 needs a one-line correction.
6. **Schemes last about three days** (median 75 h, 90th percentile 110 h in HI). Sub-daily windows (6 or 12 h) and a detection-delay allowance of up to several windows will be needed; set in week 2.
7. **Shortcut features to watch:** ACH carries about 87% of HI-Small laundering (rate 0.0075 vs at most 0.0004 elsewhere); weekend days have far less licit traffic but similar laundering counts; 1 Sep has a start-up burst of extra traffic. Detector ablations in weeks 4–5 report results with and without payment format.
8. **Self-transfers are common** (591 K in HI, 804 K in LI, mostly "Reinvestment"). They carry no counterparty, so graph features skip them; behaviour features keep them.
9. **38% of HI entities (35% LI) hold accounts at two or more banks.** The account-versus-customer gap in the privacy unit is large, which strengthens the limitation stated in Section 8.3.
10. **Memory scales with rows:** 3.6 GB at 6.9 M rows. HI-Medium (the G0 fallback, about 31 M rows) needs the duplicate check and account counts moved to a chunked pass before it can be ingested on 8 GB.

## What you run on your machine

Times are estimates for a laptop with 8 GB of RAM.

### 1. Prerequisites (once)

- git and Python 3.11, 3.12 or 3.13.
- uv:
  - macOS / Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- About 5 GB of free disk for both small datasets and their Parquet copies.

### 2. Get the code (1 min)

```bash
git clone https://github.com/allu0786ansari/FinMesh.git   # or: git pull
cd FinMesh
uv sync
```

### 3. Check the install (1 min)

```bash
uv run pytest
```

Expected: `18 passed, 4 skipped`. The 4 skipped tests are the real-data checks; they run in step 7.

### 4. Smoke test and scale check (2 min)

```bash
uv run finmesh fixture
uv run finmesh week1 --dataset FIXTURE-Small
uv run python scripts/scale_check.py --rows 5000000
```

Expected: the same smoke numbers as above (`rows 4,081 ... unmatched 0 ambiguous 0`), and the scale check finishing well under 8 GB. If the scale check uses more than about 5 GB, stop and tell me before ingesting LI-Small.

### 5. Download AMLworld (10–30 min, depends on your connection)

You need `HI-Small_Trans.csv`, `HI-Small_Patterns.txt`, `LI-Small_Trans.csv`, `LI-Small_Patterns.txt`, and if available `HI-Small_accounts.csv`, `LI-Small_accounts.csv`.

**Option A, Kaggle API:**

1. On kaggle.com: Settings → API → Create New Token. Save `kaggle.json` to `~/.kaggle/kaggle.json` (Windows: `C:\Users\<you>\.kaggle\kaggle.json`).
2. Open the dataset page once in a browser and accept its terms if asked.
3. Run:

```bash
uv sync --extra kaggle
uv run finmesh download --dataset HI-Small
uv run finmesh download --dataset LI-Small
```

**Option B, browser:** download the files from the dataset page "IBM Transactions for Anti Money Laundering (AML)" and place them, with their names unchanged, in:

```
data/raw/HI-Small/HI-Small_Trans.csv
data/raw/HI-Small/HI-Small_Patterns.txt
data/raw/HI-Small/HI-Small_accounts.csv      (optional)
data/raw/LI-Small/LI-Small_Trans.csv
data/raw/LI-Small/LI-Small_Patterns.txt
data/raw/LI-Small/LI-Small_accounts.csv      (optional)
```

Files elsewhere? Pass `--raw-dir <folder>` to the next command, or set `FINMESH_DATA` to move the whole data root.

While you are on the dataset page, note its licence (for example "CDLA-Sharing-1.0") and fill the table in `docs/data_card.md`.

Then confirm the files are seen:

```bash
uv run finmesh check
```

### 6. Ingest and profile (2–5 min per dataset)

```bash
uv run finmesh week1 --dataset HI-Small
uv run finmesh week1 --dataset LI-Small
```

This writes typed Parquet to `data/parquet/<dataset>/`, a stamped report to `data/artifacts/week01/`, and the readable profile to `docs/data_profile/HI-Small.md` and `docs/data_profile/LI-Small.md`.

### 7. Verify against the published sizes (seconds)

```bash
uv run pytest -m real_data -v
```

Expected: 4 passed. These check the row count (within 2%), the laundering rate (within 15%), zero malformed cells, and that at least 99% of pattern lines link to a transaction.

### 8. Share the results

```bash
git add docs/data_profile/ docs/data_card.md
git commit -m "Week 1: AMLworld data profiles"
git push
```

The data itself is ignored by git; only the profiles and the data card go up. I start week 2 from those profiles: they set the window length and the federation choice, and give the first read on the G0 scheme counts.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `HeaderMismatchError` | Not the raw AMLworld CSV (for example a re-saved or "formatted" version) | Re-download the original `*_Trans.csv` |
| `MissingRawDataError` | Files not in `data/raw/<dataset>/` | Move them, or use `--raw-dir` |
| Many `unmatched` pattern lines | Pattern-file format differs from what the parser expects | Send me the first 20 lines of the pattern file and the ingest output |
| Kaggle 403 / 401 | Terms not accepted, or token missing | Accept terms on the page; check `kaggle.json` |
| `make: command not found` (Windows) | No make | Use the `uv run ...` commands shown here; the Makefile only wraps them |
| Memory error | Other programs using RAM, or a very small machine | Close other apps; run one dataset at a time; tell me the scale-check numbers |

## Week-1 checklist against the plan

- [x] Repository layout; uv, Ruff, mypy, pytest, GitHub Actions and secret scan
- [x] Download HI-Small and LI-Small (done 24 Oct); licence variant still to record in `docs/data_card.md`
- [x] Loaders: CSV to Parquet with polars; SHA-256 manifest for every file
- [x] Unique account key (bank + account); duplicate and malformed-row checks
- [x] Profile both sets (`docs/data_profile/`, verified above)
- [x] Parse pattern files, link schemes to transactions, count per pattern and the labelled share
- [x] Literature matrix started (`docs/lit_matrix.md`, every cited work, status column)
- [ ] Venue deadlines: searched on 23 Oct; no 2027 calls published yet (`docs/venues.md`)

## Open items for you

1. **Code licence.** Apache-2.0 or MIT; none is set yet.
2. **Dataset licence variant**, from the Kaggle page, into `docs/data_card.md`.
3. **Federation definition for G0** (finding 3). Week 2 computes the G0 count for each option on train and validation schemes only, so the choice never sees test schemes:
    - A. real bank IDs, top K by number of accounts, K in {8, 16, 32, 64}, everything else as the outside world;
    - B. bank IDs treated as branches and grouped into K institutions by a fixed label-free rule (by country if the accounts file's bank names carry one, otherwise balanced by account count), so every account belongs to a member;
    - C. either of the above on HI-Medium.
4. **Observation window** (finding 1): model and evaluate on 1–10 Sep only, unless you object.
