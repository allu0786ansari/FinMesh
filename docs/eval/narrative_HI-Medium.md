# Constrained case narrative (H3b) · HI-Medium

Level S2, seed 0; 200 detected validation schemes sampled by pattern (up to 25 each). Model `llama3.2:3b` on this machine, temperature 0; json-only first, schema-constrained retry, template fallback (A21). The model writes the text only: the typology comes from the X6 attributor (shown only above τ), the evidence from a fixed template of what S2 reveals to the owner, and the review actions from the catalogue. 37,572 s in total (562 s for the S2 attributor), peak memory 1,264 MB.

## H3b on validation

| Item | Validation |
| --- | --- |
| Grounded first replies [95% Wilson CI] | 0.1050 [0.0697, 0.1552] |
| Target | 0.9500 |
| Met on validation | no |

Grounded = valid JSON, typology equal to the one shown (or UNATTRIBUTED), and every cited field present in the evidence. Judged on test.

## Reply quality and latency

| Item | Value |
| --- | --- |
| First reply: valid JSON | 28.5% |
| First reply: typology as shown | 28.5% |
| First reply: cited fields all real | 10.5% |
| First reply: cites at least one field | 28.5% |
| First reply: every number appears in the prompt | 28.5% |
| Retried (schema-constrained) | 89.5% |
| Retry grounded | 27.9% |
| Template fallback | 64.5% |
| Final text: numbers all from the prompt | 100.0% |
| Cases with a call error | 119 |
| Latency per case, p50 / p95 / max | 240.1 / 240.3 / 240.4 s (target p95 ≤ 30 s) |

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
| BIPARTITE | 25 | 0 | 0 | 12.0% |
| CYCLE | 25 | 0 | 0 | 8.0% |
| FAN-IN | 25 | 0 | 0 | 8.0% |
| FAN-OUT | 25 | 0 | 0 | 16.0% |
| GATHER-SCATTER | 25 | 0 | 0 | 4.0% |
| RANDOM | 25 | 0 | 0 | 8.0% |
| SCATTER-GATHER | 25 | 0 | 0 | 20.0% |
| STACK | 25 | 0 | 0 | 8.0% |

## Example cases

### An unattributed case

- Scheme 1365: true pattern **BIPARTITE**; shown to the analyst: **UNATTRIBUTED** (top candidates: BIPARTITE 0.97, STACK 0.02, FAN-IN 0.01).
- First reply: json no, typology no, cited no, numeric no; final text from **template**; 176.5 s.
- Cited fields: none.

> 2 accounts at 2 federation members are linked in this case over 6 hours; 1 of them are at your bank. The pattern is unattributed; candidates to check: BIPARTITE, STACK, FAN-IN. Largest fan-out at your bank: 0; largest fan-in: 1; average pass-through: 0.00.

Review actions (from the catalogue, not the model):

1. Map both groups and the links between them
1. Reconstruct the layers across banks
1. Identify the senders and whether they share attributes

### A case whose first reply failed the check

- Scheme 1365: true pattern **BIPARTITE**; shown to the analyst: **UNATTRIBUTED** (top candidates: BIPARTITE 0.97, STACK 0.02, FAN-IN 0.01).
- First reply: json no, typology no, cited no, numeric no; final text from **template**; 176.5 s.
- Cited fields: none.

> 2 accounts at 2 federation members are linked in this case over 6 hours; 1 of them are at your bank. The pattern is unattributed; candidates to check: BIPARTITE, STACK, FAN-IN. Largest fan-out at your bank: 0; largest fan-in: 1; average pass-through: 0.00.

Review actions (from the catalogue, not the model):

1. Map both groups and the links between them
1. Reconstruct the layers across banks
1. Identify the senders and whether they share attributes

Every case (prompt size, raw replies, checks, final text) is in `narrative_HI-Medium_cases.jsonl`.
