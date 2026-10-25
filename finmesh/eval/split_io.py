"""Read the frozen split plan written by ``finmesh g0`` (``split_plan.json``)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from finmesh.data.splits import ObservationWindow, Period, SplitPlan
from finmesh.paths import DatasetPaths


def _dt(text: str) -> datetime:
    return datetime.fromisoformat(text)


def plan_from_dict(d: dict[str, object]) -> SplitPlan:
    ow = d["observation"]
    assert isinstance(ow, dict)
    observation = ObservationWindow(
        start=_dt(ow["start"]),
        end=_dt(ow["end"]),
        dense_days=int(ow["dense_days"]),
        median_daily_rows=float(ow["median_daily_rows"]),
        rows_in_window=int(ow["rows_in_window"]),
        rows_before=int(ow["rows_before"]),
        rows_after=int(ow["rows_after"]),
        laundering_rows_after=int(ow["laundering_rows_after"]),
    )
    periods = d["periods"]
    assert isinstance(periods, list)
    return SplitPlan(
        window_hours=int(str(d["window_hours"])),
        observation=observation,
        periods=tuple(Period(p["name"], _dt(p["start"]), _dt(p["end"])) for p in periods),
    )


def plan_path(paths: DatasetPaths) -> Path:
    return paths.parquet / "split_plan.json"


def load_plan(paths: DatasetPaths) -> SplitPlan:
    path = plan_path(paths)
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run `finmesh g0 --dataset {paths.name}` first")
    return plan_from_dict(json.loads(path.read_text()))
