"""Parse AMLworld pattern files and link schemes to transaction rows.

A pattern file is a sequence of blocks::

    BEGIN LAUNDERING ATTEMPT - FAN-OUT:  Max 16-degree Fan-Out
    2022/09/01 05:14,00952,8139F54E0,0111632,8062C56E0,5331.44,US Dollar,...,ACH,1
    ...
    END LAUNDERING ATTEMPT - FAN-OUT

Each block is one scheme: a single laundering attempt following one of the
eight generator patterns. Lines are in the transactions-CSV column order.
Schemes are numbered in file order (``scheme_id`` 0, 1, 2, ...).

Linking matches each pattern line to its transactions row on
:data:`finmesh.data.schema.LINK_KEY`. The report counts lines that match no
row, lines that match several identical rows, and transactions claimed by
more than one scheme, because each of these changes scheme-level metrics.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import polars as pl

from finmesh.data.ingest import normalise
from finmesh.data.schema import CANONICAL_COLUMNS, LINK_KEY, PATTERN_TYPES

_BEGIN = re.compile(r"^BEGIN LAUNDERING ATTEMPT\s*-\s*([A-Za-z\-]+)\s*(?::\s*(.*))?$")
_END = re.compile(r"^END LAUNDERING ATTEMPT")


@dataclass
class PatternParseReport:
    schemes: int = 0
    pattern_rows: int = 0
    unknown_pattern_names: list[str] = field(default_factory=list)
    unclosed_blocks: int = 0
    rows_outside_blocks: int = 0
    malformed_rows: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemes": self.schemes,
            "pattern_rows": self.pattern_rows,
            "unknown_pattern_names": sorted(set(self.unknown_pattern_names)),
            "unclosed_blocks": self.unclosed_blocks,
            "rows_outside_blocks": self.rows_outside_blocks,
            "malformed_rows": self.malformed_rows,
        }


def parse_pattern_file(path: Path) -> tuple[pl.DataFrame, PatternParseReport]:
    """Return one row per pattern-file transaction line, with scheme metadata."""
    report = PatternParseReport()
    records: dict[str, list[Any]] = {
        "scheme_id": [],
        "pattern": [],
        "pattern_detail": [],
        "line_no": [],
        **{c: [] for c in CANONICAL_COLUMNS},
    }
    scheme_id = -1
    pattern: str | None = None
    detail: str | None = None

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            begin = _BEGIN.match(text)
            if begin:
                if pattern is not None:
                    report.unclosed_blocks += 1
                scheme_id += 1
                pattern = begin.group(1).upper()
                detail = (begin.group(2) or "").strip() or None
                if pattern not in PATTERN_TYPES:
                    report.unknown_pattern_names.append(pattern)
                continue
            if _END.match(text):
                pattern, detail = None, None
                continue
            if pattern is None:
                report.rows_outside_blocks += 1
                continue
            cells = next(csv.reader([text]))
            if len(cells) != len(CANONICAL_COLUMNS):
                report.malformed_rows += 1
                continue
            records["scheme_id"].append(scheme_id)
            records["pattern"].append(pattern)
            records["pattern_detail"].append(detail)
            records["line_no"].append(line_no)
            for name, value in zip(CANONICAL_COLUMNS, cells, strict=True):
                records[name].append(value)
    if pattern is not None:
        report.unclosed_blocks += 1

    report.schemes = scheme_id + 1
    report.pattern_rows = len(records["line_no"])
    raw = pl.DataFrame(
        records,
        schema={
            "scheme_id": pl.Int64,
            "pattern": pl.String,
            "pattern_detail": pl.String,
            "line_no": pl.Int64,
            **{c: pl.String for c in CANONICAL_COLUMNS},
        },
    )
    rows = normalise(raw.lazy(), with_row_index=False).collect()
    return rows, report


def summarise_schemes(pattern_rows: pl.DataFrame) -> pl.DataFrame:
    """One row per scheme: pattern, size, accounts, banks and time span."""
    return (
        pattern_rows.group_by("scheme_id")
        .agg(
            pl.col("pattern").first(),
            pl.col("pattern_detail").first(),
            pl.len().alias("n_rows"),
            pl.concat_list("src_key", "dst_key")
            .explode(empty_as_null=False)
            .n_unique()
            .alias("n_accounts"),
            pl.concat_list("from_bank", "to_bank")
            .explode(empty_as_null=False)
            .unique()
            .sort()
            .alias("banks"),
            pl.col("timestamp").min().alias("start"),
            pl.col("timestamp").max().alias("end"),
        )
        .with_columns(pl.col("banks").list.len().alias("n_banks"))
        .sort("scheme_id")
    )


def link_schemes(
    transactions_parquet: Path, pattern_rows: pl.DataFrame
) -> tuple[pl.DataFrame, dict[str, Any]]:
    """Map pattern lines to ``tx_id`` values; return links and a linking report."""
    keyed = pattern_rows.with_row_index("pattern_row").select("pattern_row", "scheme_id", *LINK_KEY)
    tx = pl.scan_parquet(transactions_parquet).select("tx_id", "is_laundering", *LINK_KEY)
    joined = tx.join(keyed.lazy(), on=list(LINK_KEY), how="inner").collect(engine="streaming")

    per_line = joined.group_by("pattern_row").agg(pl.len().alias("matches"))
    matched_lines = per_line.height
    ambiguous_lines = per_line.filter(pl.col("matches") > 1).height

    links = joined.select("tx_id", "scheme_id").unique().sort(["scheme_id", "tx_id"])
    per_tx = links.group_by("tx_id").agg(pl.len().alias("schemes"))

    report: dict[str, Any] = {
        "pattern_rows": pattern_rows.height,
        "matched_pattern_rows": matched_lines,
        "unmatched_pattern_rows": pattern_rows.height - matched_lines,
        "ambiguous_pattern_rows": ambiguous_lines,
        "linked_transactions": links["tx_id"].n_unique(),
        "transactions_in_multiple_schemes": per_tx.filter(pl.col("schemes") > 1).height,
        "linked_rows_labelled_licit": int(
            joined.filter(pl.col("is_laundering") == 0)["tx_id"].n_unique()
        ),
        "schemes_with_no_linked_rows": int(
            pattern_rows["scheme_id"].n_unique() - links["scheme_id"].n_unique()
        ),
    }
    return links, report
