# X6 · pattern attribution by sharing level · LI-Large-W16

> **Sealed test (week 18).** Every model trained on the training partition; every calibration, threshold, fusion and attribution parameter fitted on validation and frozen; test scored label-free, then opened once per seed through the logged seal (`finmesh sealed-log`). Wording below that says *validation* in a column or check name refers to the frozen rule; every number is on **test**.

Seeds [0, 1, 2]; 92 pattern-labelled test schemes, 8 patterns. Each level uses its frozen G2 fusion and linking rule; a scheme is attributed through the incident holding most of its alerted accounts within 72 h, using only what the level reveals to the incident's owner (`docs/protocol/attribution_mapping.md`). Attributor: multinomial LightGBM fitted on all detected validation schemes and applied to the test schemes. Accuracy is end to end (undetected schemes count as wrong), averaged over seeds, with a 1,000-replicate scheme bootstrap. 17,574 s, peak memory 3,103 MB.

## Pattern accuracy, end to end [95% CI]

| Level | Schemes detected | Attributor (GBDT) | Majority class | Rule-based shape | Catalogue matching |
| --- | --- | --- | --- | --- | --- |
| S0 · own data only | 0.7428 | 0.1159 [0.0652, 0.1703] | 0.0942 [0.0435, 0.1558] | 0.0725 [0.0253, 0.1268] | 0.1558 [0.0906, 0.2283] |
| S1 · + cross-bank structure | 0.7138 | 0.1123 [0.0652, 0.1630] | 0.0725 [0.0398, 0.1123] | 0.0688 [0.0217, 0.1232] | 0.1196 [0.0688, 0.1775] |
| S2 · + other banks' records | 0.6812 | 0.1196 [0.0761, 0.1703] | 0.0616 [0.0181, 0.1123] | 0.0652 [0.0217, 0.1196] | 0.1268 [0.0688, 0.1957] |
| S3 (ε = 2) · + noisy records | 0.7029 | 0.0942 [0.0543, 0.1377] | 0.0580 [0.0145, 0.1087] | 0.0688 [0.0217, 0.1232] | 0.1268 [0.0725, 0.1885] |
| Oracle · all data pooled | 0.8261 | 0.1196 [0.0688, 0.1775] | 0.1268 [0.0652, 0.1957] | 0.1051 [0.0507, 0.1667] | 0.1014 [0.0507, 0.1594] |

## H3a on test

S2 − S0 attributor accuracy has a 95% CI above 0, and S2's attributor beats the majority and rule baselines. Decided here, on test.

| Item | Test |
| --- | --- |
| S2 − S0 (attributor) | 0.0036 [-0.0326, 0.0435] |
| S2 attributor − majority | 0.0580 [0.0072, 0.1124] |
| S2 attributor − rules | 0.0543 [-0.0110, 0.1232] |
| Met on test | no |

## Attributor on detected schemes

| Level | Accuracy (detected schemes) | Macro-F1 (detected schemes) |
| --- | --- | --- |
| S0 · own data only | 0.1558 | 0.1257 |
| S1 · + cross-bank structure | 0.1580 | 0.1285 |
| S2 · + other banks' records | 0.1765 | 0.1551 |
| S3 (ε = 2) · + noisy records | 0.1323 | 0.1092 |
| Oracle · all data pooled | 0.1447 | 0.1138 |

## Attributor recall by pattern (end to end)

| Pattern | S0 | S1 | S2 | S3 | oracle |
| --- | --- | --- | --- | --- | --- |
| BIPARTITE | 0.0417 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| CYCLE | 0.1282 | 0.0513 | 0.1282 | 0.0769 | 0.0513 |
| FAN-IN | 0.0222 | 0.0222 | 0.0667 | 0.0222 | 0.0222 |
| FAN-OUT | 0.2778 | 0.2500 | 0.2222 | 0.1667 | 0.1667 |
| GATHER-SCATTER | 0.0769 | 0.1538 | 0.1026 | 0.1795 | 0.1538 |
| RANDOM | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| SCATTER-GATHER | 0.0769 | 0.1538 | 0.1282 | 0.1026 | 0.2051 |
| STACK | 0.3333 | 0.2593 | 0.2963 | 0.1852 | 0.3704 |

## All paired comparisons

| Comparison | Accuracy difference [95% CI] |
| --- | --- |
| S1-S0 | -0.0036 [-0.0471, 0.0399] |
| S2-S0 | 0.0036 [-0.0326, 0.0435] |
| S3-S0 | -0.0217 [-0.0689, 0.0254] |
| oracle-S0 | 0.0036 [-0.0581, 0.0688] |
| S2 attributor-majority | 0.0580 [0.0072, 0.1124] |
| S0 attributor-majority | 0.0217 [-0.0616, 0.0979] |
| S2 attributor-rules | 0.0543 [-0.0110, 0.1232] |
| S0 attributor-rules | 0.0435 [-0.0326, 0.1160] |
| S2 attributor-catalogue | -0.0072 [-0.0833, 0.0616] |
| S0 attributor-catalogue | -0.0399 [-0.1159, 0.0362] |

Stage-level accuracy: not reported: the stage distribution is degenerate ({'layering': 92}).
