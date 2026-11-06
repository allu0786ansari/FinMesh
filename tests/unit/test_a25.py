"""Amendment A25: improvements confirmed on fresh data (Large windows)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest


def test_window_rule_ends_at_the_dense_period() -> None:
    from finmesh.data.window import choose_window

    daily = {date(2022, 9, d): 1000 for d in range(1, 21)}
    daily[date(2022, 9, 21)] = 10  # sparse tail
    daily[date(2022, 9, 22)] = 5
    assert choose_window(daily, 16) == (date(2022, 9, 5), date(2022, 9, 20))
    with pytest.raises(ValueError):
        choose_window(daily, 25)


def test_cut_window_on_the_fixture(fixture_paths: Any, fixture_truth: object) -> None:
    from finmesh.data.window import cut_window

    raw_root = Path(fixture_paths.raw).parent
    r = cut_window(raw_root, "FIXTURE-Small", days=6)
    assert r["dataset"] == "FIXTURE-Small-W6"
    assert r["window"] == ["2022-09-05", "2022-09-10"]
    dst = raw_root / "FIXTURE-Small-W6"
    lines = (dst / "FIXTURE-Small-W6_Trans.csv").read_text().splitlines()
    assert lines[0].startswith("Timestamp") and len(lines) - 1 == r["transactions"]
    assert all("2022/09/05" <= x[:10] <= "2022/09/10" for x in lines[1:])
    pat = (dst / "FIXTURE-Small-W6_Patterns.txt").read_text()
    body = [x for x in pat.splitlines() if x and not x.startswith(("BEGIN", "END"))]
    assert body and all("2022/09/05" <= x[:10] <= "2022/09/10" for x in body)
    assert pat.count("BEGIN") == pat.count("END") == r["pattern_blocks"]["kept"]
    assert (dst / "FIXTURE-Small-W6_accounts.csv").exists()
    assert json.loads((dst / "window.json").read_text())["transactions"] == r["transactions"]


def test_case_quality_columns() -> None:
    import polars as pl

    from finmesh.eval.schemes import scheme_outcomes

    # Scheme 1: accounts 1, 2, 3 (windows 10, 11, 12); scheme 2: accounts 7, 8; scheme 3 undetected.
    sw = pl.DataFrame(
        {
            "scheme_id": [1, 1, 1, 2, 2, 3],
            "member": [0, 1, 2, 0, 1, 0],
            "account": [1, 2, 3, 7, 8, 9],
            "window": [10, 11, 12, 20, 21, 30],
        }
    )
    schemes = pl.DataFrame(
        {
            "scheme_id": [1, 2, 3],
            "pattern": ["FAN-OUT", "CYCLE", "STACK"],
            "members": [3, 2, 1],
            "first_window": [10, 20, 30],
        }
    )
    alerts = sw.select("member", "account", "window").with_columns(
        pl.Series("alert", [True, True, True, True, True, False])
    )
    incidents = pl.DataFrame(
        {
            "member": [0, 1, 2, 0, 1],
            "account": [1, 2, 3, 7, 8],
            "window": [10, 11, 12, 20, 21],
            "incident": [100, 100, 101, 200, 201],  # scheme 1 split in two; scheme 2 unlinked
        }
    )
    out = scheme_outcomes(alerts, sw, schemes, 6, 12, incidents).sort("scheme_id")
    r = out.to_dicts()
    assert r[0]["linked"] and r[0]["completeness"] == pytest.approx(2 / 3)
    assert r[0]["fragmentation"] == 2 and r[0]["time_to_link_h"] == 6.0  # second account, window 11
    assert not r[1]["linked"] and r[1]["completeness"] == 0.5 and r[1]["time_to_link_h"] is None
    assert r[2]["completeness"] is None and not r[2]["detected"]
    plain = scheme_outcomes(alerts, sw, schemes, 6, 12)
    assert plain["completeness"].null_count() == 3
