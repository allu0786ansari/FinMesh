# A25 P4 adaptive token budget replay · HI-Medium

Rule: budget = max(A16 74,510, 2 × the bank's use in the previous epoch), capped at 298,040. Recorded legitimate use of the X1 test runs (label-free); validation history included.

| Seed | Refused, frozen A16 | Refused, adaptive | Bank-epochs over (frozen → adaptive) | PT2 frozen | PT2 adaptive |
| --- | --- | --- | --- | --- | --- |
| 0 | 20.79% | 13.30% | 8 → 7 of 16 | 19.9 | 4.15 |
| 1 | 20.39% | 12.80% | 6 → 5 of 16 | — | — |
| 2 | 21.30% | 13.86% | 5 → 4 of 16 | — | — |

Largest adaptive refusal **13.86%** (target under 1.00%: **missed**). PT2 asks hashing ÷ OPRF ≥ 10; the adversary uses its best epoch.

## Ratchet: an adversary spending its whole budget every epoch

| Epochs of full spending | Budget | OPRF re-identification | PT2 |
| --- | --- | --- | --- |
| 0 | 74,510 | 0.0224 | 19.9 |
| 1 | 149,020 | 0.0847 | 5.25 |
| 2 | 298,040 | 0.224 | 1.99 |
| 3 | 298,040 | 0.224 | 1.99 |
| 4 | 298,040 | 0.224 | 1.99 |
| 6 | 298,040 | 0.224 | 1.99 |
| 8 | 298,040 | 0.224 | 1.99 |

The cap stops it before it can tokenise every candidate.

