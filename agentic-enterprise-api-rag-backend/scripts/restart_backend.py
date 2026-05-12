#!/usr/bin/env python3
"""stop_backend + start_backend; verify health runtime PID changes when possible."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import backend_lifecycle_lib as bl


def main() -> int:
    parser = argparse.ArgumentParser(description="Restart backend on 8010.")
    parser.add_argument("--host", default=bl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=bl.DEFAULT_PORT)
    args = parser.parse_args()

    old_pid = None
    try:
        prev = bl.fetch_health_json(args.host, args.port)
        old_pid = (prev.get("runtime") or {}).get("process_pid")
        print(f"[restart_backend] Previous runtime process_pid: {old_pid}")
    except Exception as exc:
        print(f"[restart_backend] No prior health (or backend down): {exc}")

    stop_py = Path(__file__).resolve().parent / "stop_backend.py"
    r = subprocess.run([sys.executable, str(stop_py), "--port", str(args.port)], timeout=60)
    if r.returncode != 0:
        print("[restart_backend] stop_backend reported issues (continuing).", file=sys.stderr)

    start_py = Path(__file__).resolve().parent / "start_backend.py"
    r2 = subprocess.run(
        [sys.executable, str(start_py), "--force-kill", "--host", args.host, "--port", str(args.port)],
        timeout=120,
    )
    if r2.returncode != 0:
        print("[restart_backend] start_backend failed.", file=sys.stderr)
        return r2.returncode

    try:
        new = bl.fetch_health_json(args.host, args.port)
        new_pid = (new.get("runtime") or {}).get("process_pid")
        print(f"[restart_backend] New runtime process_pid: {new_pid}")
        if old_pid is not None and new_pid is not None:
            if old_pid != new_pid:
                print("[restart_backend] Verified: process_pid changed after restart.")
            else:
                print(
                    "[restart_backend] Warning: process_pid unchanged — unusual; confirm single instance.",
                    file=sys.stderr,
                )
    except Exception as exc:
        print(f"[restart_backend] Could not read health after restart: {exc}", file=sys.stderr)
        return 5

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
