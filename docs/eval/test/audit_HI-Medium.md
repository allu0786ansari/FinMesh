# Leakage audit A1–A3 on test · HI-Medium

> **Sealed test (week 18).** Every model trained on the training partition; every calibration, threshold, fusion and attribution parameter fitted on validation and frozen; test scored label-free, then opened once per seed through the logged seal (`finmesh sealed-log`). Wording below that says *validation* in a column or check name refers to the frozen rule; every number is on **test**.

Seed 0. An honest-but-curious peer attacks everything it receives. A2 and A3 use a strong adversary: a gradient-boosted classifier trained on the true attributes of half the queried accounts (split by account), tested on the other half, against a prior-only attack that sees what the adversary knew before asking (its own accounts in the request, its score bucket, the window and the two banks). Intervals bootstrap the queried accounts. H1c margin (A15): upper 95% bound of (attack − prior) TPR at 1% FPR at most 0.05.

![Utility-leakage frontier](frontier_HI-Medium.png)

Targets: 197,436 (adversary, counterparty, window) triples; test half 99,247. Prevalence: A2 third-member relationship 0.434; A3 amount in top decile 0.100; A3 fan-in in top decile 0.023; A3 pass-through account 0.004.

## A2 third-member relationship

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0025 [0.0020, 0.0031] | 0.0148 [0.0130, 0.0162] | 0.5378 [0.5342, 0.5414] | — | — |
| S1 | 0.0024 [0.0019, 0.0035] | 0.0169 [0.0155, 0.0188] | 0.5393 [0.5361, 0.5429] | 0.0021 [0.0009, 0.0042] | yes |
| S2 | 0.0514 [0.0482, 0.0549] | 0.1025 [0.0958, 0.1074] | 0.6221 [0.6183, 0.6256] | 0.0877 [0.0802, 0.0928] | no |
| S4 | 0.0531 [0.0485, 0.0567] | 0.1091 [0.1028, 0.1139] | 0.6242 [0.6203, 0.6275] | 0.0943 [0.0878, 0.0989] | no |
| S3[eps=0.5] | 0.0020 [0.0013, 0.0029] | 0.0175 [0.0155, 0.0194] | 0.5367 [0.5333, 0.5410] | 0.0027 [0.0003, 0.0053] | yes |
| S3[eps=1] | 0.0022 [0.0015, 0.0032] | 0.0173 [0.0150, 0.0193] | 0.5375 [0.5334, 0.5416] | 0.0025 [0.0005, 0.0050] | yes |
| S3[eps=2] | 0.0022 [0.0015, 0.0033] | 0.0175 [0.0158, 0.0194] | 0.5369 [0.5329, 0.5414] | 0.0027 [0.0004, 0.0051] | yes |
| S3[eps=4] | 0.0021 [0.0015, 0.0028] | 0.0178 [0.0159, 0.0203] | 0.5391 [0.5348, 0.5435] | 0.0030 [0.0005, 0.0059] | yes |
| S3[eps=8] | 0.0027 [0.0019, 0.0036] | 0.0189 [0.0165, 0.0210] | 0.5365 [0.5332, 0.5409] | 0.0041 [0.0018, 0.0068] | yes |
| PD[tau=2] | 0.0115 [0.0096, 0.0137] | 0.0372 [0.0345, 0.0402] | 0.5575 [0.5545, 0.5610] | 0.0224 [0.0195, 0.0251] | yes |
| PD[tau=3] | 0.0063 [0.0049, 0.0079] | 0.0255 [0.0235, 0.0281] | 0.5485 [0.5450, 0.5519] | 0.0107 [0.0086, 0.0130] | yes |
| PD[tau=4] | 0.0052 [0.0040, 0.0067] | 0.0224 [0.0204, 0.0246] | 0.5455 [0.5420, 0.5489] | 0.0076 [0.0055, 0.0098] | yes |

S4 − S2, TPR at 1% FPR: 0.0066 [0.0026, 0.0104].

## A3 amount in top decile

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0023 [0.0013, 0.0033] | 0.0174 [0.0148, 0.0200] | 0.5699 [0.5632, 0.5766] | — | — |
| S1 | 0.0018 [0.0009, 0.0030] | 0.0179 [0.0148, 0.0205] | 0.5704 [0.5634, 0.5769] | 0.0005 [-0.0019, 0.0024] | yes |
| S2 | 0.0635 [0.0572, 0.0692] | 0.1216 [0.1135, 0.1292] | 0.6506 [0.6448, 0.6574] | 0.1042 [0.0962, 0.1121] | no |
| S4 | 0.0630 [0.0574, 0.0700] | 0.1236 [0.1162, 0.1313] | 0.6532 [0.6473, 0.6601] | 0.1062 [0.0985, 0.1142] | no |
| S3[eps=0.5] | 0.0029 [0.0017, 0.0044] | 0.0190 [0.0163, 0.0219] | 0.5636 [0.5559, 0.5709] | 0.0016 [-0.0020, 0.0049] | yes |
| S3[eps=1] | 0.0030 [0.0021, 0.0043] | 0.0175 [0.0151, 0.0205] | 0.5626 [0.5551, 0.5701] | 0.0001 [-0.0035, 0.0039] | yes |
| S3[eps=2] | 0.0026 [0.0016, 0.0039] | 0.0159 [0.0128, 0.0183] | 0.5609 [0.5544, 0.5682] | -0.0015 [-0.0052, 0.0021] | yes |
| S3[eps=4] | 0.0015 [0.0008, 0.0023] | 0.0154 [0.0122, 0.0184] | 0.5618 [0.5551, 0.5694] | -0.0019 [-0.0056, 0.0015] | yes |
| S3[eps=8] | 0.0017 [0.0009, 0.0025] | 0.0174 [0.0144, 0.0209] | 0.5598 [0.5526, 0.5668] | 0.0000 [-0.0039, 0.0032] | yes |
| PD[tau=2] | 0.0196 [0.0167, 0.0229] | 0.0385 [0.0341, 0.0431] | 0.5863 [0.5802, 0.5923] | 0.0211 [0.0172, 0.0247] | yes |
| PD[tau=3] | 0.0071 [0.0054, 0.0087] | 0.0246 [0.0213, 0.0280] | 0.5778 [0.5716, 0.5845] | 0.0073 [0.0043, 0.0094] | yes |
| PD[tau=4] | 0.0033 [0.0020, 0.0046] | 0.0200 [0.0174, 0.0234] | 0.5742 [0.5677, 0.5806] | 0.0026 [0.0005, 0.0048] | yes |

S4 − S2, TPR at 1% FPR: 0.0020 [-0.0021, 0.0059].

## A3 fan-in in top decile

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0266 [0.0202, 0.0359] | 0.0615 [0.0527, 0.0723] | 0.7312 [0.7158, 0.7454] | — | — |
| S1 | 0.0243 [0.0188, 0.0317] | 0.0593 [0.0492, 0.0702] | 0.7301 [0.7144, 0.7441] | -0.0022 [-0.0075, 0.0031] | yes |
| S2 | 0.6950 [0.6639, 0.7248] | 0.7202 [0.6912, 0.7481] | 0.8873 [0.8717, 0.9021] | 0.6587 [0.6265, 0.6889] | no |
| S4 | 0.6946 [0.6629, 0.7229] | 0.7185 [0.6891, 0.7461] | 0.8853 [0.8692, 0.9005] | 0.6569 [0.6269, 0.6869] | no |
| S3[eps=0.5] | 0.0102 [0.0059, 0.0162] | 0.0487 [0.0363, 0.0589] | 0.7295 [0.7145, 0.7435] | -0.0128 [-0.0257, -0.0023] | yes |
| S3[eps=1] | 0.0071 [0.0040, 0.0109] | 0.0452 [0.0341, 0.0565] | 0.7223 [0.7061, 0.7354] | -0.0164 [-0.0290, -0.0054] | yes |
| S3[eps=2] | 0.0053 [0.0023, 0.0094] | 0.0381 [0.0297, 0.0457] | 0.7290 [0.7131, 0.7420] | -0.0235 [-0.0345, -0.0123] | yes |
| S3[eps=4] | 0.0066 [0.0029, 0.0117] | 0.0544 [0.0439, 0.0678] | 0.7269 [0.7104, 0.7417] | -0.0071 [-0.0182, 0.0049] | yes |
| S3[eps=8] | 0.0084 [0.0036, 0.0132] | 0.0589 [0.0468, 0.0713] | 0.7286 [0.7133, 0.7430] | -0.0027 [-0.0166, 0.0085] | yes |
| PD[tau=2] | 0.0974 [0.0829, 0.1116] | 0.1346 [0.1188, 0.1512] | 0.7735 [0.7592, 0.7867] | 0.0730 [0.0608, 0.0868] | no |
| PD[tau=3] | 0.0425 [0.0333, 0.0557] | 0.0819 [0.0695, 0.0947] | 0.7460 [0.7310, 0.7595] | 0.0204 [0.0128, 0.0295] | yes |
| PD[tau=4] | 0.0328 [0.0252, 0.0423] | 0.0726 [0.0610, 0.0854] | 0.7396 [0.7259, 0.7528] | 0.0111 [0.0050, 0.0178] | yes |

S4 − S2, TPR at 1% FPR: -0.0018 [-0.0062, 0.0009].

## A3 pass-through account

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0026 [0.0000, 0.0083] | 0.0156 [0.0054, 0.0291] | 0.4984 [0.4704, 0.5293] | — | — |
| S1 | 0.0000 [0.0000, 0.0000] | 0.0130 [0.0029, 0.0267] | 0.5054 [0.4771, 0.5347] | -0.0026 [-0.0133, 0.0058] | yes |
| S2 | 0.0675 [0.0000, 0.0916] | 0.0831 [0.0484, 0.1137] | 0.5049 [0.4674, 0.5503] | 0.0675 [0.0359, 0.0984] | no |
| S4 | 0.1299 [0.0868, 0.1772] | 0.1455 [0.1021, 0.1949] | 0.5961 [0.5599, 0.6317] | 0.1299 [0.0850, 0.1774] | no |
| S3[eps=0.5] | 0.0000 [0.0000, 0.0057] | 0.0182 [0.0061, 0.0319] | 0.4900 [0.4595, 0.5283] | 0.0026 [-0.0175, 0.0193] | yes |
| S3[eps=1] | 0.0026 [0.0000, 0.0084] | 0.0078 [0.0000, 0.0193] | 0.4789 [0.4458, 0.5090] | -0.0078 [-0.0242, 0.0052] | yes |
| S3[eps=2] | 0.0000 [0.0000, 0.0000] | 0.0052 [0.0000, 0.0113] | 0.4818 [0.4452, 0.5125] | -0.0104 [-0.0269, 0.0000] | yes |
| S3[eps=4] | 0.0026 [0.0000, 0.0085] | 0.0104 [0.0026, 0.0191] | 0.4805 [0.4534, 0.5138] | -0.0052 [-0.0204, 0.0083] | yes |
| S3[eps=8] | 0.0026 [0.0000, 0.0085] | 0.0156 [0.0024, 0.0362] | 0.5232 [0.4838, 0.5539] | 0.0000 [-0.0175, 0.0183] | yes |
| PD[tau=2] | 0.0338 [0.0121, 0.0608] | 0.0468 [0.0219, 0.0816] | 0.5481 [0.5184, 0.5786] | 0.0312 [0.0076, 0.0579] | no |
| PD[tau=3] | 0.0182 [0.0026, 0.0388] | 0.0286 [0.0111, 0.0518] | 0.5152 [0.4868, 0.5449] | 0.0130 [-0.0027, 0.0301] | yes |
| PD[tau=4] | 0.0078 [0.0000, 0.0173] | 0.0182 [0.0074, 0.0326] | 0.5120 [0.4864, 0.5412] | 0.0026 [-0.0080, 0.0110] | yes |

S4 − S2, TPR at 1% FPR: 0.0623 [0.0277, 0.1060].

## H1c on test

- S1 and S3 (ε ≤ 2) within the margin on every assessable A2/A3 target: **yes**
- Per level (all assessable targets within): S1 yes, S2 no, S4 no, S3 ε=0.5 yes, S3 ε=1 yes, S3 ε=2 yes, S3 ε=4 yes, S3 ε=8 yes, PD τ=2 no, PD τ=3 yes, PD τ=4 yes
- Targets without enough positives in the test half to assess: none
- S4 above S2 (CI of the difference above 0), per target: {'A2_third_party': True, 'A3_amount_top': False, 'A3_fan_in_top': False, 'A3_pass_through': True}
- S3 TPR at 1% FPR by ε (monotone expected): A2 third-member relationship: 0.5→0.0175, 1→0.0173, 2→0.0175, 4→0.0178, 8→0.0189; A3 amount in top decile: 0.5→0.0190, 1→0.0175, 2→0.0159, 4→0.0154, 8→0.0174; A3 fan-in in top decile: 0.5→0.0487, 1→0.0452, 2→0.0381, 4→0.0544, 8→0.0589; A3 pass-through account: 0.5→0.0182, 1→0.0078, 2→0.0052, 4→0.0104, 8→0.0156

## A1 token re-identification

Targets: the tokens of every other member's evidence records. Candidates: every account at another member that the adversary's customers traded with up to the end of validation. Hashing: all candidates tokenised offline, unmetered. OPRF: candidates tokenised within the spare per-epoch budget, every query logged; expected re-identification with candidates queried in random order. Budgets: the protocol's (74,510; A16 sizes it to twice the largest legitimate use on test), twice the largest legitimate use in this run (337,826), and the week-6 placeholder (250,000).

| Adversary | Target tokens | Candidates | Legitimate queries | Hashing | OPRF, protocol budget | OPRF, sized in this run | OPRF, 250,000 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 93,655 | 456,035 | 51,521 | 0.4348 | 0.0219 | 0.2730 | 0.1892 |
| 1 | 93,391 | 457,019 | 54,048 | 0.4388 | 0.0196 | 0.2724 | 0.1881 |
| 2 | 95,543 | 458,017 | 47,272 | 0.4351 | 0.0259 | 0.2760 | 0.1926 |
| 3 | 96,803 | 458,589 | 41,508 | 0.4384 | 0.0316 | 0.2833 | 0.1993 |
| 4 | 95,491 | 459,020 | 45,624 | 0.4374 | 0.0275 | 0.2784 | 0.1947 |
| 5 | 93,117 | 456,085 | 50,042 | 0.4348 | 0.0233 | 0.2743 | 0.1906 |
| 6 | 95,432 | 453,621 | 44,409 | 0.4328 | 0.0287 | 0.2799 | 0.1961 |
| 7 | 93,954 | 550,264 | 168,913 | 0.5045 | 0.0000 | 0.1549 | 0.0743 |

Pooled: hashing 0.4445, OPRF at the protocol budget 0.0224, sized in this run 0.2617. Hashing ÷ OPRF at the protocol budget: **19.86** (PT2 asks for at least 10).

Mechanism check on real tokens: {'checked': 200, 'hash_matches': 200, 'oprf_matches': 200}.

## A4 linkability across epochs

Validation lies inside one 7-day epoch, so key rotation is simulated at its midpoint. Each second-half record an adversary received is ranked among up to 99 first-half records from the same responder by similarity of the record's fields (and embedding at S4); hit@1 is how often the true account comes first. S3 records are released afresh after a rotation (memoised per record and epoch), so they are re-noised independently in each half. Positive control: without rotation, equal tokens link every pair (hit@1 = 1).

| Level | Queries | Chance hit@1 | Hit@1 [95% CI] | Mean reciprocal rank |
| --- | --- | --- | --- | --- |
| S2 | 4,741 | 0.0100 | 0.6231 [0.6085, 0.6368] | 0.6697 |
| S4 | 4,741 | 0.0100 | 0.6627 [0.6475, 0.6760] | 0.7000 |
| S3 ε=0.5 | 4,741 | 0.0100 | 0.0105 [0.0076, 0.0137] | 0.0521 |
| S3 ε=1 | 4,741 | 0.0100 | 0.0103 [0.0076, 0.0131] | 0.0518 |
| S3 ε=2 | 4,741 | 0.0100 | 0.0110 [0.0082, 0.0146] | 0.0522 |
| S3 ε=4 | 4,741 | 0.0100 | 0.0114 [0.0089, 0.0143] | 0.0530 |
| S3 ε=8 | 4,741 | 0.0100 | 0.0114 [0.0089, 0.0144] | 0.0550 |
| PD τ=2 | 1,383 | 0.0101 | 0.6226 [0.6023, 0.6479] | 0.6690 |
| PD τ=3 | 979 | 0.0169 | 0.6221 [0.5934, 0.6507] | 0.6784 |
| PD τ=4 | 664 | 0.0265 | 0.6431 [0.6145, 0.6762] | 0.7036 |

## A5 membership inference on S4 disclosures

Can a peer tell whether an account-window was in another member's autoencoder training sample from what S4 discloses (top deviations, magnitude buckets, embedding)? 80,000 rows, half members; strong adversary trained on half and tested on 40,034. Chance: TPR equals FPR, AUC 0.5. The global DP model's membership inference is X5 (weeks 10–12).

TPR at 0.1% FPR 0.0010 [0.0004, 0.0017]; TPR at 1% FPR 0.0128 [0.0109, 0.0154]; AUC 0.5019 [0.4964, 0.5074].

## A6 query leakage

What does being asked reveal? The request carries the requester's score bucket in the clear (by design: PD needs it). Here a responder predicts whether its own candidate account-window is laundering from its own score, then from its own score plus the requests it received about it. Measured, not prevented.

114,890 candidate account-windows; 0.5806 were asked about at least once, 0.8270 of the laundering ones.

| Responder sees | AUC | TPR at 0.1% FPR | TPR at 1% FPR |
| --- | --- | --- | --- |
| own | 0.7469 [0.7363, 0.7598] | 0.0957 [0.0838, 0.1107] | 0.2158 [0.1986, 0.2366] |
| own+requests | 0.7743 [0.7615, 0.7849] | 0.1509 [0.1299, 0.1783] | 0.3240 [0.3030, 0.3443] |

Gain from requests, TPR at 1% FPR: 0.1081 [0.0899, 0.1247].
