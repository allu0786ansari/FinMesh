# X1 · sharing ladder on validation · LI-Medium

Seeds [0, 1, 2]; primary budget alerts_1_per_1000_per_day; schemes detected within 12 windows; primary fusion **stacker** (amendment A13). Per-scheme outcomes are averaged over seeds before the scheme bootstrap. Total 1,521 s, peak memory 1,614 MB.

![Linked detection per sharing level](frontier_LI-Medium.png)

## Linked detection per level (primary fusion)

| Configuration | Linked [95% CI] | Across members | Detected [95% CI] | Gain over S0 [95% CI] | p | AUPRC (mean) |
| --- | --- | --- | --- | --- | --- | --- |
| S0 (no sharing) | 0.1541 [0.0895, 0.2187] | 0.0000 | 0.8530 [0.7849, 0.9176] | — | — | 0.0861 |
| S1 tokens + alert flags | 0.6631 [0.5771, 0.7455] | 0.6452 | 0.8387 [0.7670, 0.9104] | 0.5090 [0.4194, 0.6057] | 0.0000 | 0.0952 |
| S2 minimised records | 0.6953 [0.6093, 0.7778] | 0.6846 | 0.8351 [0.7634, 0.9033] | 0.5412 [0.4479, 0.6380] | 0.0000 | 0.1038 |
| S4 records + embeddings | 0.6523 [0.5663, 0.7312] | 0.6344 | 0.8065 [0.7348, 0.8746] | 0.4982 [0.4086, 0.5950] | 0.0000 | 0.1061 |
| Score propagation (plaintext) | 0.7491 [0.6702, 0.8280] | 0.7312 | 0.8459 [0.7706, 0.9140] | 0.5950 [0.5018, 0.6882] | 0.0000 | 0.1102 |
| Oracle (pooled) | 0.7025 [0.6165, 0.7886] | 0.6559 | 0.9104 [0.8495, 0.9642] | 0.5484 [0.4588, 0.6344] | 0.0000 | 0.1188 |

Random alerts at the same budget: detected 0.0113, linked 0.0000.

## H1b on validation: share of the oracle gain recovered

(level − S0) / (oracle − S0) in linked detection, scheme bootstrap. Preregistered target: at least 0.60 for S2, judged on test.

| Level | Recovery [95% CI] |
| --- | --- |
| S1/stacker | 0.9281 [0.8344, 1.03] |
| S2/stacker | 0.9869 [0.8725, 1.11] |
| S4/stacker | 0.9085 [0.7986, 1.04] |

## Secondary fusion rules

| Level / rule | Linked | Detected | Gain over S0 | AUPRC (mean) |
| --- | --- | --- | --- | --- |
| S1/noisy_or | 0.6738 [0.5877, 0.7528] | 0.8423 [0.7742, 0.9032] | 0.5197 [0.4264, 0.6094] | 0.0901 |
| S1/kofn | 0.5520 [0.4588, 0.6417] | 0.7921 [0.7168, 0.8602] | 0.3978 [0.3011, 0.4946] | 0.0844 |
| S2/noisy_or | 0.6882 [0.6022, 0.7671] | 0.8244 [0.7490, 0.8925] | 0.5341 [0.4373, 0.6237] | 0.1023 |
| S2/kofn | 0.5520 [0.4588, 0.6417] | 0.7921 [0.7168, 0.8602] | 0.3978 [0.3011, 0.4946] | 0.0844 |
| S4/noisy_or | 0.6882 [0.6022, 0.7671] | 0.8244 [0.7490, 0.8925] | 0.5341 [0.4373, 0.6237] | 0.1023 |
| S4/kofn | 0.5520 [0.4588, 0.6417] | 0.7921 [0.7168, 0.8602] | 0.3978 [0.3011, 0.4946] | 0.0844 |

## Protocol per seed

| Seed | Level | Requests | Answered: alert | Record, no alert | Refused | Token evaluations | Messages | Seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | S1 | 205,502 | 7,450 | 0 | 543 | 254,267 | 411,036 | 88.20 |
| 0 | S2 | 205,502 | 7,450 | 53,662 | 543 | 254,267 | 411,036 | 88.60 |
| 0 | S4 | 205,502 | 7,450 | 53,662 | 543 | 254,267 | 411,036 | 87.50 |
| 1 | S1 | 197,151 | 6,758 | 0 | 538 | 241,828 | 394,334 | 83.50 |
| 1 | S2 | 197,151 | 6,758 | 46,417 | 538 | 241,828 | 394,334 | 83.60 |
| 1 | S4 | 197,151 | 6,758 | 46,417 | 538 | 241,828 | 394,334 | 83.50 |
| 2 | S1 | 190,467 | 6,767 | 0 | 535 | 234,476 | 380,966 | 81.10 |
| 2 | S2 | 190,467 | 6,767 | 45,345 | 535 | 234,476 | 380,966 | 80.80 |
| 2 | S4 | 190,467 | 6,767 | 45,345 | 535 | 234,476 | 380,966 | 80.80 |

## Time per seed

| Seed | s0 | oracle | records | propagation | evaluate | total |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 15.90 | 45.30 | 23.40 | 0.4000 | 154.10 | 503.30 |
| 1 | 21.70 | 43.70 | 26.20 | 0.4000 | 161.80 | 504.60 |
| 2 | 22.70 | 28.40 | 24.70 | 0.5000 | 162.80 | 481.90 |
