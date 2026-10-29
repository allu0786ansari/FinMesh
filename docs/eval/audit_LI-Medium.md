# Leakage audit A1–A3 on validation · LI-Medium

Seed 0. An honest-but-curious peer attacks everything it receives. A2 and A3 use a strong adversary: a gradient-boosted classifier trained on the true attributes of half the queried accounts (split by account), tested on the other half, against a prior-only attack that sees what the adversary knew before asking (its own accounts in the request, its score bucket, the window and the two banks). Intervals bootstrap the queried accounts. H1c margin (A15): upper 95% bound of (attack − prior) TPR at 1% FPR at most 0.05.

![Utility-leakage frontier](frontier_LI-Medium.png)

Targets: 179,702 (adversary, counterparty, window) triples; test half 89,922. Prevalence: A2 third-member relationship 0.326; A3 amount in top decile 0.100; A3 fan-in in top decile 0.083; A3 pass-through account 0.002.

## A2 third-member relationship

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0236 [0.0169, 0.0336] | 0.0513 [0.0432, 0.0623] | 0.5968 [0.5918, 0.6018] | — | — |
| S1 | 0.0288 [0.0186, 0.0402] | 0.0735 [0.0633, 0.0858] | 0.6159 [0.6100, 0.6216] | 0.0223 [0.0170, 0.0277] | yes |
| S2 | 0.2288 [0.2131, 0.2423] | 0.3287 [0.3191, 0.3397] | 0.7927 [0.7881, 0.7965] | 0.2775 [0.2679, 0.2868] | no |
| S4 | 0.2377 [0.2259, 0.2501] | 0.3507 [0.3415, 0.3615] | 0.7940 [0.7892, 0.7978] | 0.2995 [0.2904, 0.3092] | no |
| S3[eps=0.5] | 0.0267 [0.0181, 0.0385] | 0.0750 [0.0642, 0.0870] | 0.6291 [0.6235, 0.6353] | 0.0238 [0.0183, 0.0282] | yes |
| S3[eps=1] | 0.0245 [0.0160, 0.0371] | 0.0748 [0.0650, 0.0876] | 0.6296 [0.6237, 0.6356] | 0.0236 [0.0185, 0.0289] | yes |
| S3[eps=2] | 0.0261 [0.0176, 0.0389] | 0.0763 [0.0661, 0.0889] | 0.6297 [0.6245, 0.6362] | 0.0251 [0.0189, 0.0291] | yes |
| S3[eps=4] | 0.0260 [0.0170, 0.0376] | 0.0775 [0.0679, 0.0879] | 0.6324 [0.6273, 0.6382] | 0.0262 [0.0212, 0.0303] | yes |
| S3[eps=8] | 0.0255 [0.0158, 0.0368] | 0.0749 [0.0645, 0.0871] | 0.6448 [0.6397, 0.6507] | 0.0237 [0.0180, 0.0278] | yes |
| PD[tau=2] | 0.0329 [0.0235, 0.0460] | 0.0853 [0.0744, 0.0984] | 0.6369 [0.6317, 0.6427] | 0.0341 [0.0285, 0.0392] | yes |
| PD[tau=3] | 0.0283 [0.0189, 0.0412] | 0.0738 [0.0634, 0.0874] | 0.6201 [0.6145, 0.6256] | 0.0226 [0.0182, 0.0291] | yes |
| PD[tau=4] | 0.0282 [0.0187, 0.0398] | 0.0746 [0.0641, 0.0872] | 0.6184 [0.6127, 0.6241] | 0.0233 [0.0188, 0.0287] | yes |

S4 − S2, TPR at 1% FPR: 0.0220 [0.0176, 0.0272].

## A3 amount in top decile

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0336 [0.0116, 0.0634] | 0.0570 [0.0348, 0.0883] | 0.5905 [0.5793, 0.6069] | — | — |
| S1 | 0.0498 [0.0215, 0.0866] | 0.0700 [0.0396, 0.1062] | 0.5977 [0.5842, 0.6148] | 0.0129 [0.0024, 0.0224] | yes |
| S2 | 0.2041 [0.1726, 0.2376] | 0.2962 [0.2735, 0.3237] | 0.7900 [0.7821, 0.8007] | 0.2392 [0.2254, 0.2503] | no |
| S4 | 0.2154 [0.1886, 0.2501] | 0.2972 [0.2729, 0.3252] | 0.7901 [0.7824, 0.8004] | 0.2402 [0.2269, 0.2513] | no |
| S3[eps=0.5] | 0.0476 [0.0199, 0.0819] | 0.0650 [0.0363, 0.0997] | 0.5872 [0.5717, 0.6049] | 0.0080 [-0.0032, 0.0182] | yes |
| S3[eps=1] | 0.0486 [0.0203, 0.0822] | 0.0683 [0.0371, 0.1006] | 0.5858 [0.5709, 0.6027] | 0.0113 [-0.0007, 0.0216] | yes |
| S3[eps=2] | 0.0474 [0.0203, 0.0784] | 0.0644 [0.0349, 0.0954] | 0.5883 [0.5739, 0.6045] | 0.0074 [-0.0038, 0.0163] | yes |
| S3[eps=4] | 0.0464 [0.0195, 0.0783] | 0.0644 [0.0372, 0.0973] | 0.5880 [0.5744, 0.6058] | 0.0074 [-0.0028, 0.0173] | yes |
| S3[eps=8] | 0.0491 [0.0207, 0.0831] | 0.0654 [0.0375, 0.0996] | 0.5908 [0.5767, 0.6097] | 0.0084 [-0.0013, 0.0184] | yes |
| PD[tau=2] | 0.1169 [0.0917, 0.1508] | 0.1364 [0.1094, 0.1710] | 0.6417 [0.6300, 0.6578] | 0.0794 [0.0688, 0.0880] | no |
| PD[tau=3] | 0.0621 [0.0326, 0.0986] | 0.0771 [0.0471, 0.1140] | 0.6027 [0.5892, 0.6192] | 0.0201 [0.0099, 0.0293] | yes |
| PD[tau=4] | 0.0545 [0.0253, 0.0917] | 0.0747 [0.0449, 0.1106] | 0.6004 [0.5873, 0.6168] | 0.0177 [0.0076, 0.0268] | yes |

S4 − S2, TPR at 1% FPR: 0.0010 [-0.0018, 0.0027].

## A3 fan-in in top decile

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0435 [0.0325, 0.0508] | 0.1237 [0.1138, 0.1312] | 0.6629 [0.6557, 0.6700] | — | — |
| S1 | 0.0405 [0.0326, 0.0498] | 0.1811 [0.1677, 0.1928] | 0.7188 [0.7115, 0.7259] | 0.0575 [0.0462, 0.0713] | no |
| S2 | 0.9115 [0.9009, 0.9205] | 0.9260 [0.9170, 0.9331] | 0.9816 [0.9794, 0.9837] | 0.8023 [0.7906, 0.8141] | no |
| S4 | 0.9124 [0.9018, 0.9206] | 0.9272 [0.9182, 0.9336] | 0.9815 [0.9792, 0.9835] | 0.8036 [0.7913, 0.8145] | no |
| S3[eps=0.5] | 0.0445 [0.0376, 0.0514] | 0.1958 [0.1803, 0.2100] | 0.7175 [0.7085, 0.7247] | 0.0721 [0.0603, 0.0865] | no |
| S3[eps=1] | 0.0464 [0.0388, 0.0531] | 0.1983 [0.1843, 0.2099] | 0.7209 [0.7123, 0.7283] | 0.0747 [0.0631, 0.0870] | no |
| S3[eps=2] | 0.0444 [0.0351, 0.0520] | 0.1923 [0.1786, 0.2042] | 0.7219 [0.7132, 0.7283] | 0.0686 [0.0562, 0.0817] | no |
| S3[eps=4] | 0.0428 [0.0327, 0.0519] | 0.1983 [0.1861, 0.2110] | 0.7337 [0.7253, 0.7407] | 0.0747 [0.0624, 0.0872] | no |
| S3[eps=8] | 0.0534 [0.0448, 0.0612] | 0.1904 [0.1788, 0.2032] | 0.7819 [0.7743, 0.7887] | 0.0667 [0.0577, 0.0801] | no |
| PD[tau=2] | 0.0557 [0.0482, 0.0643] | 0.1936 [0.1801, 0.2078] | 0.7342 [0.7269, 0.7414] | 0.0700 [0.0599, 0.0861] | no |
| PD[tau=3] | 0.0378 [0.0308, 0.0498] | 0.1842 [0.1695, 0.1943] | 0.7193 [0.7123, 0.7260] | 0.0605 [0.0501, 0.0729] | no |
| PD[tau=4] | 0.0379 [0.0318, 0.0475] | 0.1808 [0.1663, 0.1934] | 0.7188 [0.7113, 0.7258] | 0.0572 [0.0457, 0.0710] | no |

S4 − S2, TPR at 1% FPR: 0.0012 [-0.0007, 0.0030].

## A3 pass-through account

| Level | TPR at 0.1% FPR | TPR at 1% FPR | AUC | Attack − prior, TPR at 1% | Within margin |
| --- | --- | --- | --- | --- | --- |
| prior | 0.0000 [0.0000, 0.0000] | 0.0113 [0.0000, 0.0296] | 0.5219 [0.4843, 0.5612] | — | — |
| S1 | 0.0000 [0.0000, 0.0000] | 0.0056 [0.0000, 0.0161] | 0.4953 [0.4554, 0.5395] | -0.0056 [-0.0203, 0.0000] | yes |
| S2 | 0.2429 [0.0000, 0.2995] | 0.2486 [0.1744, 0.3161] | 0.6718 [0.6099, 0.7278] | 0.2373 [0.1676, 0.2997] | no |
| S4 | 0.0000 [0.0000, 0.0255] | 0.0169 [0.0000, 0.0382] | 0.4783 [0.4318, 0.5226] | 0.0056 [-0.0175, 0.0359] | yes |
| S3[eps=0.5] | 0.0000 [0.0000, 0.0000] | 0.0056 [0.0000, 0.0203] | 0.4802 [0.4282, 0.5201] | -0.0056 [-0.0254, 0.0120] | yes |
| S3[eps=1] | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | 0.5653 [0.5194, 0.6123] | -0.0113 [-0.0296, 0.0000] | yes |
| S3[eps=2] | 0.0056 [0.0000, 0.0180] | 0.0169 [0.0000, 0.0378] | 0.5038 [0.4548, 0.5533] | 0.0056 [-0.0111, 0.0274] | yes |
| S3[eps=4] | 0.0000 [0.0000, 0.0000] | 0.0169 [0.0000, 0.0438] | 0.5093 [0.4642, 0.5520] | 0.0056 [-0.0178, 0.0385] | yes |
| S3[eps=8] | 0.0000 [0.0000, 0.0000] | 0.0452 [0.0187, 0.0757] | 0.5290 [0.4742, 0.5803] | 0.0339 [0.0000, 0.0704] | no |
| PD[tau=2] | 0.0847 [0.0431, 0.1347] | 0.0904 [0.0464, 0.1360] | 0.5833 [0.5323, 0.6321] | 0.0791 [0.0349, 0.1346] | no |
| PD[tau=3] | 0.0113 [0.0000, 0.0273] | 0.0169 [0.0000, 0.0375] | 0.5400 [0.5032, 0.5836] | 0.0056 [-0.0139, 0.0267] | yes |
| PD[tau=4] | 0.0056 [0.0000, 0.0175] | 0.0113 [0.0000, 0.0275] | 0.5105 [0.4652, 0.5569] | 0.0000 [-0.0180, 0.0158] | yes |

S4 − S2, TPR at 1% FPR: -0.2316 [-0.2937, -0.1612].

## H1c on validation

- S1 and S3 (ε ≤ 2) within the margin on every assessable A2/A3 target: **no**
- Per level (all assessable targets within): S1 no, S2 no, S4 no, S3 ε=0.5 no, S3 ε=1 no, S3 ε=2 no, S3 ε=4 no, S3 ε=8 no, PD τ=2 no, PD τ=3 no, PD τ=4 no
- Targets without enough positives in the test half to assess: none
- S4 above S2 (CI of the difference above 0), per target: {'A2_third_party': True, 'A3_amount_top': False, 'A3_fan_in_top': False, 'A3_pass_through': False}
- S3 TPR at 1% FPR by ε (monotone expected): A2 third-member relationship: 0.5→0.0750, 1→0.0748, 2→0.0763, 4→0.0775, 8→0.0749; A3 amount in top decile: 0.5→0.0650, 1→0.0683, 2→0.0644, 4→0.0644, 8→0.0654; A3 fan-in in top decile: 0.5→0.1958, 1→0.1983, 2→0.1923, 4→0.1983, 8→0.1904; A3 pass-through account: 0.5→0.0056, 1→0.0000, 2→0.0169, 4→0.0169, 8→0.0452

## A1 token re-identification

Targets: the tokens of every other member's evidence records. Candidates: every account at another member that the adversary's customers traded with up to the end of validation. Hashing: all candidates tokenised offline, unmetered. OPRF: candidates tokenised within the spare per-epoch budget, every query logged; expected re-identification with candidates queried in random order. Budgets: the protocol's (87,580; A16 sizes it to twice the largest legitimate use on validation), twice the largest legitimate use in this run (87,580), and the week-6 placeholder (250,000).

| Adversary | Target tokens | Candidates | Legitimate queries | Hashing | OPRF, protocol budget | OPRF, sized in this run | OPRF, 250,000 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 51,993 | 420,932 | 43,790 | 0.3997 | 0.0416 | 0.0416 | 0.1958 |
| 1 | 54,943 | 423,190 | 35,626 | 0.3974 | 0.0488 | 0.0488 | 0.2013 |
| 2 | 56,430 | 423,171 | 27,863 | 0.4002 | 0.0565 | 0.0565 | 0.2101 |
| 3 | 57,551 | 522,201 | 24,447 | 0.4492 | 0.0543 | 0.0543 | 0.1940 |
| 4 | 55,997 | 425,971 | 31,257 | 0.4009 | 0.0530 | 0.0530 | 0.2059 |
| 5 | 56,078 | 421,741 | 30,646 | 0.3990 | 0.0539 | 0.0539 | 0.2075 |
| 6 | 54,957 | 422,503 | 35,021 | 0.3963 | 0.0493 | 0.0493 | 0.2016 |
| 7 | 58,140 | 422,685 | 25,617 | 0.3908 | 0.0573 | 0.0573 | 0.2074 |

Pooled: hashing 0.4044, OPRF at the protocol budget 0.0520, sized in this run 0.0520. Hashing ÷ OPRF at the protocol budget: **7.78** (PT2 asks for at least 10).

Mechanism check on real tokens: {'checked': 200, 'hash_matches': 200, 'oprf_matches': 200}.

## A4 linkability across epochs

Validation lies inside one 7-day epoch, so key rotation is simulated at its midpoint. Each second-half record an adversary received is ranked among up to 99 first-half records from the same responder by similarity of the record's fields (and embedding at S4); hit@1 is how often the true account comes first. S3 records are released afresh after a rotation (memoised per record and epoch), so they are re-noised independently in each half. Positive control: without rotation, equal tokens link every pair (hit@1 = 1).

| Level | Queries | Chance hit@1 | Hit@1 [95% CI] | Mean reciprocal rank |
| --- | --- | --- | --- | --- |
| S2 | 2,241 | 0.0100 | 0.4618 [0.4426, 0.4824] | 0.5216 |
| S4 | 2,241 | 0.0100 | 0.5011 [0.4770, 0.5190] | 0.5497 |
| S3 ε=0.5 | 2,241 | 0.0100 | 0.0107 [0.0067, 0.0161] | 0.0505 |
| S3 ε=1 | 2,241 | 0.0100 | 0.0089 [0.0049, 0.0125] | 0.0510 |
| S3 ε=2 | 2,241 | 0.0100 | 0.0129 [0.0085, 0.0178] | 0.0549 |
| S3 ε=4 | 2,241 | 0.0100 | 0.0094 [0.0054, 0.0134] | 0.0522 |
| S3 ε=8 | 2,241 | 0.0100 | 0.0120 [0.0076, 0.0170] | 0.0532 |
| PD τ=2 | 100 | 0.0197 | 0.7100 [0.6200, 0.7903] | 0.7553 |
| PD τ=3 | 19 | 0.0860 | 0.8421 [0.6316, 0.9487] | 0.8820 |
| PD τ=4 | 0 | — | — | — |

## A5 membership inference on S4 disclosures

Can a peer tell whether an account-window was in another member's autoencoder training sample from what S4 discloses (top deviations, magnitude buckets, embedding)? 80,000 rows, half members; strong adversary trained on half and tested on 39,790. Chance: TPR equals FPR, AUC 0.5. The global DP model's membership inference is X5 (weeks 10–12).

TPR at 0.1% FPR 0.0016 [0.0009, 0.0021]; TPR at 1% FPR 0.0094 [0.0076, 0.0112]; AUC 0.5004 [0.4951, 0.5062].

## A6 query leakage

What does being asked reveal? The request carries the requester's score bucket in the clear (by design: PD needs it). Here a responder predicts whether its own candidate account-window is laundering from its own score, then from its own score plus the requests it received about it. Measured, not prevented.

68,019 candidate account-windows; 0.7013 were asked about at least once, 0.7641 of the laundering ones.

| Responder sees | AUC | TPR at 0.1% FPR | TPR at 1% FPR |
| --- | --- | --- | --- |
| own | 0.6437 [0.6266, 0.6614] | 0.0387 [0.0290, 0.0553] | 0.0920 [0.0757, 0.1099] |
| own+requests | 0.6190 [0.6017, 0.6364] | 0.0767 [0.0573, 0.0954] | 0.1162 [0.0922, 0.1384] |

Gain from requests, TPR at 1% FPR: 0.0242 [0.0065, 0.0385].
