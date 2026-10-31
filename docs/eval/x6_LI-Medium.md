# X6 · pattern attribution by sharing level · LI-Medium

Seeds [0, 1, 2]; 93 pattern-labelled validation schemes, 8 patterns. Each level uses its frozen G2 fusion and linking rule; a scheme is attributed through the incident holding most of its alerted accounts within 72 h, using only what the level reveals to the incident's owner (`docs/protocol/attribution_mapping.md`). Attributor: multinomial LightGBM cross-fitted on the two time halves of validation. Accuracy is end to end (undetected schemes count as wrong), averaged over seeds, with a 1,000-replicate scheme bootstrap. 977 s, peak memory 1,466 MB.

## Pattern accuracy, end to end [95% CI]

| Level | Schemes detected | Attributor (GBDT) | Majority class | Rule-based shape | Catalogue matching |
| --- | --- | --- | --- | --- | --- |
| S0 · own data only | 0.8530 | 0.1219 [0.0717, 0.1828] | 0.1183 [0.0609, 0.1828] | 0.0573 [0.0179, 0.1075] | 0.1111 [0.0609, 0.1685] |
| S1 · + cross-bank structure | 0.8387 | 0.1075 [0.0717, 0.1470] | 0.1290 [0.0752, 0.1864] | 0.0681 [0.0251, 0.1183] | 0.1075 [0.0573, 0.1650] |
| S2 · + other banks' records | 0.8351 | 0.1505 [0.1004, 0.2007] | 0.1362 [0.0789, 0.1935] | 0.0645 [0.0215, 0.1219] | 0.1219 [0.0681, 0.1900] |
| S3 (ε = 2) · + noisy records | 0.8136 | 0.1039 [0.0681, 0.1434] | 0.1219 [0.0717, 0.1756] | 0.0430 [0.0108, 0.0860] | 0.1039 [0.0573, 0.1649] |
| Oracle · all data pooled | 0.9104 | 0.1613 [0.1111, 0.2186] | 0.1254 [0.0645, 0.1935] | 0.0860 [0.0323, 0.1398] | 0.0860 [0.0394, 0.1434] |

## H3a on validation

S2 − S0 attributor accuracy has a 95% CI above 0, and S2's attributor beats the majority and rule baselines. Judged on test.

| Item | Validation |
| --- | --- |
| S2 − S0 (attributor) | 0.0287 [-0.0323, 0.0896] |
| S2 attributor − majority | 0.0143 [-0.0538, 0.0824] |
| S2 attributor − rules | 0.0860 [0.0142, 0.1470] |
| Met on validation | no |

## Attributor on detected schemes

| Level | Accuracy (detected schemes) | Macro-F1 (detected schemes) |
| --- | --- | --- |
| S0 · own data only | 0.1431 | 0.1107 |
| S1 · + cross-bank structure | 0.1280 | 0.0981 |
| S2 · + other banks' records | 0.1803 | 0.1658 |
| S3 (ε = 2) · + noisy records | 0.1274 | 0.1049 |
| Oracle · all data pooled | 0.1770 | 0.1615 |

## Attributor recall by pattern (end to end)

| Pattern | S0 | S1 | S2 | S3 | oracle |
| --- | --- | --- | --- | --- | --- |
| BIPARTITE | 0.1875 | 0.2292 | 0.1042 | 0.1875 | 0.2083 |
| CYCLE | 0.0303 | 0.0606 | 0.0606 | 0.0303 | 0.0606 |
| FAN-IN | 0.0303 | 0.0606 | 0.2424 | 0.0303 | 0.1212 |
| FAN-OUT | 0.1282 | 0.0769 | 0.1538 | 0.1795 | 0.2821 |
| GATHER-SCATTER | 0.0741 | 0.0370 | 0.0370 | 0.0370 | 0.1481 |
| RANDOM | 0.0417 | 0.0833 | 0.0417 | 0.0417 | 0.1250 |
| SCATTER-GATHER | 0.3571 | 0.1905 | 0.3333 | 0.1429 | 0.2143 |
| STACK | 0.0000 | 0.0303 | 0.1515 | 0.0909 | 0.0606 |

## All paired comparisons

| Comparison | Accuracy difference [95% CI] |
| --- | --- |
| S1-S0 | -0.0143 [-0.0682, 0.0394] |
| S2-S0 | 0.0287 [-0.0323, 0.0896] |
| S3-S0 | -0.0179 [-0.0753, 0.0394] |
| oracle-S0 | 0.0394 [-0.0287, 0.1040] |
| S2 attributor-majority | 0.0143 [-0.0538, 0.0824] |
| S0 attributor-majority | 0.0036 [-0.0538, 0.0609] |
| S2 attributor-rules | 0.0860 [0.0142, 0.1470] |
| S0 attributor-rules | 0.0645 [-0.0000, 0.1362] |
| S2 attributor-catalogue | 0.0287 [-0.0502, 0.1004] |
| S0 attributor-catalogue | 0.0108 [-0.0538, 0.0753] |

Stage-level accuracy: not reported: the stage distribution is degenerate ({'layering': 93}).
