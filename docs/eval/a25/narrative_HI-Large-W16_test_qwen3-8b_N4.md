# Constrained case narrative (H3b) · HI-Large-W16 · protocol A25N

> **Sealed test (week 18).** Every model trained on the training partition; every calibration, threshold, fusion and attribution parameter fitted on validation and frozen; test scored label-free, then opened once per seed through the logged seal (`finmesh sealed-log`). Wording below that says *validation* in a column or check name refers to the frozen rule; every number is on **test**.

Level S2, seed 0; 200 detected test schemes sampled by pattern (up to 25 each). Model `qwen3:8b` on this machine, temperature 0; json-only first, schema-constrained retry, template fallback (A25N). The model writes the text only: the typology comes from the X6 attributor (shown only above τ), the evidence from a fixed template of what S2 reveals to the owner, and the review actions from the catalogue. 2,190 s in total (attribution tables from `finmesh test-x1`, attributor fitted on test).

## H3b on test

| Item | Test |
| --- | --- |
| Grounded first replies [95% Wilson CI] | 1.00 [0.9812, 1.0000] |
| Target | 0.9500 |
| Met on test | yes |

Grounded = valid JSON, typology equal to the one shown (or UNATTRIBUTED), and every cited field present in the evidence. Decided here, on test.

## Strict grounding (A25N)

Strict = H3b, plus 1 to 4 cited fields, every number in the narrative taken from the evidence or confidence lines, and no typology named outside the candidates; A23 adds claim consistency, number words and no copied placeholders. The retry and the template are triggered by strict failure, so the analyst only sees strictly checked text.

| Item | Test |
| --- | --- |
| Strictly grounded first replies [95% Wilson CI] | 0.8200 [0.7609, 0.8671] |
| First reply cites 1 to 4 fields | 100.0% |
| First reply names no outside typology | 100.0% |
| Replies that arrived (no timeout or error) | 200 of 200 |
| H3b among replies that arrived | 100.0% |
| Strict among replies that arrived | 82.0% |
| Delivered text names no outside typology | 100.0% |

## Claim consistency (A23)

Per-sentence rules tie the claims small models make most often to the evidence that would support them (pass-through, many payers or payees, cycles, gathering, splitting, layering); hedged sentences are skipped. Part of strict grounding in A23.

| Item | Test |
| --- | --- |
| First replies claim-consistent | 83.5% |
| Delivered text claim-consistent | 100.0% |

| Unsupported claim | First replies | Delivered text |
| --- | --- | --- |
| cycle | 9 | 0 |
| many_payers | 1 | 0 |
| pass_through | 23 | 0 |

## What the analyst sees: the top three candidates (secondary)

Cross-fitted attributor, seed 0, all 620 pattern-labelled test schemes; end to end counts undetected schemes as misses; 1,000-replicate scheme bootstrap.

| Level | Top 1, end to end [95% CI] | Top 3, end to end [95% CI] | Top 3, detected schemes |
| --- | --- | --- | --- |
| S0 · own data only | 0.0887 [0.0661, 0.1113] | 0.2694 [0.2371, 0.3048] | 35.9% |
| S2 · + shared evidence | 0.1081 [0.0839, 0.1323] | 0.2919 [0.2565, 0.3290] | 40.8% |
| Baseline · 3 most frequent patterns | — | 0.2726 [0.2387, 0.3081] | 38.1% |
| Baseline · chance | — | — | 37.5% |

| Comparison | Difference [95% CI] |
| --- | --- |
| S2 - S0 (top 3) | 0.0226 [-0.0178, 0.0613] |
| S2 - S0 (top 1) | 0.0194 [-0.0097, 0.0516] |
| S2 top 3 - frequency top 3 | 0.0194 [-0.0210, 0.0581] |

## Reply quality and latency

| Item | Value |
| --- | --- |
| First reply: valid JSON | 100.0% |
| First reply: typology as shown | 100.0% |
| First reply: cited fields all real | 100.0% |
| First reply: cites at least one field | 100.0% |
| First reply: every number appears in the prompt | 100.0% |
| Retried (schema-constrained) | 73.0% |
| Retry grounded | 100.0% |
| Template fallback | 10.0% |
| Final text: numbers all from the prompt | 100.0% |
| Cases with a call error | 0 |
| Latency per case, p50 / p95 / max | 10.1 / 15.9 / 145.0 s (target p95 ≤ 30 s) |

## Abstention: when the attributor's label is shown

τ = **none**: the smallest threshold whose selective accuracy on all detected validation schemes is at least 50% with coverage at least 10% (444 detected of 620 schemes; attributor accuracy without abstention 15.1%). No threshold qualifies: every case is UNATTRIBUTED with its top three candidates.

| τ | Coverage | Selective accuracy | Schemes labelled |
| --- | --- | --- | --- |
| 0.30 | 91.2% | 15.3% | 405 |
| 0.35 | 87.4% | 15.7% | 388 |
| 0.40 | 77.7% | 15.9% | 345 |
| 0.45 | 71.4% | 16.4% | 317 |
| 0.50 | 63.7% | 16.6% | 283 |
| 0.55 | 56.3% | 18.0% | 250 |
| 0.60 | 46.8% | 18.8% | 208 |
| 0.65 | 42.3% | 18.6% | 188 |
| 0.70 | 35.4% | 17.8% | 157 |
| 0.75 | 30.0% | 18.0% | 133 |
| 0.80 | 26.6% | 19.5% | 118 |
| 0.85 | 20.3% | 18.9% | 90 |
| 0.90 | 16.0% | 16.9% | 71 |
| 0.95 | 9.5% | 16.7% | 42 |

## In the sample

- Labelled cases: 0, correct —.
- Unattributed cases: 200; the true pattern is among the three candidates listed in 40.0%.

| Pattern | Cases | Labelled | Labelled correctly | Grounded first replies |
| --- | --- | --- | --- | --- |
| BIPARTITE | 25 | 0 | 0 | 100.0% |
| CYCLE | 25 | 0 | 0 | 100.0% |
| FAN-IN | 25 | 0 | 0 | 100.0% |
| FAN-OUT | 25 | 0 | 0 | 100.0% |
| GATHER-SCATTER | 25 | 0 | 0 | 100.0% |
| RANDOM | 25 | 0 | 0 | 100.0% |
| SCATTER-GATHER | 25 | 0 | 0 | 100.0% |
| STACK | 25 | 0 | 0 | 100.0% |

## Example cases

### An unattributed case written by the model

- Scheme 232: true pattern **GATHER-SCATTER**; shown to the analyst: **UNATTRIBUTED** (top candidates: RANDOM 0.33, BIPARTITE 0.30, GATHER-SCATTER 0.12).
- First reply: json yes, typology yes, cited yes, numeric yes; final text from **first**; 3.4 s.
- Cited fields: `own_max_amount_in`, `own_mean_cross_bank_share`, `own_mean_new_counterparty_share`.

> The linked case holds 1 accounts at 1 federation members over 6 hours, of which 1 are at your bank. The pattern is unattributed; candidates to check: RANDOM, BIPARTITE, GATHER-SCATTER. Key evidence: max amount received by one account in a window (at your bank): 31,312; mean share of transfers with other banks (at your bank): 1.00, nearly all with other banks; mean share of new counterparties (at your bank): 0.50, most new counterparties.

Review actions (from the catalogue, not the model):

1. Follow the funds forward and backward across banks
1. Map both groups and the links between them
1. Treat the central account as a possible collection point

### A case whose first reply failed the check

- Scheme 222: true pattern **GATHER-SCATTER**; shown to the analyst: **UNATTRIBUTED** (top candidates: FAN-OUT 0.85, FAN-IN 0.09, RANDOM 0.05).
- First reply: json yes, typology yes, cited yes, numeric yes; final text from **template**; 145.0 s.
- Cited fields: `own_accounts`, `own_max_fan_out`, `own_max_amount_out`, `own_mean_new_counterparty_share`.

> The linked case holds 1 accounts at 1 federation members over 6 hours, of which 1 are at your bank. The pattern is unattributed; candidates to check: FAN-OUT, FAN-IN, RANDOM. At your bank: largest number of payees of one account, 1 (one payee); largest number of payers of one account, 0 (no payers); mean pass-through share, 0.00 (none passed on).

Review actions (from the catalogue, not the model):

1. Review the source of the large credit before the split
1. Identify the senders and whether they share attributes
1. Follow the funds forward and backward across banks

Every case (prompt size, raw replies, checks, final text) is in `narrative_HI-Large-W16_A25N_cases.jsonl`.
