# X6 · pattern attribution by sharing level · HI-Large-W16

> **Sealed test (week 18).** Every model trained on the training partition; every calibration, threshold, fusion and attribution parameter fitted on validation and frozen; test scored label-free, then opened once per seed through the logged seal (`finmesh sealed-log`). Wording below that says *validation* in a column or check name refers to the frozen rule; every number is on **test**.

Seeds [0, 1, 2]; 620 pattern-labelled test schemes, 8 patterns. Each level uses its frozen G2 fusion and linking rule; a scheme is attributed through the incident holding most of its alerted accounts within 72 h, using only what the level reveals to the incident's owner (`docs/protocol/attribution_mapping.md`). Attributor: multinomial LightGBM fitted on all detected validation schemes and applied to the test schemes. Accuracy is end to end (undetected schemes count as wrong), averaged over seeds, with a 1,000-replicate scheme bootstrap. 22,602 s, peak memory 3,355 MB.

## Pattern accuracy, end to end [95% CI]

| Level | Schemes detected | Attributor (GBDT) | Majority class | Rule-based shape | Catalogue matching |
| --- | --- | --- | --- | --- | --- |
| S0 · own data only | 0.7478 | 0.0882 [0.0715, 0.1059] | 0.0957 [0.0720, 0.1188] | 0.0677 [0.0510, 0.0882] | 0.0968 [0.0769, 0.1188] |
| S1 · + cross-bank structure | 0.7237 | 0.0919 [0.0763, 0.1086] | 0.0957 [0.0731, 0.1188] | 0.0645 [0.0478, 0.0828] | 0.0866 [0.0661, 0.1086] |
| S2 · + other banks' records | 0.7140 | 0.1075 [0.0892, 0.1258] | 0.0946 [0.0720, 0.1172] | 0.0629 [0.0468, 0.0823] | 0.0823 [0.0651, 0.1006] |
| S3 (ε = 2) · + noisy records | 0.7215 | 0.0860 [0.0720, 0.1000] | 0.0952 [0.0726, 0.1178] | 0.0661 [0.0495, 0.0850] | 0.0903 [0.0710, 0.1102] |
| Oracle · all data pooled | 0.7887 | 0.1124 [0.0957, 0.1323] | 0.1000 [0.0769, 0.1231] | 0.0737 [0.0548, 0.0952] | 0.0849 [0.0656, 0.1048] |

## H3a on test

S2 − S0 attributor accuracy has a 95% CI above 0, and S2's attributor beats the majority and rule baselines. Decided here, on test.

| Item | Test |
| --- | --- |
| S2 − S0 (attributor) | 0.0194 [-0.0011, 0.0414] |
| S2 attributor − majority | 0.0129 [-0.0161, 0.0398] |
| S2 attributor − rules | 0.0446 [0.0172, 0.0683] |
| Met on test | no |

## Attributor on detected schemes

| Level | Accuracy (detected schemes) | Macro-F1 (detected schemes) |
| --- | --- | --- |
| S0 · own data only | 0.1179 | 0.1082 |
| S1 · + cross-bank structure | 0.1269 | 0.1201 |
| S2 · + other banks' records | 0.1504 | 0.1480 |
| S3 (ε = 2) · + noisy records | 0.1192 | 0.1107 |
| Oracle · all data pooled | 0.1425 | 0.1377 |

## Attributor recall by pattern (end to end)

| Pattern | S0 | S1 | S2 | S3 | oracle |
| --- | --- | --- | --- | --- | --- |
| BIPARTITE | 0.0228 | 0.0274 | 0.0502 | 0.0457 | 0.0868 |
| CYCLE | 0.0578 | 0.1111 | 0.1067 | 0.0400 | 0.0711 |
| FAN-IN | 0.1603 | 0.0970 | 0.1435 | 0.0506 | 0.0970 |
| FAN-OUT | 0.0855 | 0.0769 | 0.0940 | 0.0598 | 0.1496 |
| GATHER-SCATTER | 0.1308 | 0.1055 | 0.1308 | 0.1435 | 0.1772 |
| RANDOM | 0.0329 | 0.0329 | 0.0892 | 0.0563 | 0.0516 |
| SCATTER-GATHER | 0.1473 | 0.1744 | 0.1318 | 0.1395 | 0.1047 |
| STACK | 0.0506 | 0.0928 | 0.1055 | 0.1392 | 0.1519 |

## All paired comparisons

| Comparison | Accuracy difference [95% CI] |
| --- | --- |
| S1-S0 | 0.0038 [-0.0129, 0.0226] |
| S2-S0 | 0.0194 [-0.0011, 0.0414] |
| S3-S0 | -0.0022 [-0.0215, 0.0172] |
| oracle-S0 | 0.0242 [0.0027, 0.0462] |
| S2 attributor-majority | 0.0129 [-0.0161, 0.0398] |
| S0 attributor-majority | -0.0075 [-0.0355, 0.0199] |
| S2 attributor-rules | 0.0446 [0.0172, 0.0683] |
| S0 attributor-rules | 0.0204 [-0.0075, 0.0457] |
| S2 attributor-catalogue | 0.0253 [-0.0000, 0.0489] |
| S0 attributor-catalogue | -0.0086 [-0.0339, 0.0151] |

Stage-level accuracy: not reported: the stage distribution is degenerate ({'layering': 620}).
