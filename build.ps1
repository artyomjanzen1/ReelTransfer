$ErrorActionPreference = "Stop"

Write-Host "[1/3] Installing dependencies..."
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
& $venvPython -m pip install -r (Join-Path $projectRoot "requirements.txt")

Write-Host "[2/3] Building with PyInstaller..."
& $venvPython -m PyInstaller --noconfirm --clean (Join-Path $projectRoot "reeltransfer.spec")

Write-Host "[3/3] Done. Output in .\dist\reeltransfer"
