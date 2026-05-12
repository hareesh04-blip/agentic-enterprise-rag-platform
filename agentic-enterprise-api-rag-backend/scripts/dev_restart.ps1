# Developer helper: restart backend on 127.0.0.1:8010.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $here "..")
python scripts/restart_backend.py @args
