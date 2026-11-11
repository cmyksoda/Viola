"""Builds Viola as a double-click app with Python inside: Viola.app on macOS, Viola.exe on Windows.

Needs `pip install -r requirements.txt pyinstaller pillow`. The result lands in packaging/build/dist.
"""

import os
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "packaging" / "build"


def data(source, target):
    return ["--add-data", f"{ROOT / source}{os.pathsep}{target}"]


args = [
    str(ROOT / "viola.py"),
    "--name", "Viola",
    "--windowed",
    "--noconfirm",
    "--clean",
    "--distpath", str(BUILD / "dist"),
    "--workpath", str(BUILD / "work"),
    "--specpath", str(BUILD),
    # Pillow turns the PNG into the .icns or .ico each system wants.
    "--icon", str(ROOT / "web" / "icon-512.png"),
    *data("web", "web"),
    *data("LICENSE", "."),
    *data("licenses", "licenses"),
]
if sys.platform == "darwin":
    args += ["--osx-bundle-identifier", "io.github.cmyksoda.viola"]
elif sys.platform == "win32":
    # One file to download and double-click, with nothing to unzip.
    args += ["--onefile"]

PyInstaller.__main__.run(args)
