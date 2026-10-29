# Leakage audit A1–A3 on validation · HI-Medium

Seed 0. An honest-but-curious peer attacks everything it receives. A2 and A3 use a strong adversary: a gradient-boosted classifier trained on the true attributes of half the queried accounts (split by account), tested on the other half, against a prior-only attack that sees what the adversary knew before asking (its own accounts in the request, its score bucket, the window and the two banks). Intervals bootstrap the queried accounts. H1c margin (A15): upper 95% bound of (attack − prior) TPR at 1% FPR at most 0.05.

![Utility-leakage frontier](frontier_HI-Medium.png)

Targets: 177,609 (adversary, counterparty, window) triples; test half 88,742. Prevalence: A2 third-member relationship 0.357; A3 amount in top decile 0.100; A3 fan-in in top decile 0.064; A3 pass-through account 0.003.

## A2 third-member relationship

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0128 [0.0068, 0.0181] | 0.0313 [0.0255, 0.0372] | 0.5599 [0.5552, 0.5644] | — | — |
| S1 | 0.0166 [0.0095, 0.0241] | 0.0354 [0.0281, 0.0429] | 0.5659 [0.5608, 0.5706] | 0.0040 [0.0011, 0.0066] | yes |
| S2 | 0.1542 [0.1424, 0.1658] | 0.2506 [0.2400, 0.2603] | 0.7598 [0.7559, 0.7633] | 0.2193 [0.2118, 0.2281] | no |
| S4 | 0.1723 [0.1618, 0.1823] | 0.2659 [0.2569, 0.2765] | 0.7633 [0.7590, 0.7668] | 0.2346 [0.2261, 0.2450] | no |
| S3[eps=0.5] | 0.0157 [0.0086, 0.0226] | 0.0381 [0.0307, 0.0462] | 0.5793 [0.5740, 0.5839] | 0.0068 [0.0027, 0.0104] | yes |
| S3[eps=1] | 0.0162 [0.0090, 0.0234] | 0.0389 [0.0306, 0.0474] | 0.5793 [0.5729, 0.5840] | 0.0076 [0.0037, 0.0112] | yes |
| S3[eps=2] | 0.0155 [0.0087, 0.0223] | 0.0391 [0.0310, 0.0472] | 0.5775 [0.5722, 0.5825] | 0.0078 [0.0033, 0.0112] | yes |
| S3[eps=4] | 0.0152 [0.0084, 0.0222] | 0.0416 [0.0336, 0.0489] | 0.5853 [0.5798, 0.5909] | 0.0102 [0.0060, 0.0137] | yes |
| S3[eps=8] | 0.0158 [0.0091, 0.0227] | 0.0378 [0.0299, 0.0453] | 0.5976 [0.5919, 0.6026] | 0.0065 [0.0030, 0.0096] | yes |
| PD[tau=2] | 0.0330 [0.0248, 0.0393] | 0.0854 [0.0775, 0.0932] | 0.6208 [0.6161, 0.6255] | 0.0541 [0.0489, 0.0585] | no |
| PD[tau=3] | 0.0247 [0.0170, 0.0312] | 0.0653 [0.0564, 0.0730] | 0.5974 [0.5918, 0.6021] | 0.0339 [0.0283, 0.0371] | yes |
| PD[tau=4] | 0.0202 [0.0131, 0.0264] | 0.0549 [0.0470, 0.0628] | 0.5868 [0.5815, 0.5913] | 0.0236 [0.0197, 0.0268] | yes |

S4 − S2, TPR at 1% FPR: 0.0153 [0.0085, 0.0212].

## A3 amount in top decile

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0271 [0.0091, 0.0464] | 0.0452 [0.0242, 0.0657] | 0.5840 [0.5724, 0.5937] | — | — |
| S1 | 0.0402 [0.0144, 0.0646] | 0.0608 [0.0346, 0.0850] | 0.5885 [0.5746, 0.6000] | 0.0156 [0.0075, 0.0239] | yes |
| S2 | 0.1436 [0.1170, 0.1663] | 0.2469 [0.2229, 0.2663] | 0.7603 [0.7516, 0.7670] | 0.2017 [0.1891, 0.2158] | no |
| S4 | 0.1429 [0.1224, 0.1652] | 0.2553 [0.2303, 0.2744] | 0.7606 [0.7519, 0.7677] | 0.2101 [0.1967, 0.2236] | no |
| S3[eps=0.5] | 0.0387 [0.0131, 0.0622] | 0.0569 [0.0291, 0.0809] | 0.5762 [0.5627, 0.5893] | 0.0117 [0.0030, 0.0203] | yes |
| S3[eps=1] | 0.0395 [0.0135, 0.0639] | 0.0588 [0.0321, 0.0841] | 0.5804 [0.5662, 0.5928] | 0.0136 [0.0043, 0.0225] | yes |
| S3[eps=2] | 0.0401 [0.0149, 0.0634] | 0.0591 [0.0330, 0.0830] | 0.5788 [0.5640, 0.5915] | 0.0139 [0.0050, 0.0220] | yes |
| S3[eps=4] | 0.0385 [0.0132, 0.0611] | 0.0575 [0.0330, 0.0808] | 0.5784 [0.5654, 0.5924] | 0.0123 [0.0048, 0.0209] | yes |
| S3[eps=8] | 0.0399 [0.0143, 0.0636] | 0.0644 [0.0388, 0.0888] | 0.5871 [0.5745, 0.6001] | 0.0192 [0.0106, 0.0283] | yes |
| PD[tau=2] | 0.0804 [0.0552, 0.1063] | 0.1462 [0.1212, 0.1673] | 0.6477 [0.6351, 0.6584] | 0.1010 [0.0924, 0.1108] | no |
| PD[tau=3] | 0.0586 [0.0354, 0.0830] | 0.1090 [0.0840, 0.1326] | 0.6201 [0.6067, 0.6316] | 0.0638 [0.0553, 0.0731] | no |
| PD[tau=4] | 0.0491 [0.0260, 0.0720] | 0.0903 [0.0653, 0.1145] | 0.6094 [0.5974, 0.6210] | 0.0451 [0.0376, 0.0540] | no |

S4 − S2, TPR at 1% FPR: 0.0084 [0.0005, 0.0130].

## A3 fan-in in top decile

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0248 [0.0187, 0.0299] | 0.0702 [0.0636, 0.0801] | 0.6615 [0.6537, 0.6693] | — | — |
| S1 | 0.0227 [0.0178, 0.0285] | 0.0782 [0.0685, 0.0883] | 0.6663 [0.6577, 0.6746] | 0.0080 [0.0013, 0.0119] | yes |
| S2 | 0.8656 [0.8537, 0.8783] | 0.8844 [0.8727, 0.8944] | 0.9677 [0.9632, 0.9710] | 0.8142 [0.7981, 0.8253] | no |
| S4 | 0.8663 [0.8529, 0.8776] | 0.8855 [0.8739, 0.8962] | 0.9678 [0.9631, 0.9712] | 0.8152 [0.7984, 0.8292] | no |
| S3[eps=0.5] | 0.0174 [0.0136, 0.0220] | 0.0791 [0.0698, 0.0887] | 0.6699 [0.6608, 0.6773] | 0.0089 [0.0019, 0.0137] | yes |
| S3[eps=1] | 0.0213 [0.0154, 0.0280] | 0.0782 [0.0700, 0.0870] | 0.6738 [0.6654, 0.6809] | 0.0080 [0.0016, 0.0130] | yes |
| S3[eps=2] | 0.0230 [0.0173, 0.0293] | 0.0754 [0.0682, 0.0843] | 0.6743 [0.6647, 0.6816] | 0.0051 [-0.0019, 0.0105] | yes |
| S3[eps=4] | 0.0216 [0.0159, 0.0270] | 0.0789 [0.0703, 0.0884] | 0.6908 [0.6826, 0.6993] | 0.0087 [0.0021, 0.0123] | yes |
| S3[eps=8] | 0.0300 [0.0225, 0.0370] | 0.0867 [0.0779, 0.0964] | 0.7342 [0.7259, 0.7426] | 0.0165 [0.0078, 0.0236] | yes |
| PD[tau=2] | 0.0926 [0.0827, 0.1029] | 0.1434 [0.1322, 0.1556] | 0.7253 [0.7185, 0.7338] | 0.0732 [0.0637, 0.0808] | no |
| PD[tau=3] | 0.0387 [0.0331, 0.0464] | 0.0980 [0.0877, 0.1088] | 0.6852 [0.6769, 0.6934] | 0.0278 [0.0191, 0.0339] | yes |
| PD[tau=4] | 0.0326 [0.0262, 0.0398] | 0.0883 [0.0784, 0.0988] | 0.6779 [0.6693, 0.6856] | 0.0181 [0.0112, 0.0231] | yes |

S4 − S2, TPR at 1% FPR: 0.0011 [-0.0012, 0.0036].

## A3 pass-through account

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0036 [0.0000, 0.0122] | 0.0182 [0.0036, 0.0335] | 0.5027 [0.4697, 0.5392] | — | — |
| S1 | 0.0000 [0.0000, 0.0000] | 0.0182 [0.0037, 0.0352] | 0.5224 [0.4847, 0.5608] | 0.0000 [-0.0159, 0.0149] | yes |
| S2 | 0.0547 [0.0211, 0.0882] | 0.0620 [0.0317, 0.0974] | 0.4495 [0.4080, 0.4983] | 0.0438 [0.0105, 0.0844] | no |
| S4 | 0.0000 [0.0000, 0.2818] | 0.2920 [0.2249, 0.3516] | 0.6490 [0.6011, 0.6879] | 0.2737 [0.2056, 0.3309] | no |
| S3[eps=0.5] | 0.0000 [0.0000, 0.0000] | 0.0146 [0.0000, 0.0323] | 0.5037 [0.4675, 0.5377] | -0.0036 [-0.0243, 0.0236] | yes |
| S3[eps=1] | 0.0109 [0.0000, 0.0288] | 0.0401 [0.0157, 0.0674] | 0.4911 [0.4533, 0.5287] | 0.0219 [-0.0036, 0.0540] | no |
| S3[eps=2] | 0.0073 [0.0000, 0.0227] | 0.0328 [0.0033, 0.0655] | 0.5335 [0.4877, 0.5754] | 0.0146 [-0.0133, 0.0507] | no |
| S3[eps=4] | 0.0000 [0.0000, 0.0000] | 0.0109 [0.0000, 0.0249] | 0.5321 [0.4888, 0.5700] | -0.0073 [-0.0256, 0.0118] | yes |
| S3[eps=8] | 0.0073 [0.0000, 0.0214] | 0.0365 [0.0172, 0.0554] | 0.5553 [0.5125, 0.5933] | 0.0182 [-0.0039, 0.0426] | yes |
| PD[tau=2] | 0.2117 [0.1538, 0.2837] | 0.2263 [0.1688, 0.2997] | 0.6152 [0.5715, 0.6597] | 0.2080 [0.1538, 0.2715] | no |
| PD[tau=3] | 0.1642 [0.1152, 0.2182] | 0.1715 [0.1226, 0.2283] | 0.5768 [0.5356, 0.6254] | 0.1533 [0.1031, 0.2103] | no |
| PD[tau=4] | 0.1168 [0.0722, 0.1707] | 0.1277 [0.0811, 0.1881] | 0.5416 [0.4897, 0.5848] | 0.1095 [0.0680, 0.1741] | no |

S4 − S2, TPR at 1% FPR: 0.2299 [0.1594, 0.2926].

## H1c on validation

- S1 and S3 (ε ≤ 2) within the margin on every assessable A2/A3 target: **no**
- Per level (all assessable targets within): S1 yes, S2 no, S4 no, S3 ε=0.5 yes, S3 ε=1 no, S3 ε=2 no, S3 ε=4 yes, S3 ε=8 yes, PD τ=2 no, PD τ=3 no, PD τ=4 no
- Targets without enough positives in the test half to assess: none
- S4 above S2 (CI of the difference above 0), per target: {'A2_third_party': True, 'A3_amount_top': True, 'A3_fan_in_top': False, 'A3_pass_through': True}
- S3 TPR at 1% FPR by ε (monotone expected): A2 third-member relationship: 0.5→0.0381, 1→0.0389, 2→0.0391, 4→0.0416, 8→0.0378; A3 amount in top decile: 0.5→0.0569, 1→0.0588, 2→0.0591, 4→0.0575, 8→0.0644; A3 fan-in in top decile: 0.5→0.0791, 1→0.0782, 2→0.0754, 4→0.0789, 8→0.0867; A3 pass-through account: 0.5→0.0146, 1→0.0401, 2→0.0328, 4→0.0109, 8→0.0365

## A1 token re-identification

Targets: the tokens of every other member's evidence records. Candidates: every account at another member that the adversary's customers traded with up to the end of validation. Hashing: all candidates tokenised offline, unmetered. OPRF: candidates tokenised within the spare per-epoch budget, every query logged; expected re-identification with candidates queried in random order. Budgets: the protocol's (74,510; A16 sizes it to twice the largest legitimate use on validation), twice the largest legitimate use in this run (74,510), and the week-6 placeholder (250,000).

| Adversary | Target tokens | Candidates | Legitimate queries | Hashing | OPRF, protocol budget | OPRF, sized in this run | OPRF, 250,000 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 58,682 | 432,745 | 35,422 | 0.4117 | 0.0372 | 0.0372 | 0.2041 |
| 1 | 58,874 | 434,202 | 34,972 | 0.4143 | 0.0377 | 0.0377 | 0.2052 |
| 2 | 59,511 | 435,281 | 34,225 | 0.4166 | 0.0386 | 0.0386 | 0.2065 |
| 3 | 60,711 | 435,836 | 28,371 | 0.4156 | 0.0440 | 0.0440 | 0.2113 |
| 4 | 59,973 | 435,674 | 31,813 | 0.4119 | 0.0404 | 0.0404 | 0.2063 |
| 5 | 57,823 | 433,597 | 36,773 | 0.4147 | 0.0361 | 0.0361 | 0.2040 |
| 6 | 59,277 | 430,266 | 33,549 | 0.4076 | 0.0388 | 0.0388 | 0.2050 |
| 7 | 58,629 | 529,315 | 37,255 | 0.4750 | 0.0334 | 0.0334 | 0.1909 |

Pooled: hashing 0.4209, OPRF at the protocol budget 0.0383, sized in this run 0.0383. Hashing ÷ OPRF at the protocol budget: **10.99** (PT2 asks for at least 10).

Mechanism check on real tokens: {'checked': 200, 'hash_matches': 200, 'oprf_matches': 200}.

## A4 linkability across epochs

Validation lies inside one 7-day epoch, so key rotation is simulated at its midpoint. Each second-half record an adversary received is ranked among up to 99 first-half records from the same responder by similarity of the record's fields (and embedding at S4); hit@1 is how often the true account comes first. S3 records are released afresh after a rotation (memoised per record and epoch), so they are re-noised independently in each half. Positive control: without rotation, equal tokens link every pair (hit@1 = 1).

| Level | Queries | Chance hit@1 | Hit@1 [95% CI] | Mean reciprocal rank |
| --- | --- | --- | --- | --- |
| S2 | 3,269 | 0.0100 | 0.5350 [0.5188, 0.5525] | 0.5836 |
| S4 | 3,269 | 0.0100 | 0.5629 [0.5451, 0.5766] | 0.6041 |
| S3 ε=0.5 | 3,269 | 0.0100 | 0.0125 [0.0083, 0.0162] | 0.0544 |
| S3 ε=1 | 3,269 | 0.0100 | 0.0089 [0.0055, 0.0125] | 0.0521 |
| S3 ε=2 | 3,269 | 0.0100 | 0.0089 [0.0061, 0.0119] | 0.0526 |
| S3 ε=4 | 3,269 | 0.0100 | 0.0128 [0.0092, 0.0162] | 0.0549 |
| S3 ε=8 | 3,269 | 0.0100 | 0.0116 [0.0083, 0.0156] | 0.0549 |
| PD τ=2 | 1,226 | 0.0103 | 0.6134 [0.5832, 0.6419] | 0.6645 |
| PD τ=3 | 933 | 0.0175 | 0.6484 [0.6163, 0.6796] | 0.7019 |
| PD τ=4 | 614 | 0.0267 | 0.6922 [0.6531, 0.7264] | 0.7445 |

## A5 membership inference on S4 disclosures

Can a peer tell whether an account-window was in another member's autoencoder training sample from what S4 discloses (top deviations, magnitude buckets, embedding)? 80,000 rows, half members; strong adversary trained on half and tested on 40,034. Chance: TPR equals FPR, AUC 0.5. The global DP model's membership inference is X5 (weeks 10–12).

TPR at 0.1% FPR 0.0010 [0.0004, 0.0017]; TPR at 1% FPR 0.0128 [0.0109, 0.0154]; AUC 0.5019 [0.4964, 0.5074].

## A6 query leakage

What does being asked reveal? The request carries the requester's score bucket in the clear (by design: PD needs it). Here a responder predicts whether its own candidate account-window is laundering from its own score, then from its own score plus the requests it received about it. Measured, not prevented.

70,275 candidate account-windows; 0.6547 were asked about at least once, 0.7964 of the laundering ones.

| Responder sees | AUC | TPR at 0.1% FPR | TPR at 1% FPR |
| --- | --- | --- | --- |
| own | 0.7715 [0.7588, 0.7848] | 0.1556 [0.0978, 0.1684] | 0.3248 [0.3063, 0.3465] |
| own+requests | 0.7824 [0.7703, 0.7953] | 0.2292 [0.1946, 0.2558] | 0.3997 [0.3735, 0.4233] |

Gain from requests, TPR at 1% FPR: 0.0748 [0.0548, 0.0935].
