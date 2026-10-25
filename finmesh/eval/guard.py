"""Label guard (proposal criterion CC1: no label ever reaches scoring code).

Two layers:

* **Types.** Scoring and feature code accept a :class:`FeatureFrame`, whose
  constructor refuses any label-bearing column. Labels travel separately in a
  :class:`LabelFrame`, which only evaluation code joins to scores. mypy then
  rejects passing labels where features are expected.
* **Static check.** ``tests/contract/test_label_guard.py`` scans the source of
  the packages that build features, score or share evidence and fails if any
  of them names a label column.

The guard protects against mistakes, not against deliberate misuse.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import polars as pl

LABEL_COLUMNS: frozenset[str] = frozenset(
    {
        "is_laundering",
        "label",
        "masked",
        "eval_mask",
        "scheme_id",
        "pattern",
        "pattern_detail",
        "scheme_partition",
    }
)

# Packages whose code must never name a label column (checked statically).
LABEL_FREE_PACKAGES: tuple[str, ...] = (
    "finmesh/features",
    "finmesh/models",
    "finmesh/sharing",
    "finmesh/matching",
    "finmesh/fusion",
)

# Columns that identify an account-window; shared by features, scores and labels.
KEY_COLUMNS: tuple[str, ...] = ("member", "account", "window")


class LabelLeakError(RuntimeError):
    """A label-bearing column reached code that must be label-free."""


def label_columns_in(columns: Iterable[str]) -> list[str]:
    return sorted(c for c in columns if c in LABEL_COLUMNS or "launder" in c.lower())


def assert_label_free(columns: Iterable[str], where: str) -> None:
    leaked = label_columns_in(columns)
    if leaked:
        raise LabelLeakError(f"{where}: label columns {leaked} must not reach scoring code")


@dataclass(frozen=True)
class FeatureFrame:
    """Account-window features, guaranteed label-free at construction."""

    frame: pl.DataFrame

    def __post_init__(self) -> None:
        assert_label_free(self.frame.columns, "FeatureFrame")
        missing = [c for c in KEY_COLUMNS if c not in self.frame.columns]
        if missing:
            raise ValueError(f"FeatureFrame needs key columns {missing}")


@dataclass(frozen=True)
class ScoreFrame:
    """Scores for account-windows: key columns plus ``score``; label-free."""

    frame: pl.DataFrame

    def __post_init__(self) -> None:
        assert_label_free(self.frame.columns, "ScoreFrame")
        need = [*KEY_COLUMNS, "score"]
        missing = [c for c in need if c not in self.frame.columns]
        if missing:
            raise ValueError(f"ScoreFrame needs columns {missing}")


@dataclass(frozen=True)
class LabelFrame:
    """Account-window labels for one partition; only evaluation code reads it."""

    frame: pl.DataFrame
    partition: str

    def keys(self) -> pl.DataFrame:
        """Label-free view of the same rows (no copy): what a scorer may see."""
        cols = [c for c in self.frame.columns if c not in LABEL_COLUMNS]
        return self.frame.select(cols)

    def join_scores(self, scores: ScoreFrame) -> pl.DataFrame:
        """Scores with labels, for evaluation only. Unscored windows get score null.

        Fast path: scorers return rows in the order of :meth:`keys`, so when the
        key columns match row for row the score column is attached directly. A
        hash join on 30 M account-windows needs several GB; this needs none.
        """
        sf = scores.frame
        if sf.height == self.frame.height and all(
            self.frame[c].equals(sf[c], check_dtypes=False) for c in KEY_COLUMNS
        ):
            return self.frame.with_columns(sf["score"])
        return self.frame.join(sf.select(*KEY_COLUMNS, "score"), on=list(KEY_COLUMNS), how="left")
