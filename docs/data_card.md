# Data card: IBM AMLworld (as used by FinMesh)

## Source

- **Dataset:** IBM Transactions for Anti Money Laundering (AML), published on Kaggle by the AMLworld authors (`ealtman2019/ibm-transactions-for-anti-money-laundering-aml`).
- **Paper:** Altman, E. et al. (2023). *Realistic Synthetic Financial Transactions for Anti-Money Laundering Models.* NeurIPS Datasets and Benchmarks.
- **Nature:** fully synthetic. A multi-agent simulation of individuals, companies and banks in which some agents launder money; the generator tracks illicit funds through placement, layering and integration. No real person or account is represented.

## Licence

- **Community Data License Agreement – Permissive, Version 2.0 (CDLA-Permissive-2.0).** Full text: [`docs/data_License.md`](data_License.md).
- Derived data may be shared, with or without changes, provided the agreement text goes with it (Section 2.1). Results, including trained models and their outputs, carry no restriction (Section 3.1).
- FinMesh still releases **code and aggregate results only** by default: raw and row-level derived files are large and add nothing to reproducibility, since `finmesh download` and the pipeline rebuild them. Any row-level release ships `docs/data_License.md` alongside.

| Field | Value |
| --- | --- |
| Licence variant | CDLA-Permissive-2.0 |
| Checked by / date | Allaudin Ansari, 25 Oct 2026 |
| Redistribution of derived data allowed? | Yes, with the agreement text attached |

## Files used

Per dataset (`HI-Medium` and `LI-Medium` for headline results, `HI-Small` and `LI-Small` for development; amendment A6):

| File | Content | FinMesh use |
| --- | --- | --- |
| `<name>_Trans.csv` | One row per transaction: timestamp, sender bank and account, receiver bank and account, amounts and currencies, payment format, laundering label | All modelling |
| `<name>_Patterns.txt` | Laundering schemes as `BEGIN/END LAUNDERING ATTEMPT` blocks, one of eight patterns each | Scheme events, scheme-level metrics, attribution labels |
| `<name>_accounts.csv` | Account to bank and owning entity | Entity-across-banks statistics (account vs customer privacy unit) |

## Known properties that shape the design

| Property | HI-Small | LI-Small | Consequence |
| --- | --- | --- | --- |
| Transactions | 5,078,345 | 6,924,049 | Streaming ingestion; fits 8 GB |
| Dense period | 1–10 Sep 2022 | 1–10 Sep 2022 | Sub-daily windows; delayed-label work out of scope |
| Sparse tail | 11–18 Sep, 1,108 rows, 59% laundering | 11–17 Sep, 223 rows, 60% laundering | Excluded from modelling and evaluation (proposed) |
| Laundering rows | 5,177 (1 in 981) | 3,565 (1 in 1,942) | Alert-budget operating points, not fixed FPR |
| Schemes (pattern file) | 370 | 117 | Scheme counts limit RQ1 power (Gate G0) |
| Pattern-labelled laundering | 62% | 29% | Attribution scored on the labelled subset only |
| Bank IDs | 30,470 | 41,815 | Federation definition decided at G0 |
| Entities with accounts at 2+ banks | 38% | 35% | Account-level DP unit is not customer-level |

Measured on 24 Oct 2026; full detail in `docs/data_profile/<dataset>.md`.

## Processing in FinMesh (week 1)

1. The CSV header is checked against the exact AMLworld header; any other file is refused.
2. Every column is read as text and cast explicitly; failed casts become nulls and are counted, never dropped silently.
3. `tx_id` = zero-based row number in the original CSV, the only transaction identifier used downstream.
4. Bank IDs are parsed as integers (`"010"` and `"10"` are the same bank). Account keys are `<bank>:<account>`, because account strings are only unique within a bank.
5. Pattern-file lines are matched to CSV rows on timestamp, both parties, amount paid, payment currency and payment format; unmatched and ambiguous lines are reported.
6. A SHA-256 manifest of raw inputs and outputs is written; its hash is stamped on every artifact.

## Limitations

- Single simulator: HI and LI are two regimes of one generator, not independent worlds.
- Leakage measured on synthetic accounts may understate or overstate real-world risk.
- Pattern labels cover only some laundering rows; schemes are generator constructs, not investigator-confirmed cases.
