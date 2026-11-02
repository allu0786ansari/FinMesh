# Constrained case narrative (H3b) · LI-Medium · protocol A23

Level S2, seed 0; 77 detected validation schemes sampled by pattern (up to 25 each). Model `llama3.2:3b` on this machine, temperature 0; json-only first, schema-constrained retry, template fallback (A23). The model writes the text only: the typology comes from the X6 attributor (shown only above τ), the evidence from a fixed template of what S2 reveals to the owner, and the review actions from the catalogue. 7,578 s in total (315 s for the attributor), peak memory 1,280 MB.

## H3b on validation

| Item | Validation |
| --- | --- |
| Grounded first replies [95% Wilson CI] | 0.8831 [0.7925, 0.9373] |
| Target | 0.9500 |
| Met on validation | no |

Grounded = valid JSON, typology equal to the one shown (or UNATTRIBUTED), and every cited field present in the evidence. Judged on test.

## Strict grounding (A22)

Strict = H3b, plus 1 to 4 cited fields, every number in the narrative taken from the evidence or confidence lines, and no typology named outside the candidates. The retry and the template are triggered by strict failure, so the analyst only sees strictly checked text.

| Item | Validation |
| --- | --- |
| Strictly grounded first replies [95% Wilson CI] | 0.1948 [0.1218, 0.2969] |
| First reply cites 1 to 4 fields | 28.6% |
| First reply names no outside typology | 93.5% |
| Replies that arrived (no timeout or error) | 77 of 77 |
| H3b among replies that arrived | 88.3% |
| Strict among replies that arrived | 19.5% |
| Delivered text names no outside typology | 100.0% |

## Claim consistency (A23)

Per-sentence rules tie the claims small models make most often to the evidence that would support them (pass-through, many payers or payees, cycles, gathering, splitting, layering); hedged sentences are skipped. Part of strict grounding in A23.

| Item | Validation |
| --- | --- |
| First replies claim-consistent | 85.7% |
| Delivered text claim-consistent | 100.0% |

| Unsupported claim | First replies | Delivered text |
| --- | --- | --- |
| cycle | 4 | 0 |
| pass_through | 5 | 0 |
| split | 1 | 0 |

## A22 → A23 on the same sample

| Item | A22 | A23 |
| --- | --- | --- |
| H3b: grounded first replies | 94.8% | 88.3% |
| Strict grounding (rules of each run) | 70.1% | 19.5% |
| Valid JSON | 94.8% | 98.7% |
| Cited fields all real | 94.8% | 93.5% |
| Template fallback | 0.0% | 10.4% |
| Cases with a call error | 1.3% | 0.0% |
| Delivered text claim-consistent (A23 rules) | 5.2% | 100.0% |

## What the analyst sees: the top three candidates (A22, secondary)

Cross-fitted attributor, seed 0, all 93 pattern-labelled validation schemes; end to end counts undetected schemes as misses; 1,000-replicate scheme bootstrap.

| Level | Top 1, end to end [95% CI] | Top 3, end to end [95% CI] | Top 3, detected schemes |
| --- | --- | --- | --- |
| S0 · own data only | 0.1183 [0.0538, 0.1935] | 0.3118 [0.2258, 0.4086] | 36.7% |
| S2 · + shared evidence | 0.1075 [0.0535, 0.1720] | 0.4194 [0.3226, 0.5161] | 50.6% |
| Baseline · 3 most frequent patterns | — | 0.3978 [0.3011, 0.5054] | 48.1% |
| Baseline · chance | — | — | 37.5% |

| Comparison | Difference [95% CI] |
| --- | --- |
| S2 - S0 (top 3) | 0.1075 [-0.0110, 0.2258] |
| S2 - S0 (top 1) | -0.0108 [-0.0860, 0.0645] |
| S2 top 3 - frequency top 3 | 0.0215 [-0.1183, 0.1613] |

## Reply quality and latency

| Item | Value |
| --- | --- |
| First reply: valid JSON | 98.7% |
| First reply: typology as shown | 93.5% |
| First reply: cited fields all real | 93.5% |
| First reply: cites at least one field | 98.7% |
| First reply: every number appears in the prompt | 93.5% |
| Retried (schema-constrained) | 80.5% |
| Retry grounded | 100.0% |
| Template fallback | 10.4% |
| Final text: numbers all from the prompt | 100.0% |
| Cases with a call error | 0 |
| Latency per case, p50 / p95 / max | 68.6 / 239.5 / 452.2 s (target p95 ≤ 30 s) |

## Abstention: when the attributor's label is shown

τ = **none**: the smallest threshold whose selective accuracy on all detected validation schemes is at least 50% with coverage at least 10% (77 detected of 93 schemes; attributor accuracy without abstention 13.0%). No threshold qualifies: every case is UNATTRIBUTED with its top three candidates.

| τ | Coverage | Selective accuracy | Schemes labelled |
| --- | --- | --- | --- |
| 0.30 | 100.0% | 13.0% | 77 |
| 0.35 | 98.7% | 13.2% | 76 |
| 0.40 | 96.1% | 13.5% | 74 |
| 0.45 | 94.8% | 13.7% | 73 |
| 0.50 | 92.2% | 12.7% | 71 |
| 0.55 | 88.3% | 11.8% | 68 |
| 0.60 | 83.1% | 12.5% | 64 |
| 0.65 | 81.8% | 12.7% | 63 |
| 0.70 | 77.9% | 13.3% | 60 |
| 0.75 | 68.8% | 11.3% | 53 |
| 0.80 | 68.8% | 11.3% | 53 |
| 0.85 | 62.3% | 10.4% | 48 |
| 0.90 | 55.8% | 11.6% | 43 |
| 0.95 | 39.0% | 10.0% | 30 |

## In the sample

- Labelled cases: 0, correct —.
- Unattributed cases: 77; the true pattern is among the three candidates listed in 50.6%.

| Pattern | Cases | Labelled | Labelled correctly | Grounded first replies |
| --- | --- | --- | --- | --- |
| BIPARTITE | 14 | 0 | 0 | 85.7% |
| CYCLE | 10 | 0 | 0 | 90.0% |
| FAN-IN | 9 | 0 | 0 | 100.0% |
| FAN-OUT | 10 | 0 | 0 | 90.0% |
| GATHER-SCATTER | 7 | 0 | 0 | 100.0% |
| RANDOM | 7 | 0 | 0 | 85.7% |
| SCATTER-GATHER | 13 | 0 | 0 | 69.2% |
| STACK | 7 | 0 | 0 | 100.0% |

## Example cases

### An unattributed case written by the model

- Scheme 224: true pattern **BIPARTITE**; shown to the analyst: **UNATTRIBUTED** (top candidates: RANDOM 1.00, CYCLE 0.00, BIPARTITE 0.00).
- First reply: json yes, typology yes, cited yes, numeric yes, cites_ok yes, mentions_ok yes, consistent yes, strict yes; final text from **first**; 84.6 s.
- Cited fields: `case_accounts`, `case_members`, `case_account_windows`, `case_span_hours`.

> Two case accounts at the bank were involved in a money transfer, with one account receiving a large amount and the other account paying out a smaller amount. The case accounts were linked to two federation members, and the money transfer occurred within a 6-hour window.

Review actions (from the catalogue, not the model):

1. Follow the funds forward and backward across banks
1. Reconstruct the full chain across banks
1. Map both groups and the links between them

### A case whose first reply failed the check

- Scheme 232: true pattern **BIPARTITE**; shown to the analyst: **UNATTRIBUTED** (top candidates: SCATTER-GATHER 0.73, CYCLE 0.13, BIPARTITE 0.13).
- First reply: json yes, typology yes, cited yes, numeric yes, cites_ok no, mentions_ok yes, consistent yes, strict no; final text from **retry**; 80.4 s.
- Cited fields: `own_accounts`, `own_account_windows`, `own_span_hours`, `own_max_fan_out`, `own_max_fan_in`, `own_mean_pass_through`, `own_max_cycles`, `own_max_gather_scatter`, `own_max_scatter_gather`, `own_max_amount_out`, `own_max_amount_in`, `own_mean_cross_bank_share`, `own_mean_new_counterparty_share`, `case_accounts`, `case_members`, `case_account_windows`, `case_span_hours`.

> A single case account at the bank was involved in a transaction with one payee, resulting in a maximum amount paid out of 9,974. The account was part of a case with one federation member and one case account, both of which were active for 6 hours.

Review actions (from the catalogue, not the model):

1. Link the intermediate accounts as one case
1. Reconstruct the full chain across banks
1. Map both groups and the links between them

Every case (prompt size, raw replies, checks, final text) is in `narrative_LI-Medium_A23_cases.jsonl`.
