# Step 54 — run Demo Stability Pack from backend repo root.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $here "..")
python scripts/demo_stability_check.py @args
