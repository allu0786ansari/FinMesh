# Constrained case narrative (H3b) · LI-Large-W16 · protocol A25N

> **Sealed test (week 18).** Every model trained on the training partition; every calibration, threshold, fusion and attribution parameter fitted on validation and frozen; test scored label-free, then opened once per seed through the logged seal (`finmesh sealed-log`). Wording below that says *validation* in a column or check name refers to the frozen rule; every number is on **test**.

Level S2, seed 0; 61 detected test schemes sampled by pattern (up to 25 each). Model `qwen3:8b` on this machine, temperature 0; json-only first, schema-constrained retry, template fallback (A25N). The model writes the text only: the typology comes from the X6 attributor (shown only above τ), the evidence from a fixed template of what S2 reveals to the owner, and the review actions from the catalogue. 717 s in total (attribution tables from `finmesh test-x1`, attributor fitted on test).

## H3b on test

| Item | Test |
| --- | --- |
| Grounded first replies [95% Wilson CI] | 0.9508 [0.8651, 0.9831] |
| Target | 0.9500 |
| Met on test | yes |

Grounded = valid JSON, typology equal to the one shown (or UNATTRIBUTED), and every cited field present in the evidence. Decided here, on test.

## Strict grounding (A25N)

Strict = H3b, plus 1 to 4 cited fields, every number in the narrative taken from the evidence or confidence lines, and no typology named outside the candidates; A23 adds claim consistency, number words and no copied placeholders. The retry and the template are triggered by strict failure, so the analyst only sees strictly checked text.

| Item | Test |
| --- | --- |
| Strictly grounded first replies [95% Wilson CI] | 0.5574 [0.4330, 0.6749] |
| First reply cites 1 to 4 fields | 100.0% |
| First reply names no outside typology | 100.0% |
| Replies that arrived (no timeout or error) | 61 of 61 |
| H3b among replies that arrived | 95.1% |
| Strict among replies that arrived | 55.7% |
| Delivered text names no outside typology | 100.0% |

## Claim consistency (A23)

Per-sentence rules tie the claims small models make most often to the evidence that would support them (pass-through, many payers or payees, cycles, gathering, splitting, layering); hedged sentences are skipped. Part of strict grounding in A23.

| Item | Test |
| --- | --- |
| First replies claim-consistent | 60.7% |
| Delivered text claim-consistent | 100.0% |

| Unsupported claim | First replies | Delivered text |
| --- | --- | --- |
| cycle | 14 | 0 |
| pass_through | 10 | 0 |

## What the analyst sees: the top three candidates (secondary)

Cross-fitted attributor, seed 0, all 92 pattern-labelled test schemes; end to end counts undetected schemes as misses; 1,000-replicate scheme bootstrap.

| Level | Top 1, end to end [95% CI] | Top 3, end to end [95% CI] | Top 3, detected schemes |
| --- | --- | --- | --- |
| S0 · own data only | 0.0978 [0.0435, 0.1630] | 0.3370 [0.2500, 0.4348] | 45.6% |
| S2 · + shared evidence | 0.1630 [0.0870, 0.2391] | 0.3152 [0.2174, 0.4022] | 47.5% |
| Baseline · 3 most frequent patterns | — | 0.2826 [0.1848, 0.3696] | 42.6% |
| Baseline · chance | — | — | 37.5% |

| Comparison | Difference [95% CI] |
| --- | --- |
| S2 - S0 (top 3) | -0.0217 [-0.1304, 0.0870] |
| S2 - S0 (top 1) | 0.0652 [0.0000, 0.1304] |
| S2 top 3 - frequency top 3 | 0.0326 [-0.0764, 0.1413] |

## Reply quality and latency

| Item | Value |
| --- | --- |
| First reply: valid JSON | 100.0% |
| First reply: typology as shown | 100.0% |
| First reply: cited fields all real | 95.1% |
| First reply: cites at least one field | 100.0% |
| First reply: every number appears in the prompt | 100.0% |
| Retried (schema-constrained) | 85.2% |
| Retry grounded | 100.0% |
| Template fallback | 23.0% |
| Final text: numbers all from the prompt | 100.0% |
| Cases with a call error | 0 |
| Latency per case, p50 / p95 / max | 9.0 / 15.2 / 143.1 s (target p95 ≤ 30 s) |

## Abstention: when the attributor's label is shown

τ = **none**: the smallest threshold whose selective accuracy on all detected validation schemes is at least 50% with coverage at least 10% (61 detected of 92 schemes; attributor accuracy without abstention 24.6%). No threshold qualifies: every case is UNATTRIBUTED with its top three candidates.

| τ | Coverage | Selective accuracy | Schemes labelled |
| --- | --- | --- | --- |
| 0.30 | 98.4% | 25.0% | 60 |
| 0.35 | 96.7% | 23.7% | 59 |
| 0.40 | 96.7% | 23.7% | 59 |
| 0.45 | 88.5% | 20.4% | 54 |
| 0.50 | 83.6% | 21.6% | 51 |
| 0.55 | 83.6% | 21.6% | 51 |
| 0.60 | 80.3% | 22.4% | 49 |
| 0.65 | 73.8% | 17.8% | 45 |
| 0.70 | 67.2% | 17.1% | 41 |
| 0.75 | 57.4% | 11.4% | 35 |
| 0.80 | 54.1% | 12.1% | 33 |
| 0.85 | 44.3% | 14.8% | 27 |
| 0.90 | 41.0% | 16.0% | 25 |
| 0.95 | 37.7% | 17.4% | 23 |

## In the sample

- Labelled cases: 0, correct —.
- Unattributed cases: 61; the true pattern is among the three candidates listed in 47.5%.

| Pattern | Cases | Labelled | Labelled correctly | Grounded first replies |
| --- | --- | --- | --- | --- |
| BIPARTITE | 5 | 0 | 0 | 100.0% |
| CYCLE | 8 | 0 | 0 | 87.5% |
| FAN-IN | 10 | 0 | 0 | 100.0% |
| FAN-OUT | 11 | 0 | 0 | 90.9% |
| GATHER-SCATTER | 6 | 0 | 0 | 100.0% |
| RANDOM | 6 | 0 | 0 | 100.0% |
| SCATTER-GATHER | 9 | 0 | 0 | 88.9% |
| STACK | 6 | 0 | 0 | 100.0% |

## Example cases

### An unattributed case written by the model

- Scheme 307: true pattern **RANDOM**; shown to the analyst: **UNATTRIBUTED** (top candidates: STACK 0.92, BIPARTITE 0.03, FAN-OUT 0.03).
- First reply: json yes, typology yes, cited yes, numeric yes; final text from **first**; 9.0 s.
- Cited fields: `own_accounts`, `own_max_fan_out`, `own_max_fan_in`, `own_mean_pass_through`.

> The linked case holds 2 accounts at 2 federation members over 6 hours, of which 1 are at your bank. The pattern is unattributed; candidates to check: STACK, BIPARTITE, FAN-OUT. Key evidence: case accounts at your bank (at your bank): 1; max distinct payees of one account (at your bank): 1, one payee; max distinct payers of one account (at your bank): 0, no payers; mean share of inflow paid out again (at your bank): 0.00, none passed on.

Review actions (from the catalogue, not the model):

1. Reconstruct the layers across banks
1. Map both groups and the links between them
1. Review the source of the large credit before the split

### A case whose first reply failed the check

- Scheme 269: true pattern **FAN-IN**; shown to the analyst: **UNATTRIBUTED** (top candidates: STACK 0.98, FAN-OUT 0.01, SCATTER-GATHER 0.00).
- First reply: json yes, typology yes, cited yes, numeric yes; final text from **retry**; 143.1 s.
- Cited fields: `own_max_fan_out`, `own_max_fan_in`, `own_mean_pass_through`, `own_max_cycles`.

> The linked case holds 2 accounts at 2 federation members over 6 hours, of which 1 are at your bank. The pattern is unattributed; candidates to check: STACK, FAN-OUT, SCATTER-GATHER. Key evidence: case accounts at your bank (at your bank): 1; alerted account-windows at your bank (at your bank): 1; hours spanned at your bank (at your bank): 6; max distinct payees of one account (at your bank): 1, one payee.

Review actions (from the catalogue, not the model):

1. Reconstruct the layers across banks
1. Review the source of the large credit before the split
1. Link the intermediate accounts as one case

Every case (prompt size, raw replies, checks, final text) is in `narrative_LI-Large-W16_A25N_cases.jsonl`.
