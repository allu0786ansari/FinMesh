"""CC5, static half: bank-side code never names the token service's key material.

Bank-side modules are those a bank node runs: its node, evidence store,
request guard and message types, and the token *client*. None of them may
name the token service, key derivation, blind evaluation or a key pair, so a
bank process has no code path to a key. The orchestration module that wires
the in-process run (``finmesh/sharing/simulate.py``) is the deliberate
exception: it plays the network between the parties.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from finmesh.paths import REPO_ROOT

BANK_SIDE = sorted(
    p for p in (REPO_ROOT / "finmesh" / "sharing").glob("*.py") if p.name != "simulate.py"
)
FORBIDDEN = {
    "TokenService",
    "derive_key_pair",
    "generate_key_pair",
    "blind_evaluate",
    "KeyPair",
    "audit_evaluate",
    "secret",
    "_TokenService__keys",
    "_TokenService__seed",
}


def _names(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.Import):
            found.update(a.name.split(".")[-1] for a in node.names)
    return found


def test_bank_side_modules_exist() -> None:
    assert {p.name for p in BANK_SIDE} >= {"node.py", "evidence.py", "requests.py", "messages.py"}


@pytest.mark.parametrize("module", BANK_SIDE, ids=lambda p: p.name)
def test_bank_side_module_never_names_key_material(module: Path) -> None:
    leaked = _names(ast.parse(module.read_text())) & FORBIDDEN
    assert not leaked, f"{module.name} names {sorted(leaked)}"


def test_token_client_only_blinds_and_unblinds() -> None:
    tree = ast.parse((REPO_ROOT / "finmesh" / "matching" / "tokens.py").read_text())
    client = next(
        n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "TokenClient"
    )
    used = _names(client)
    assert {"blind", "finalize", "transport"} <= used
    assert not used & (FORBIDDEN - {"secret"}), "TokenClient must not touch the service's keys"
