# Build the tode Windows installer (tode-setup.exe).
#
#   powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
#
# Requires: Python 3.12 on PATH, and Inno Setup (iscc) for the installer step.
# Output: dist\tode\  (bundle) and packaging\Output\tode-setup.exe
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist)  { Remove-Item -Recurse -Force dist }

pyinstaller packaging\tode.spec --noconfirm

# Wrap the one-dir bundle in the Inno Setup wizard, if iscc is available.
$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if ($iscc) {
    & $iscc.Source packaging\tode_installer.iss
    Write-Host "Built: packaging\Output\tode-setup.exe"
} else {
    Write-Warning "Inno Setup (iscc) not found — bundle is in dist\tode\ but no installer was produced."
    Write-Warning "Install Inno Setup from https://jrsoftware.org/isdl.php and re-run."
}
