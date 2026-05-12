# Developer helper: start backend on 127.0.0.1:8010 (optional --force-kill).
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $here "..")
python scripts/start_backend.py @args
