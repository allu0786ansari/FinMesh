# A5 · membership inference on the federated model · LI-Medium

Deployed setup (A19): account unit (bags of at most 8 windows), degree cap 16. Each member's training accounts split 50/50 by a fixed hash: IN (243,329 accounts, 3,822 with laundering) trains the models, OUT (243,378, 3,797 with laundering) never does. Seed 0; 50 rounds; DP settings dp-tune LI-Small (A19) (clip 10, batch 2048, lr 0.01). The attacker is a peer bank holding the global model and the candidate's rows and labels (worst case). LOSS = −mean weighted loss of the account's bag; REF = the attacker's own local non-private MLP's loss minus the global model's. A useless attack has TPR = FPR and AUC 0.5. Run `20261030T213940Z`; 1,880 s, peak memory 2,303 MB.

| Model | Attack | Accounts | AUC [95% CI] | TPR at 1% FPR [95% CI] | DP bound at 1% FPR | Empirical ε lower bound (1% FPR) | TPR at 0.1% FPR [95% CI] |
| --- | --- | --- | --- | --- | --- | --- | --- |
| non-private FedAvg | LOSS | all | 0.5001 [0.4987, 0.5018] | 0.0104 [0.0100, 0.0111] | — | 0.0000 | 0.0011 [0.0010, 0.0013] |
| non-private FedAvg | LOSS | laundering | 0.5073 [0.4952, 0.5201] | 0.0113 [0.0057, 0.0163] | — | 0.0000 | 0.0031 [0.0013, 0.0052] |
| non-private FedAvg | REF | all | 0.5008 [0.4994, 0.5025] | 0.0101 [0.0095, 0.0105] | — | 0.0000 | 0.0011 [0.0010, 0.0012] |
| non-private FedAvg | REF | laundering | 0.5106 [0.4989, 0.5237] | 0.0157 [0.0097, 0.0198] | — | 0.0000 | 0.0018 [0.0005, 0.0061] |
| DP, ε = 1 | LOSS | all | 0.5000 [0.4984, 0.5019] | 0.0104 [0.0099, 0.0111] | 0.0272 | 0.0000 | 0.0010 [0.0008, 0.0012] |
| DP, ε = 1 | LOSS | laundering | 0.5083 [0.4963, 0.5190] | 0.0094 [0.0059, 0.0156] | — | 0.0000 | 0.0013 [0.0003, 0.0036] |
| DP, ε = 1 | REF | all | 0.4999 [0.4985, 0.5015] | 0.0101 [0.0095, 0.0105] | 0.0272 | 0.0000 | 0.0011 [0.0009, 0.0012] |
| DP, ε = 1 | REF | laundering | 0.5149 [0.5023, 0.5275] | 0.0113 [0.0074, 0.0150] | — | 0.0000 | 0.0016 [0.0000, 0.0029] |
| DP, ε = 3 | LOSS | all | 0.5005 [0.4989, 0.5020] | 0.0099 [0.0094, 0.0105] | 0.2009 | 0.0000 | 0.0012 [0.0009, 0.0013] |
| DP, ε = 3 | LOSS | laundering | 0.5070 [0.4936, 0.5188] | 0.0084 [0.0055, 0.0157] | — | 0.0000 | 0.0016 [0.0005, 0.0030] |
| DP, ε = 3 | REF | all | 0.5000 [0.4986, 0.5014] | 0.0100 [0.0094, 0.0105] | 0.2009 | 0.0000 | 0.0011 [0.0010, 0.0013] |
| DP, ε = 3 | REF | laundering | 0.5122 [0.4985, 0.5255] | 0.0115 [0.0073, 0.0180] | — | 0.0000 | 0.0008 [0.0000, 0.0035] |
| DP, ε = 10 | LOSS | all | 0.5005 [0.4990, 0.5020] | 0.0104 [0.0099, 0.0110] | 220.26 | 0.0000 | 0.0011 [0.0009, 0.0013] |
| DP, ε = 10 | LOSS | laundering | 0.5085 [0.4954, 0.5196] | 0.0136 [0.0075, 0.0207] | — | 0.0000 | 0.0018 [0.0005, 0.0034] |
| DP, ε = 10 | REF | all | 0.4998 [0.4984, 0.5012] | 0.0100 [0.0094, 0.0105] | 220.26 | 0.0000 | 0.0012 [0.0010, 0.0014] |
| DP, ε = 10 | REF | laundering | 0.5134 [0.5005, 0.5253] | 0.0107 [0.0072, 0.0171] | — | 0.0000 | 0.0013 [0.0000, 0.0031] |

**Audit passed:** no DP model's TPR at 1% FPR exceeds e^ε × 0.01 + δ.

The empirical ε lower bound comes from Clopper–Pearson 95% bounds at one threshold chosen on the same data, so it is indicative; a value above the target ε would also flag a leak. Laundering accounts are few, so their intervals are wide.
