#!/usr/bin/env python3
"""Start uvicorn on 127.0.0.1:8010 and verify via GET /api/v1/health."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import backend_lifecycle_lib as bl


def main() -> int:
    parser = argparse.ArgumentParser(description="Start backend on port 8010 (Windows-friendly).")
    parser.add_argument(
        "--force-kill",
        "-f",
        action="store_true",
        help="If port is in use, terminate the listener PID before starting.",
    )
    parser.add_argument("--host", default=bl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=bl.DEFAULT_PORT)
    args = parser.parse_args()

    pid = bl.find_listener_pid(args.port)
    if pid is not None:
        print(f"[start_backend] Port {args.port} is in use by PID {pid}.")
        if not args.force_kill:
            print("[start_backend] Re-run with --force-kill to stop it and start a new server.")
            return 2
        print(f"[start_backend] Terminating PID {pid} (--force-kill)...")
        bl.terminate_pid(pid)
        bl.wait_until_port_free(args.port)

    if bl.find_listener_pid(args.port) is not None:
        print("[start_backend] Listener still present after kill.", file=sys.stderr)
        return 3

    print("[start_backend] Launching uvicorn (detached)...")
    proc = bl.start_uvicorn_detached(host=args.host, port=args.port)

    data = bl.poll_health_ready(host=args.host, port=args.port)
    if not data:
        err = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        if err.strip():
            print("[start_backend] uvicorn stderr tail:", file=sys.stderr)
            print(err[-2000:], file=sys.stderr)
        proc.poll()
        return 4

    rt = data.get("runtime") or {}
    print("[start_backend] OK - health response:")
    print(bl.format_runtime_summary(data))
    print(f"[start_backend] subprocess PID (launcher): {proc.pid}")
    print(f"[start_backend] backend process_pid (from health): {rt.get('process_pid')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
