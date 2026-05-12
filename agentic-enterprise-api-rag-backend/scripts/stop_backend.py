#!/usr/bin/env python3
"""Stop process listening on TCP port 8010 (taskkill on Windows)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import backend_lifecycle_lib as bl


def main() -> int:
    parser = argparse.ArgumentParser(description="Stop backend listener on port 8010.")
    parser.add_argument("--port", type=int, default=bl.DEFAULT_PORT)
    args = parser.parse_args()

    pid = bl.find_listener_pid(args.port)
    if pid is None:
        print(f"[stop_backend] No LISTENING process found on port {args.port}.")
        if bl.is_port_open(bl.DEFAULT_HOST, args.port):
            print("[stop_backend] Warning: port accepts connections but PID unknown.", file=sys.stderr)
        return 0

    print(f"[stop_backend] Stopping PID {pid} on port {args.port}...")
    ok = bl.terminate_pid(pid)
    if not ok:
        print("[stop_backend] taskkill/kill returned non-zero.", file=sys.stderr)

    if bl.wait_until_port_free(args.port):
        print("[stop_backend] Port released.")
        return 0

    print("[stop_backend] Port may still be busy after timeout.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
