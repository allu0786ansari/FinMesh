# experiments/

The experiment runners live in the package and run from the command line (`uv run finmesh --help`):

| Experiment | Runner | Command |
| --- | --- | --- |
| X1–X3: sharing ladder, S3/PD sweeps, audit A1–A3 | `finmesh/training/x1.py` | `x1`, `test-x1` |
| X4: neural scorer, FedAvg, DP-SGD | `finmesh/training/x4.py` | `x4` |
| X5: privacy unit, degree cap, tuned DP | `finmesh/training/x5.py` | `x5`, `test-x5` |
| X6: attribution by sharing level | `finmesh/training/x6.py` | `x6` |
| X7: demo path latency, faults, probes | `finmesh/services/x7.py` | `x7` |
| A25: protected flag, benchmark, stronger detector, budget replay | `finmesh/training/flags.py`, `benchmark.py`, `txdetector.py`, `budget_replay.py` | `flag-frontier`, `benchmark`, `plus-validation`, `budget-replay` |

Frozen settings are in [`finmesh/schemas/`](../finmesh/schemas/) and [`docs/protocol/`](../docs/protocol/). The commands for every run are in [`docs/runlog/`](../docs/runlog/).
