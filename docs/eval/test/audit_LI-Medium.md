# Leakage audit A1–A3 on test · LI-Medium

> **Sealed test (week 18).** Every model trained on the training partition; every calibration, threshold, fusion and attribution parameter fitted on validation and frozen; test scored label-free, then opened once per seed through the logged seal (`finmesh sealed-log`). Wording below that says *validation* in a column or check name refers to the frozen rule; every number is on **test**.

Seed 0. An honest-but-curious peer attacks everything it receives. A2 and A3 use a strong adversary: a gradient-boosted classifier trained on the true attributes of half the queried accounts (split by account), tested on the other half, against a prior-only attack that sees what the adversary knew before asking (its own accounts in the request, its score bucket, the window and the two banks). Intervals bootstrap the queried accounts. H1c margin (A15): upper 95% bound of (attack − prior) TPR at 1% FPR at most 0.05.

![Utility-leakage frontier](frontier_LI-Medium.png)

Targets: 197,378 (adversary, counterparty, window) triples; test half 98,512. Prevalence: A2 third-member relationship 0.384; A3 amount in top decile 0.100; A3 fan-in in top decile 0.062; A3 pass-through account 0.003.

## A2 third-member relationship

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0145 [0.0093, 0.0216] | 0.0332 [0.0281, 0.0403] | 0.5788 [0.5742, 0.5829] | — | — |
| S1 | 0.0178 [0.0115, 0.0266] | 0.0512 [0.0441, 0.0598] | 0.5936 [0.5887, 0.5982] | 0.0180 [0.0146, 0.0207] | yes |
| S2 | 0.1366 [0.1273, 0.1461] | 0.2080 [0.1989, 0.2167] | 0.7300 [0.7263, 0.7335] | 0.1748 [0.1671, 0.1813] | no |
| S4 | 0.1341 [0.1271, 0.1413] | 0.2156 [0.2061, 0.2237] | 0.7312 [0.7274, 0.7347] | 0.1824 [0.1745, 0.1896] | no |
| S3[eps=0.5] | 0.0162 [0.0097, 0.0253] | 0.0501 [0.0433, 0.0582] | 0.5961 [0.5917, 0.6014] | 0.0169 [0.0132, 0.0201] | yes |
| S3[eps=1] | 0.0163 [0.0098, 0.0246] | 0.0494 [0.0420, 0.0579] | 0.5966 [0.5922, 0.6011] | 0.0162 [0.0119, 0.0195] | yes |
| S3[eps=2] | 0.0167 [0.0098, 0.0252] | 0.0500 [0.0433, 0.0585] | 0.5970 [0.5921, 0.6020] | 0.0168 [0.0129, 0.0196] | yes |
| S3[eps=4] | 0.0163 [0.0105, 0.0245] | 0.0499 [0.0426, 0.0590] | 0.5939 [0.5895, 0.5982] | 0.0167 [0.0127, 0.0203] | yes |
| S3[eps=8] | 0.0168 [0.0108, 0.0251] | 0.0488 [0.0421, 0.0576] | 0.5956 [0.5912, 0.6000] | 0.0156 [0.0123, 0.0190] | yes |
| PD[tau=2] | 0.0194 [0.0127, 0.0279] | 0.0601 [0.0528, 0.0686] | 0.6101 [0.6061, 0.6144] | 0.0270 [0.0235, 0.0303] | yes |
| PD[tau=3] | 0.0179 [0.0115, 0.0265] | 0.0520 [0.0452, 0.0608] | 0.5966 [0.5917, 0.6010] | 0.0188 [0.0158, 0.0217] | yes |
| PD[tau=4] | 0.0171 [0.0109, 0.0259] | 0.0514 [0.0445, 0.0604] | 0.5955 [0.5905, 0.6001] | 0.0182 [0.0143, 0.0212] | yes |

S4 − S2, TPR at 1% FPR: 0.0075 [0.0035, 0.0123].

## A3 amount in top decile

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0253 [0.0060, 0.0512] | 0.0365 [0.0162, 0.0636] | 0.5982 [0.5889, 0.6076] | — | — |
| S1 | 0.0334 [0.0089, 0.0660] | 0.0445 [0.0202, 0.0763] | 0.6043 [0.5934, 0.6185] | 0.0080 [0.0022, 0.0157] | yes |
| S2 | 0.0900 [0.0679, 0.1164] | 0.1481 [0.1279, 0.1750] | 0.7127 [0.7055, 0.7227] | 0.1116 [0.1033, 0.1184] | no |
| S4 | 0.0891 [0.0671, 0.1146] | 0.1499 [0.1307, 0.1767] | 0.7156 [0.7085, 0.7254] | 0.1135 [0.1061, 0.1198] | no |
| S3[eps=0.5] | 0.0281 [0.0082, 0.0545] | 0.0403 [0.0207, 0.0661] | 0.5961 [0.5878, 0.6062] | 0.0038 [-0.0014, 0.0087] | yes |
| S3[eps=1] | 0.0283 [0.0080, 0.0550] | 0.0382 [0.0178, 0.0648] | 0.5956 [0.5882, 0.6038] | 0.0017 [-0.0041, 0.0083] | yes |
| S3[eps=2] | 0.0286 [0.0078, 0.0552] | 0.0409 [0.0188, 0.0686] | 0.5981 [0.5880, 0.6094] | 0.0044 [-0.0016, 0.0094] | yes |
| S3[eps=4] | 0.0283 [0.0088, 0.0547] | 0.0404 [0.0205, 0.0657] | 0.5920 [0.5845, 0.6010] | 0.0039 [-0.0031, 0.0094] | yes |
| S3[eps=8] | 0.0280 [0.0075, 0.0556] | 0.0391 [0.0176, 0.0671] | 0.5959 [0.5869, 0.6078] | 0.0026 [-0.0040, 0.0081] | yes |
| PD[tau=2] | 0.0459 [0.0237, 0.0761] | 0.0648 [0.0418, 0.0960] | 0.6251 [0.6148, 0.6393] | 0.0283 [0.0225, 0.0370] | yes |
| PD[tau=3] | 0.0336 [0.0094, 0.0653] | 0.0457 [0.0211, 0.0773] | 0.6068 [0.5966, 0.6202] | 0.0092 [0.0040, 0.0166] | yes |
| PD[tau=4] | 0.0338 [0.0091, 0.0657] | 0.0445 [0.0198, 0.0768] | 0.6056 [0.5954, 0.6195] | 0.0080 [0.0021, 0.0159] | yes |

S4 − S2, TPR at 1% FPR: 0.0018 [-0.0008, 0.0049].

## A3 fan-in in top decile

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0607 [0.0468, 0.0784] | 0.1220 [0.1064, 0.1367] | 0.6709 [0.6611, 0.6812] | — | — |
| S1 | 0.0668 [0.0501, 0.0892] | 0.2141 [0.1944, 0.2349] | 0.7133 [0.7026, 0.7251] | 0.0921 [0.0785, 0.1033] | no |
| S2 | 0.8370 [0.8235, 0.8501] | 0.8758 [0.8629, 0.8845] | 0.9590 [0.9546, 0.9633] | 0.7538 [0.7353, 0.7693] | no |
| S4 | 0.8380 [0.8251, 0.8508] | 0.8699 [0.8579, 0.8799] | 0.9560 [0.9509, 0.9606] | 0.7480 [0.7313, 0.7646] | no |
| S3[eps=0.5] | 0.0560 [0.0401, 0.0728] | 0.2040 [0.1845, 0.2197] | 0.7039 [0.6920, 0.7152] | 0.0821 [0.0664, 0.0963] | no |
| S3[eps=1] | 0.0482 [0.0341, 0.0675] | 0.2061 [0.1875, 0.2196] | 0.7046 [0.6941, 0.7154] | 0.0842 [0.0690, 0.0965] | no |
| S3[eps=2] | 0.0488 [0.0344, 0.0689] | 0.2069 [0.1884, 0.2211] | 0.7037 [0.6912, 0.7134] | 0.0850 [0.0711, 0.0972] | no |
| S3[eps=4] | 0.0527 [0.0390, 0.0720] | 0.2094 [0.1904, 0.2268] | 0.7075 [0.6975, 0.7200] | 0.0874 [0.0723, 0.1012] | no |
| S3[eps=8] | 0.0540 [0.0399, 0.0688] | 0.2060 [0.1892, 0.2231] | 0.7094 [0.6977, 0.7210] | 0.0840 [0.0706, 0.0961] | no |
| PD[tau=2] | 0.0882 [0.0713, 0.1110] | 0.2331 [0.2118, 0.2555] | 0.7327 [0.7219, 0.7430] | 0.1111 [0.0984, 0.1209] | no |
| PD[tau=3] | 0.0675 [0.0510, 0.0893] | 0.2155 [0.1954, 0.2373] | 0.7145 [0.7038, 0.7266] | 0.0936 [0.0802, 0.1048] | no |
| PD[tau=4] | 0.0675 [0.0510, 0.0874] | 0.2134 [0.1936, 0.2327] | 0.7142 [0.7033, 0.7266] | 0.0915 [0.0775, 0.1029] | no |

S4 − S2, TPR at 1% FPR: -0.0058 [-0.0086, -0.0024].

## A3 pass-through account

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0029 [0.0000, 0.0089] | 0.0144 [0.0051, 0.0266] | 0.5334 [0.5055, 0.5624] | — | — |
| S1 | 0.0029 [0.0000, 0.0089] | 0.0115 [0.0027, 0.0207] | 0.5287 [0.5007, 0.5609] | -0.0029 [-0.0104, 0.0000] | yes |
| S2 | 0.0000 [0.0000, 0.0000] | 0.0029 [0.0000, 0.0093] | 0.4931 [0.4586, 0.5298] | -0.0115 [-0.0266, 0.0001] | yes |
| S4 | 0.0000 [0.0000, 0.1324] | 0.1499 [0.1090, 0.1934] | 0.6258 [0.5874, 0.6667] | 0.1354 [0.0906, 0.1801] | no |
| S3[eps=0.5] | 0.0000 [0.0000, 0.0000] | 0.0259 [0.0108, 0.0392] | 0.5212 [0.4902, 0.5510] | 0.0115 [-0.0088, 0.0291] | yes |
| S3[eps=1] | 0.0000 [0.0000, 0.0000] | 0.0144 [0.0030, 0.0269] | 0.5358 [0.5083, 0.5681] | 0.0000 [-0.0176, 0.0164] | yes |
| S3[eps=2] | 0.0000 [0.0000, 0.0000] | 0.0029 [0.0000, 0.0094] | 0.5106 [0.4778, 0.5447] | -0.0115 [-0.0238, 0.0000] | yes |
| S3[eps=4] | 0.0000 [0.0000, 0.0000] | 0.0202 [0.0079, 0.0356] | 0.5086 [0.4775, 0.5418] | 0.0058 [-0.0114, 0.0249] | yes |
| S3[eps=8] | 0.0000 [0.0000, 0.0000] | 0.0029 [0.0000, 0.0102] | 0.5244 [0.4913, 0.5546] | -0.0115 [-0.0234, 0.0001] | yes |
| PD[tau=2] | 0.0086 [0.0000, 0.0202] | 0.0144 [0.0053, 0.0272] | 0.5283 [0.4948, 0.5622] | 0.0000 [-0.0161, 0.0171] | yes |
| PD[tau=3] | 0.0058 [0.0000, 0.0141] | 0.0144 [0.0051, 0.0251] | 0.5350 [0.5010, 0.5678] | 0.0000 [-0.0093, 0.0063] | yes |
| PD[tau=4] | 0.0058 [0.0000, 0.0148] | 0.0144 [0.0031, 0.0261] | 0.5249 [0.4950, 0.5559] | 0.0000 [-0.0093, 0.0080] | yes |

S4 − S2, TPR at 1% FPR: 0.1470 [0.1069, 0.1877].

## H1c on test

- S1 and S3 (ε ≤ 2) within the margin on every assessable A2/A3 target: **no**
- Per level (all assessable targets within): S1 no, S2 no, S4 no, S3 ε=0.5 no, S3 ε=1 no, S3 ε=2 no, S3 ε=4 no, S3 ε=8 no, PD τ=2 no, PD τ=3 no, PD τ=4 no
- Targets without enough positives in the test half to assess: none
- S4 above S2 (CI of the difference above 0), per target: {'A2_third_party': True, 'A3_amount_top': False, 'A3_fan_in_top': False, 'A3_pass_through': True}
- S3 TPR at 1% FPR by ε (monotone expected): A2 third-member relationship: 0.5→0.0501, 1→0.0494, 2→0.0500, 4→0.0499, 8→0.0488; A3 amount in top decile: 0.5→0.0403, 1→0.0382, 2→0.0409, 4→0.0404, 8→0.0391; A3 fan-in in top decile: 0.5→0.2040, 1→0.2061, 2→0.2069, 4→0.2094, 8→0.2060; A3 pass-through account: 0.5→0.0259, 1→0.0144, 2→0.0029, 4→0.0202, 8→0.0029

## A1 token re-identification

Targets: the tokens of every other member's evidence records. Candidates: every account at another member that the adversary's customers traded with up to the end of validation. Hashing: all candidates tokenised offline, unmetered. OPRF: candidates tokenised within the spare per-epoch budget, every query logged; expected re-identification with candidates queried in random order. Budgets: the protocol's (87,580; A16 sizes it to twice the largest legitimate use on test), twice the largest legitimate use in this run (93,268), and the week-6 placeholder (250,000).

| Adversary | Target tokens | Candidates | Legitimate queries | Hashing | OPRF, protocol budget | OPRF, sized in this run | OPRF, 250,000 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 73,010 | 442,222 | 46,634 | 0.4016 | 0.0372 | 0.0423 | 0.1847 |
| 1 | 75,621 | 444,555 | 43,736 | 0.4053 | 0.0400 | 0.0452 | 0.1880 |
| 2 | 79,630 | 445,480 | 27,131 | 0.4082 | 0.0554 | 0.0606 | 0.2042 |
| 3 | 80,411 | 541,574 | 26,340 | 0.4593 | 0.0519 | 0.0568 | 0.1897 |
| 4 | 76,894 | 447,485 | 39,574 | 0.4073 | 0.0437 | 0.0489 | 0.1915 |
| 5 | 78,591 | 443,979 | 33,767 | 0.4075 | 0.0494 | 0.0546 | 0.1984 |
| 6 | 76,439 | 444,467 | 37,109 | 0.4067 | 0.0462 | 0.0514 | 0.1948 |
| 7 | 81,095 | 444,230 | 27,293 | 0.4010 | 0.0544 | 0.0596 | 0.2010 |

Pooled: hashing 0.4124, OPRF at the protocol budget 0.0475, sized in this run 0.0526. Hashing ÷ OPRF at the protocol budget: **8.69** (PT2 asks for at least 10).

Mechanism check on real tokens: {'checked': 200, 'hash_matches': 200, 'oprf_matches': 200}.

## A4 linkability across epochs

Validation lies inside one 7-day epoch, so key rotation is simulated at its midpoint. Each second-half record an adversary received is ranked among up to 99 first-half records from the same responder by similarity of the record's fields (and embedding at S4); hit@1 is how often the true account comes first. S3 records are released afresh after a rotation (memoised per record and epoch), so they are re-noised independently in each half. Positive control: without rotation, equal tokens link every pair (hit@1 = 1).

| Level | Queries | Chance hit@1 | Hit@1 [95% CI] | Mean reciprocal rank |
| --- | --- | --- | --- | --- |
| S2 | 3,179 | 0.0100 | 0.5344 [0.5197, 0.5496] | 0.5946 |
| S4 | 3,179 | 0.0100 | 0.5996 [0.5848, 0.6162] | 0.6395 |
| S3 ε=0.5 | 3,179 | 0.0100 | 0.0094 [0.0069, 0.0129] | 0.0523 |
| S3 ε=1 | 3,179 | 0.0100 | 0.0094 [0.0063, 0.0132] | 0.0523 |
| S3 ε=2 | 3,179 | 0.0100 | 0.0098 [0.0069, 0.0132] | 0.0533 |
| S3 ε=4 | 3,179 | 0.0100 | 0.0104 [0.0079, 0.0138] | 0.0529 |
| S3 ε=8 | 3,179 | 0.0100 | 0.0101 [0.0066, 0.0132] | 0.0539 |
| PD τ=2 | 171 | 0.0187 | 0.7661 [0.6958, 0.8304] | 0.8000 |
| PD τ=3 | 11 | 0.0740 | 0.8182 [0.5455, 1.00] | 0.8591 |
| PD τ=4 | 0 | — | — | — |

## A5 membership inference on S4 disclosures

Can a peer tell whether an account-window was in another member's autoencoder training sample from what S4 discloses (top deviations, magnitude buckets, embedding)? 80,000 rows, half members; strong adversary trained on half and tested on 39,790. Chance: TPR equals FPR, AUC 0.5. The global DP model's membership inference is X5 (weeks 10–12).

TPR at 0.1% FPR 0.0016 [0.0009, 0.0021]; TPR at 1% FPR 0.0094 [0.0076, 0.0112]; AUC 0.5004 [0.4951, 0.5062].

## A6 query leakage

What does being asked reveal? The request carries the requester's score bucket in the clear (by design: PD needs it). Here a responder predicts whether its own candidate account-window is laundering from its own score, then from its own score plus the requests it received about it. Measured, not prevented.

94,984 candidate account-windows; 0.5604 were asked about at least once, 0.7604 of the laundering ones.

| Responder sees | AUC | TPR at 0.1% FPR | TPR at 1% FPR |
| --- | --- | --- | --- |
| own | 0.6699 [0.6561, 0.6857] | 0.0331 [0.0214, 0.0493] | 0.0879 [0.0695, 0.1069] |
| own+requests | 0.6814 [0.6670, 0.6992] | 0.0613 [0.0446, 0.0810] | 0.1266 [0.1035, 0.1479] |

Gain from requests, TPR at 1% FPR: 0.0387 [0.0225, 0.0513].
