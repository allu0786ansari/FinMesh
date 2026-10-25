"""Account-level features: behaviour, first-hop graph and history (week 4).

An account's own legs are all visible to the member holding it, so these
features need nothing beyond the account's rows. They are computed one hash
slice of accounts at a time (``account % slices == i``): every leg of an
account falls in the same slice, so history features stay exact while
memory stays bounded.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from finmesh.features.edges import FORMATS

DIR_OUT, DIR_IN = 0, 1


def legs_for_slice(
    edges: Path, membership: pl.DataFrame, slices: int, i: int, sub: int = 1, j: int = 0
) -> pl.DataFrame:
    """Both sides of every edge whose own account falls in slice ``i`` (sub-slice ``j``).

    Sub-slices split a slice further by ``(account // slices) % sub``, so a
    slice can be processed in parts with every account's legs kept together.

    Columns: account, member, bank, cp, cp_bank, cp_member, dir, usd, ccy,
    xccy, fmt, timestamp, window.
    """
    e = pl.scan_parquet(edges)
    common = ("fmt", "timestamp", "window")
    xccy = (pl.col("pay_ccy") != pl.col("recv_ccy")).alias("xccy")

    def mine(col: str) -> pl.Expr:
        key = pl.col(col)
        return (key % slices == i) & ((key // slices) % sub == j)

    out_side = e.filter(mine("src")).select(
        pl.col("src").alias("account"),
        pl.col("from_bank").alias("bank"),
        pl.col("dst").alias("cp"),
        pl.col("to_bank").alias("cp_bank"),
        pl.lit(DIR_OUT, pl.Int8).alias("dir"),
        pl.col("usd_paid").alias("usd"),
        pl.col("pay_ccy").alias("ccy"),
        xccy,
        *common,
    )
    in_side = e.filter(mine("dst")).select(
        pl.col("dst").alias("account"),
        pl.col("to_bank").alias("bank"),
        pl.col("src").alias("cp"),
        pl.col("from_bank").alias("cp_bank"),
        pl.lit(DIR_IN, pl.Int8).alias("dir"),
        pl.col("usd_received").alias("usd"),
        pl.col("recv_ccy").alias("ccy"),
        xccy,
        *common,
    )
    m = membership.lazy()
    return (
        pl.concat([out_side, in_side])
        .join(m, on="bank", how="inner")
        .join(
            m.select(pl.col("bank").alias("cp_bank"), pl.col("member").alias("cp_member")),
            on="cp_bank",
            how="left",
        )
        .collect(engine="streaming")
    )


def _share(cond: pl.Expr, among: pl.Expr) -> pl.Expr:
    return cond.filter(among).mean()


def account_features(
    legs: pl.DataFrame, delay_tolerance_h: float = 24.0, history: int = 12
) -> pl.DataFrame:
    """One row per (account, window) with behaviour, graph and history features.

    ``history`` is the history span in windows (schema ``history_hours`` / window length).
    """
    selfx = pl.col("account") == pl.col("cp")
    other = ~selfx
    out_ = pl.col("dir") == DIR_OUT
    in_ = pl.col("dir") == DIR_IN
    usd = pl.col("usd")
    key = ["account", "window"]

    base = legs.group_by(key).agg(
        pl.col("member").first(),
        pl.col("bank").first(),
        (out_ & other).sum().alias("tx_out"),
        (in_ & other).sum().alias("tx_in"),
        (out_ & selfx).sum().alias("self_tx"),
        usd.filter(out_ & other).sum().alias("amt_out"),
        usd.filter(in_ & other).sum().alias("amt_in"),
        usd.filter(out_ & other).max().fill_null(0).alias("amt_out_max"),
        usd.filter(in_ & other).max().fill_null(0).alias("amt_in_max"),
        ((pl.col("timestamp").max() - pl.col("timestamp").min()).dt.total_minutes() / 60).alias(
            "active_span_h"
        ),
        pl.col("ccy").n_unique().alias("currencies_n"),
        pl.col("xccy").mean().alias("cross_currency_share"),
        usd.is_null().mean().alias("unconvertible_share"),
        *[
            (pl.col("fmt") == i).mean().alias(f"fmt_{name.lower().replace(' ', '_')}_share")
            for i, name in enumerate(FORMATS)
        ],
        pl.col("cp").filter(out_ & other).n_unique().alias("fan_out"),
        pl.col("cp").filter(in_ & other).n_unique().alias("fan_in"),
        _share(pl.col("cp_bank") != pl.col("bank"), other).alias("cross_bank_share"),
        _share(
            pl.col("cp_member").is_not_null() & (pl.col("cp_member") != pl.col("member")),
            other,
        ).alias("cross_member_share"),
        _share(pl.col("cp_member").is_null(), other).alias("outside_share"),
        pl.len().alias("legs"),
        usd.sum().alias("amt_all"),
    )
    base = base.with_columns(
        (pl.col("amt_in") - pl.col("amt_out")).alias("amt_net"),
        (
            pl.min_horizontal("amt_in", "amt_out")
            / pl.when(pl.max_horizontal("amt_in", "amt_out") > 0).then(
                pl.max_horizontal("amt_in", "amt_out")
            )
        ).alias("pass_through"),
    )
    return (
        base.join(_hhi(legs.filter(other)), on=key, how="left")
        .join(_delays(legs.filter(other), delay_tolerance_h), on=key, how="left")
        .join(_new_counterparties(legs.filter(other), history), on=key, how="left")
        .join(_history(base, history), on=key, how="left")
        .with_columns(pl.col("new_cp_n").fill_null(0))
    )


def _hhi(legs: pl.DataFrame) -> pl.DataFrame:
    """Herfindahl index of amounts across counterparties, per direction."""
    per_cp = legs.group_by("account", "window", "dir", "cp").agg(pl.col("usd").sum())
    total = pl.col("usd").sum().over("account", "window", "dir")
    hhi = (
        per_cp.with_columns((pl.col("usd") / pl.when(total > 0).then(total)).alias("s"))
        .group_by("account", "window", "dir")
        .agg(pl.when(pl.col("s").is_not_null().any()).then((pl.col("s") ** 2).sum()).alias("hhi"))
    )
    return (
        hhi.filter(pl.col("dir") == DIR_OUT)
        .select("account", "window", pl.col("hhi").alias("out_amount_hhi"))
        .join(
            hhi.filter(pl.col("dir") == DIR_IN).select(
                "account", "window", pl.col("hhi").alias("in_amount_hhi")
            ),
            on=["account", "window"],
            how="full",
            coalesce=True,
        )
    )


def _delays(legs: pl.DataFrame, tolerance_h: float) -> pl.DataFrame:
    """Per outbound leg, hours since the latest inbound leg at or before it."""
    outs = legs.filter(pl.col("dir") == DIR_OUT).select("account", "window", "timestamp")
    ins = legs.filter(pl.col("dir") == DIR_IN).select("account", pl.col("timestamp").alias("t_in"))
    if outs.height == 0 or ins.height == 0:
        return pl.DataFrame(
            schema={
                "account": pl.UInt64,
                "window": pl.Int32,
                "in_out_delay_min_h": pl.Float64,
                "in_out_delay_med_h": pl.Float64,
            }
        )
    joined = outs.sort("timestamp").join_asof(
        ins.sort("t_in"),
        left_on="timestamp",
        right_on="t_in",
        by="account",
        strategy="backward",
        tolerance=f"{int(tolerance_h * 60)}m",
        check_sortedness=False,  # sorted globally by time, hence within every account
    )
    delay = (pl.col("timestamp") - pl.col("t_in")).dt.total_minutes() / 60
    return (
        joined.filter(pl.col("t_in").is_not_null())
        .with_columns(delay.alias("d"))
        .group_by("account", "window")
        .agg(
            pl.col("d").min().alias("in_out_delay_min_h"),
            pl.col("d").median().alias("in_out_delay_med_h"),
        )
    )


def _new_counterparties(legs: pl.DataFrame, history: int) -> pl.DataFrame:
    """Counterparties not seen by the account in the previous ``history`` windows.

    For each (account, counterparty) pair, the previous window in which it
    occurred; the pair is new in window w when there is none, or it is more
    than ``history`` windows back. Depends only on windows up to w.
    """
    pairs = legs.select("account", "cp", "window").unique().sort("account", "cp", "window")
    prev = pl.col("window").shift(1).over("account", "cp")
    new = prev.is_null() | (pl.col("window") - prev > history)
    return (
        pairs.with_columns(new.alias("new"))
        .group_by("account", "window")
        .agg(pl.col("new").sum().alias("new_cp_n"), pl.col("new").mean().alias("new_cp_share"))
    )


def _history(base: pl.DataFrame, history: int) -> pl.DataFrame:
    """Activity relative to the account's previous ``history`` windows (causal).

    Every output depends only on windows [w - history, w], so it means the
    same in every period once ``history`` windows have passed.
    """
    span = f"{history}i"
    h = (
        base.select("account", "window", "legs", "amt_all")
        .sort("account", "window")
        .with_columns(pl.lit(1, pl.Int64).alias("one"))
    )

    def prior(col: str) -> pl.Expr:
        return pl.col(col).rolling_sum_by("window", window_size=span, closed="left").over("account")

    gap = pl.col("window") - pl.col("window").shift(1).over("account")
    h = h.with_columns(
        pl.when(gap <= history).then(gap).otherwise(history + 1).alias("recency_windows"),
        prior("one").alias("prior_active_windows"),
        (prior("legs") / history).alias("prior_leg_rate"),
        (prior("amt_all") / history).alias("prior_amt_rate"),
    )
    return h.select(
        "account",
        "window",
        "recency_windows",
        "prior_active_windows",
        "prior_leg_rate",
        (pl.col("legs").log1p() - pl.col("prior_leg_rate").log1p()).alias("legs_vs_history"),
        (pl.col("amt_all").log1p() - pl.col("prior_amt_rate").log1p()).alias("amt_vs_history"),
    )
