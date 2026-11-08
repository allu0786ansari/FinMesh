# A25 P4 adaptive token budget replay · HI-Large-W16

Rule: budget = max(A16 109,282, 2 × the bank's use in the previous epoch), capped at 437,128. Recorded legitimate use of the X1 test runs (label-free); validation history included.

| Seed | Refused, frozen A16 | Refused, adaptive | Bank-epochs over (frozen → adaptive) | PT2 frozen | PT2 adaptive |
| --- | --- | --- | --- | --- | --- |
| 0 | 5.12% | 5.12% | 6 → 6 of 16 | 7.99 | 2.59 |
| 1 | 6.12% | 6.12% | 6 → 6 of 16 | — | — |
| 2 | 5.59% | 5.59% | 6 → 6 of 16 | — | — |

Largest adaptive refusal **6.12%** (target under 1.00%: **missed**). PT2 asks hashing ÷ OPRF ≥ 10; the adversary uses its best epoch.

## Ratchet: an adversary spending its whole budget every epoch

| Epochs of full spending | Budget | OPRF re-identification | PT2 |
| --- | --- | --- | --- |
| 0 | 109,282 | 0.0485 | 8.07 |
| 1 | 218,564 | 0.139 | 2.82 |
| 2 | 437,128 | 0.32 | 1.22 |
| 3 | 437,128 | 0.32 | 1.22 |
| 4 | 437,128 | 0.32 | 1.22 |
| 6 | 437,128 | 0.32 | 1.22 |
| 8 | 437,128 | 0.32 | 1.22 |

The cap stops it before it can tokenise every candidate.

