"""
Step 45.1 — List FastAPI routes (method + path) for route alignment checks.

Run from backend root:
  python scripts/list_routes.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_ROOT = str(Path(__file__).resolve().parents[1])
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from fastapi.routing import APIRoute  # noqa: E402

from app.main import app  # noqa: E402


def main() -> None:
    rows: list[tuple[str, str]] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        methods = sorted(m for m in (route.methods or set()) if m not in {"HEAD", "OPTIONS"})
        method_str = ",".join(methods) if methods else "-"
        rows.append((method_str, route.path))

    rows.sort(key=lambda x: x[1])
    print(f"Total APIRoutes: {len(rows)}")
    print("-" * 90)
    print(f"{'METHODS':<16} PATH")
    print("-" * 90)
    for method_str, path in rows:
        print(f"{method_str:<16} {path}")


if __name__ == "__main__":
    main()

