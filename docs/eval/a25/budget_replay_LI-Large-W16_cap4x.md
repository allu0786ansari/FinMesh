# A25 P4 adaptive token budget replay · LI-Large-W16

Rule: budget = max(A16 87,926, 2 × the bank's use in the previous epoch), capped at 351,704. Recorded legitimate use of the X1 test runs (label-free); validation history included.

| Seed | Refused, frozen A16 | Refused, adaptive | Bank-epochs over (frozen → adaptive) | PT2 frozen | PT2 adaptive |
| --- | --- | --- | --- | --- | --- |
| 0 | 4.67% | 4.67% | 4 → 4 of 16 | 9.01 | 3.2 |
| 1 | 3.47% | 3.47% | 4 → 4 of 16 | — | — |
| 2 | 1.25% | 1.25% | 2 → 2 of 16 | — | — |

Largest adaptive refusal **4.67%** (target under 1.00%: **missed**). PT2 asks hashing ÷ OPRF ≥ 10; the adversary uses its best epoch.

## Ratchet: an adversary spending its whole budget every epoch

| Epochs of full spending | Budget | OPRF re-identification | PT2 |
| --- | --- | --- | --- |
| 0 | 87,926 | 0.0412 | 9.32 |
| 1 | 175,852 | 0.114 | 3.36 |
| 2 | 351,704 | 0.26 | 1.48 |
| 3 | 351,704 | 0.26 | 1.48 |
| 4 | 351,704 | 0.26 | 1.48 |
| 6 | 351,704 | 0.26 | 1.48 |
| 8 | 351,704 | 0.26 | 1.48 |

The cap stops it before it can tokenise every candidate.

