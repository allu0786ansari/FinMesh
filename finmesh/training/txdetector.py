"""A25 P6 adequacy track: the stronger detector (S0+, S2+, oracle+).

The P6 adequacy rule was triggered on HI-Medium (our account-window detector, mapped to
transactions, was 14.5 F1 points below LightGBM + graph features on the benchmark's
validation split). The transaction model that beat the published results on the same split
(benchmark model B) becomes the detector of an extra track in the Large confirmation.

**Unit.** One row per (transaction, side held at the scoring bank): the transaction's own
fields, the role (sender or receiver), the own account's account-window features, and the
counterparty's features *when the bank can see them*:

- **S0+ (one model per member, member view):** the counterparty's member-view features only
  when the counterparty is held at the same member; otherwise missing. Each member trains
  on its own rows.
- **oracle+ (one pooled model, pooled view):** both accounts' pooled features, always.

**Account-window score:** the largest score among the account's rows in the window. It then
enters the ladder exactly where the account-window LightGBM did (calibration on the end of
training, A13 alerts, records, sharing levels, stackers, the relational oracle).

**Training labels:** the transaction's laundering flag in the training partition, after the
burn-in, with G0's evaluation mask applied (legs of schemes assigned to another partition,
and gaps, are left out, as in the account-window labels). Negatives are subsampled at
``NEGATIVE_RATE`` by a fixed hash of the transaction id and weighted back. Early stopping
on the end of training, as for every other model. Scoring reads no label.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import lightgbm as lgb
import numpy as np
import polars as pl

from finmesh.data.lowmem import hashed_key
from finmesh.features.build import FeatureStore
from finmesh.models.gbdt import EARLY_STOPPING, MAX_ROUNDS, PARAMS
from finmesh.paths import DatasetPaths
from finmesh.training.data import SAMPLE_SALT

NEGATIVE_RATE = 0.05
OWN: tuple[str, ...] = (
    "log_amount_paid",
    "log_amount_received",
    "payment_currency_code",
    "receiving_currency_code",
    "payment_format_code",
    "cross_currency",
    "same_bank",
    "self_transfer",
    "hour",
    "weekday",
    "role",
    "cp_local",
)
CATEGORICAL = ("payment_currency_code", "receiving_currency_code", "payment_format_code")


def columns(cols: tuple[str, ...]) -> tuple[str, ...]:
    return (*OWN, *(f"own_{c}" for c in cols), *(f"cp_{c}" for c in cols))


def codes(paths: DatasetPaths) -> dict[str, dict[str, int]]:
    lf = pl.scan_parquet(paths.transactions)
    cur = pl.concat(
        [
            lf.select(pl.col("payment_currency").alias("c")),
            lf.select(pl.col("receiving_currency").alias("c")),
        ]
    )
    cs = sorted(str(c) for c in cur.unique().collect(engine="streaming")["c"].drop_nulls())
    fs = lf.select("payment_format").unique().collect(engine="streaming")["payment_format"]
    return {
        "currency": {c: i for i, c in enumerate(cs)},
        "format": {f: i for i, f in enumerate(sorted(str(f) for f in fs.drop_nulls()))},
    }


def partition_tx(
    paths: DatasetPaths,
    plan: Any,
    partition: str,
    membership: pl.DataFrame,
    code: dict[str, dict[str, int]],
    with_target: bool,
) -> pl.DataFrame:
    """One partition's transactions with both sides' accounts and members (label-free unless
    ``with_target``, which is used for the training partition only)."""
    split = pl.scan_parquet(paths.parquet / f"split_w{plan.window_hours}.parquet").filter(
        pl.col("partition").cast(pl.String) == partition
    )
    mem = membership.lazy()
    ts = pl.col("timestamp")
    sel = [
        "tx_id",
        hashed_key("src_key").alias("src"),
        hashed_key("dst_key").alias("dst"),
        "from_bank",
        "to_bank",
        pl.col("amount_paid").log1p().cast(pl.Float32).alias("log_amount_paid"),
        pl.col("amount_received").log1p().cast(pl.Float32).alias("log_amount_received"),
        pl.col("payment_currency")
        .replace_strict(code["currency"], default=-1, return_dtype=pl.Int16)
        .alias("payment_currency_code"),
        pl.col("receiving_currency")
        .replace_strict(code["currency"], default=-1, return_dtype=pl.Int16)
        .alias("receiving_currency_code"),
        pl.col("payment_format")
        .replace_strict(code["format"], default=-1, return_dtype=pl.Int16)
        .alias("payment_format_code"),
        (pl.col("payment_currency") != pl.col("receiving_currency"))
        .cast(pl.Int8)
        .alias("cross_currency"),
        (pl.col("from_bank") == pl.col("to_bank")).cast(pl.Int8).alias("same_bank"),
        (pl.col("src_key") == pl.col("dst_key")).cast(pl.Int8).alias("self_transfer"),
        ts.dt.hour().cast(pl.Int8).alias("hour"),
        ts.dt.weekday().cast(pl.Int8).alias("weekday"),
    ]
    tx = pl.scan_parquet(paths.transactions)
    if with_target:
        sel.append(pl.col("is_laundering").cast(pl.Int8).alias("y"))
    keep = ["tx_id", "window"] + (["eval_mask"] if with_target else [])
    return (
        tx.select(sel)
        .join(split.select(keep), on="tx_id", how="inner")
        .join(
            mem.select(pl.col("bank").alias("from_bank"), pl.col("member").alias("src_member")),
            on="from_bank",
            how="left",
        )
        .join(
            mem.select(pl.col("bank").alias("to_bank"), pl.col("member").alias("dst_member")),
            on="to_bank",
            how="left",
        )
        .drop("from_bank", "to_bank")
        .with_columns(pl.col("window").cast(pl.Int32))
        .sort("window", "tx_id")
        .collect(engine="streaming")
    )


def sides(tx: pl.DataFrame) -> pl.DataFrame:
    """Two rows per transaction: the sender's view and the receiver's."""
    base = [c for c in tx.columns if c not in ("src", "dst", "src_member", "dst_member")]
    a = tx.select(
        *base,
        pl.col("src").alias("own"),
        pl.col("src_member").alias("own_member"),
        pl.col("dst").alias("cp"),
        pl.col("dst_member").alias("cp_member"),
        pl.lit(0, pl.Int8).alias("role"),
    )
    b = tx.select(
        *base,
        pl.col("dst").alias("own"),
        pl.col("dst_member").alias("own_member"),
        pl.col("src").alias("cp"),
        pl.col("src_member").alias("cp_member"),
        pl.lit(1, pl.Int8).alias("role"),
    )
    return pl.concat([a, b]).with_columns(
        (pl.col("own_member") == pl.col("cp_member")).cast(pl.Int8).alias("cp_local")
    )


def attach(
    rows: pl.DataFrame, feats: pl.DataFrame, cols: tuple[str, ...], pooled: bool
) -> pl.DataFrame:
    """Own and counterparty account-window features. Member view: the counterparty's only
    when held at the same member (the join on the own member finds nothing otherwise)."""
    f = feats.select("member", "account", "window", *cols)
    own = f.rename({"account": "own", "member": "own_member", **{c: f"own_{c}" for c in cols}})
    out = rows.join(own, on=["own_member", "own", "window"], how="left", maintain_order="left")
    if pooled:
        cp = f.drop("member").rename({"account": "cp", **{c: f"cp_{c}" for c in cols}})
        return out.join(cp, on=["cp", "window"], how="left", maintain_order="left")
    cp = f.rename({"account": "cp", "member": "own_member", **{c: f"cp_{c}" for c in cols}})
    return out.join(cp, on=["own_member", "cp", "window"], how="left", maintain_order="left")


def _matrix(frame: pl.DataFrame, names: tuple[str, ...]) -> np.ndarray[Any, Any]:
    return frame.select(pl.col(list(names)).cast(pl.Float32)).to_numpy().astype(np.float32)


def _day_chunks(
    store: FeatureStore, partition: str, windows: list[int], per_day: int, cols: tuple[str, ...]
) -> Iterator[tuple[int, int, pl.DataFrame]]:
    files = sorted(store.layout.partition_dir(partition).glob("feat_*.parquet"))
    for d in sorted({w // per_day for w in windows}):
        w0, w1 = d * per_day, d * per_day + per_day - 1
        feats = (
            pl.scan_parquet(files)
            .filter(pl.col("window").is_between(w0, w1))
            .select("member", "account", "window", *cols)
            .collect()
        )
        yield w0, w1, feats


@dataclass
class TxDetector:
    """S0+ (``pooled`` False: one model per member) or oracle+ (one pooled model)."""

    paths: DatasetPaths
    plan: Any
    store: FeatureStore
    cols: tuple[str, ...]
    membership: pl.DataFrame
    pooled: bool
    seed: int
    models: dict[int, lgb.Booster] = field(default_factory=dict)  # -1: the pooled model
    info: dict[str, Any] = field(default_factory=dict)
    _code: dict[str, dict[str, int]] | None = None

    @property
    def names(self) -> tuple[str, ...]:
        return columns(self.cols)

    def code(self) -> dict[str, dict[str, int]]:
        if self._code is None:
            self._code = codes(self.paths)
        return self._code

    def _rows(
        self,
        partition: str,
        with_target: bool,
        w_from: int | None = None,
        sample: float | None = None,
    ) -> Iterator[pl.DataFrame]:
        """Side rows with features, a window at a time (bounded memory)."""
        tx = partition_tx(
            self.paths, self.plan, partition, self.membership, self.code(), with_target
        )
        if w_from is not None:
            tx = tx.filter(pl.col("window") >= w_from)
        if with_target:
            tx = tx.filter(~pl.col("eval_mask").fill_null(True)).drop("eval_mask")
        if sample is not None:
            u = pl.col("tx_id").hash(seed=SAMPLE_SALT + self.seed).cast(pl.Float64) / 2.0**64
            tx = tx.filter((pl.col("y") == 1) | (u < sample))
        per_day = 24 // self.plan.window_hours
        ws = tx["window"].unique().sort().to_list()
        for w0, w1, feats in _day_chunks(self.store, partition, ws, per_day, self.cols):
            day = sides(tx.filter(pl.col("window").is_between(w0, w1)))
            for w in range(w0, w1 + 1):
                part = day.filter(pl.col("window") == w)
                if part.height:
                    yield attach(part, feats.filter(pl.col("window") == w), self.cols, self.pooled)
            del day, feats

    def fit(self, windows: Any, progress: Callable[[str], None] = lambda _m: None) -> TxDetector:
        """Train on the training partition after the burn-in; stop on its end."""
        parts: dict[str, list[Any]] = {"fit": [], "stop": []}
        for rows in self._rows("train", True, windows.burn_in, NEGATIVE_RATE):
            y = rows["y"].to_numpy().astype(np.int8)
            late = rows["window"].to_numpy() >= windows.stop_from
            x = _matrix(rows, self.names)
            mem = rows["own_member"].fill_null(-1).to_numpy()
            for k, m in (("fit", ~late), ("stop", late)):
                parts[k].append((x[m], y[m], mem[m]))
        data = {}
        for k in ("fit", "stop"):
            xs, ys, ms = zip(*parts[k], strict=True)
            data[k] = (np.concatenate(xs), np.concatenate(ys), np.concatenate(ms))
        del parts
        groups = (
            [-1] if self.pooled else sorted(int(m) for m in np.unique(data["fit"][2]) if m >= 0)
        )
        for g in groups:
            fi = np.ones(len(data["fit"][1]), bool) if g == -1 else data["fit"][2] == g
            si = np.ones(len(data["stop"][1]), bool) if g == -1 else data["stop"][2] == g
            yf, ys = data["fit"][1][fi], data["stop"][1][si]
            if yf.sum() == 0 or ys.sum() == 0:
                continue  # as fit_local_models: a member without positives keeps no model
            wf = np.where(yf == 1, 1.0, 1.0 / NEGATIVE_RATE)
            wsv = np.where(ys == 1, 1.0, 1.0 / NEGATIVE_RATE)
            train = lgb.Dataset(
                data["fit"][0][fi],
                yf,
                weight=wf,
                feature_name=list(self.names),
                categorical_feature=list(CATEGORICAL),
                free_raw_data=True,
            )
            stop = lgb.Dataset(data["stop"][0][si], ys, weight=wsv, reference=train)
            self.models[g] = lgb.train(
                {**PARAMS, "seed": self.seed},
                train,
                num_boost_round=MAX_ROUNDS,
                valid_sets=[stop],
                callbacks=[lgb.early_stopping(EARLY_STOPPING, verbose=False)],
            )
            self.info[str(g)] = {
                "rounds": int(self.models[g].best_iteration or self.models[g].current_iteration()),
                "train_rows": int(fi.sum()),
                "train_positives": int(yf.sum()),
            }
            progress(
                f"{'oracle+' if self.pooled else f'S0+ member {g}'}: "
                f"{self.info[str(g)]['rounds']} rounds"
            )
        return self

    def table(self, partition: str, w_from: int | None = None) -> pl.DataFrame:
        """(account, window, score): the largest side score of each account-window."""
        out = []
        for rows in self._rows(partition, False, w_from):
            x = _matrix(rows, self.names)
            mem = rows["own_member"].fill_null(-1).to_numpy()
            s = np.zeros(rows.height, dtype=np.float64)
            for g, model in self.models.items():
                idx = np.ones(rows.height, bool) if g == -1 else mem == g
                if idx.any():
                    s[idx] = model.predict(x[idx], num_iteration=model.best_iteration)
            out.append(
                rows.select("own", "window")
                .with_columns(pl.Series("score", s))
                .group_by("own", "window")
                .agg(pl.col("score").max())
            )
        if not out:
            return pl.DataFrame(
                schema={"account": pl.UInt64, "window": pl.Int32, "score": pl.Float64}
            )
        return pl.concat(out).rename({"own": "account"})


class TableScorer:
    """A feature-frame scorer backed by account-window tables (the ladder's ``fn``). The
    partition is read from the frame's windows; each table is built on first use."""

    def __init__(
        self,
        detector: TxDetector,
        partition_windows: dict[str, tuple[int, int]],
        w_from: dict[str, int] | None = None,
    ) -> None:
        self.detector = detector
        self.ranges = partition_windows
        self.w_from = w_from or {}
        self.tables: dict[str, pl.DataFrame] = {}
        self.missing = 0

    def _partition(self, window: int) -> str:
        for name, (lo, hi) in self.ranges.items():
            if lo <= window <= hi:
                return name
        raise ValueError(f"window {window} is in no partition")

    def __call__(self, feat: pl.DataFrame) -> np.ndarray[Any, Any]:
        if feat.height == 0:
            return np.zeros(0)
        part = self._partition(int(feat["window"].min()))  # type: ignore[arg-type]
        if part not in self.tables:
            self.tables[part] = self.detector.table(part, self.w_from.get(part))
        s = feat.select("account", "window").join(
            self.tables[part], on=["account", "window"], how="left", maintain_order="left"
        )["score"]
        self.missing += s.null_count()
        return s.fill_null(0.0).to_numpy()

    def score(self, feat: pl.DataFrame) -> np.ndarray[Any, Any]:
        return self(feat)

    def release(self, partition: str) -> None:
        self.tables.pop(partition, None)


__all__ = ["NEGATIVE_RATE", "TableScorer", "TxDetector", "columns", "sides"]
