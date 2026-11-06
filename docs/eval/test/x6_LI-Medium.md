# X6 · pattern attribution by sharing level · LI-Medium

> **Sealed test (week 18).** Every model trained on the training partition; every calibration, threshold, fusion and attribution parameter fitted on validation and frozen; test scored label-free, then opened once per seed through the logged seal (`finmesh sealed-log`). Wording below that says *validation* in a column or check name refers to the frozen rule; every number is on **test**.

Seeds [0, 1, 2]; 94 pattern-labelled validation schemes, 8 patterns. Each level uses its frozen G2 fusion and linking rule; a scheme is attributed through the incident holding most of its alerted accounts within 72 h, using only what the level reveals to the incident's owner (`docs/protocol/attribution_mapping.md`). Attributor: multinomial LightGBM cross-fitted on the two time halves of validation. Accuracy is end to end (undetected schemes count as wrong), averaged over seeds, with a 1,000-replicate scheme bootstrap. 15,624 s, peak memory 3,228 MB.

## Pattern accuracy, end to end [95% CI]

| Level | Schemes detected | Attributor (GBDT) | Majority class | Rule-based shape | Catalogue matching |
| --- | --- | --- | --- | --- | --- |
| S0 · own data only | 0.7908 | 0.1702 [0.1170, 0.2340] | 0.0851 [0.0319, 0.1383] | 0.0745 [0.0284, 0.1241] | 0.1064 [0.0532, 0.1631] |
| S1 · + cross-bank structure | 0.7943 | 0.1809 [0.1206, 0.2482] | 0.0922 [0.0426, 0.1489] | 0.0567 [0.0213, 0.0994] | 0.0887 [0.0426, 0.1384] |
| S2 · + other banks' records | 0.7943 | 0.1986 [0.1348, 0.2660] | 0.0957 [0.0426, 0.1596] | 0.0532 [0.0177, 0.1028] | 0.0887 [0.0390, 0.1418] |
| S3 (ε = 2) · + noisy records | 0.7872 | 0.1206 [0.0745, 0.1667] | 0.0922 [0.0426, 0.1489] | 0.0603 [0.0213, 0.1064] | 0.0887 [0.0426, 0.1418] |
| Oracle · all data pooled | 0.8936 | 0.1560 [0.1028, 0.2128] | 0.0887 [0.0390, 0.1454] | 0.0887 [0.0390, 0.1455] | 0.1525 [0.0887, 0.2234] |

## H3a on test

S2 − S0 attributor accuracy has a 95% CI above 0, and S2's attributor beats the majority and rule baselines. Decided here, on test.

| Item | Test |
| --- | --- |
| S2 − S0 (attributor) | 0.0284 [-0.0461, 0.0887] |
| S2 attributor − majority | 0.1028 [0.0177, 0.1809] |
| S2 attributor − rules | 0.1454 [0.0708, 0.2199] |
| Met on test | no |

## Attributor on detected schemes

| Level | Accuracy (detected schemes) | Macro-F1 (detected schemes) |
| --- | --- | --- |
| S0 · own data only | 0.2146 | 0.1656 |
| S1 · + cross-bank structure | 0.2279 | 0.1863 |
| S2 · + other banks' records | 0.2500 | 0.2159 |
| S3 (ε = 2) · + noisy records | 0.1531 | 0.1366 |
| Oracle · all data pooled | 0.1743 | 0.1631 |

## Attributor recall by pattern (end to end)

| Pattern | S0 | S1 | S2 | S3 | oracle |
| --- | --- | --- | --- | --- | --- |
| BIPARTITE | 0.3056 | 0.3056 | 0.2500 | 0.3056 | 0.1944 |
| CYCLE | 0.1250 | 0.0833 | 0.1667 | 0.1667 | 0.2083 |
| FAN-IN | 0.0000 | 0.1481 | 0.1481 | 0.1111 | 0.0370 |
| FAN-OUT | 0.1282 | 0.1538 | 0.1026 | 0.0000 | 0.1026 |
| GATHER-SCATTER | 0.0000 | 0.0000 | 0.0333 | 0.0000 | 0.0667 |
| RANDOM | 0.0303 | 0.1212 | 0.1212 | 0.1818 | 0.1818 |
| SCATTER-GATHER | 0.4762 | 0.4762 | 0.5476 | 0.1667 | 0.3095 |
| STACK | 0.1569 | 0.0784 | 0.1373 | 0.0588 | 0.1176 |

## All paired comparisons

| Comparison | Accuracy difference [95% CI] |
| --- | --- |
| S1-S0 | 0.0106 [-0.0532, 0.0709] |
| S2-S0 | 0.0284 [-0.0461, 0.0887] |
| S3-S0 | -0.0496 [-0.1206, 0.0213] |
| oracle-S0 | -0.0142 [-0.0816, 0.0496] |
| S2 attributor-majority | 0.1028 [0.0177, 0.1809] |
| S0 attributor-majority | 0.0851 [0.0177, 0.1525] |
| S2 attributor-rules | 0.1454 [0.0708, 0.2199] |
| S0 attributor-rules | 0.0957 [0.0106, 0.1809] |
| S2 attributor-catalogue | 0.1099 [0.0426, 0.1845] |
| S0 attributor-catalogue | 0.0638 [-0.0142, 0.1383] |

Stage-level accuracy: not reported: the stage distribution is degenerate ({'layering': 94}).
