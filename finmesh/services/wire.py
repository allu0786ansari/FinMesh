"""JSON wire format for the allowlisted messages (demo path).

Every message is checked against the allowlist (:func:`finmesh.sharing.messages.check`)
before it is encoded and again after it is decoded, so the HTTP path enforces exactly the
policy of the in-process bus. Bytes travel as lower-case hex. Decoding is strict: the type
must be the one the endpoint expects, the field set must match exactly, and every value
must have its declared type; anything else is rejected.
"""

from __future__ import annotations

from dataclasses import MISSING, fields
from typing import Any, TypeVar

from finmesh.sharing.messages import (
    ALLOWLIST,
    EvidenceRecordWire,
    MessageRejected,
    check,
)

T = TypeVar("T")
_BY_NAME = {cls.__name__: cls for cls in ALLOWLIST}


def _enc(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, tuple):
        return [_enc(v) for v in value]
    if isinstance(value, EvidenceRecordWire):
        return encode(value)["body"]
    return value


def encode(message: Any) -> dict[str, Any]:
    """``{"type": name, "body": {field: value}}`` for an allowlisted message."""
    check(message)
    return {
        "type": type(message).__name__,
        "body": {f.name: _enc(getattr(message, f.name)) for f in fields(message)},
    }


def _bytes(value: Any, name: str) -> bytes:
    if not isinstance(value, str):
        raise MessageRejected(f"{name}: expected hex text")
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise MessageRejected(f"{name}: not hex") from exc


def _int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MessageRejected(f"{name}: expected an integer")
    return value


def _dec(kind: str, value: Any, name: str) -> Any:
    kind = kind.replace(" ", "")
    if kind == "int":
        return _int(value, name)
    if kind == "bool":
        if not isinstance(value, bool):
            raise MessageRejected(f"{name}: expected true or false")
        return value
    if kind == "str":
        if not isinstance(value, str):
            raise MessageRejected(f"{name}: expected text")
        return value
    if kind == "bytes":
        return _bytes(value, name)
    if kind in ("tuple[bytes,...]", "tuple[int,...]"):
        if not isinstance(value, list):
            raise MessageRejected(f"{name}: expected a list")
        inner = "bytes" if "bytes" in kind else "int"
        return tuple(_dec(inner, v, name) for v in value)
    if kind == "EvidenceRecordWire|None":
        return None if value is None else _decode_body(EvidenceRecordWire, value)
    raise MessageRejected(f"{name}: unsupported field type {kind}")


def _decode_body(cls: type[T], body: Any) -> T:
    if not isinstance(body, dict):
        raise MessageRejected("body must be an object")
    declared = {f.name: f for f in fields(cls)}  # type: ignore[arg-type]
    required = {
        n for n, f in declared.items() if f.default is MISSING and f.default_factory is MISSING
    }
    if not set(body) <= set(declared) or not required <= set(body):
        raise MessageRejected(f"{cls.__name__}: unexpected or missing fields")
    values = {n: _dec(str(declared[n].type), v, n) for n, v in body.items()}
    message = cls(**values)
    check(message)
    return message


def decode(data: Any, expected: type[T]) -> T:
    """The message in ``data``, which must be of type ``expected``."""
    if not isinstance(data, dict) or set(data) != {"type", "body"}:
        raise MessageRejected("expected {type, body}")
    if data["type"] != expected.__name__ or data["type"] not in _BY_NAME:
        raise MessageRejected(f"expected {expected.__name__}, got {data['type']!r}")
    return _decode_body(expected, data["body"])


__all__ = ["decode", "encode"]
