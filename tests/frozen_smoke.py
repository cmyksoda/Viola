"""Starts a built Viola app (`frozen_smoke.py PATH`) as a backend in a throwaway home, and checks it serves the page."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

app = Path(sys.argv[1]).resolve()
home = Path(tempfile.mkdtemp(prefix="viola-frozen-"))
env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), APPDATA=str(home / "AppData"),
           XDG_DATA_HOME=str(home / "data"))
for name in ("VIOLA_API_KEY", "ANTHROPIC_API_KEY"):
    env.pop(name, None)

# The same folder the app will pick on this system, with a spare port in its settings.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.update(env)
import server  # noqa: E402

with socket.socket() as probe:
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
folder = server.data_dir()
folder.mkdir(parents=True)
(folder / "config.json").write_text(json.dumps({"port": port, "token": "smoke"}))

proc = subprocess.Popen([str(app), "--server-only"], env=env)
try:
    deadline = time.time() + 60
    while True:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=2) as resp:
                assert json.load(resp)["app"] == "viola"
            break
        except OSError:
            if time.time() > deadline or proc.poll() is not None:
                sys.exit(f"the app never answered (exit code {proc.poll()})")
            time.sleep(1)
    for path in ("/", "/app.js", "/fonts/win95-sans.woff2"):
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as resp:
            assert resp.status == 200, path
    print("the built app serves Viola")
finally:
    if sys.platform == "win32":
        # A one-file build runs the app in a child process, which outlives a plain kill.
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    proc.kill()
    proc.wait()
