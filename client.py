"""Compatibility import for users of the original repository layout."""

from pmwhale.client import (
    CLOB_API,
    DATA_API,
    GAMMA_API,
    MAX_HOLDERS_LIMIT,
    MAX_TRADES,
    PolyClient,
)

__all__ = [
    "CLOB_API",
    "DATA_API",
    "GAMMA_API",
    "MAX_HOLDERS_LIMIT",
    "MAX_TRADES",
    "PolyClient",
]
