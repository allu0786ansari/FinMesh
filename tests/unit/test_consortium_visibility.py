from __future__ import annotations

import polars as pl
import pytest

from finmesh.data.consortium import (
    CANDIDATES,
    ConsortiumSpec,
    bank_sizes,
    build_membership,
    membership_summary,
)
from finmesh.data.visibility import (
    account_share,
    attach_members,
    coverage,
    leg_kind_expr,
    member_view,
    visible_members_expr,
)
from finmesh.paths import DatasetPaths


def _sizes() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "bank": [70, 1, 2, 3, 4, 5, 6],
            "accounts": [15, 900, 800, 400, 300, 200, 100],
            "tx_touching": [999_999, 10, 10, 10, 10, 10, 10],
        }
    )


def test_spec_parse_and_names() -> None:
    assert ConsortiumSpec.parse("b8") == ConsortiumSpec("B", 8)
    assert [c.name for c in CANDIDATES] == ["A8", "A16", "A32", "A64", "B4", "B8", "B16"]
    with pytest.raises(ValueError):
        ConsortiumSpec.parse("C4")


def test_option_a_ranks_by_accounts_not_volume() -> None:
    m = build_membership(_sizes(), ConsortiumSpec("A", 3))
    assert m["bank"].to_list() == [1, 2, 3]  # hub bank 70 is not picked first
    assert m["member"].to_list() == [0, 1, 2]


def test_option_b_balances_and_covers_every_bank() -> None:
    sizes = _sizes()
    m = build_membership(sizes, ConsortiumSpec("B", 2))
    assert set(m["bank"]) == set(sizes["bank"])
    loads = sizes.join(m, on="bank").group_by("member").agg(pl.col("accounts").sum())["accounts"]
    assert abs(loads[0] - loads[1]) <= 100  # greedy balance within one small bank
    summary = membership_summary(sizes, m)
    assert summary["banks"].sum() == sizes.height


def test_bank_sizes_count_distinct_accounts(
    fixture_paths: DatasetPaths, ingested: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    from finmesh.data import lowmem

    lf = pl.scan_parquet(fixture_paths.transactions)
    exact = (
        pl.concat(
            [
                lf.select(pl.col("from_bank").alias("bank"), pl.col("src_key").alias("k")),
                lf.select(pl.col("to_bank").alias("bank"), pl.col("dst_key").alias("k")),
            ]
        )
        .group_by("bank")
        .agg(pl.col("k").n_unique().alias("accounts"))
        .collect()
    )
    monkeypatch.setattr(lowmem, "KEYS_PER_SLICE", 700)  # force many slices
    sliced = bank_sizes(fixture_paths.transactions).select("bank", "accounts")
    assert sliced.sort("bank").equals(exact.sort("bank").cast({"accounts": pl.UInt32}))


def test_membership_is_deterministic(
    fixture_paths: DatasetPaths, ingested: dict[str, object]
) -> None:
    sizes = bank_sizes(fixture_paths.transactions)
    one = build_membership(sizes, ConsortiumSpec("B", 8))
    two = build_membership(bank_sizes(fixture_paths.transactions), ConsortiumSpec("B", 8))
    assert one.equals(two)
    assert sizes["rank"].to_list() == list(range(1, sizes.height + 1))


def _toy() -> pl.LazyFrame:
    return pl.LazyFrame(
        {
            "from_bank": [1, 1, 2, 9, 1],
            "to_bank": [1, 2, 9, 9, 9],
            "src_key": ["1:a", "1:a", "2:b", "9:x", "1:c"],
            "dst_key": ["1:c", "2:b", "9:x", "9:y", "9:y"],
        }
    )


def test_leg_kinds_and_views() -> None:
    membership = pl.DataFrame(
        {"bank": [1, 2], "member": [0, 1]}, schema={"bank": pl.Int64, "member": pl.Int32}
    )
    lf = attach_members(_toy(), membership)
    kinds = lf.select(leg_kind_expr().cast(pl.String)).collect().to_series().to_list()
    assert kinds == ["internal", "cross_member", "boundary", "invisible", "boundary"]

    view0 = member_view(lf, 0).collect()
    assert view0["side"].to_list() == ["internal", "out", "out"]
    view1 = member_view(lf, 1).collect()
    assert view1["side"].to_list() == ["in", "out"]
    # Member 1 never sees the 9 -> 9 transaction nor member 0's internal one.
    assert set(view1["src_key"]) == {"1:a", "2:b"}

    cov = coverage(lf)
    assert cov["rows_by_leg_kind"]["invisible"] == 1
    assert cov["visible_share"] == pytest.approx(4 / 5)
    # Accounts per bank: bank 1 holds a and c, bank 2 holds b, bank 9 holds x and y.
    sizes = pl.DataFrame({"bank": [1, 2, 9], "accounts": [2, 1, 2]})
    acc = account_share(sizes, membership)
    assert acc == {"accounts": 5, "member_accounts": 3, "member_account_share": 0.6}

    grouped = (
        lf.collect()
        .with_columns(pl.lit(1).alias("g"))
        .group_by("g")
        .agg(visible_members_expr().alias("m"))
    )
    assert grouped["m"].to_list() == [[0, 1]]
