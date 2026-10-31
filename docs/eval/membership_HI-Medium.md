# A5 · membership inference on the federated model · HI-Medium

Deployed setup (A19): account unit (bags of at most 8 windows), degree cap 16. Each member's training accounts split 50/50 by a fixed hash: IN (249,495 accounts, 6,883 with laundering) trains the models, OUT (249,846, 6,855 with laundering) never does. Seed 0; 50 rounds; DP settings dp-tune HI-Small (A19) (clip 10, batch 512, lr 0.01). The attacker is a peer bank holding the global model and the candidate's rows and labels (worst case). LOSS = −mean weighted loss of the account's bag; REF = the attacker's own local non-private MLP's loss minus the global model's. A useless attack has TPR = FPR and AUC 0.5. Run `20261030T212856Z`; 641 s, peak memory 2,240 MB.

| Model | Attack | Accounts | AUC [95% CI] | TPR at 1% FPR [95% CI] | DP bound at 1% FPR | Empirical ε lower bound (1% FPR) | TPR at 0.1% FPR [95% CI] |
| --- | --- | --- | --- | --- | --- | --- | --- |
| non-private FedAvg | LOSS | all | 0.5013 [0.4997, 0.5030] | 0.0100 [0.0094, 0.0105] | — | 0.0000 | 0.0010 [0.0009, 0.0012] |
| non-private FedAvg | LOSS | laundering | 0.5055 [0.4964, 0.5169] | 0.0106 [0.0068, 0.0140] | — | 0.0000 | 0.0019 [0.0009, 0.0037] |
| non-private FedAvg | REF | all | 0.5012 [0.4998, 0.5025] | 0.0106 [0.0101, 0.0111] | — | 0.0000 | 0.0012 [0.0010, 0.0014] |
| non-private FedAvg | REF | laundering | 0.5151 [0.5061, 0.5236] | 0.0108 [0.0087, 0.0154] | — | 0.0000 | 0.0035 [0.0015, 0.0065] |
| DP, ε = 1 | LOSS | all | 0.5010 [0.4996, 0.5030] | 0.0103 [0.0097, 0.0108] | 0.0272 | 0.0000 | 0.0011 [0.0009, 0.0012] |
| DP, ε = 1 | LOSS | laundering | 0.5055 [0.4961, 0.5169] | 0.0093 [0.0063, 0.0148] | — | 0.0000 | 0.0022 [0.0003, 0.0037] |
| DP, ε = 1 | REF | all | 0.4989 [0.4972, 0.5008] | 0.0099 [0.0094, 0.0104] | 0.0272 | 0.0000 | 0.0009 [0.0008, 0.0011] |
| DP, ε = 1 | REF | laundering | 0.5055 [0.4967, 0.5171] | 0.0099 [0.0080, 0.0134] | — | 0.0000 | 0.0007 [0.0001, 0.0016] |
| DP, ε = 3 | LOSS | all | 0.5012 [0.4996, 0.5030] | 0.0103 [0.0097, 0.0109] | 0.2009 | 0.0000 | 0.0009 [0.0007, 0.0011] |
| DP, ε = 3 | LOSS | laundering | 0.5061 [0.4973, 0.5180] | 0.0123 [0.0090, 0.0157] | — | 0.0000 | 0.0025 [0.0010, 0.0037] |
| DP, ε = 3 | REF | all | 0.4989 [0.4973, 0.5007] | 0.0099 [0.0093, 0.0103] | 0.2009 | 0.0000 | 0.0010 [0.0008, 0.0011] |
| DP, ε = 3 | REF | laundering | 0.5059 [0.4972, 0.5177] | 0.0078 [0.0050, 0.0112] | — | 0.0000 | 0.0004 [0.0000, 0.0020] |
| DP, ε = 10 | LOSS | all | 0.5016 [0.5000, 0.5035] | 0.0105 [0.0101, 0.0110] | 220.26 | 0.0000 | 0.0010 [0.0008, 0.0012] |
| DP, ε = 10 | LOSS | laundering | 0.5061 [0.4970, 0.5175] | 0.0119 [0.0082, 0.0158] | — | 0.0000 | 0.0031 [0.0004, 0.0042] |
| DP, ε = 10 | REF | all | 0.4991 [0.4974, 0.5008] | 0.0100 [0.0094, 0.0104] | 220.26 | 0.0000 | 0.0010 [0.0009, 0.0012] |
| DP, ε = 10 | REF | laundering | 0.5065 [0.4976, 0.5178] | 0.0081 [0.0062, 0.0111] | — | 0.0000 | 0.0004 [0.0000, 0.0015] |

**Audit passed:** no DP model's TPR at 1% FPR exceeds e^ε × 0.01 + δ.

The empirical ε lower bound comes from Clopper–Pearson 95% bounds at one threshold chosen on the same data, so it is indicative; a value above the target ε would also flag a leak. Laundering accounts are few, so their intervals are wide.
