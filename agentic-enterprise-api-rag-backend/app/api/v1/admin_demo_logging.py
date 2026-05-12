"""Shared logging prefix for admin/demo read endpoints (unexpected errors only)."""

from __future__ import annotations

import logging

ADMIN_DEMO_PREFIX = "[admin.demo]"


def log_demo_endpoint_failure(logger: logging.Logger, operation: str) -> None:
    """Call from an ``except`` block; records stack trace with a stable prefix."""
    logger.exception("%s Unhandled error in %s", ADMIN_DEMO_PREFIX, operation)
