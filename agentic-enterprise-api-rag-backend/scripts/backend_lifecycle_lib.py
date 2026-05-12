"""
Shared helpers for backend lifecycle scripts (Step 53).
Primary target: Windows (netstat / taskkill). Limited POSIX support for PID discovery.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8010
HEALTH_PATH = "/api/v1/health"


def health_url(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> str:
    return f"http://{host}:{port}{HEALTH_PATH}"


def is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_windows_netstat_line_for_port(line: str, port: int) -> int | None:
    # e.g. TCP    127.0.0.1:8010         0.0.0.0:0              LISTENING       24700
    if "LISTENING" not in line.upper():
        return None
    if f":{port}" not in line:
        return None
    parts = line.split()
    if not parts:
        return None
    try:
        return int(parts[-1])
    except ValueError:
        return None


def find_listener_pid(port: int = DEFAULT_PORT) -> int | None:
    """Best-effort PID for process listening on TCP port (Windows netstat)."""
    if sys.platform == "win32":
        try:
            proc = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            for line in (proc.stdout or "").splitlines():
                pid = _parse_windows_netstat_line_for_port(line, port)
                if pid is not None:
                    return pid
        except Exception:
            return None
        return None

    # POSIX: try lsof
    try:
        proc = subprocess.run(
            ["lsof", "-i", f"TCP:{port}", "-sTCP:LISTEN", "-t"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return int(proc.stdout.strip().split()[0])
    except Exception:
        pass
    return None


def terminate_pid(pid: int) -> bool:
    if sys.platform == "win32":
        r = subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return r.returncode == 0
    r = subprocess.run(["kill", "-9", str(pid)], capture_output=True, text=True, timeout=30)
    return r.returncode == 0


def wait_until_port_free(port: int = DEFAULT_PORT, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if find_listener_pid(port) is None and not is_port_open(DEFAULT_HOST, port):
            return True
        time.sleep(0.3)
    return find_listener_pid(port) is None and not is_port_open(DEFAULT_HOST, port)


def fetch_health_json(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, timeout: float = 10.0) -> dict[str, Any]:
    url = health_url(host, port)
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def format_runtime_summary(data: dict[str, Any]) -> str:
    rt = data.get("runtime") or {}
    lines = [
        f"status:           {data.get('status', 'N/A')}",
        f"BUILD_VERSION:    {rt.get('build_version', 'N/A')}",
        f"process_pid:      {rt.get('process_pid', 'N/A')}",
        f"process_start:    {rt.get('process_start_time', 'N/A')}",
        f"uptime_s:         {rt.get('backend_uptime_seconds', 'N/A')}",
        f"llm_provider:     {rt.get('llm_provider', 'N/A')}",
        f"embedding_provider: {rt.get('embedding_provider', 'N/A')}",
        f"vector_collection: {rt.get('active_vector_collection', 'N/A')}",
    ]
    return "\n".join(lines)


def poll_health_ready(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    attempts: int = 60,
    delay: float = 0.5,
) -> dict[str, Any] | None:
    last_err: str | None = None
    for _ in range(attempts):
        try:
            return fetch_health_json(host, port)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            last_err = str(exc)
            time.sleep(delay)
    print(f"[lifecycle] Health poll failed after {attempts} attempts: {last_err}", file=sys.stderr)
    return None


def start_uvicorn_detached(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> subprocess.Popen[Any]:
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    return subprocess.Popen(
        cmd,
        cwd=str(BACKEND_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        env=os.environ.copy(),
    )
