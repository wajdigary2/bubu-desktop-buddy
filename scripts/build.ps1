# Build a standalone Windows executable for Bubu Desktop Buddy.
#
#   powershell -ExecutionPolicy Bypass -File scripts\build.ps1
#
# Result: dist\BubuDesktopBuddy.exe

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

python -m pip install -r requirements-dev.txt
python tools/generate_icon.py

python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name BubuDesktopBuddy `
    --icon assets/icon.ico `
    --add-data "assets;assets" `
    --exclude-module tkinter `
    main.py

Write-Host ""
Write-Host "Done! Executable is in dist\BubuDesktopBuddy.exe" -ForegroundColor Green
