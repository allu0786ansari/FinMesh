"""Neighbourhood features on each member's visible graph (week 4).

For member m and window w, the graph is every distinct directed account pair
(src, dst) with a transaction that m can see (one end held at m) in windows
``w - lookback + 1 .. w``. Features are computed for m's accounts active in
w. Edges between two accounts held elsewhere are absent, so cycles and
2-paths that leave m's view are invisible: exactly the limitation that
evidence sharing (weeks 6–9) is meant to relieve.

Counting rules, with no self-loops:

* ``cyc2(a)``: accounts b with a->b and b->a;
* ``cyc3(a)``: pairs (b, c) with a->b->c->a, all distinct, b not a hub;
* ``cyc4(a)``: triples (b, c, d) with a->b->c->d->a, all distinct, b and d
  not hubs. From 2-path counts n_out(a, c) = #{b: a->b->c} and
  n_in(c, a) = #{d: c->d->a}: sum over c != a of
  n_out * n_in - #{b in both};
* ``sg_out_max(a)`` = max over c of n_out(a, c), ``sg_in_max(a)`` = max over
  c of n_in(c, a): scatter-gather from the source and sink side.

A hub has visible degree (distinct in- plus out-neighbours over the lookback)
above the cap. Hubs are never intermediates of a 2-path, which bounds the
work at (edges x cap) per window; hub contact is reported separately.
"""

from __future__ import annotations

import polars as pl

NEIGHBOURHOOD_COUNTS: tuple[str, ...] = (
    "nb_out_deg",
    "nb_in_deg",
    "gs_min_fan",
    "cyc2",
    "cyc3",
    "cyc4",
    "sg_out_max",
    "sg_in_max",
    "cp_in_deg_max",
    "cp_out_deg_max",
    "hub_neighbours",
)


def _count(df: pl.DataFrame, by: str, name: str) -> pl.DataFrame:
    return df.group_by(by).agg(pl.len().cast(pl.UInt32).alias(name)).rename({by: "a"})


def window_features(
    visible: pl.DataFrame, member: int, window: int, lookback: int, cap: int
) -> pl.DataFrame:
    """Neighbourhood features for ``member``'s accounts active in ``window``.

    ``visible``: edges m can see, columns src, dst, src_member, dst_member,
    window (self-loops already removed). Returns columns a, then
    :data:`NEIGHBOURHOOD_COUNTS`.
    """
    span = visible.filter(pl.col("window").is_between(window - lookback + 1, window))
    now = span.filter(pl.col("window") == window)
    active = (
        pl.concat(
            [
                now.filter(pl.col("src_member") == member).select(pl.col("src").alias("a")),
                now.filter(pl.col("dst_member") == member).select(pl.col("dst").alias("a")),
            ]
        )
        .unique()
        .sort("a")
    )
    if active.height == 0:
        return pl.DataFrame(schema={"a": pl.UInt64, **{c: pl.UInt32 for c in NEIGHBOURHOOD_COUNTS}})

    e = span.select("src", "dst").unique()
    out_deg = e.group_by("src").agg(pl.len().cast(pl.UInt32).alias("od")).rename({"src": "n"})
    in_deg = e.group_by("dst").agg(pl.len().cast(pl.UInt32).alias("id")).rename({"dst": "n"})
    deg = out_deg.join(in_deg, on="n", how="full", coalesce=True).with_columns(
        (pl.col("od").fill_null(0) + pl.col("id").fill_null(0)).alias("deg")
    )
    hubs = deg.filter(pl.col("deg") > cap).select("n")

    # Edges leaving / entering an active account, and edges usable as 2-path legs.
    from_a = e.join(active, left_on="src", right_on="a", how="semi")
    into_a = e.join(active, left_on="dst", right_on="a", how="semi")
    mid_out = e.join(hubs, left_on="src", right_on="n", how="anti")  # b -> c, b not a hub
    mid_in = e.join(hubs, left_on="dst", right_on="n", how="anti")  # c -> d, d not a hub

    p2_out = (
        from_a.rename({"src": "a", "dst": "b"})
        .join(mid_out.rename({"src": "b", "dst": "c"}), on="b")
        .filter(pl.col("c") != pl.col("a"))
    )
    p2_in = (
        mid_in.rename({"src": "c", "dst": "d"})
        .join(into_a.rename({"src": "d", "dst": "a"}), on="d")
        .filter(pl.col("c") != pl.col("a"))
    )

    cyc2 = _count(
        from_a.join(e.rename({"src": "dst", "dst": "src"}), on=["src", "dst"], how="semi"),
        "src",
        "cyc2",
    )
    cyc3 = _count(
        p2_out.join(e.rename({"src": "c", "dst": "a"}), on=["c", "a"], how="semi"), "a", "cyc3"
    )
    n_out = p2_out.group_by("a", "c").agg(pl.len().cast(pl.Int64).alias("n1"))
    n_in = p2_in.group_by("c", "a").agg(pl.len().cast(pl.Int64).alias("n2"))
    overlap = (
        p2_out.join(p2_in.rename({"d": "b"}), on=["a", "b", "c"])
        .group_by("a", "c")
        .agg(pl.len().cast(pl.Int64).alias("ov"))
    )
    cyc4 = (
        n_out.join(n_in, on=["a", "c"])
        .join(overlap, on=["a", "c"], how="left")
        .group_by("a")
        .agg(
            (pl.col("n1") * pl.col("n2") - pl.col("ov").fill_null(0))
            .sum()
            .cast(pl.UInt32)
            .alias("cyc4")
        )
    )
    sg_out = n_out.group_by("a").agg(pl.col("n1").max().cast(pl.UInt32).alias("sg_out_max"))
    sg_in = n_in.group_by("a").agg(pl.col("n2").max().cast(pl.UInt32).alias("sg_in_max"))
    cp_in = (
        from_a.join(in_deg, left_on="dst", right_on="n")
        .group_by("src")
        .agg(pl.col("id").max().alias("cp_in_deg_max"))
        .rename({"src": "a"})
    )
    cp_out = (
        into_a.join(out_deg, left_on="src", right_on="n")
        .group_by("dst")
        .agg(pl.col("od").max().alias("cp_out_deg_max"))
        .rename({"dst": "a"})
    )
    neighbours = pl.concat(
        [
            from_a.select(pl.col("src").alias("a"), pl.col("dst").alias("n")),
            into_a.select(pl.col("dst").alias("a"), pl.col("src").alias("n")),
        ]
    ).unique()
    hub_nb = _count(neighbours.join(hubs, on="n", how="semi"), "a", "hub_neighbours")

    out = active.join(deg.select(pl.col("n").alias("a"), "od", "id"), on="a", how="left")
    for part in (cyc2, cyc3, cyc4, sg_out, sg_in, cp_in, cp_out, hub_nb):
        out = out.join(part, on="a", how="left")
    out = out.rename({"od": "nb_out_deg", "id": "nb_in_deg"}).with_columns(
        pl.col(c).fill_null(0).cast(pl.UInt32) for c in NEIGHBOURHOOD_COUNTS if c != "gs_min_fan"
    )
    return out.with_columns(
        pl.min_horizontal("nb_in_deg", "nb_out_deg").alias("gs_min_fan")
    ).select("a", *NEIGHBOURHOOD_COUNTS)
