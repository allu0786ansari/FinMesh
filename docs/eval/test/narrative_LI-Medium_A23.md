# Constrained case narrative (H3b) · LI-Medium · protocol A23

> **Sealed test (week 18).** Every model trained on the training partition; every calibration, threshold, fusion and attribution parameter fitted on validation and frozen; test scored label-free, then opened once per seed through the logged seal (`finmesh sealed-log`). Wording below that says *validation* in a column or check name refers to the frozen rule; every number is on **test**.

Level S2, seed 0; 76 detected test schemes sampled by pattern (up to 25 each). Model `llama3.2:3b` on this machine, temperature 0; json-only first, schema-constrained retry, template fallback (A23). The model writes the text only: the typology comes from the X6 attributor (shown only above τ), the evidence from a fixed template of what S2 reveals to the owner, and the review actions from the catalogue. 7,610 s in total (attribution tables from `finmesh test-x1`, attributor fitted on test).

## H3b on test

| Item | Test |
| --- | --- |
| Grounded first replies [95% Wilson CI] | 0.9211 [0.8383, 0.9633] |
| Target | 0.9500 |
| Met on test | no |

Grounded = valid JSON, typology equal to the one shown (or UNATTRIBUTED), and every cited field present in the evidence. Decided here, on test.

## Strict grounding (A23)

Strict = H3b, plus 1 to 4 cited fields, every number in the narrative taken from the evidence or confidence lines, and no typology named outside the candidates; A23 adds claim consistency, number words and no copied placeholders. The retry and the template are triggered by strict failure, so the analyst only sees strictly checked text.

| Item | Test |
| --- | --- |
| Strictly grounded first replies [95% Wilson CI] | 0.1184 [0.0636, 0.2100] |
| First reply cites 1 to 4 fields | 14.5% |
| First reply names no outside typology | 92.1% |
| Replies that arrived (no timeout or error) | 75 of 76 |
| H3b among replies that arrived | 93.3% |
| Strict among replies that arrived | 12.0% |
| Delivered text names no outside typology | 100.0% |

## Claim consistency (A23)

Per-sentence rules tie the claims small models make most often to the evidence that would support them (pass-through, many payers or payees, cycles, gathering, splitting, layering); hedged sentences are skipped. Part of strict grounding in A23.

| Item | Test |
| --- | --- |
| First replies claim-consistent | 88.2% |
| Delivered text claim-consistent | 100.0% |

| Unsupported claim | First replies | Delivered text |
| --- | --- | --- |
| cycle | 4 | 0 |
| pass_through | 2 | 0 |
| split | 1 | 0 |

## What the analyst sees: the top three candidates (secondary)

Cross-fitted attributor, seed 0, all 94 pattern-labelled validation schemes; end to end counts undetected schemes as misses; 1,000-replicate scheme bootstrap.

| Level | Top 1, end to end [95% CI] | Top 3, end to end [95% CI] | Top 3, detected schemes |
| --- | --- | --- | --- |
| S0 · own data only | 0.2128 [0.1383, 0.3085] | 0.4255 [0.3298, 0.5213] | 53.3% |
| S2 · + shared evidence | 0.1596 [0.0957, 0.2340] | 0.3298 [0.2340, 0.4255] | 40.8% |
| Baseline · 3 most frequent patterns | — | 0.3085 [0.2234, 0.3936] | 38.2% |
| Baseline · chance | — | — | 37.5% |

| Comparison | Difference [95% CI] |
| --- | --- |
| S2 - S0 (top 3) | -0.0957 [-0.2128, 0.0213] |
| S2 - S0 (top 1) | -0.0532 [-0.1489, 0.0319] |
| S2 top 3 - frequency top 3 | 0.0213 [-0.0851, 0.1383] |

## Reply quality and latency

| Item | Value |
| --- | --- |
| First reply: valid JSON | 97.4% |
| First reply: typology as shown | 93.4% |
| First reply: cited fields all real | 94.7% |
| First reply: cites at least one field | 97.4% |
| First reply: every number appears in the prompt | 93.4% |
| Retried (schema-constrained) | 88.2% |
| Retry grounded | 100.0% |
| Template fallback | 7.9% |
| Final text: numbers all from the prompt | 100.0% |
| Cases with a call error | 1 |
| Latency per case, p50 / p95 / max | 64.8 / 298.1 / 933.1 s (target p95 ≤ 30 s) |

## Abstention: when the attributor's label is shown

τ = **none**: the smallest threshold whose selective accuracy on all detected validation schemes is at least 50% with coverage at least 10% (76 detected of 94 schemes; attributor accuracy without abstention 19.7%). No threshold qualifies: every case is UNATTRIBUTED with its top three candidates.

| τ | Coverage | Selective accuracy | Schemes labelled |
| --- | --- | --- | --- |
| 0.30 | 98.7% | 20.0% | 75 |
| 0.35 | 94.7% | 20.8% | 72 |
| 0.40 | 88.2% | 22.4% | 67 |
| 0.45 | 81.6% | 22.6% | 62 |
| 0.50 | 77.6% | 23.7% | 59 |
| 0.55 | 71.1% | 25.9% | 54 |
| 0.60 | 68.4% | 26.9% | 52 |
| 0.65 | 63.2% | 25.0% | 48 |
| 0.70 | 61.8% | 23.4% | 47 |
| 0.75 | 57.9% | 25.0% | 44 |
| 0.80 | 51.3% | 25.6% | 39 |
| 0.85 | 44.7% | 23.5% | 34 |
| 0.90 | 36.8% | 21.4% | 28 |
| 0.95 | 25.0% | 26.3% | 19 |

## In the sample

- Labelled cases: 0, correct —.
- Unattributed cases: 76; the true pattern is among the three candidates listed in 40.8%.

| Pattern | Cases | Labelled | Labelled correctly | Grounded first replies |
| --- | --- | --- | --- | --- |
| BIPARTITE | 9 | 0 | 0 | 88.9% |
| CYCLE | 6 | 0 | 0 | 83.3% |
| FAN-IN | 6 | 0 | 0 | 66.7% |
| FAN-OUT | 11 | 0 | 0 | 100.0% |
| GATHER-SCATTER | 7 | 0 | 0 | 100.0% |
| RANDOM | 9 | 0 | 0 | 100.0% |
| SCATTER-GATHER | 14 | 0 | 0 | 85.7% |
| STACK | 14 | 0 | 0 | 100.0% |

## Example cases

### An unattributed case written by the model

- Scheme 370: true pattern **STACK**; shown to the analyst: **UNATTRIBUTED** (top candidates: FAN-OUT 0.53, STACK 0.19, CYCLE 0.17).
- First reply: json yes, typology yes, cited yes, numeric yes, cites_ok yes, mentions_ok yes, consistent yes, strict yes; final text from **first**; 38.4 s.
- Cited fields: `case_accounts`, `case_members`, `case_account_windows`, `case_span_hours`.

> A case with 3 linked accounts and 3 federation members was analyzed. The case had 4 alerted account-windows and 12 hours spanned. The case had 3 accounts and 3 federation members, and the case had 4 alerted account-windows and 12 hours spanned.

Review actions (from the catalogue, not the model):

1. Review the source of the large credit before the split
1. Reconstruct the layers across banks
1. Reconstruct the full chain across banks

### A case whose first reply failed the check

- Scheme 320: true pattern **STACK**; shown to the analyst: **UNATTRIBUTED** (top candidates: STACK 0.94, FAN-IN 0.06, RANDOM 0.00).
- First reply: json yes, typology yes, cited yes, numeric yes, cites_ok no, mentions_ok yes, consistent yes, strict no; final text from **retry**; 57.0 s.
- Cited fields: `case_accounts`, `case_members`, `case_account_windows`, `case_span_hours`, `others_fan_in`, `others_amt_in`, `others_cross_bank_share`, `others_new_cp_share`.

> Two case accounts were linked to a case with two federation members and two account windows. The case spanned six hours, and the linked case accounts spanned six hours as well. The case had two account windows, and the linked case had two account windows.

Review actions (from the catalogue, not the model):

1. Reconstruct the layers across banks
1. Identify the senders and whether they share attributes
1. Follow the funds forward and backward across banks

Every case (prompt size, raw replies, checks, final text) is in `narrative_LI-Medium_A23_cases.jsonl`.
