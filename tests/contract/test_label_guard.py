"""CC1, static half: label-free packages never name a label column.

Every module under the packages that build features, score, share evidence or
fuse incidents is parsed, and every string literal and attribute or variable
name is checked against the label columns. The runtime half is the
FeatureFrame / ScoreFrame constructors (tests/unit/test_universe_sealed.py).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from finmesh.eval.guard import LABEL_COLUMNS, LABEL_FREE_PACKAGES
from finmesh.paths import REPO_ROOT

MODULES = sorted(p for pkg in LABEL_FREE_PACKAGES for p in (REPO_ROOT / pkg).rglob("*.py"))


def _names(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.add(node.value)
        elif isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
        elif isinstance(node, ast.keyword) and node.arg:
            found.add(node.arg)
    return found


def test_label_free_packages_exist() -> None:
    assert MODULES, "no modules found; check LABEL_FREE_PACKAGES"


@pytest.mark.parametrize("module", MODULES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_module_names_no_label_column(module: Path) -> None:
    tree = ast.parse(module.read_text())
    leaked = sorted(n for n in _names(tree) if n in LABEL_COLUMNS or "launder" in n.lower())
    assert not leaked, f"{module.relative_to(REPO_ROOT)} names label columns {leaked}"
