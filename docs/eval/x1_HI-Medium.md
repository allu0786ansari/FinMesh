# X1 · sharing ladder on validation · HI-Medium

Seeds [0, 1, 2]; primary budget alerts_1_per_1000_per_day; schemes detected within 12 windows; primary fusion **stacker** (amendment A13). Per-scheme outcomes are averaged over seeds before the scheme bootstrap. Total 1,801 s, peak memory 1,620 MB.

![Linked detection per sharing level](frontier_HI-Medium.png)

## Linked detection per level (primary fusion)

| Configuration | Linked [95% CI] | Across members | Detected [95% CI] | Gain over S0 [95% CI] | p | AUPRC (mean) |
| --- | --- | --- | --- | --- | --- | --- |
| S0 (no sharing) | 0.1736 [0.1446, 0.2033] | 0.0000 | 0.8730 [0.8469, 0.8966] | — | — | 0.3337 |
| S1 tokens + alert flags | 0.7266 [0.6933, 0.7592] | 0.6933 | 0.8554 [0.8282, 0.8814] | 0.5529 [0.5136, 0.5935] | 0.0000 | 0.3735 |
| S2 minimised records | 0.7356 [0.7030, 0.7713] | 0.7036 | 0.8584 [0.8330, 0.8839] | 0.5620 [0.5227, 0.6025] | 0.0000 | 0.3763 |
| S4 records + embeddings | 0.7042 [0.6703, 0.7405] | 0.6745 | 0.8391 [0.8100, 0.8669] | 0.5306 [0.4894, 0.5711] | 0.0000 | 0.3897 |
| Score propagation (plaintext) | 0.7036 [0.6697, 0.7399] | 0.6655 | 0.8566 [0.8300, 0.8832] | 0.5299 [0.4912, 0.5705] | 0.0000 | 0.4027 |
| Oracle (pooled) | 0.6721 [0.6364, 0.7066] | 0.6219 | 0.8905 [0.8651, 0.9153] | 0.4985 [0.4567, 0.5372] | 0.0000 | 0.3961 |

Random alerts at the same budget: detected 0.0102, linked 0.0000.

## H1b on validation: share of the oracle gain recovered

(level − S0) / (oracle − S0) in linked detection, scheme bootstrap. Preregistered target: at least 0.60 for S2, judged on test.

| Level | Recovery [95% CI] |
| --- | --- |
| S1/stacker | 1.11 [1.06, 1.16] |
| S2/stacker | 1.13 [1.07, 1.19] |
| S4/stacker | 1.06 [1.01, 1.12] |

## Secondary fusion rules

| Level / rule | Linked | Detected | Gain over S0 | AUPRC (mean) |
| --- | --- | --- | --- | --- |
| S1/noisy_or | 0.6800 [0.6449, 0.7145] | 0.8669 [0.8403, 0.8923] | 0.5064 [0.4670, 0.5487] | 0.3623 |
| S1/kofn | 0.6467 [0.6104, 0.6830] | 0.8603 [0.8342, 0.8863] | 0.4731 [0.4277, 0.5160] | 0.3650 |
| S2/noisy_or | 0.6842 [0.6503, 0.7205] | 0.8215 [0.7925, 0.8494] | 0.5106 [0.4713, 0.5517] | 0.3786 |
| S2/kofn | 0.6467 [0.6104, 0.6830] | 0.8603 [0.8342, 0.8863] | 0.4731 [0.4277, 0.5160] | 0.3650 |
| S4/noisy_or | 0.6842 [0.6503, 0.7205] | 0.8215 [0.7925, 0.8494] | 0.5106 [0.4713, 0.5517] | 0.3786 |
| S4/kofn | 0.6467 [0.6104, 0.6830] | 0.8603 [0.8342, 0.8863] | 0.4731 [0.4277, 0.5160] | 0.3650 |

## Protocol per seed

| Seed | Level | Requests | Answered: alert | Record, no alert | Refused | Token evaluations | Messages | Seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | S1 | 231,520 | 10,076 | 0 | 811 | 272,380 | 463,072 | 98.90 |
| 0 | S2 | 231,520 | 10,076 | 56,219 | 811 | 272,380 | 463,072 | 100.50 |
| 0 | S4 | 231,520 | 10,076 | 56,219 | 811 | 272,380 | 463,072 | 96.80 |
| 1 | S1 | 223,237 | 9,963 | 0 | 789 | 261,691 | 446,506 | 93.10 |
| 1 | S2 | 223,237 | 9,963 | 49,804 | 789 | 261,691 | 446,506 | 92.60 |
| 1 | S4 | 223,237 | 9,963 | 49,804 | 789 | 261,691 | 446,506 | 91.90 |
| 2 | S1 | 259,834 | 9,962 | 0 | 782 | 265,152 | 519,700 | 98.30 |
| 2 | S2 | 259,834 | 9,962 | 48,875 | 782 | 265,152 | 519,700 | 98.50 |
| 2 | S4 | 259,834 | 9,962 | 48,875 | 782 | 265,152 | 519,700 | 98.50 |

## Time per seed

| Seed | s0 | oracle | records | propagation | evaluate | total |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 40.10 | 91.20 | 22.90 | 0.4000 | 165.10 | 615.90 |
| 1 | 37.10 | 78.70 | 22.50 | 0.3000 | 155.40 | 571.70 |
| 2 | 42.00 | 64.80 | 21.50 | 0.4000 | 159.20 | 583.40 |
