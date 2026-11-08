"""``finmesh paper-assets``: every figure and table of the paper, from the committed pages.

Writes ``docs/paper/figures/*.pdf|png``, ``docs/paper/tables/*.tex`` and
``docs/paper/assets.json`` (every number a figure or table shows, for checking).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finmesh.paper import figures, tables
from finmesh.paths import REPO_ROOT

PAPER = REPO_ROOT / "docs" / "paper"


def build_assets(out: Path = PAPER) -> dict[str, Any]:
    fig = figures.build(out / "figures")
    tab = tables.build(out / "tables", related=out / "static" / "tab_related.tex")
    numbers = {"figures": fig["numbers"], "tables": tab}
    (out / "assets.json").write_text(json.dumps(numbers, indent=1, default=str) + "\n")
    return {
        "figures": fig["files"],
        "tables": sorted(str(p) for p in (out / "tables").glob("*.tex")),
    }


__all__ = ["PAPER", "build_assets"]
