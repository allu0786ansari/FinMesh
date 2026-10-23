# Data card: IBM AMLworld (as used by FinMesh)

## Source

- **Dataset:** IBM Transactions for Anti Money Laundering (AML), published on Kaggle by the AMLworld authors (`ealtman2019/ibm-transactions-for-anti-money-laundering-aml`).
- **Paper:** Altman, E. et al. (2023). *Realistic Synthetic Financial Transactions for Anti-Money Laundering Models.* NeurIPS Datasets and Benchmarks.
- **Nature:** fully synthetic. A multi-agent simulation of individuals, companies and banks in which some agents launder money; the generator tracks illicit funds through placement, layering and integration. No real person or account is represented.

## Licence

- **Status: to confirm on the Kaggle dataset page before any derived data is released (proposal Section 7.1).** The authors describe a Community Data License Agreement (CDLA) licence; the variant (Sharing or Permissive) decides whether derived files may be redistributed.
- Until confirmed, FinMesh releases **code and aggregate results only**, never raw or derived row-level data.

| Field | Value |
| --- | --- |
| Licence variant | _fill in from the dataset page_ |
| Checked by / date | _fill in_ |
| Redistribution of derived data allowed? | _fill in_ |

## Files used

Per dataset (`HI-Small`, `LI-Small`; `HI-Medium` only as the G0 fallback):

| File | Content | FinMesh use |
| --- | --- | --- |
| `<name>_Trans.csv` | One row per transaction: timestamp, sender bank and account, receiver bank and account, amounts and currencies, payment format, laundering label | All modelling |
| `<name>_Patterns.txt` | Laundering schemes as `BEGIN/END LAUNDERING ATTEMPT` blocks, one of eight patterns each | Scheme events, scheme-level metrics, attribution labels |
| `<name>_accounts.csv` | Account to bank and owning entity | Entity-across-banks statistics (account vs customer privacy unit) |

## Known properties that shape the design

| Property | HI-Small | LI-Small | Consequence |
| --- | --- | --- | --- |
| Transactions | about 5 M | about 7 M | Streaming ingestion; fits 8 GB |
| Days spanned | 10 | 10 | Sub-daily windows; delayed-label work out of scope |
| Laundering rate | about 1 in 981 | about 1 in 1,942 | Alert-budget operating points, not fixed FPR |
| Pattern-labelled laundering | a minority of laundering rows | same | Attribution scored on the labelled subset only |

Values above are from the published descriptions; the measured values for your download are written by `finmesh profile` to `docs/data_profile/<dataset>.md`.

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
