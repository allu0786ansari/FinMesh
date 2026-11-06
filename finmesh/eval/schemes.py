"""Scheme-level outcomes and the random-alert baseline (proposal Section 9).

For each scheme in a partition, using only its account-windows in that
partition (other legs are masked):

* **detected**: at least one of its account-windows is alerted within the
  allowed delay (``delay_windows`` after its first window; ``None`` = anywhere
  in the partition);
* **time to detect**: hours from its first window to the first such alert;
* **linked**: at least two of its distinct accounts end up in one incident
  within the delay; **linked across members** when those accounts sit at two
  or more members. Linked detection is the primary RQ1 metric. Without an
  incident table every alert is its own incident, so nothing is linked:
  this is the honest S0 floor until fusion exists (week 7).

The random-alert baseline is computed exactly, not simulated: if member ``m``
alerts a share ``p_m`` of its account-windows at random, a scheme is detected
with probability ``1 - prod(1 - p_m)`` over its account-windows within the
delay.
"""

from __future__ import annotations

import polars as pl

KEYS = ["member", "account", "window"]


def _within_delay(
    sw: pl.DataFrame, schemes: pl.DataFrame, delay_windows: int | None
) -> pl.DataFrame:
    sw = sw.join(schemes.select("scheme_id", "first_window"), on="scheme_id", how="inner")
    if delay_windows is None:
        return sw
    return sw.filter(pl.col("window") <= pl.col("first_window") + delay_windows)


def scheme_outcomes(
    alerts: pl.DataFrame,
    scheme_windows: pl.DataFrame,
    schemes: pl.DataFrame,
    window_hours: int,
    delay_windows: int | None = None,
    incidents: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """One row per scheme: detected, time to detect, linked, linked across members."""
    sw = _within_delay(scheme_windows, schemes, delay_windows)
    alerted = alerts.filter(pl.col("alert")).select(*KEYS, pl.lit(True).alias("alert"))
    hit = sw.join(alerted, on=KEYS, how="left").with_columns(pl.col("alert").fill_null(False))
    detected = hit.group_by("scheme_id").agg(
        pl.col("alert").any().alias("detected"),
        pl.col("window").filter(pl.col("alert")).min().alias("first_alert_window"),
    )
    if incidents is None:
        linked = detected.select(
            "scheme_id", pl.lit(False).alias("linked"), pl.lit(False).alias("linked_cross_member")
        )
    else:
        joined = hit.filter(pl.col("alert")).join(incidents.select(*KEYS, "incident"), on=KEYS)
        # A25 P2: the window in which an incident first holds two of the scheme's accounts
        # (the second-earliest first alert among its accounts).
        first_seen = joined.group_by("scheme_id", "incident", "account").agg(
            pl.col("window").min().alias("w")
        )
        per_incident = (
            first_seen.group_by("scheme_id", "incident")
            .agg(
                pl.len().alias("accounts"),
                pl.col("w").sort().get(1, null_on_oob=True).alias("second_w"),
            )
            .join(
                joined.group_by("scheme_id", "incident").agg(
                    pl.col("member").n_unique().alias("members")
                ),
                on=["scheme_id", "incident"],
            )
        )
        linked = per_incident.group_by("scheme_id").agg(
            (pl.col("accounts") >= 2).any().alias("linked"),
            ((pl.col("accounts") >= 2) & (pl.col("members") >= 2))
            .any()
            .alias("linked_cross_member"),
            pl.col("accounts").max().alias("largest_incident_accounts"),
            pl.col("incident").n_unique().alias("incidents"),
            pl.col("second_w").min().alias("first_link_window"),
        )
    out = (
        schemes.select("scheme_id", "pattern", "members", "first_window")
        .join(detected, on="scheme_id", how="left")
        .join(linked, on="scheme_id", how="left")
        .with_columns(
            pl.col("detected", "linked", "linked_cross_member").fill_null(False),
            ((pl.col("first_alert_window") - pl.col("first_window")) * window_hours)
            .cast(pl.Float64)
            .alias("time_to_detect_h"),
        )
        .drop("first_alert_window")
    )
    if incidents is not None:  # A25 P2: case-quality columns (null where not defined)
        size = sw.group_by("scheme_id").agg(pl.col("account").n_unique().alias("scheme_accounts"))
        out = (
            out.join(size, on="scheme_id", how="left")
            .with_columns(
                (pl.col("largest_incident_accounts") / pl.col("scheme_accounts"))
                .cast(pl.Float64)
                .alias("completeness"),
                pl.col("incidents").cast(pl.Float64).alias("fragmentation"),
                ((pl.col("first_link_window") - pl.col("first_window")) * window_hours)
                .cast(pl.Float64)
                .alias("time_to_link_h"),
            )
            .with_columns(
                pl.when(pl.col("linked")).then(pl.col("time_to_link_h")).alias("time_to_link_h")
            )
            .drop("largest_incident_accounts", "incidents", "first_link_window", "scheme_accounts")
        )
    else:
        out = out.with_columns(
            pl.lit(None, pl.Float64).alias("completeness"),
            pl.lit(None, pl.Float64).alias("fragmentation"),
            pl.lit(None, pl.Float64).alias("time_to_link_h"),
        )
    return out.sort("scheme_id")


def alert_rates(alerts: pl.DataFrame) -> pl.DataFrame:
    """Realised share of account-windows alerted, per member."""
    return alerts.group_by("member").agg(pl.col("alert").mean().alias("rate"))


def random_detection_probability(
    scheme_windows: pl.DataFrame,
    schemes: pl.DataFrame,
    rates: pl.DataFrame,
    delay_windows: int | None = None,
) -> pl.DataFrame:
    """Exact probability that random alerting at ``rates`` detects each scheme."""
    sw = _within_delay(scheme_windows, schemes, delay_windows).join(rates, on="member", how="left")
    per = sw.group_by("scheme_id").agg(
        (1.0 - (1.0 - pl.col("rate").fill_null(0.0)).log().sum().exp()).alias("p_detect")
    )
    return (
        schemes.select("scheme_id")
        .join(per, on="scheme_id", how="left")
        .with_columns(pl.col("p_detect").fill_null(0.0))
    )
