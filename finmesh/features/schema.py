"""Feature schemas, frozen in ``finmesh/schemas/features_v<N>.json`` (week 4).

The JSON file is the contract between the extractor and every model: names,
order, dtypes, families and definitions. Its SHA-256 is pinned by a test, so
a change to the file fails CI until it is released as a new version.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import polars as pl

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"
SCHEMA_VERSION = 2
KEYS: tuple[str, ...] = ("member", "account", "window")
FAMILIES: tuple[str, ...] = ("behaviour", "graph", "history", "neighbourhood")

_DTYPES: dict[str, pl.DataType] = {"u32": pl.UInt32(), "f32": pl.Float32()}


@dataclass(frozen=True)
class FeatureSchema:
    version: int
    features: tuple[dict[str, str], ...]
    params: dict[str, Any]
    sha256: str

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(f["name"] for f in self.features)

    def dtype(self, name: str) -> pl.DataType:
        return _DTYPES[next(f["dtype"] for f in self.features if f["name"] == name)]

    def family(self, family: str) -> tuple[str, ...]:
        return tuple(f["name"] for f in self.features if f["family"] == family)

    def counts(self) -> tuple[str, ...]:
        return tuple(f["name"] for f in self.features if f["dtype"] == "u32")

    def cast(self, frame: pl.DataFrame) -> pl.DataFrame:
        """Keys then features in schema order, with schema dtypes."""
        return frame.select(
            *KEYS, *[pl.col(n).cast(self.dtype(n), strict=False) for n in self.names]
        )


def schema_path(version: int = SCHEMA_VERSION) -> Path:
    return SCHEMA_DIR / f"features_v{version}.json"


@cache
def load_schema(version: int = SCHEMA_VERSION) -> FeatureSchema:
    raw = schema_path(version).read_bytes()
    doc = json.loads(raw)
    return FeatureSchema(
        version=int(doc["version"]),
        features=tuple(doc["features"]),
        params=dict(doc["params"]),
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def render_schema(schema: FeatureSchema | None = None) -> str:
    """Human-readable copy of the schema file (``docs/protocol/features_v<N>.md``)."""
    schema = schema or load_schema()
    doc = json.loads(schema_path(schema.version).read_text())
    changes = f"changes_from_v{schema.version - 1}"
    lines = [
        f"# Feature schema v{schema.version}",
        "",
        f"Generated from `finmesh/schemas/features_v{schema.version}.json` "
        f"(SHA-256 `{schema.sha256[:16]}`); the JSON file is authoritative.",
        "",
        *(
            [f"**Changes from v{schema.version - 1}:** {doc[changes]}", ""]
            if changes in doc
            else []
        ),
        f"**Unit:** {doc['unit']}. **Keys:** "
        + ", ".join(f"`{k['name']}` ({k['definition']})" for k in doc["keys"])
        + ".",
        "",
        "## Parameters",
        "",
        *[f"- `{k}`: {v}" for k, v in schema.params.items()],
        "",
        "## Conventions",
        "",
        *[f"- {c}" for c in doc["conventions"]],
    ]
    for family in FAMILIES:
        lines += ["", f"## {family.capitalize()}", "", "| Feature | Type | Definition |"]
        lines.append("| --- | --- | --- |")
        lines += [
            f"| `{f['name']}` | {f['dtype']} | {f['definition']} |"
            for f in schema.features
            if f["family"] == family
        ]
    return "\n".join(lines) + "\n"
