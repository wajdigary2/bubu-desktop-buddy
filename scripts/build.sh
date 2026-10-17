#!/usr/bin/env bash
# Build a standalone Linux executable for Bubu Desktop Buddy.
#
#   ./scripts/build.sh
#
# Result: dist/BubuDesktopBuddy
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -x "$ROOT/.venv/bin/python" ]; then
    PY="$ROOT/.venv/bin/python"
else
    PY="$(command -v python3)"
fi

"$PY" -m pip install -r requirements-dev.txt
"$PY" tools/generate_icon.py

"$PY" -m PyInstaller --noconfirm --clean --onefile --windowed \
    --name BubuDesktopBuddy \
    --icon assets/icon.png \
    --add-data "assets:assets" \
    --exclude-module tkinter \
    main.py

echo ""
echo "Done! Executable is in dist/BubuDesktopBuddy"
