#!/usr/bin/env python3
"""Installs web/icon.svg (or the SVG given second) as Viola's icon in a hicolor folder (the one given), with its PNG sizes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server

server.install_icon(Path(sys.argv[2]) if len(sys.argv) > 2 else server.WEB_DIR / "icon.svg", Path(sys.argv[1]))
