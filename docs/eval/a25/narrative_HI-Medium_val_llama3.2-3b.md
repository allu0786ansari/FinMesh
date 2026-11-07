# Constrained case narrative (H3b) · HI-Medium · protocol A25N

Level S2, seed 0; 200 detected validation schemes sampled by pattern (up to 25 each). Model `llama3.2:3b` on this machine, temperature 0; json-only first, schema-constrained retry, template fallback (A25N). The model writes the text only: the typology comes from the X6 attributor (shown only above τ), the evidence from a fixed template of what S2 reveals to the owner, and the review actions from the catalogue. 1,216 s in total.

## H3b on validation

| Item | Validation |
| --- | --- |
| Grounded first replies [95% Wilson CI] | 0.9550 [0.9167, 0.9761] |
| Target | 0.9500 |
| Met on validation | yes |

Grounded = valid JSON, typology equal to the one shown (or UNATTRIBUTED), and every cited field present in the evidence. Judged on test.

## Strict grounding (A25N)

Strict = H3b, plus 1 to 4 cited fields, every number in the narrative taken from the evidence or confidence lines, and no typology named outside the candidates; A23 adds claim consistency, number words and no copied placeholders. The retry and the template are triggered by strict failure, so the analyst only sees strictly checked text.

| Item | Validation |
| --- | --- |
| Strictly grounded first replies [95% Wilson CI] | 0.1250 [0.0861, 0.1780] |
| First reply cites 1 to 4 fields | 19.5% |
| First reply names no outside typology | 93.5% |
| Replies that arrived (no timeout or error) | 200 of 200 |
| H3b among replies that arrived | 95.5% |
| Strict among replies that arrived | 12.5% |
| Delivered text names no outside typology | 100.0% |

## Claim consistency (A23)

Per-sentence rules tie the claims small models make most often to the evidence that would support them (pass-through, many payers or payees, cycles, gathering, splitting, layering); hedged sentences are skipped. Part of strict grounding in A23.

| Item | Validation |
| --- | --- |
| First replies claim-consistent | 87.5% |
| Delivered text claim-consistent | 100.0% |

| Unsupported claim | First replies | Delivered text |
| --- | --- | --- |
| cycle | 4 | 0 |
| many_payers | 3 | 0 |
| pass_through | 11 | 0 |
| split | 4 | 0 |

## What the analyst sees: the top three candidates (secondary)

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
| First reply: valid JSON | 98.5% |
| First reply: typology as shown | 98.0% |
| First reply: cited fields all real | 96.0% |
| First reply: cites at least one field | 98.5% |
| First reply: every number appears in the prompt | 95.0% |
| Retried (schema-constrained) | 87.5% |
| Retry grounded | 100.0% |
| Template fallback | 35.0% |
| Final text: numbers all from the prompt | 100.0% |
| Cases with a call error | 0 |
| Latency per case, p50 / p95 / max | 4.9 / 9.7 / 120.9 s (target p95 ≤ 30 s) |

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
| BIPARTITE | 25 | 0 | 0 | 100.0% |
| CYCLE | 25 | 0 | 0 | 92.0% |
| FAN-IN | 25 | 0 | 0 | 96.0% |
| FAN-OUT | 25 | 0 | 0 | 96.0% |
| GATHER-SCATTER | 25 | 0 | 0 | 100.0% |
| RANDOM | 25 | 0 | 0 | 92.0% |
| SCATTER-GATHER | 25 | 0 | 0 | 92.0% |
| STACK | 25 | 0 | 0 | 96.0% |

## Example cases

### An unattributed case written by the model

- Scheme 1465: true pattern **STACK**; shown to the analyst: **UNATTRIBUTED** (top candidates: FAN-OUT 0.37, STACK 0.33, FAN-IN 0.30).
- First reply: json yes, typology yes, cited yes, numeric yes, cites_ok yes, mentions_ok yes, consistent yes, strict yes; final text from **first**; 1.5 s.
- Cited fields: `case_accounts`, `case_members`, `case_account_windows`, `case_span_hours`.

> A case with 5 linked accounts and 5 federation members was analyzed. The case accounts and members were active for 72 hours, and there were 21 alerted account-windows. The case had 5 accounts, 5 members, and 21 account-windows.

Review actions (from the catalogue, not the model):

1. Review the source of the large credit before the split
1. Reconstruct the layers across banks
1. Identify the senders and whether they share attributes

### A case whose first reply failed the check

- Scheme 1365: true pattern **BIPARTITE**; shown to the analyst: **UNATTRIBUTED** (top candidates: BIPARTITE 0.97, STACK 0.02, FAN-IN 0.01).
- First reply: json yes, typology yes, cited yes, numeric yes, cites_ok no, mentions_ok yes, consistent yes, strict no; final text from **template**; 120.9 s.
- Cited fields: `own_max_amount_in`, `own_mean_cross_bank_share`, `case_accounts`, `case_members`, `case_account_windows`, `case_span_hours`.

> The linked case holds 2 accounts at 2 federation members over 6 hours, of which 1 are at your bank. The pattern is unattributed; candidates to check: BIPARTITE, STACK, FAN-IN. At your bank: largest number of payees of one account, 0 (no payees); largest number of payers of one account, 1 (one payer); mean pass-through share, 0.00 (none passed on).

Review actions (from the catalogue, not the model):

1. Map both groups and the links between them
1. Reconstruct the layers across banks
1. Identify the senders and whether they share attributes

Every case (prompt size, raw replies, checks, final text) is in `narrative_HI-Medium_A25N_cases.jsonl`.
