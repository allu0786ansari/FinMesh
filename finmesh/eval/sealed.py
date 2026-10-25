"""The evaluation store and the sealed test (proposal Section 9, criterion CC2).

:class:`EvalStore` serves train and validation labels freely and refuses the
test partition. Test labels and test scheme tables come only from
:func:`open_sealed_test`, which:

1. hashes the frozen configuration being evaluated;
2. refuses a second opening for the same configuration hash and seed, unless
   ``allow_repeat`` is set (and even then the repeat is logged);
3. appends an entry to ``data/sealed/<ds>/access_log.jsonl`` (time, config
   hash, seed, purpose, git commit) **before** returning any data.

The seal protects the research protocol against mistakes; it is not access
control against a determined user. Its log is the evidence for CC2 at G4.
"""

from __future__ import annotations

import getpass
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from finmesh.eval.guard import LabelFrame
from finmesh.eval.provenance import git_commit
from finmesh.eval.split_io import load_plan
from finmesh.eval.universe import LABEL_VARIANTS, SEALED_PARTITIONS, EvalLayout, sealed_root
from finmesh.paths import DatasetPaths


class SealedTestError(PermissionError):
    """The test partition was requested outside the sealed entry point."""


def config_hash(config: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()


@dataclass(frozen=True)
class PartitionData:
    """Everything evaluation needs for one partition."""

    partition: str
    labels: LabelFrame
    scheme_windows: pl.DataFrame
    schemes: pl.DataFrame
    hours: float
    windows: tuple[int, int]

    @property
    def days(self) -> float:
        return self.hours / 24


def label_variant(frame: pl.DataFrame, variant: str) -> pl.DataFrame:
    """Universe rows with ``label`` and ``masked`` for the chosen variant (A9)."""
    if variant not in LABEL_VARIANTS:
        raise ValueError(f"label variant must be one of {LABEL_VARIANTS}")
    if variant == "primary":
        return frame
    return frame.with_columns(
        (pl.col("label").cast(pl.Boolean) | pl.col("incidental")).cast(pl.Int8).alias("label"),
        (pl.col("masked") & ~pl.col("incidental")).alias("masked"),
    )


class EvalStore:
    def __init__(self, paths: DatasetPaths, option: str = "B8") -> None:
        plan = load_plan(paths)
        self.paths = paths
        self.layout = EvalLayout(paths, plan.window_hours, option)
        if not self.layout.meta.exists():
            raise FileNotFoundError(
                f"{self.layout.meta} missing; run `finmesh labels --dataset {paths.name}` first"
            )
        self.meta: dict[str, Any] = json.loads(self.layout.meta.read_text())

    @property
    def window_hours(self) -> int:
        return int(self.meta["window_hours"])

    def accounts_per_member(self) -> pl.DataFrame:
        return pl.read_parquet(self.layout.accounts_per_member)

    def universe_keys(self, partition: str) -> pl.DataFrame:
        """Label-free account-windows to score: member, bank, account, window, tx.

        Prefer ``partition(p).labels.keys()`` when the labels are loaded anyway:
        it shares memory with them and keeps the row order the fast join expects.
        """
        self._refuse_sealed(partition)
        return self._read(partition).select("member", "bank", "account", "window", "tx")

    def partition(self, partition: str, variant: str = "primary") -> PartitionData:
        """Labels and scheme tables; ``variant`` "touch" is the A9 sensitivity label."""
        self._refuse_sealed(partition)
        return self._load(partition, variant)

    def _refuse_sealed(self, partition: str) -> None:
        if partition in SEALED_PARTITIONS:
            raise SealedTestError(
                f"the {partition!r} partition is sealed; use finmesh.eval.sealed.open_sealed_test"
            )

    def _read(self, partition: str) -> pl.DataFrame:
        return pl.read_parquet(self.layout.partition_dir(partition) / "universe_*.parquet")

    def _load(self, partition: str, variant: str = "primary") -> PartitionData:
        if variant not in LABEL_VARIANTS:
            raise ValueError(f"label variant must be one of {LABEL_VARIANTS}")
        d = self.layout.partition_dir(partition)
        win = self.meta["partition_windows"][partition]
        frame = self._read(partition)
        scheme_windows = pl.read_parquet(d / "scheme_windows.parquet")
        if "incidental" not in frame.columns:
            raise FileNotFoundError(
                "labels predate amendment A9; rebuild them with "
                f"`finmesh labels --dataset {self.paths.name}`"
            )
        if variant == "touch":
            frame = frame.with_columns(
                (pl.col("label").cast(pl.Boolean) | pl.col("incidental"))
                .cast(pl.Int8)
                .alias("label"),
                (pl.col("masked") & ~pl.col("incidental")).alias("masked"),
            )
        else:
            scheme_windows = scheme_windows.filter(~pl.col("incidental"))
        return PartitionData(
            partition=partition,
            labels=LabelFrame(frame, partition),
            scheme_windows=scheme_windows.drop("incidental"),
            schemes=pl.read_parquet(d / "schemes.parquet"),
            hours=float(self.meta["partition_hours"][partition]),
            windows=(int(win[0]), int(win[1])),
        )


def access_log_path(paths: DatasetPaths) -> Path:
    return sealed_root(paths) / "access_log.jsonl"


def read_access_log(paths: DatasetPaths) -> list[dict[str, Any]]:
    path = access_log_path(paths)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def open_sealed_test(
    store: EvalStore,
    config: dict[str, Any],
    seed: int,
    purpose: str,
    allow_repeat: bool = False,
    variant: str = "primary",
) -> PartitionData:
    """The only way to read test labels. Logs first, then returns the data."""
    digest = config_hash({**config, "label_variant": variant})
    log = read_access_log(store.paths)
    previous = [e for e in log if e["config_hash"] == digest and e["seed"] == seed]
    if previous and not allow_repeat:
        raise SealedTestError(
            f"test already opened for config {digest[:12]} and seed {seed} "
            f"on {previous[0]['time']}; each frozen configuration is evaluated once per seed"
        )
    entry = {
        "time": datetime.now(UTC).isoformat(timespec="seconds"),
        "dataset": store.paths.name,
        "option": store.meta["option"],
        "config_hash": digest,
        "seed": seed,
        "purpose": purpose,
        "repeat": bool(previous),
        "label_variant": variant,
        "git_commit": git_commit(),
        "user": getpass.getuser(),
    }
    path = access_log_path(store.paths)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(entry) + "\n")
    return store._load("test", variant)
