"""A throwaway home folder with a stand-in claude, and Viola's backend running in it.

Importing this sets it all up, so it has to come before anything imports server.
"""

import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAKE = ROOT / "tests" / "fake_claude.py"
HOME = Path(tempfile.mkdtemp(prefix="viola-test-"))
LOG = HOME / "claude-log.jsonl"
BIN = HOME / "bin"
WINDOWS = sys.platform == "win32"

BIN.mkdir()
if WINDOWS:
    # A .cmd file, like the one npm installs claude as, so arguments also pass through cmd's quoting.
    (BIN / "claude.cmd").write_text(f'@"{sys.executable}" "{FAKE}" %*\r\n')
else:
    (BIN / "claude").write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE}" "$@"\n')
    (BIN / "claude").chmod(0o755)
os.environ.update(
    HOME=str(HOME), USERPROFILE=str(HOME), APPDATA=str(HOME / "AppData"), XDG_DATA_HOME=str(HOME / "data"),
    CLAUDE_CONFIG_DIR=str(HOME / ".claude"), VIOLA_TEST_LOG=str(LOG), PATH=str(BIN) + os.pathsep + os.environ["PATH"],
)
for name in ("VIOLA_API_KEY", "ANTHROPIC_API_KEY"):
    os.environ.pop(name, None)
sys.path.insert(0, str(ROOT))

import server  # noqa: E402

app = server.App()
httpd = server.make_server(app, "127.0.0.1", 0)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"


def close():
    app.shutdown()
    httpd.shutdown()
    shutil.rmtree(HOME, ignore_errors=True)
