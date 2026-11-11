#!/usr/bin/env bash
# Adds Viola to the app launcher and puts a `viola` command on PATH.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
icons="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
mkdir -p "$apps" "$icons" "$HOME/.local/bin"

python3 "$here/tools/icons.py" "${icons%/scalable/apps}"
sed "s|@APP@|$here/viola.py|" "$here/viola.desktop" > "$apps/viola.desktop"
ln -sf "$here/viola.py" "$HOME/.local/bin/viola"
chmod +x "$here/viola.py"

update-desktop-database "$apps" 2>/dev/null || true
gtk-update-icon-cache -q "${icons%/scalable/apps}" 2>/dev/null || true
kbuildsycoca6 2>/dev/null || true
echo "Installed. Open Viola from your app launcher, or run: viola"
