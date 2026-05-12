#!/usr/bin/env python3
"""GET /api/v1/health and print runtime summary; exit 1 if unavailable."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import backend_lifecycle_lib as bl


def main() -> int:
    parser = argparse.ArgumentParser(description="Print backend runtime from GET /health.")
    parser.add_argument("--host", default=bl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=bl.DEFAULT_PORT)
    parser.add_argument("--json", action="store_true", help="Print full JSON response.")
    args = parser.parse_args()

    try:
        data = bl.fetch_health_json(args.host, args.port)
    except Exception as exc:
        print(f"[check_backend_runtime] Backend not reachable: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(bl.format_runtime_summary(data))

    rt = data.get("runtime") or {}
    if not rt.get("build_version") and not rt.get("process_pid"):
        print("[check_backend_runtime] Health OK but missing runtime block (stale build?).", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
