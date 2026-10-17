#!/usr/bin/env bash
# Launch Bubu Desktop Buddy from a source checkout on Linux.
#
# Uses the project virtualenv at .venv if present, otherwise the system
# python3. This is the command the .desktop launcher points at.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -x "$ROOT/.venv/bin/python" ]; then
    PY="$ROOT/.venv/bin/python"
else
    PY="$(command -v python3)"
fi

# Bubu walks by moving his own frameless window, which pure Wayland does not
# allow. When XWayland is available, prefer its xcb backend so he can move.
if [ -z "${QT_QPA_PLATFORM:-}" ] \
    && [ -n "${WAYLAND_DISPLAY:-}" ] && [ -n "${DISPLAY:-}" ]; then
    export QT_QPA_PLATFORM=xcb
fi

cd "$ROOT"
exec "$PY" -m bubu "$@"
