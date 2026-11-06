# X6 · pattern attribution by sharing level · HI-Medium

> **Sealed test (week 18).** Every model trained on the training partition; every calibration, threshold, fusion and attribution parameter fitted on validation and frozen; test scored label-free, then opened once per seed through the logged seal (`finmesh sealed-log`). Wording below that says *validation* in a column or check name refers to the frozen rule; every number is on **test**.

Seeds [0, 1, 2]; 500 pattern-labelled validation schemes, 8 patterns. Each level uses its frozen G2 fusion and linking rule; a scheme is attributed through the incident holding most of its alerted accounts within 72 h, using only what the level reveals to the incident's owner (`docs/protocol/attribution_mapping.md`). Attributor: multinomial LightGBM cross-fitted on the two time halves of validation. Accuracy is end to end (undetected schemes count as wrong), averaged over seeds, with a 1,000-replicate scheme bootstrap. 24,856 s, peak memory 3,565 MB.

## Pattern accuracy, end to end [95% CI]

| Level | Schemes detected | Attributor (GBDT) | Majority class | Rule-based shape | Catalogue matching |
| --- | --- | --- | --- | --- | --- |
| S0 · own data only | 0.8373 | 0.1280 [0.1080, 0.1480] | 0.0900 [0.0733, 0.1073] | 0.1073 [0.0813, 0.1340] | 0.1247 [0.0980, 0.1507] |
| S1 · + cross-bank structure | 0.8220 | 0.1500 [0.1267, 0.1734] | 0.0927 [0.0753, 0.1100] | 0.1180 [0.0920, 0.1460] | 0.1247 [0.1020, 0.1467] |
| S2 · + other banks' records | 0.8267 | 0.1720 [0.1467, 0.1967] | 0.0960 [0.0780, 0.1147] | 0.1107 [0.0847, 0.1380] | 0.1227 [0.1000, 0.1493] |
| S3 (ε = 2) · + noisy records | 0.8227 | 0.1473 [0.1247, 0.1700] | 0.0953 [0.0773, 0.1140] | 0.1153 [0.0900, 0.1420] | 0.1280 [0.1060, 0.1507] |
| Oracle · all data pooled | 0.8533 | 0.1613 [0.1367, 0.1880] | 0.0993 [0.0820, 0.1180] | 0.1200 [0.0926, 0.1480] | 0.1220 [0.0966, 0.1493] |

## H3a on test

S2 − S0 attributor accuracy has a 95% CI above 0, and S2's attributor beats the majority and rule baselines. Decided here, on test.

| Item | Test |
| --- | --- |
| S2 − S0 (attributor) | 0.0440 [0.0213, 0.0673] |
| S2 attributor − majority | 0.0760 [0.0440, 0.1053] |
| S2 attributor − rules | 0.0613 [0.0273, 0.0953] |
| Met on test | yes |

## Attributor on detected schemes

| Level | Accuracy (detected schemes) | Macro-F1 (detected schemes) |
| --- | --- | --- |
| S0 · own data only | 0.1529 | 0.1499 |
| S1 · + cross-bank structure | 0.1825 | 0.1751 |
| S2 · + other banks' records | 0.2081 | 0.2017 |
| S3 (ε = 2) · + noisy records | 0.1792 | 0.1731 |
| Oracle · all data pooled | 0.1891 | 0.1876 |

## Attributor recall by pattern (end to end)

| Pattern | S0 | S1 | S2 | S3 | oracle |
| --- | --- | --- | --- | --- | --- |
| BIPARTITE | 0.1231 | 0.2103 | 0.1795 | 0.1897 | 0.2359 |
| CYCLE | 0.1741 | 0.0995 | 0.2388 | 0.1095 | 0.1592 |
| FAN-IN | 0.1322 | 0.1149 | 0.1494 | 0.0977 | 0.1207 |
| FAN-OUT | 0.0573 | 0.0938 | 0.0573 | 0.0938 | 0.1250 |
| GATHER-SCATTER | 0.1905 | 0.2857 | 0.3036 | 0.2202 | 0.2202 |
| RANDOM | 0.1029 | 0.0735 | 0.1373 | 0.0637 | 0.1324 |
| SCATTER-GATHER | 0.1603 | 0.2372 | 0.1474 | 0.3526 | 0.1667 |
| STACK | 0.1000 | 0.1238 | 0.1714 | 0.1048 | 0.1381 |

## All paired comparisons

| Comparison | Accuracy difference [95% CI] |
| --- | --- |
| S1-S0 | 0.0220 [-0.0020, 0.0467] |
| S2-S0 | 0.0440 [0.0213, 0.0673] |
| S3-S0 | 0.0193 [-0.0040, 0.0427] |
| oracle-S0 | 0.0333 [0.0073, 0.0607] |
| S2 attributor-majority | 0.0760 [0.0440, 0.1053] |
| S0 attributor-majority | 0.0380 [0.0107, 0.0607] |
| S2 attributor-rules | 0.0613 [0.0273, 0.0953] |
| S0 attributor-rules | 0.0207 [-0.0120, 0.0547] |
| S2 attributor-catalogue | 0.0493 [0.0120, 0.0833] |
| S0 attributor-catalogue | 0.0033 [-0.0307, 0.0367] |

Stage-level accuracy: not reported: the stage distribution is degenerate ({'layering': 500}).
