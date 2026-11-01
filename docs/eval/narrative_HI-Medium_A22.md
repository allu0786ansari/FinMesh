# Constrained case narrative (H3b) · HI-Medium · protocol A22

Level S2, seed 0; 200 detected validation schemes sampled by pattern (up to 25 each). Model `llama3.2:3b` on this machine, temperature 0; json-only first, schema-constrained retry, template fallback (A22). The model writes the text only: the typology comes from the X6 attributor (shown only above τ), the evidence from a fixed template of what S2 reveals to the owner, and the review actions from the catalogue. 13,600 s in total (344 s for the attributor), peak memory 1,282 MB.

## H3b on validation

| Item | Validation |
| --- | --- |
| Grounded first replies [95% Wilson CI] | 0.9350 [0.8920, 0.9616] |
| Target | 0.9500 |
| Met on validation | no |

Grounded = valid JSON, typology equal to the one shown (or UNATTRIBUTED), and every cited field present in the evidence. Judged on test.

## Strict grounding (A22)

Strict = H3b, plus 1 to 4 cited fields, every number in the narrative taken from the evidence or confidence lines, and no typology named outside the candidates. The retry and the template are triggered by strict failure, so the analyst only sees strictly checked text.

| Item | Validation |
| --- | --- |
| Strictly grounded first replies [95% Wilson CI] | 0.6100 [0.5409, 0.6749] |
| First reply cites 1 to 4 fields | 64.5% |
| First reply names no outside typology | 90.0% |
| Replies that arrived (no timeout or error) | 199 of 200 |
| H3b among replies that arrived | 94.0% |
| Strict among replies that arrived | 61.3% |
| Delivered text names no outside typology | 100.0% |

## A21 → A22 on the same sample

| Item | A21 (first run) | A22 |
| --- | --- | --- |
| H3b: grounded first replies | 10.5% | 93.5% |
| Valid JSON | 28.5% | 94.0% |
| Cited fields all real | 10.5% | 93.5% |
| Template fallback | 64.5% | 1.5% |
| Cases with a call error | 59.5% | 0.5% |

## What the analyst sees: the top three candidates (A22, secondary)

Cross-fitted attributor, seed 0, all 551 pattern-labelled validation schemes; end to end counts undetected schemes as misses; 1,000-replicate scheme bootstrap.

| Level | Top 1, end to end [95% CI] | Top 3, end to end [95% CI] | Top 3, detected schemes |
| --- | --- | --- | --- |
| S0 · own data only | 0.1325 [0.1034, 0.1615] | 0.4102 [0.3684, 0.4519] | 47.6% |
| S2 · + shared evidence | 0.2051 [0.1742, 0.2396] | 0.4701 [0.4247, 0.5154] | 54.9% |
| Baseline · 3 most frequent patterns | — | 0.3122 [0.2722, 0.3521] | 36.4% |
| Baseline · chance | — | — | 37.5% |

| Comparison | Difference [95% CI] |
| --- | --- |
| S2 - S0 (top 3) | 0.0599 [0.0127, 0.1089] |
| S2 - S0 (top 1) | 0.0726 [0.0363, 0.1089] |
| S2 top 3 - frequency top 3 | 0.1579 [0.1071, 0.2123] |

## Reply quality and latency

| Item | Value |
| --- | --- |
| First reply: valid JSON | 94.0% |
| First reply: typology as shown | 94.0% |
| First reply: cited fields all real | 93.5% |
| First reply: cites at least one field | 94.0% |
| First reply: every number appears in the prompt | 94.0% |
| Retried (schema-constrained) | 39.0% |
| Retry grounded | 100.0% |
| Template fallback | 1.5% |
| Final text: numbers all from the prompt | 100.0% |
| Cases with a call error | 1 |
| Latency per case, p50 / p95 / max | 45.0 / 152.9 / 700.3 s (target p95 ≤ 30 s) |

## Abstention: when the attributor's label is shown

τ = **none**: the smallest threshold whose selective accuracy on all detected validation schemes is at least 50% with coverage at least 10% (472 detected of 551 schemes; attributor accuracy without abstention 23.9%). No threshold qualifies: every case is UNATTRIBUTED with its top three candidates.

| τ | Coverage | Selective accuracy | Schemes labelled |
| --- | --- | --- | --- |
| 0.30 | 96.4% | 24.2% | 455 |
| 0.35 | 93.9% | 23.7% | 443 |
| 0.40 | 81.6% | 24.2% | 385 |
| 0.45 | 77.8% | 24.5% | 367 |
| 0.50 | 72.0% | 25.9% | 340 |
| 0.55 | 64.2% | 25.1% | 303 |
| 0.60 | 57.4% | 26.6% | 271 |
| 0.65 | 52.5% | 28.2% | 248 |
| 0.70 | 48.1% | 27.3% | 227 |
| 0.75 | 43.4% | 27.8% | 205 |
| 0.80 | 40.0% | 27.5% | 189 |
| 0.85 | 34.3% | 26.5% | 162 |
| 0.90 | 27.8% | 27.5% | 131 |
| 0.95 | 22.9% | 29.6% | 108 |

## In the sample

- Labelled cases: 0, correct —.
- Unattributed cases: 200; the true pattern is among the three candidates listed in 53.5%.

| Pattern | Cases | Labelled | Labelled correctly | Grounded first replies |
| --- | --- | --- | --- | --- |
| BIPARTITE | 25 | 0 | 0 | 92.0% |
| CYCLE | 25 | 0 | 0 | 96.0% |
| FAN-IN | 25 | 0 | 0 | 88.0% |
| FAN-OUT | 25 | 0 | 0 | 100.0% |
| GATHER-SCATTER | 25 | 0 | 0 | 100.0% |
| RANDOM | 25 | 0 | 0 | 88.0% |
| SCATTER-GATHER | 25 | 0 | 0 | 84.0% |
| STACK | 25 | 0 | 0 | 100.0% |

## Example cases

### An unattributed case written by the model

- Scheme 1365: true pattern **BIPARTITE**; shown to the analyst: **UNATTRIBUTED** (top candidates: BIPARTITE 0.97, STACK 0.02, FAN-IN 0.01).
- First reply: json yes, typology yes, cited yes, numeric yes, cites_ok yes, mentions_ok yes, strict yes; final text from **first**; 94.8 s.
- Cited fields: `others_fan_in`, `others_cross_bank_share`, `others_new_cp_share`.

> Several accounts at your bank received money from a single payer and passed most of it on. Other members report accounts with similar inflows. The linked case has two accounts and two alerted account-windows. The case spans six hours. Other members' records show that they have a low number of distinct payers and a high number of transfers with other banks.

Review actions (from the catalogue, not the model):

1. Map both groups and the links between them
1. Reconstruct the layers across banks
1. Identify the senders and whether they share attributes

### A case whose first reply failed the check

- Scheme 1465: true pattern **STACK**; shown to the analyst: **UNATTRIBUTED** (top candidates: FAN-OUT 0.37, STACK 0.33, FAN-IN 0.30).
- First reply: json yes, typology yes, cited yes, numeric yes, cites_ok no, mentions_ok yes, strict no; final text from **retry**; 63.4 s.
- Cited fields: `case_accounts`, `case_members`, `case_account_windows`, `case_span_hours`, `others_fan_in`, `others_amt_in`, `others_cross_bank_share`.

> Several accounts at your bank received money from many payers and passed most of it on. Other members report accounts with similar inflows. The linked case accounts received money from many payers and passed most of it on. Other members' records show accounts with similar inflows.

Review actions (from the catalogue, not the model):

1. Review the source of the large credit before the split
1. Reconstruct the layers across banks
1. Identify the senders and whether they share attributes

Every case (prompt size, raw replies, checks, final text) is in `narrative_HI-Medium_A22_cases.jsonl`.
