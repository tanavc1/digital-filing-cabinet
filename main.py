"""
Digital Filing Cabinet — Backward Compatibility Shim
=====================================================

All code has moved to the `core/` package.
This file re-exports the public API for any scripts that still import from `main`.

Prefer importing from `core` directly:
    from core import Config, RAGEngine, EvidenceContract

This shim will be removed in a future release.
"""
from core import Config, RAGEngine, EvidenceContract, DEFAULT_WORKSPACE_ID  # noqa: F401
from core.store import LanceStore  # noqa: F401
from core.utils import now_ts  # noqa: F401
