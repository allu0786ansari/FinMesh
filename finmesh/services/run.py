"""Process entry points for the demo path's services (uvicorn factories).

The token service reads its configuration from the environment, so its secret seed and
the banks' keys never appear on a command line (where other users could read them):

* ``FINMESH_TOKEN_SEED``: 64 hex characters, the OPRF key seed;
* ``FINMESH_BANK_KEYS``: JSON object ``{"<bank>": "<hex key>"}``;
* ``FINMESH_TOKEN_BUDGET`` (optional): evaluations per bank and epoch.

Run it with ``uvicorn --factory finmesh.services.run:token_app_from_env``.
"""

from __future__ import annotations

import json
import os

from fastapi import FastAPI

from finmesh.matching.tokens import QUERY_BUDGET, TokenService
from finmesh.services.apps import token_app


def token_app_from_env() -> FastAPI:
    seed_hex = os.environ.get("FINMESH_TOKEN_SEED", "")
    if len(seed_hex) != 64:
        raise RuntimeError("FINMESH_TOKEN_SEED must be 64 hex characters")
    keys = {
        int(b): bytes.fromhex(k) for b, k in json.loads(os.environ["FINMESH_BANK_KEYS"]).items()
    }
    budget = int(os.environ.get("FINMESH_TOKEN_BUDGET", QUERY_BUDGET))
    return token_app(TokenService(seed=bytes.fromhex(seed_hex), budget=budget), keys)


__all__ = ["token_app_from_env"]
