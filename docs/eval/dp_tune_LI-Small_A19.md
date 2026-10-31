# DP hyperparameters on the proxy federation · LI-Small · A19

Amendment A19: FedAvg with DP-SGD at ε = 3 (window unit, seed 0, 50 rounds; 20 local steps per round for every setting, so every setting takes the same 1,000 updates and a larger batch costs more compute) for every setting in the grid, scored by AUPRC on this federation's training hold-out (25,362 rows, 288 positives). The best setting is written to `finmesh/schemas/dp_hparams.json` and used unchanged on the Medium set of the same regime; no Medium data is used here. Total 2,014 s, peak memory 576 MB.

| Clip norm | Expected batch | Learning rate | Local steps per round | Hold-out AUPRC | Share clipped | Noise multiplier | Seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1.00 | 512 | 0.0010 | 20 | 0.1505 | 0.0205 | 2.75 | 50.40 |
| 1.00 | 512 | 0.0030 | 20 | 0.2346 | 0.0174 | 2.75 | 51.40 |
| 1.00 | 512 | 0.0100 | 20 | 0.2683 | 0.0177 | 2.75 | 56.30 |
| 1.00 | 2,048 | 0.0010 | 20 | 0.1560 | 0.0204 | 10.47 | 172.10 |
| 1.00 | 2,048 | 0.0030 | 20 | 0.2377 | 0.0174 | 10.47 | 167.80 |
| 1.00 | 2,048 | 0.0100 | 20 | 0.2735 | 0.0177 | 10.47 | 169.00 |
| 3.00 | 512 | 0.0010 | 20 | 0.1713 | 0.0156 | 2.75 | 47.90 |
| 3.00 | 512 | 0.0030 | 20 | 0.2516 | 0.0156 | 2.75 | 48.00 |
| 3.00 | 512 | 0.0100 | 20 | 0.2784 | 0.0167 | 2.75 | 47.80 |
| 3.00 | 2,048 | 0.0010 | 20 | 0.1754 | 0.0157 | 10.47 | 168.60 |
| 3.00 | 2,048 | 0.0030 | 20 | 0.2553 | 0.0156 | 10.47 | 170.60 |
| 3.00 | 2,048 | 0.0100 | 20 | 0.2827 | 0.0167 | 10.47 | 167.70 |
| 10.00 | 512 | 0.0010 | 20 | 0.1807 | 0.0154 | 2.75 | 51.20 |
| 10.00 | 512 | 0.0030 | 20 | 0.2623 | 0.0154 | 2.75 | 50.80 |
| 10.00 | 512 | 0.0100 | 20 | 0.2880 | 0.0155 | 2.75 | 50.70 |
| 10.00 | 2,048 | 0.0010 | 20 | 0.1871 | 0.0154 | 10.47 | 167.40 |
| 10.00 | 2,048 | 0.0030 | 20 | 0.2649 | 0.0154 | 10.47 | 172.10 |
| 10.00 | 2,048 | 0.0100 | 20 | 0.2966 | 0.0155 | 10.47 | 171.10 |

**Chosen:** clip 10, expected batch 2048, learning rate 0.01, 20 local steps per round, hold-out AUPRC 0.2966.

Non-private FedAvg on the same hold-out: AUPRC 0.4139; the chosen DP setting reaches 0.7167 of it.

The choice lies on the grid's edge in: clip, batch, lr. A19 allows one retune only, so the edge is reported, not extended.
