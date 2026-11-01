# Constrained case narrative (H3b) · LI-Medium

Level S2, seed 0; 77 detected validation schemes sampled by pattern (up to 25 each). Model `llama3.2:3b` on this machine, temperature 0; json-only first, schema-constrained retry, template fallback (A21). The model writes the text only: the typology comes from the X6 attributor (shown only above τ), the evidence from a fixed template of what S2 reveals to the owner, and the review actions from the catalogue. 12,307 s in total (381 s for the S2 attributor), peak memory 1,233 MB.

## H3b on validation

| Item | Validation |
| --- | --- |
| Grounded first replies [95% Wilson CI] | 0.1818 [0.1115, 0.2824] |
| Target | 0.9500 |
| Met on validation | no |

Grounded = valid JSON, typology equal to the one shown (or UNATTRIBUTED), and every cited field present in the evidence. Judged on test.

## Reply quality and latency

| Item | Value |
| --- | --- |
| First reply: valid JSON | 49.4% |
| First reply: typology as shown | 49.4% |
| First reply: cited fields all real | 18.2% |
| First reply: cites at least one field | 49.4% |
| First reply: every number appears in the prompt | 49.4% |
| Retried (schema-constrained) | 81.8% |
| Retry grounded | 44.4% |
| Template fallback | 45.5% |
| Final text: numbers all from the prompt | 100.0% |
| Cases with a call error | 30 |
| Latency per case, p50 / p95 / max | 128.6 / 240.4 / 240.4 s (target p95 ≤ 30 s) |

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
| BIPARTITE | 14 | 0 | 0 | 0.0% |
| CYCLE | 10 | 0 | 0 | 20.0% |
| FAN-IN | 9 | 0 | 0 | 33.3% |
| FAN-OUT | 10 | 0 | 0 | 0.0% |
| GATHER-SCATTER | 7 | 0 | 0 | 28.6% |
| RANDOM | 7 | 0 | 0 | 14.3% |
| SCATTER-GATHER | 13 | 0 | 0 | 38.5% |
| STACK | 7 | 0 | 0 | 14.3% |

## Example cases

### An unattributed case

- Scheme 224: true pattern **BIPARTITE**; shown to the analyst: **UNATTRIBUTED** (top candidates: RANDOM 1.00, CYCLE 0.00, BIPARTITE 0.00).
- First reply: json no, typology no, cited no, numeric no; final text from **template**; 240.4 s.
- Cited fields: none.

> 2 accounts at 2 federation members are linked in this case over 6 hours; 1 of them are at your bank. The pattern is unattributed; candidates to check: RANDOM, CYCLE, BIPARTITE. Largest fan-out at your bank: 1; largest fan-in: 0; average pass-through: 0.00.

Review actions (from the catalogue, not the model):

1. Follow the funds forward and backward across banks
1. Reconstruct the full chain across banks
1. Map both groups and the links between them

### A case whose first reply failed the check

- Scheme 224: true pattern **BIPARTITE**; shown to the analyst: **UNATTRIBUTED** (top candidates: RANDOM 1.00, CYCLE 0.00, BIPARTITE 0.00).
- First reply: json no, typology no, cited no, numeric no; final text from **template**; 240.4 s.
- Cited fields: none.

> 2 accounts at 2 federation members are linked in this case over 6 hours; 1 of them are at your bank. The pattern is unattributed; candidates to check: RANDOM, CYCLE, BIPARTITE. Largest fan-out at your bank: 1; largest fan-in: 0; average pass-through: 0.00.

Review actions (from the catalogue, not the model):

1. Follow the funds forward and backward across banks
1. Reconstruct the full chain across banks
1. Map both groups and the links between them

Every case (prompt size, raw replies, checks, final text) is in `narrative_LI-Medium_cases.jsonl`.
