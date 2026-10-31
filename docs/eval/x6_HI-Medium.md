# X6 · pattern attribution by sharing level · HI-Medium

Seeds [0, 1, 2]; 551 pattern-labelled validation schemes, 8 patterns. Each level uses its frozen G2 fusion and linking rule; a scheme is attributed through the incident holding most of its alerted accounts within 72 h, using only what the level reveals to the incident's owner (`docs/protocol/attribution_mapping.md`). Attributor: multinomial LightGBM cross-fitted on the two time halves of validation. Accuracy is end to end (undetected schemes count as wrong), averaged over seeds, with a 1,000-replicate scheme bootstrap. 1,271 s, peak memory 1,610 MB.

## Pattern accuracy, end to end [95% CI]

| Level | Schemes detected | Attributor (GBDT) | Majority class | Rule-based shape | Catalogue matching |
| --- | --- | --- | --- | --- | --- |
| S0 · own data only | 0.8730 | 0.1464 [0.1240, 0.1706] | 0.1083 [0.0810, 0.1361] | 0.1107 [0.0859, 0.1361] | 0.1313 [0.1071, 0.1579] |
| S1 · + cross-bank structure | 0.8554 | 0.1869 [0.1621, 0.2123] | 0.1131 [0.0853, 0.1410] | 0.0974 [0.0738, 0.1216] | 0.1107 [0.0889, 0.1331] |
| S2 · + other banks' records | 0.8584 | 0.1887 [0.1621, 0.2160] | 0.1113 [0.0841, 0.1379] | 0.1016 [0.0786, 0.1270] | 0.1101 [0.0871, 0.1361] |
| S3 (ε = 2) · + noisy records | 0.8548 | 0.1924 [0.1645, 0.2184] | 0.1131 [0.0853, 0.1410] | 0.1010 [0.0774, 0.1258] | 0.1107 [0.0895, 0.1331] |
| Oracle · all data pooled | 0.8905 | 0.1791 [0.1530, 0.2069] | 0.1107 [0.0829, 0.1373] | 0.1083 [0.0841, 0.1343] | 0.1252 [0.0998, 0.1525] |

## H3a on validation

S2 − S0 attributor accuracy has a 95% CI above 0, and S2's attributor beats the majority and rule baselines. Judged on test.

| Item | Validation |
| --- | --- |
| S2 − S0 (attributor) | 0.0423 [0.0157, 0.0678] |
| S2 attributor − majority | 0.0774 [0.0429, 0.1150] |
| S2 attributor − rules | 0.0871 [0.0508, 0.1228] |
| Met on validation | yes |

## Attributor on detected schemes

| Level | Accuracy (detected schemes) | Macro-F1 (detected schemes) |
| --- | --- | --- |
| S0 · own data only | 0.1676 | 0.1612 |
| S1 · + cross-bank structure | 0.2187 | 0.2089 |
| S2 · + other banks' records | 0.2199 | 0.2118 |
| S3 (ε = 2) · + noisy records | 0.2250 | 0.2142 |
| Oracle · all data pooled | 0.2011 | 0.1937 |

## Attributor recall by pattern (end to end)

| Pattern | S0 | S1 | S2 | S3 | oracle |
| --- | --- | --- | --- | --- | --- |
| BIPARTITE | 0.2051 | 0.2692 | 0.2906 | 0.3333 | 0.3205 |
| CYCLE | 0.1279 | 0.1689 | 0.1781 | 0.1689 | 0.1324 |
| FAN-IN | 0.1126 | 0.1261 | 0.1171 | 0.1081 | 0.0946 |
| FAN-OUT | 0.1949 | 0.1795 | 0.1538 | 0.1590 | 0.1385 |
| GATHER-SCATTER | 0.1476 | 0.3333 | 0.3190 | 0.2952 | 0.2238 |
| RANDOM | 0.0862 | 0.1897 | 0.1782 | 0.2184 | 0.2011 |
| SCATTER-GATHER | 0.2176 | 0.1574 | 0.1852 | 0.1574 | 0.2176 |
| STACK | 0.0546 | 0.0492 | 0.0601 | 0.0765 | 0.0820 |

## All paired comparisons

| Comparison | Accuracy difference [95% CI] |
| --- | --- |
| S1-S0 | 0.0405 [0.0151, 0.0653] |
| S2-S0 | 0.0423 [0.0157, 0.0678] |
| S3-S0 | 0.0460 [0.0175, 0.0726] |
| oracle-S0 | 0.0327 [0.0048, 0.0587] |
| S2 attributor-majority | 0.0774 [0.0429, 0.1150] |
| S0 attributor-majority | 0.0381 [0.0060, 0.0732] |
| S2 attributor-rules | 0.0871 [0.0508, 0.1228] |
| S0 attributor-rules | 0.0357 [0.0018, 0.0714] |
| S2 attributor-catalogue | 0.0786 [0.0417, 0.1119] |
| S0 attributor-catalogue | 0.0151 [-0.0163, 0.0454] |

Stage-level accuracy: not reported: the stage distribution is degenerate ({'layering': 551}).
