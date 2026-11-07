# A25 P4 adaptive token budget replay · LI-Medium

Rule: budget = max(A16 87,580, 2 × the bank's use in the previous epoch), capped at 350,320. Recorded legitimate use of the X1 test runs (label-free); validation history included.

| Seed | Refused, frozen A16 | Refused, adaptive | Bank-epochs over (frozen → adaptive) | PT2 frozen | PT2 adaptive |
| --- | --- | --- | --- | --- | --- |
| 0 | 0.21% | 0.21% | 1 → 1 of 16 | 8.61 | 4.65 |
| 1 | 0.00% | 0.00% | 0 → 0 of 16 | — | — |
| 2 | 0.00% | 0.00% | 0 → 0 of 16 | — | — |

Largest adaptive refusal **0.21%** (target under 1.00%: **met**). PT2 asks hashing ÷ OPRF ≥ 10; the adversary uses its best epoch.

## Ratchet: an adversary spending its whole budget every epoch

| Epochs of full spending | Budget | OPRF re-identification | PT2 |
| --- | --- | --- | --- |
| 0 | 87,580 | 0.0475 | 8.69 |
| 1 | 175,160 | 0.127 | 3.26 |
| 2 | 350,320 | 0.285 | 1.45 |
| 3 | 350,320 | 0.285 | 1.45 |
| 4 | 350,320 | 0.285 | 1.45 |
| 6 | 350,320 | 0.285 | 1.45 |
| 8 | 350,320 | 0.285 | 1.45 |

The cap stops it before it can tokenise every candidate.

