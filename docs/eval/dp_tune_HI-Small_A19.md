# DP hyperparameters on the proxy federation · HI-Small · A19

Amendment A19: FedAvg with DP-SGD at ε = 3 (window unit, seed 0, 50 rounds; 20 local steps per round for every setting, so every setting takes the same 1,000 updates and a larger batch costs more compute) for every setting in the grid, scored by AUPRC on this federation's training hold-out (18,815 rows, 417 positives). The best setting is written to `finmesh/schemas/dp_hparams.json` and used unchanged on the Medium set of the same regime; no Medium data is used here. Total 2,295 s, peak memory 565 MB.

| Clip norm | Expected batch | Learning rate | Local steps per round | Hold-out AUPRC | Share clipped | Noise multiplier | Seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1.00 | 512 | 0.0010 | 20 | 0.4158 | 0.0322 | 3.56 | 51.10 |
| 1.00 | 512 | 0.0030 | 20 | 0.5737 | 0.0325 | 3.56 | 51.20 |
| 1.00 | 512 | 0.0100 | 20 | 0.6409 | 0.0374 | 3.56 | 51.70 |
| 1.00 | 2,048 | 0.0010 | 20 | 0.4219 | 0.0323 | 13.80 | 200.60 |
| 1.00 | 2,048 | 0.0030 | 20 | 0.5763 | 0.0329 | 13.80 | 201.00 |
| 1.00 | 2,048 | 0.0100 | 20 | 0.6409 | 0.0376 | 13.80 | 198.00 |
| 3.00 | 512 | 0.0010 | 20 | 0.4427 | 0.0270 | 3.56 | 50.00 |
| 3.00 | 512 | 0.0030 | 20 | 0.5971 | 0.0302 | 3.56 | 48.70 |
| 3.00 | 512 | 0.0100 | 20 | 0.6512 | 0.0357 | 3.56 | 49.20 |
| 3.00 | 2,048 | 0.0010 | 20 | 0.4482 | 0.0271 | 13.80 | 195.20 |
| 3.00 | 2,048 | 0.0030 | 20 | 0.5991 | 0.0305 | 13.80 | 202.00 |
| 3.00 | 2,048 | 0.0100 | 20 | 0.6483 | 0.0357 | 13.80 | 198.50 |
| 10.00 | 512 | 0.0010 | 20 | 0.4579 | 0.0267 | 3.56 | 50.00 |
| 10.00 | 512 | 0.0030 | 20 | 0.5911 | 0.0293 | 3.56 | 50.50 |
| 10.00 | 512 | 0.0100 | 20 | 0.6519 | 0.0316 | 3.56 | 51.60 |
| 10.00 | 2,048 | 0.0010 | 20 | 0.4606 | 0.0268 | 13.80 | 201.60 |
| 10.00 | 2,048 | 0.0030 | 20 | 0.5917 | 0.0296 | 13.80 | 204.70 |
| 10.00 | 2,048 | 0.0100 | 20 | 0.6505 | 0.0314 | 13.80 | 203.00 |

**Chosen:** clip 10, expected batch 512, learning rate 0.01, 20 local steps per round, hold-out AUPRC 0.6519.

Non-private FedAvg on the same hold-out: AUPRC 0.7176; the chosen DP setting reaches 0.9083 of it.

The choice lies on the grid's edge in: clip, lr. A19 allows one retune only, so the edge is reported, not extended.
