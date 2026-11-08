# Leakage audit A1–A3 on test · HI-Large-W16

> **Sealed test (week 18).** Every model trained on the training partition; every calibration, threshold, fusion and attribution parameter fitted on validation and frozen; test scored label-free, then opened once per seed through the logged seal (`finmesh sealed-log`). Wording below that says *validation* in a column or check name refers to the frozen rule; every number is on **test**.

Seed 0. An honest-but-curious peer attacks everything it receives. A2 and A3 use a strong adversary: a gradient-boosted classifier trained on the true attributes of half the queried accounts (split by account), tested on the other half, against a prior-only attack that sees what the adversary knew before asking (its own accounts in the request, its score bucket, the window and the two banks). Intervals bootstrap the queried accounts. H1c margin (A15): upper 95% bound of (attack − prior) TPR at 1% FPR at most 0.05.

![Utility-leakage frontier](frontier_HI-Large-W16.png)

Targets: 194,723 (adversary, counterparty, window) triples; test half 97,199. Prevalence: A2 third-member relationship 0.380; A3 amount in top decile 0.100; A3 fan-in in top decile 0.082; A3 pass-through account 0.003.

## A2 third-member relationship

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0151 [0.0110, 0.0189] | 0.0573 [0.0533, 0.0616] | 0.5692 [0.5655, 0.5732] | — | — |
| S1 | 0.0170 [0.0115, 0.0206] | 0.0590 [0.0548, 0.0633] | 0.5720 [0.5682, 0.5755] | 0.0017 [0.0002, 0.0033] | yes |
| S2 | 0.1974 [0.1872, 0.2044] | 0.2740 [0.2666, 0.2824] | 0.7909 [0.7873, 0.7941] | 0.2167 [0.2103, 0.2246] | no |
| S4 | 0.2069 [0.1983, 0.2157] | 0.2957 [0.2873, 0.3048] | 0.7949 [0.7915, 0.7982] | 0.2384 [0.2302, 0.2470] | no |
| S3[eps=0.5] | 0.0151 [0.0120, 0.0190] | 0.0600 [0.0558, 0.0649] | 0.5803 [0.5747, 0.5849] | 0.0027 [0.0007, 0.0048] | yes |
| S3[eps=1] | 0.0145 [0.0116, 0.0186] | 0.0584 [0.0547, 0.0634] | 0.5808 [0.5768, 0.5848] | 0.0011 [-0.0003, 0.0031] | yes |
| S3[eps=2] | 0.0149 [0.0116, 0.0189] | 0.0601 [0.0555, 0.0649] | 0.5814 [0.5769, 0.5857] | 0.0028 [0.0009, 0.0047] | yes |
| S3[eps=4] | 0.0175 [0.0129, 0.0215] | 0.0603 [0.0560, 0.0650] | 0.5807 [0.5763, 0.5853] | 0.0030 [0.0009, 0.0049] | yes |
| S3[eps=8] | 0.0130 [0.0094, 0.0165] | 0.0613 [0.0573, 0.0661] | 0.5809 [0.5771, 0.5858] | 0.0040 [0.0020, 0.0062] | yes |
| PD[tau=2] | 0.0250 [0.0222, 0.0302] | 0.0944 [0.0900, 0.1006] | 0.6283 [0.6246, 0.6319] | 0.0371 [0.0339, 0.0418] | yes |
| PD[tau=3] | 0.0143 [0.0110, 0.0196] | 0.0684 [0.0642, 0.0736] | 0.5892 [0.5854, 0.5929] | 0.0111 [0.0089, 0.0135] | yes |
| PD[tau=4] | 0.0108 [0.0075, 0.0149] | 0.0645 [0.0602, 0.0698] | 0.5792 [0.5755, 0.5828] | 0.0072 [0.0054, 0.0091] | yes |
| S1F[gate=2] | 0.0169 [0.0129, 0.0211] | 0.0577 [0.0535, 0.0626] | 0.5712 [0.5669, 0.5748] | 0.0004 [-0.0007, 0.0020] | yes |

S4 − S2, TPR at 1% FPR: 0.0218 [0.0161, 0.0287].

## A3 amount in top decile

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0041 [0.0014, 0.0086] | 0.0212 [0.0168, 0.0283] | 0.5835 [0.5772, 0.5899] | — | — |
| S1 | 0.0075 [0.0020, 0.0180] | 0.0290 [0.0211, 0.0411] | 0.5866 [0.5793, 0.5941] | 0.0078 [0.0028, 0.0136] | yes |
| S2 | 0.1636 [0.1507, 0.1776] | 0.2556 [0.2438, 0.2681] | 0.7916 [0.7865, 0.7971] | 0.2344 [0.2234, 0.2457] | no |
| S4 | 0.1634 [0.1510, 0.1744] | 0.2585 [0.2467, 0.2710] | 0.7897 [0.7846, 0.7950] | 0.2373 [0.2264, 0.2485] | no |
| S3[eps=0.5] | 0.0068 [0.0014, 0.0168] | 0.0265 [0.0184, 0.0380] | 0.5806 [0.5742, 0.5877] | 0.0053 [-0.0011, 0.0113] | yes |
| S3[eps=1] | 0.0072 [0.0012, 0.0176] | 0.0265 [0.0187, 0.0385] | 0.5794 [0.5726, 0.5867] | 0.0053 [-0.0010, 0.0105] | yes |
| S3[eps=2] | 0.0076 [0.0018, 0.0184] | 0.0253 [0.0176, 0.0370] | 0.5818 [0.5749, 0.5896] | 0.0041 [-0.0021, 0.0097] | yes |
| S3[eps=4] | 0.0069 [0.0013, 0.0174] | 0.0256 [0.0185, 0.0374] | 0.5822 [0.5756, 0.5893] | 0.0044 [-0.0009, 0.0102] | yes |
| S3[eps=8] | 0.0088 [0.0024, 0.0213] | 0.0269 [0.0192, 0.0391] | 0.5797 [0.5721, 0.5866] | 0.0057 [-0.0007, 0.0120] | yes |
| PD[tau=2] | 0.0718 [0.0617, 0.0837] | 0.1232 [0.1141, 0.1359] | 0.6587 [0.6519, 0.6665] | 0.1019 [0.0947, 0.1094] | no |
| PD[tau=3] | 0.0252 [0.0180, 0.0357] | 0.0513 [0.0431, 0.0640] | 0.5998 [0.5925, 0.6075] | 0.0301 [0.0239, 0.0372] | yes |
| PD[tau=4] | 0.0164 [0.0092, 0.0289] | 0.0391 [0.0308, 0.0506] | 0.5931 [0.5861, 0.6004] | 0.0179 [0.0119, 0.0236] | yes |
| S1F[gate=2] | 0.0082 [0.0024, 0.0196] | 0.0292 [0.0217, 0.0414] | 0.5865 [0.5795, 0.5931] | 0.0080 [0.0029, 0.0141] | yes |

S4 − S2, TPR at 1% FPR: 0.0029 [-0.0011, 0.0062].

## A3 fan-in in top decile

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0464 [0.0384, 0.0615] | 0.2233 [0.2140, 0.2356] | 0.7391 [0.7318, 0.7469] | — | — |
| S1 | 0.0536 [0.0428, 0.0687] | 0.2242 [0.2139, 0.2376] | 0.7388 [0.7305, 0.7463] | 0.0009 [-0.0022, 0.0028] | yes |
| S2 | 0.9263 [0.9160, 0.9337] | 0.9529 [0.9458, 0.9600] | 0.9870 [0.9846, 0.9900] | 0.7296 [0.7162, 0.7410] | no |
| S4 | 0.9252 [0.9146, 0.9323] | 0.9500 [0.9419, 0.9569] | 0.9851 [0.9824, 0.9883] | 0.7267 [0.7135, 0.7389] | no |
| S3[eps=0.5] | 0.0546 [0.0394, 0.0687] | 0.2200 [0.2089, 0.2348] | 0.7298 [0.7216, 0.7382] | -0.0033 [-0.0073, 0.0006] | yes |
| S3[eps=1] | 0.0534 [0.0369, 0.0667] | 0.2210 [0.2105, 0.2332] | 0.7304 [0.7225, 0.7399] | -0.0023 [-0.0057, 0.0015] | yes |
| S3[eps=2] | 0.0481 [0.0371, 0.0628] | 0.2194 [0.2097, 0.2327] | 0.7310 [0.7226, 0.7389] | -0.0039 [-0.0072, -0.0004] | yes |
| S3[eps=4] | 0.0388 [0.0300, 0.0539] | 0.2200 [0.2102, 0.2341] | 0.7287 [0.7198, 0.7366] | -0.0033 [-0.0063, 0.0004] | yes |
| S3[eps=8] | 0.0391 [0.0315, 0.0527] | 0.2181 [0.2086, 0.2307] | 0.7367 [0.7281, 0.7441] | -0.0052 [-0.0093, -0.0021] | yes |
| PD[tau=2] | 0.1168 [0.1059, 0.1303] | 0.2801 [0.2694, 0.2921] | 0.7839 [0.7778, 0.7906] | 0.0568 [0.0512, 0.0627] | no |
| PD[tau=3] | 0.0604 [0.0536, 0.0715] | 0.2334 [0.2226, 0.2460] | 0.7464 [0.7387, 0.7535] | 0.0101 [0.0067, 0.0121] | yes |
| PD[tau=4] | 0.0529 [0.0406, 0.0698] | 0.2261 [0.2170, 0.2414] | 0.7418 [0.7337, 0.7491] | 0.0028 [-0.0003, 0.0066] | yes |
| S1F[gate=2] | 0.0542 [0.0430, 0.0681] | 0.2245 [0.2148, 0.2381] | 0.7399 [0.7325, 0.7473] | 0.0011 [-0.0009, 0.0034] | yes |

S4 − S2, TPR at 1% FPR: -0.0029 [-0.0056, 0.0004].

## A3 pass-through account

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0000 [0.0000, 0.0000] | 0.0120 [0.0000, 0.0265] | 0.5271 [0.4990, 0.5597] | — | — |
| S1 | 0.0000 [0.0000, 0.0000] | 0.0120 [0.0000, 0.0265] | 0.4884 [0.4540, 0.5312] | 0.0000 [0.0000, 0.0000] | yes |
| S2 | 0.0558 [0.0250, 0.0942] | 0.0677 [0.0335, 0.1013] | 0.5700 [0.5286, 0.6110] | 0.0558 [0.0208, 0.0856] | no |
| S4 | 0.0916 [0.0000, 0.1317] | 0.1116 [0.0755, 0.1515] | 0.6135 [0.5728, 0.6671] | 0.0996 [0.0606, 0.1381] | no |
| S3[eps=0.5] | 0.0000 [0.0000, 0.0000] | 0.0040 [0.0000, 0.0121] | 0.5100 [0.4737, 0.5518] | -0.0080 [-0.0230, 0.0044] | yes |
| S3[eps=1] | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | 0.5024 [0.4690, 0.5466] | -0.0120 [-0.0265, 0.0000] | yes |
| S3[eps=2] | 0.0000 [0.0000, 0.0000] | 0.0040 [0.0000, 0.0144] | 0.4978 [0.4609, 0.5403] | -0.0080 [-0.0246, 0.0042] | yes |
| S3[eps=4] | 0.0000 [0.0000, 0.0000] | 0.0120 [0.0000, 0.0252] | 0.5179 [0.4811, 0.5612] | 0.0000 [-0.0190, 0.0157] | yes |
| S3[eps=8] | 0.0000 [0.0000, 0.0000] | 0.0120 [0.0000, 0.0261] | 0.5525 [0.5138, 0.5896] | 0.0000 [-0.0181, 0.0187] | yes |
| PD[tau=2] | 0.0558 [0.0262, 0.0904] | 0.0598 [0.0320, 0.0942] | 0.5359 [0.4951, 0.5832] | 0.0478 [0.0177, 0.0834] | no |
| PD[tau=3] | 0.0159 [0.0000, 0.0322] | 0.0319 [0.0127, 0.0533] | 0.5200 [0.4788, 0.5664] | 0.0199 [0.0041, 0.0386] | yes |
| PD[tau=4] | 0.0120 [0.0000, 0.0260] | 0.0319 [0.0101, 0.0527] | 0.4911 [0.4580, 0.5373] | 0.0199 [0.0040, 0.0356] | yes |
| S1F[gate=2] | 0.0000 [0.0000, 0.0000] | 0.0159 [0.0000, 0.0288] | 0.4971 [0.4625, 0.5370] | 0.0040 [-0.0077, 0.0120] | yes |

S4 − S2, TPR at 1% FPR: 0.0438 [0.0035, 0.0860].

## H1c on test

- S1 and S3 (ε ≤ 2) within the margin on every assessable A2/A3 target: **yes**
- Per level (all assessable targets within): S1 yes, S2 no, S4 no, S3 ε=0.5 yes, S3 ε=1 yes, S3 ε=2 yes, S3 ε=4 yes, S3 ε=8 yes, PD τ=2 no, PD τ=3 yes, PD τ=4 yes, S1F[gate=2 yes
- Targets without enough positives in the test half to assess: none
- S4 above S2 (CI of the difference above 0), per target: {'A2_third_party': True, 'A3_amount_top': False, 'A3_fan_in_top': False, 'A3_pass_through': True}
- S3 TPR at 1% FPR by ε (monotone expected): A2 third-member relationship: 0.5→0.0600, 1→0.0584, 2→0.0601, 4→0.0603, 8→0.0613; A3 amount in top decile: 0.5→0.0265, 1→0.0265, 2→0.0253, 4→0.0256, 8→0.0269; A3 fan-in in top decile: 0.5→0.2200, 1→0.2210, 2→0.2194, 4→0.2200, 8→0.2181; A3 pass-through account: 0.5→0.0040, 1→0.0000, 2→0.0040, 4→0.0120, 8→0.0120

## A1 token re-identification

Targets: the tokens of every other member's evidence records. Candidates: every account at another member that the adversary's customers traded with up to the end of validation. Hashing: all candidates tokenised offline, unmetered. OPRF: candidates tokenised within the spare per-epoch budget, every query logged; expected re-identification with candidates queried in random order. Budgets: the protocol's (109,282; A16 sizes it to twice the largest legitimate use on test), twice the largest legitimate use in this run (120,070), and the week-6 placeholder (250,000).

| Adversary | Target tokens | Candidates | Legitimate queries | Hashing | OPRF, protocol budget | OPRF, sized in this run | OPRF, 250,000 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 128,055 | 458,902 | 44,355 | 0.3822 | 0.0541 | 0.0631 | 0.1713 |
| 1 | 125,534 | 463,094 | 50,897 | 0.3877 | 0.0489 | 0.0579 | 0.1667 |
| 2 | 121,746 | 463,744 | 59,894 | 0.3888 | 0.0414 | 0.0505 | 0.1594 |
| 3 | 122,589 | 463,167 | 60,035 | 0.3882 | 0.0413 | 0.0503 | 0.1592 |
| 4 | 128,009 | 463,462 | 47,175 | 0.3856 | 0.0517 | 0.0606 | 0.1688 |
| 5 | 125,525 | 459,008 | 47,681 | 0.3848 | 0.0516 | 0.0607 | 0.1696 |
| 6 | 128,452 | 459,042 | 43,904 | 0.3781 | 0.0539 | 0.0627 | 0.1698 |
| 7 | 124,919 | 557,856 | 52,114 | 0.4371 | 0.0448 | 0.0532 | 0.1551 |

Pooled: hashing 0.3915, OPRF at the protocol budget 0.0485, sized in this run 0.0575. Hashing ÷ OPRF at the protocol budget: **8.07** (PT2 asks for at least 10).

Mechanism check on real tokens: {'checked': 200, 'hash_matches': 200, 'oprf_matches': 200}.

## A4 linkability across epochs

Validation lies inside one 7-day epoch, so key rotation is simulated at its midpoint. Each second-half record an adversary received is ranked among up to 99 first-half records from the same responder by similarity of the record's fields (and embedding at S4); hit@1 is how often the true account comes first. S3 records are released afresh after a rotation (memoised per record and epoch), so they are re-noised independently in each half. Positive control: without rotation, equal tokens link every pair (hit@1 = 1).

| Level | Queries | Chance hit@1 | Hit@1 [95% CI] | Mean reciprocal rank |
| --- | --- | --- | --- | --- |
| S2 | 9,485 | 0.0100 | 0.4312 [0.4219, 0.4402] | 0.4973 |
| S4 | 9,485 | 0.0100 | 0.4879 [0.4783, 0.4955] | 0.5384 |
| S3 ε=0.5 | 9,485 | 0.0100 | 0.0100 [0.0081, 0.0118] | 0.0531 |
| S3 ε=1 | 9,485 | 0.0100 | 0.0095 [0.0078, 0.0113] | 0.0524 |
| S3 ε=2 | 9,485 | 0.0100 | 0.0095 [0.0079, 0.0114] | 0.0523 |
| S3 ε=4 | 9,485 | 0.0100 | 0.0096 [0.0080, 0.0119] | 0.0522 |
| S3 ε=8 | 9,485 | 0.0100 | 0.0116 [0.0095, 0.0138] | 0.0548 |
| PD τ=2 | 1,400 | 0.0100 | 0.4964 [0.4721, 0.5222] | 0.5511 |
| PD τ=3 | 513 | 0.0160 | 0.4951 [0.4541, 0.5380] | 0.5680 |
| PD τ=4 | 208 | 0.0396 | 0.4856 [0.4231, 0.5578] | 0.5866 |

## A5 membership inference on S4 disclosures

Can a peer tell whether an account-window was in another member's autoencoder training sample from what S4 discloses (top deviations, magnitude buckets, embedding)? 80,000 rows, half members; strong adversary trained on half and tested on 40,199. Chance: TPR equals FPR, AUC 0.5. The global DP model's membership inference is X5 (weeks 10–12).

TPR at 0.1% FPR 0.0015 [0.0008, 0.0023]; TPR at 1% FPR 0.0095 [0.0080, 0.0113]; AUC 0.4997 [0.4938, 0.5054].

## A6 query leakage

What does being asked reveal? The request carries the requester's score bucket in the clear (by design: PD needs it). Here a responder predicts whether its own candidate account-window is laundering from its own score, then from its own score plus the requests it received about it. Measured, not prevented.

154,692 candidate account-windows; 0.7421 were asked about at least once, 0.8771 of the laundering ones.

| Responder sees | AUC | TPR at 0.1% FPR | TPR at 1% FPR |
| --- | --- | --- | --- |
| own | 0.7398 [0.7282, 0.7504] | 0.0827 [0.0000, 0.0913] | 0.1844 [0.1677, 0.1991] |
| own+requests | 0.7510 [0.7407, 0.7613] | 0.1017 [0.0874, 0.1152] | 0.2169 [0.1973, 0.2296] |

Gain from requests, TPR at 1% FPR: 0.0325 [0.0175, 0.0453].
