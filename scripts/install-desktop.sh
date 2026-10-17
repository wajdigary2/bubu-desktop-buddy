#!/usr/bin/env bash
# Install Bubu Desktop Buddy into the Ubuntu applications menu / app grid.
#
#   ./scripts/install-desktop.sh
#
# Installs a .desktop launcher into ~/.local/share/applications and the icon
# into the hicolor theme, so Bubu shows up when you search your apps.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APPS_DIR="$DATA_HOME/applications"
ICON_DIR="$DATA_HOME/icons/hicolor/256x256/apps"
DESKTOP_FILE="$APPS_DIR/bubu-desktop-buddy.desktop"

chmod +x "$ROOT/scripts/run.sh"
mkdir -p "$APPS_DIR" "$ICON_DIR"

install -m 644 "$ROOT/assets/icon.png" "$ICON_DIR/bubu-desktop-buddy.png"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Bubu Desktop Buddy
Comment=A tiny desktop companion that walks, naps and begs for snacks
Exec=$ROOT/scripts/run.sh
Icon=bubu-desktop-buddy
Terminal=false
Categories=Utility;
Keywords=pet;buddy;companion;
EOF

chmod 644 "$DESKTOP_FILE"

# Refresh the menu cache if the tooling is available.
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "Installed. Search for 'Bubu Desktop Buddy' in your app grid."
echo "Launcher: $DESKTOP_FILE"
