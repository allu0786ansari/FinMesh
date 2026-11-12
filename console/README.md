# console/

The analyst console and the privacy ledger are served by [`finmesh/services/console.py`](../finmesh/services/console.py) and [`finmesh/services/ledger.py`](../finmesh/services/ledger.py):

```bash
uv run finmesh console --dataset HI-Medium      # binds to 127.0.0.1 only
```

The console shows the alert queue, case cards, four-eyes approval for high-impact actions, and the privacy ledger. See [`docs/runlog/week-16.md`](../docs/runlog/week-16.md).
