# setup.ps1 — create venv and install dependencies
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

python -m venv venv
& .\venv\Scripts\pip install --upgrade pip
& .\venv\Scripts\pip install -r requirements.txt

Write-Host "Setup complete. Run: .\scripts\launch.ps1"