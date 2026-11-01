# Coverage curve · HI-Medium · validation

**Secondary analysis (A21); decides no hypothesis.** Each row is X1 on one federation (S0–S4, propagation, pooled oracles; seeds 0–2; no sweeps or audit). `B8c{p}`: banks added largest first, as real partnerships recruit, until they hold p% of accounts, then grouped into 8 members; accounts at other banks are outside the federation. B8 (every bank) and A64 (64 largest banks, one member each) are the end points. The scheme denominator is the same in every row (all validation schemes), so detection is end to end.

![Coverage curve](coverage_HI-Medium.png)

## Linked detection by coverage [95% CI]

| Federation | Target | Validation accounts covered | Multi-member schemes | S0 | S1 | S2 | S4 | Propagation | Relational oracle |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A64 | 64 banks | 6.9% | 95 of 551 | 0.0018 [0.0000, 0.0054] | 0.0030 [0.0000, 0.0067] | 0.0042 [0.0006, 0.0085] | 0.0042 [0.0006, 0.0091] | 0.0060 [0.0012, 0.0127] | 0.0036 [0.0000, 0.0085] |
| B8c10 | 10% | 14.5% | 165 of 551 | 0.0060 [0.0018, 0.0109] | 0.0593 [0.0429, 0.0786] | 0.0617 [0.0448, 0.0817] | 0.0575 [0.0417, 0.0756] | 0.0678 [0.0496, 0.0889] | 0.0520 [0.0363, 0.0702] |
| B8c25 | 25% | 35.5% | 306 of 551 | 0.0254 [0.0145, 0.0381] | 0.1748 [0.1482, 0.2033] | 0.1730 [0.1464, 0.2027] | 0.1839 [0.1543, 0.2129] | 0.1851 [0.1579, 0.2136] | 0.1809 [0.1525, 0.2099] |
| B8c50 | 50% | 69.0% | 460 of 551 | 0.0901 [0.0696, 0.1131] | 0.4223 [0.3854, 0.4580] | 0.4440 [0.4077, 0.4810] | 0.4301 [0.3944, 0.4676] | 0.4398 [0.4035, 0.4773] | 0.4265 [0.3872, 0.4616] |
| B8c75 | 75% | 99.7% | 519 of 551 | 0.1446 [0.1186, 0.1718] | 0.6158 [0.5777, 0.6534] | 0.6298 [0.5910, 0.6673] | 0.5995 [0.5614, 0.6370] | 0.6104 [0.5735, 0.6485] | 0.6521 [0.6176, 0.6879] |
| B8c90 | 90% | 100.0% | 522 of 551 | 0.1597 [0.1337, 0.1887] | 0.6842 [0.6515, 0.7193] | 0.6903 [0.6558, 0.7248] | 0.6576 [0.6219, 0.6945] | 0.6649 [0.6286, 0.7006] | 0.7120 [0.6763, 0.7477] |
| B8 | 100% | 100.0% | 522 of 551 | 0.1736 [0.1446, 0.2033] | 0.7266 [0.6933, 0.7592] | 0.7356 [0.7030, 0.7713] | 0.7042 [0.6703, 0.7405] | 0.7036 [0.6697, 0.7399] | 0.7465 [0.7126, 0.7816] |

## The sharing gain by coverage

| Federation | S2 − S0 linked [95% CI] | S2 share of the relational-oracle gain [95% CI] |
| --- | --- | --- |
| A64 | 0.0024 [-0.0024, 0.0073] | 1.33 [-0.5000, 5.00] |
| B8c10 | 0.0557 [0.0399, 0.0744] | 1.21 [0.9583, 1.55] |
| B8c25 | 0.1476 [0.1216, 0.1755] | 0.9494 [0.8435, 1.09] |
| B8c50 | 0.3539 [0.3128, 0.3926] | 1.05 [0.9755, 1.14] |
| B8c75 | 0.4852 [0.4422, 0.5275] | 0.9559 [0.9050, 1.00] |
| B8c90 | 0.5306 [0.4882, 0.5705] | 0.9606 [0.9150, 1.01] |
| B8 | 0.5620 [0.5227, 0.6025] | 0.9810 [0.9363, 1.02] |

Every point on the pre-registered curve is present.
