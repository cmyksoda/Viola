"""Local HTTP + SSE backend that drives `claude -p` turns for the Viola chat UI."""

import base64
import gzip
import hmac
import json
import mimetypes
import mmap
import os
import queue
import re
import secrets
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode, urlparse

import sessions

WINDOWS = sys.platform == "win32"
MACOS = sys.platform == "darwin"
LINUX = sys.platform.startswith("linux")


def data_dir():
    if WINDOWS:
        return Path(os.environ.get("APPDATA") or Path.home() / "AppData/Roaming") / "Viola"
    if MACOS:
        return Path.home() / "Library/Application Support/Viola"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "viola"


APP_DIR = Path(__file__).resolve().parent
# Resolved because a macOS app bundle keeps web/ behind a symlink, and serve_static compares resolved paths.
WEB_DIR = (APP_DIR / "web").resolve()
DATA_DIR = data_dir()
CONV_DIR = DATA_DIR / "conversations"
CONFIG_PATH = DATA_DIR / "config.json"
SESSIONS_CACHE = DATA_DIR / "sessions-cache.json"
VERBS_CACHE = DATA_DIR / "verbs-cache.json"
UPLOAD_DIR = DATA_DIR / "uploads"

DEFAULT_PORT = 47817
RESULT_PREVIEW_LIMIT = 30000
SAVE_INTERVAL = 2.0
CREDITS_POLL_SECONDS = 300
SESSIONS_POLL_SECONDS = 60
# A chat opens with short tool outputs; the full text loads when a step is expanded.
PREVIEW_CHARS = 600
GZIP_MIN_BYTES = 1400
UPLOAD_LIMIT = 30 * 1024 * 1024
# The API takes images up to 5 MB each; bigger ones still reach Claude as a saved file path.
INLINE_IMAGE_LIMIT = 5 * 1024 * 1024
IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
WINDOWS_DEVICES = {"CON", "PRN", "AUX", "NUL", *(f"{port}{n}" for port in ("COM", "LPT") for n in range(1, 10))}

FALLBACK_MODELS = [
    {"id": "claude-fable-5-1", "name": "Fable 5.1", "line": "fable"},
    {"id": "claude-opus-5-5", "name": "Opus 5.5", "line": "opus"},
    {"id": "claude-sonnet-5-5", "name": "Sonnet 5.5", "line": "sonnet"},
    {"id": "claude-haiku-5-5", "name": "Haiku 5.5", "line": "haiku"},
]
ALL_EFFORTS = ["low", "medium", "high", "xhigh", "max"]
MODES = ("auto", "acceptEdits", "plan", "bypassPermissions", "dontAsk", "manual")
KEY_REJECTED = "Anthropic didn't accept that key. Check that it was copied whole."
ADMIN_FORBIDDEN = (
    "Anthropic won't show this key your organization's costs. That needs an Admin API key, or a key "
    "linked to an admin with no single workspace picked, and individual accounts can't use either."
)

# Inherited from a parent Claude Code session, these would mark our runs as child sessions
# and switch off transcript saving, which breaks --resume. A user's own CLAUDE_CODE_* settings pass through.
SESSION_MARKERS = {
    "CLAUDECODE", "CLAUDE_PID", "CLAUDE_EFFORT", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_CHILD_SESSION",
    "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_SESSION_ATTENDED", "CLAUDE_CODE_BRIDGE_SESSION_ID",
    "CLAUDE_CODE_EXECPATH", "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN",
    "CLAUDE_CODE_PLUGIN_DIRS", "CLAUDE_CODE_SSE_PORT",
}
KEY_VARIABLE = "VIOLA_API_KEY"
# A launcher doesn't run the shell's startup files, so a key exported there is looked up by hand.
SHELL_FILES = (".bashrc", ".zshrc", ".profile", ".bash_profile", ".zprofile", ".zshenv")

# On Windows every console program Viola starts would otherwise open a window of its own.
HIDDEN = {"creationflags": subprocess.CREATE_NO_WINDOW} if WINDOWS else {}
# Its own process group, so a stop can signal the tools a reply started too; Windows ends the tree instead.
OWN_GROUP = HIDDEN if WINDOWS else {"start_new_session": True}

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".woff2": "font/woff2",
    ".json": "application/json",
    ".webmanifest": "application/manifest+json",
}


def now_ms():
    return int(time.time() * 1000)


def write_json(path, data, mode=0o600):
    tmp = path.with_suffix(".tmp")
    # ASCII escapes keep a lone surrogate from Claude Code's output from making the file unwritable.
    with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode), "w") as fh:
        fh.write(json.dumps(data))
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            # Windows virus scanners hold new files open for a moment.
            if not WINDOWS or attempt == 19:
                raise
            time.sleep(0.05)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class Config:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        # Chats hold tool output and files, so other accounts on the computer mustn't read them.
        os.chmod(DATA_DIR, 0o700)
        CONV_DIR.mkdir(exist_ok=True)
        self.lock = threading.Lock()
        self.data = {}
        if CONFIG_PATH.exists():
            try:
                self.data = read_json(CONFIG_PATH)
            except ValueError:
                pass

        # The phone link has its own token, so it can be reset without locking out this computer's window.
        # Older settings used one token for both, which stays valid for the phone until it's reset.
        if "token" in self.data:
            self.data.setdefault("remote_token", self.data["token"])
        user = os.environ.get("USER") or os.environ.get("USERNAME") or "friend"
        defaults = {
            "token": secrets.token_urlsafe(24),
            "remote_token": secrets.token_urlsafe(24),
            "port": DEFAULT_PORT,
            "name": user[:1].upper() + user[1:],
            "assistant_name": "Claude",
            "auth": "promo",
            "api_key": "",
            "model": "claude-opus-5-5",
            "effort": "high",
            "cwd": str(Path.home()),
            "permission_mode": "auto",
            "show_thinking": True,
            "auto_titles": True,
            "terminal_chats": False,
            "theme": "system",
            "credits": None,
            "credits_anchor": None,
            "spend_by_day": {},
            "admin_key": "",
            "spent_since_set": 0.0,
            "remote": False,
            "remote_port": DEFAULT_PORT + 1,
            "slash_commands": [],
            "hidden_sessions": [],
        }

        for key, value in defaults.items():
            self.data.setdefault(key, value)
        self.save()

    def __getitem__(self, key):
        return self.data[key]

    def update(self, **changes):
        with self.lock:
            self.data.update(changes)
            self.save()

    def save(self):
        write_json(CONFIG_PATH, self.data, 0o600)
        os.chmod(CONFIG_PATH, 0o600)


def shell_key():
    """VIOLA_API_KEY as exported in a shell startup file, and which file, or ("", None)."""
    pattern = re.compile(rf"""^\s*export\s+{KEY_VARIABLE}=["']?([^"'\s]+)""", re.M)
    for name in SHELL_FILES:
        try:
            match = pattern.search((Path.home() / name).read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if match:
            return match.group(1), f"~/{name}"
    return "", None


def resolve_api_key(config):
    if config["api_key"]:
        return config["api_key"], "app settings"
    if os.environ.get(KEY_VARIABLE):
        return os.environ[KEY_VARIABLE], KEY_VARIABLE
    key, source = shell_key()
    if key:
        return key, source
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"], "ANTHROPIC_API_KEY"
    return "", None


def child_env(config):
    env = {k: v for k, v in os.environ.items() if k not in SESSION_MARKERS}
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop(KEY_VARIABLE, None)
    # In -p mode Claude Code otherwise kills background agents 10 minutes after the turn ends.
    env["CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS"] = "0"
    if config["auth"] == "promo":
        key, _ = resolve_api_key(config)
        if key:
            env["ANTHROPIC_API_KEY"] = key
    return env


ICON_SIZES = (16, 22, 24, 32, 48, 64, 128, 256)


def install_icon(svg, hicolor):
    """Installs an SVG as Viola's icon in a hicolor folder, with the PNG sizes launchers look for first."""
    scalable = hicolor / "scalable" / "apps"
    scalable.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(svg, scalable / "viola.svg")
    pngs = [hicolor / f"{size}x{size}" / "apps" / "viola.png" for size in ICON_SIZES]
    try:
        import gi

        gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import GdkPixbuf
    except (ImportError, ValueError):
        # Old PNGs would win over the new SVG, so without a renderer they go.
        for png in pngs:
            png.unlink(missing_ok=True)
        return
    for size, png in zip(ICON_SIZES, pngs):
        png.parent.mkdir(parents=True, exist_ok=True)
        GdkPixbuf.Pixbuf.new_from_file_at_size(str(svg), size, size).savev(str(png), "png", [], [])


def chat_folder(conv):
    """The chat's folder, or ValueError if it's gone: Claude Code mustn't quietly work somewhere else."""
    if not os.path.isdir(conv["cwd"]):
        raise ValueError(f"This chat's folder isn't there right now ({conv['cwd']}). "
                         "If it's on a drive or a network share, connect it and try again.")
    return conv["cwd"]


def check_folder(path):
    path = os.path.expanduser(path)
    if not os.path.isabs(path) or not os.path.isdir(path):
        raise ValueError(f"There's no folder at {path}")
    return path


def end_tree(proc):
    """Ends a program and everything it started, at once."""
    if WINDOWS:
        try:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, timeout=10, **HIDDEN)
        except (OSError, subprocess.TimeoutExpired):
            pass
        if proc.poll() is None:
            proc.kill()
        return
    try:
        # Viola starts these as process group leaders, so their tools go too.
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run_child(args, timeout, data=None, **options):
    """Like subprocess.run, except a timeout also ends what the program started (npm's claude.cmd runs node)."""
    with subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          **OWN_GROUP, **options) as proc:
        try:
            out, _ = proc.communicate(data, timeout=timeout)
        except subprocess.TimeoutExpired:
            end_tree(proc)
            proc.communicate()
            raise
    return proc.returncode, out


def adopt_login_path():
    """Adds the login shell's PATH: an app opened from the Finder gets only the system folders, without claude."""
    shell = os.environ.get("SHELL") or "/bin/zsh"
    marker = "__viola_path__"
    try:
        code, out = run_child([shell, "-ilc", f'printf "{marker}%s{marker}" "$PATH"'], 10)
    except (OSError, subprocess.TimeoutExpired):
        return
    found = re.search(rf"{marker}(.*?){marker}", out.decode(errors="replace"))
    if code != 0 or not found:
        return
    known = os.environ.get("PATH", "").split(os.pathsep)
    extra = [folder for folder in found.group(1).split(os.pathsep) if folder and folder not in known]
    os.environ["PATH"] = os.pathsep.join(known + extra)


def claude_binary():
    found = shutil.which("claude")
    if found:
        return found
    # Where Claude Code's own installer puts it, which may not be on a launcher's PATH.
    local = Path.home() / ".local/bin" / ("claude.exe" if WINDOWS else "claude")
    return str(local) if local.exists() else "claude"


def tailscale_binary():
    found = shutil.which("tailscale")
    if found:
        return found
    # The macOS app keeps its command line inside the bundle, off the PATH.
    for path in ("/Applications/Tailscale.app/Contents/MacOS/Tailscale",
                 os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Tailscale", "tailscale.exe")):
        if os.path.isfile(path):
            return path
    return "tailscale"


def claude_version():
    try:
        code, out = run_child([claude_binary(), "--version"], 20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.decode(errors="replace").strip().split(" (")[0] if code == 0 else None


SPINNER_WORD = rb'"[A-Z](?:[A-Za-z\'-]|\\x[0-9A-Fa-f]{2}|\\u[0-9A-Fa-f]{4}){2,30}"'
SPINNER_LIST = re.compile(rb"\[(?:" + SPINNER_WORD + rb",){60,}" + SPINNER_WORD + rb"\]")


def spinner_verbs():
    """Claude Code's "Pondering…" verbs, read from the installed program, since the list ships nowhere else.

    The program is searched for a long list of capitalized -ing words (about 1.5 s for the native build),
    once per installed version; an empty list means Viola uses its own.
    """
    try:
        program = Path(claude_binary()).resolve()
        stat = program.stat()
    except OSError:
        return []
    key = [str(program), stat.st_size, stat.st_mtime]
    try:
        cached = read_json(VERBS_CACHE)
        if cached.get("key") == key:
            return cached["verbs"]
    except (OSError, ValueError):
        pass
    best = []
    try:
        with open(program, "rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as data:
            for match in SPINNER_LIST.finditer(data):
                words = [w.decode("ascii").encode().decode("unicode_escape")
                         for w in re.findall(rb'"([^"]+)"', match.group())]
                if sum(w.endswith(("ing", "in'")) for w in words) >= 0.9 * len(words) and len(words) > len(best):
                    best = words
    except (OSError, ValueError):
        return []
    write_json(VERBS_CACHE, {"key": key, "verbs": best})
    return best


def anthropic_request(path, key):
    return urllib.request.Request(f"https://api.anthropic.com{path}",
                                  headers={"x-api-key": key, "anthropic-version": "2023-06-01"})


def check_key(path, key, forbidden=KEY_REJECTED):
    """Raise ValueError if Anthropic refuses the key; network trouble is let through."""
    try:
        urllib.request.urlopen(anthropic_request(path, key), timeout=15).close()
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise ValueError(KEY_REJECTED)
        if exc.code == 403:
            raise ValueError(forbidden)
    except OSError:
        pass


def utc_day(at=None):
    return time.strftime("%Y-%m-%d", time.gmtime(at))


def next_day(day):
    return (date.fromisoformat(day) + timedelta(days=1)).isoformat()


def check_admin_key(key):
    # The cost report only covers whole UTC days, so asking about today is always an empty range.
    query = urlencode({"starting_at": utc_day(time.time() - 86400) + "T00:00:00Z", "limit": 1})
    check_key(f"/v1/organizations/cost_report?{query}", key, ADMIN_FORBIDDEN)


def save_upload(name, data):
    safe = re.sub(r"[^\w.\- ]+", "_", Path(name).name).strip(" .") or "file"
    stem, suffix = os.path.splitext(safe)
    # Names stay short enough for Windows paths, and clear of the device names Windows reserves.
    safe = (stem[:100].rstrip(" .") or "file") + suffix[:16]
    if safe.split(".")[0].strip().upper() in WINDOWS_DEVICES:
        safe = "_" + safe
    folder = UPLOAD_DIR / secrets.token_hex(6)
    folder.mkdir(parents=True)
    with os.fdopen(os.open(folder / safe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as fh:
        fh.write(data)
    kind = "image" if Path(safe).suffix.lower() in IMAGE_TYPES else "file"
    return {"id": folder.name, "name": safe, "kind": kind, "size": len(data)}


def upload_path(attachment):
    """The saved file behind an attachment the page sent back, or None if it isn't one of ours."""
    if not isinstance(attachment, dict) or not re.fullmatch(r"[0-9a-f]{12}", str(attachment.get("id", ""))):
        return None
    path = UPLOAD_DIR / attachment["id"] / Path(str(attachment.get("name", ""))).name
    return path if path.is_file() else None


def message_content(text, attachments):
    """What Claude Code is sent: the typed text plus where each file was saved, with images inline."""
    if not attachments:
        return text, text
    note = "Attached, saved on this computer:\n" + "\n".join(f"- {upload_path(a)}" for a in attachments)
    wire = f"{text}\n\n{note}" if text else note
    blocks = [{"type": "text", "text": wire}]
    for attachment in attachments:
        path = upload_path(attachment)
        kind = IMAGE_TYPES.get(path.suffix.lower())
        if kind and path.stat().st_size <= INLINE_IMAGE_LIMIT:
            data = base64.b64encode(path.read_bytes()).decode()
            blocks.append({"type": "image", "source": {"type": "base64", "media_type": kind, "data": data}})
    return (blocks if len(blocks) > 1 else wire), wire


def conv_mode(conv, config):
    return conv.get("permission_mode") or config["permission_mode"]


def settle_loaded(conv):
    for msg in conv.get("messages", []):
        if msg.get("status") != "streaming":
            continue
        msg["status"] = "interrupted"
        for block in msg.get("blocks", []):
            if block.get("type") == "tool" and block.get("state") == "running":
                block["state"] = "interrupted"
            if block.get("type") == "thinking" and "ended" not in block:
                block["ended"] = block.get("started", msg["ts"])
    conv.pop("pending", None)


def light(conv):
    """The chat without the bulk of long tool outputs and inputs, which load when a step is opened."""
    messages = []
    for msg in conv["messages"]:
        if msg.get("role") != "assistant":
            messages.append(msg)
            continue
        blocks = []
        for block in msg["blocks"]:
            if block.get("type") == "tool":
                result = block.get("result") or ""
                big_input = isinstance(block.get("input"), dict) and len(json.dumps(block["input"])) > 4 * PREVIEW_CHARS
                if len(result) > PREVIEW_CHARS or big_input:
                    block = dict(block, partial=True)
                    if len(result) > PREVIEW_CHARS:
                        block["result"] = result[:PREVIEW_CHARS]
                    if big_input:
                        block["input"] = {k: v[:PREVIEW_CHARS] if isinstance(v, str) else v
                                          for k, v in block["input"].items()}
            blocks.append(block)
        messages.append(dict(msg, blocks=blocks))
    return dict(conv, messages=messages)


class Hub:
    """Fan-out of server events to every connected SSE client."""

    def __init__(self):
        self.clients = set()
        self.lock = threading.Lock()

    def subscribe(self, token=""):
        q = queue.Queue()
        q.token = token
        with self.lock:
            self.clients.add(q)
        return q

    def drop(self, token):
        """Ends the event streams opened with a token that no longer works."""
        with self.lock:
            for q in self.clients:
                if secrets.compare_digest(q.token.encode(), token.encode()):
                    q.put(None)

    def unsubscribe(self, q):
        with self.lock:
            self.clients.discard(q)

    def emit(self, event):
        data = json.dumps(event)
        with self.lock:
            for q in self.clients:
                q.put(data)


class Store:
    def __init__(self, hub):
        self.hub = hub
        self.lock = threading.RLock()
        self.convs = {}
        for path in CONV_DIR.glob("*.json"):
            try:
                conv = read_json(path)
            except ValueError:
                continue
            settle_loaded(conv)
            self.convs[conv["id"]] = conv
        self.last_save = {}

    def summary(self, conv):
        return {
            "id": conv["id"],
            "title": conv["title"],
            "updated": conv["updated"],
            "created": conv["created"],
            "running": conv.get("running", False),
            "cost": conv.get("cost", 0.0),
            "cwd": conv["cwd"],
            "terminal": bool(conv.get("source")),
        }

    def list(self):
        with self.lock:
            convs = sorted(self.convs.values(), key=lambda c: c["updated"], reverse=True)
            return [self.summary(c) for c in convs]

    def create(self, config, cwd=None, model=None, effort=None, mode=None):
        conv = {
            "id": uuid.uuid4().hex[:12],
            "title": "New chat",
            "created": now_ms(),
            "updated": now_ms(),
            "session_id": str(uuid.uuid4()),
            "session_started": False,
            "cwd": check_folder(cwd) if cwd else os.path.expanduser(config["cwd"]),
            "model": model or config["model"],
            "effort": effort or config["effort"],
            "permission_mode": mode or config["permission_mode"],
            "cost": 0.0,
            "cost_seen": 0.0,
            "seq": 0,
            "messages": [],
        }
        with self.lock:
            self.convs[conv["id"]] = conv
            self.save(conv, force=True)
        self.hub.emit({"t": "conv_meta", "conv": self.summary(conv)})
        return conv

    def get(self, conv_id):
        return self.convs.get(conv_id)

    def save(self, conv, force=False):
        with self.lock:
            # A turn finishing after its chat was deleted mustn't write the file back.
            if self.convs.get(conv["id"]) is not conv:
                return
            last = self.last_save.get(conv["id"], 0)
            if not force and time.time() - last < SAVE_INTERVAL:
                return
            self.last_save[conv["id"]] = time.time()
            data = {k: v for k, v in conv.items() if k not in ("running", "pending")}
            write_json(CONV_DIR / f"{conv['id']}.json", data)

    def delete(self, conv_id):
        with self.lock:
            self.convs.pop(conv_id, None)
            (CONV_DIR / f"{conv_id}.json").unlink(missing_ok=True)
        self.hub.emit({"t": "conv_deleted", "id": conv_id})

    def touch(self, conv):
        conv["updated"] = now_ms()
        if self.convs.get(conv["id"]) is not conv:
            return
        self.hub.emit({"t": "conv_meta", "conv": self.summary(conv)})


def billed_cents(key, first_day, end_day):
    """Billed cost, in cents, for the whole UTC days from first_day up to, not including, end_day."""
    query = {"starting_at": f"{first_day}T00:00:00Z", "ending_at": f"{end_day}T00:00:00Z", "limit": 31}
    total = 0.0
    while True:
        request = anthropic_request(f"/v1/organizations/cost_report?{urlencode(query)}", key)
        with urllib.request.urlopen(request, timeout=15) as resp:
            data = json.load(resp)
        total += sum(float(item["amount"]) for bucket in data["data"] for item in bucket["results"])
        if not data.get("has_more"):
            return total
        query["page"] = data["next_page"]


def stringify_tool_result(content):
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = []
        for item in content:
            if item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif item.get("type") == "image":
                parts.append("[image]")
        text = "\n".join(parts)
    else:
        text = json.dumps(content, ensure_ascii=False)
    return sessions.clip(text, RESULT_PREVIEW_LIMIT)


# Dollars per million tokens (input, output, cache read), first match wins. Cache writes cost 1.25x input.
# Only for counting down mid-reply; Claude Code's own total replaces the estimate when the reply ends.
PRICES = (
    ("claude-fable", 10.0, 50.0, 0.25),
    ("claude-mythos", 10.0, 50.0, 0.25),
    ("claude-opus-5-5", 4.0, 20.0, 0.20),
    ("claude-opus", 5.0, 25.0, 0.50),
    ("claude-sonnet-5", 2.0, 10.0, 0.20),
    ("claude-sonnet", 3.0, 15.0, 0.30),
    ("claude-haiku-5", 0.10, 0.50, 0.01),
    ("claude-haiku", 1.0, 5.0, 0.10),
)


def estimate_cost(model, usage):
    rates = next((r for r in PRICES if (model or "").startswith(r[0])), None)
    if rates is None:
        return 0.0
    _, fresh, out, read = rates
    tokens = lambda key: usage.get(key) or 0
    return (tokens("input_tokens") * fresh + tokens("cache_creation_input_tokens") * fresh * 1.25
            + tokens("cache_read_input_tokens") * read + tokens("output_tokens") * out) / 1e6


class Turn:
    """One `claude -p` process answering one user message, plus any sent while it works."""

    def __init__(self, app, conv, msg):
        self.app = app
        self.conv = conv
        self.msg = msg
        self.proc = None
        self.stopping = False
        self.got_result = False
        self.result_error = None
        self.block_by_api = {}
        self.stderr = []
        self.out_tokens = {}
        # API calls made since the last result, priced from their usage: {message id: (model, usage)}.
        self.calls = {}
        self.estimate = 0.0
        self.input_open = False
        self.opening_text = None
        # Messages written to Claude Code mid-reply that it hasn't picked up yet.
        self.pending = []
        self.outbox = queue.Queue()
        self.wire = {}

    def emit(self, **event):
        self.conv["seq"] += 1
        event["conv_id"] = self.conv["id"]
        event["seq"] = self.conv["seq"]
        self.app.hub.emit(event)

    def command(self):
        config = self.app.config
        conv = self.conv
        args = [
            claude_binary(), "-p",
            "--input-format", "stream-json", "--replay-user-messages",
            "--output-format", "stream-json", "--verbose", "--include-partial-messages",
            "--forward-subagent-text",
            "--permission-mode", conv_mode(conv, config),
            "--permission-prompts", "none",
            "--model", conv["model"],
            "--effort", conv["effort"],
        ]
        if config["show_thinking"]:
            args += ["--settings", json.dumps({"showThinkingSummaries": True})]
        if conv["session_started"]:
            args += ["--resume", conv["session_id"]]
        else:
            args += ["--session-id", conv["session_id"]]
        return args

    def start(self, content, wire):
        self.started = time.time()
        self.proc = subprocess.Popen(
            self.command(),
            cwd=chat_folder(self.conv),
            env=child_env(self.app.config),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **OWN_GROUP,
        )
        # Input stays open so messages sent mid-reply reach Claude Code at its next pause.
        self.input_open = True
        self.opening_text = wire
        threading.Thread(target=self.read_stderr, daemon=True).start()
        threading.Thread(target=self.read_stdout, daemon=True).start()
        threading.Thread(target=self.write_input, daemon=True).start()
        self.write(content)
        # Stop may have been pressed while Claude Code was still starting.
        if self.stopping:
            self.stop()

    def write(self, content):
        self.outbox.put({"type": "user", "message": {"role": "user", "content": content}})

    def write_input(self):
        # Writes wait here rather than in a request, so a Claude Code that's slow to read never holds up Viola.
        while (event := self.outbox.get()) is not None:
            try:
                self.proc.stdin.write((json.dumps(event) + "\n").encode())
                self.proc.stdin.flush()
            except (OSError, ValueError):
                break
        try:
            self.proc.stdin.close()
        except OSError:
            pass

    def inject(self, user_msg, content, wire):
        if not self.input_open or self.proc.poll() is not None:
            return False
        self.write(content)
        self.pending.append(user_msg)
        self.wire[id(user_msg)] = wire.strip()
        return True

    def close_input(self):
        if self.input_open:
            self.input_open = False
            self.outbox.put(None)

    def read_stderr(self):
        for line in self.proc.stderr:
            self.stderr.append(line.decode(errors="replace"))
            del self.stderr[:-40]

    def read_stdout(self):
        try:
            for line in self.proc.stdout:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                try:
                    with self.app.store.lock:
                        self.handle(event)
                        self.app.store.save(self.conv)
                except Exception as exc:  # a malformed event must not kill the turn
                    print("viola: event error:", exc, flush=True)
        finally:
            self.proc.wait()
            with self.app.store.lock:
                self.finish()

    def add_block(self, block, api_key=None):
        blocks = self.msg["blocks"]
        blocks.append(block)
        index = len(blocks) - 1
        if api_key:
            self.block_by_api[api_key] = index
        self.emit(t="block", i=index, block=block)
        return index

    def find_tool(self, tool_id):
        for index, block in enumerate(self.msg["blocks"]):
            if block.get("type") == "tool" and block.get("id") == tool_id:
                return index, block
        return None, None

    def handle(self, event):
        kind = event.get("type")
        parent = event.get("parent_tool_use_id")
        if kind == "stream_event":
            if not parent:
                self.handle_stream(event)
        elif kind == "assistant":
            self.note_usage(event.get("message") or {})
            self.handle_assistant(event, parent)
        elif kind == "user":
            self.handle_user(event, parent)
        elif kind == "system":
            self.handle_system(event)
        elif kind == "result":
            self.handle_result(event)

    def handle_stream(self, event):
        ev = event["event"]
        api_id = event.get("api_message_id")
        etype = ev.get("type")
        if etype == "content_block_start":
            cb = ev["content_block"]
            key = (api_id, ev["index"])
            if cb["type"] == "text":
                self.add_block({"type": "text", "text": ""}, key)
            elif cb["type"] in ("thinking", "redacted_thinking"):
                self.add_block({"type": "thinking", "text": "", "started": now_ms()}, key)
            elif cb["type"] in ("tool_use", "server_tool_use"):
                self.add_block(
                    {"type": "tool", "id": cb["id"], "name": cb["name"], "input": None, "state": "running"},
                    key,
                )
        elif etype == "content_block_delta":
            index = self.block_by_api.get((api_id, ev["index"]))
            if index is None:
                return
            block = self.msg["blocks"][index]
            delta = ev["delta"]
            if delta["type"] == "text_delta":
                block["text"] += delta["text"]
                self.emit(t="delta", i=index, text=delta["text"])
            elif delta["type"] == "thinking_delta" and delta.get("thinking"):
                block["text"] += delta["thinking"]
                self.emit(t="delta", i=index, text=delta["thinking"])
        elif etype == "content_block_stop":
            index = self.block_by_api.get((api_id, ev["index"]))
            if index is not None and self.msg["blocks"][index]["type"] == "thinking":
                block = self.msg["blocks"][index]
                block["ended"] = now_ms()
                self.emit(t="block_set", i=index, block=block)
        elif etype == "message_start":
            self.note_usage(ev.get("message") or {})
        elif etype == "message_delta":
            usage = ev.get("usage") or {}
            self.out_tokens[api_id] = usage.get("output_tokens", 0)
            self.emit(t="status", tokens=sum(self.out_tokens.values()))
            self.note_usage({"id": api_id, "usage": {"output_tokens": usage.get("output_tokens", 0)}})

    def note_usage(self, message):
        """Keeps a running cost estimate, so the balance counts down during long replies."""
        api_id, usage = message.get("id"), message.get("usage")
        if not api_id or not usage:
            return
        model, known = self.calls.get(api_id, (None, {}))
        merged = dict(known)
        for key, value in usage.items():
            if isinstance(value, (int, float)) and value >= merged.get(key, 0):
                merged[key] = value
        self.calls[api_id] = (message.get("model") or model, merged)
        estimate = sum(estimate_cost(m, u) for m, u in self.calls.values())
        if estimate - self.estimate >= 0.005:
            self.estimate = estimate
            self.app.publish_credits()

    def handle_assistant(self, event, parent):
        content = event["message"].get("content", [])
        if parent:
            index, block = self.find_tool(parent)
            if block is None:
                return
            texts = [c.get("text", "") for c in content if c.get("type") == "text"]
            tools = [c.get("name") for c in content if c.get("type") == "tool_use"]
            sub = block.setdefault("sub", [])
            sub.extend(t for t in texts if t)
            sub.extend(f"→ {name}" for name in tools)
            del sub[:-60]
            self.emit(t="block_set", i=index, block=block)
            return
        api_id = event["message"].get("id")
        for item in content:
            if item.get("type") in ("tool_use", "server_tool_use"):
                index, block = self.find_tool(item["id"])
                if block is None:
                    index = self.add_block({"type": "tool", "id": item["id"], "name": item["name"], "state": "running"})
                    block = self.msg["blocks"][index]
                block["input"] = item.get("input")
                self.emit(t="block_set", i=index, block=block)
            elif item.get("type") == "text":
                # Without partial deltas (e.g. a resumed stream), the full message is the only copy.
                streamed = [i for (a, _), i in self.block_by_api.items()
                            if a == api_id and self.msg["blocks"][i]["type"] == "text"]
                if not any(self.msg["blocks"][i]["text"] for i in streamed):
                    self.add_block({"type": "text", "text": item.get("text", "")})

    def handle_user(self, event, parent):
        if event.get("isReplay"):
            # Claude Code echoes each message as it reads it: the one that started this turn, then mid-reply ones.
            echoed = event.get("message", {}).get("content")
            if isinstance(echoed, list):
                echoed = "".join(c.get("text", "") for c in echoed if isinstance(c, dict))
            echoed = (echoed or "").strip()
            if self.opening_text is not None:
                opening, self.opening_text = self.opening_text.strip(), None
                if echoed == opening or not any(self.wire.get(id(m)) == echoed for m in self.pending):
                    return
            if self.pending:
                match = next((m for m in self.pending if self.wire.get(id(m)) == echoed), self.pending[0])
                self.pending.remove(match)
                self.split(match)
            return
        content = event.get("message", {}).get("content")
        if not isinstance(content, list):
            return
        for item in content:
            if item.get("type") != "tool_result":
                continue
            index, block = self.find_tool(item.get("tool_use_id"))
            if block is None or parent:
                continue
            block["result"] = stringify_tool_result(item.get("content"))
            block["state"] = "error" if item.get("is_error") else "done"
            self.emit(t="block_set", i=index, block=block)

    def split(self, user_msg):
        """Claude Code picked up a mid-reply message: end this reply here and carry on in a new one."""
        self.wrap_up("done")
        user_msg["ts"] = now_ms()
        msg = {
            "role": "assistant",
            "blocks": [],
            "status": "streaming",
            "ts": now_ms(),
            "model": self.msg["model"],
            "effort": self.msg["effort"],
        }
        self.got_result = False
        self.result_error = None
        pending = self.conv.get("pending", [])
        if user_msg in pending:
            pending.remove(user_msg)
        self.conv["messages"] += [user_msg, msg]
        self.msg = msg
        self.block_by_api = {}
        self.out_tokens = {}
        self.emit(t="turn_split", user=user_msg, msg=msg, pending=pending)

    def wrap_up(self, status):
        for block in self.msg["blocks"]:
            if block.get("type") == "tool" and block.get("state") == "running":
                block["state"] = "interrupted" if self.stopping else "done"
            if block.get("type") == "thinking" and "ended" not in block:
                block["ended"] = now_ms()
        self.msg["status"] = status
        self.msg["ended"] = now_ms()

    def handle_system(self, event):
        sub = event.get("subtype")
        if sub == "init":
            self.conv["session_started"] = True
            commands = event.get("slash_commands") or []
            if commands:
                known = {c["name"]: c for c in self.app.config["slash_commands"]}
                merged = [known.get(name, {"name": name, "description": ""}) for name in commands]
                self.app.config.update(slash_commands=merged)
        elif sub == "commands_changed":
            commands = [
                {"name": c["name"], "description": c.get("description", "")[:160]}
                for c in event.get("commands", [])
            ]
            if commands:
                self.app.config.update(slash_commands=commands)
        elif sub == "permission_denied":
            tool = event.get("tool_name") or "tool"
            self.add_block({"type": "notice", "kind": "denied", "text": f"Permission denied: {tool}"})
        elif sub == "status" and event.get("status"):
            self.emit(t="status", phase=event["status"])

    def handle_result(self, event):
        # Background agents can wake the model again later, so one process may report several results.
        self.got_result = True
        # total_cost_usd is the session's running total, carried over from earlier turns when resuming.
        total = event.get("total_cost_usd") or 0.0
        seen = self.conv.get("cost_seen", 0.0)
        cost = total - seen if total >= seen else total
        self.conv["cost_seen"] = total

        usage = event.get("usage") or {}
        last = (usage.get("iterations") or [usage])[-1]
        context = sum(last.get(k, 0) or 0
                      for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
        self.msg.update(
            cost=self.msg.get("cost", 0.0) + cost,
            duration_ms=int((time.time() - self.started) * 1000),
            context_tokens=context,
            output_tokens=(self.msg.get("output_tokens") or 0) + (usage.get("output_tokens") or 0),
        )

        cache = self.msg.setdefault("cache", {"read": 0, "write": 0, "fresh": 0})
        cache["read"] += usage.get("cache_read_input_tokens") or 0
        cache["write"] += usage.get("cache_creation_input_tokens") or 0
        cache["fresh"] += usage.get("input_tokens") or 0

        if event.get("is_error"):
            errors = event.get("errors") or []
            detail = event.get("result") or "; ".join(map(str, errors)) or event.get("subtype", "error")
            self.result_error = str(detail)[:2000]
        else:
            self.result_error = None

        self.conv["cost"] = self.conv.get("cost", 0.0) + cost
        self.calls, self.estimate = {}, 0.0
        self.app.spend(cost)
        if not self.pending:
            self.close_input()
        self.emit(t="status", phase="background")

    def finish(self):
        self.close_input()
        if self.got_result:
            if self.stopping:
                status = "interrupted"
            elif self.result_error:
                status = "error"
                self.msg["error"] = self.result_error
            else:
                status = "done"
        else:
            if self.stopping:
                status = "interrupted"
            else:
                status = "error"
                tail = "".join(self.stderr[-12:]).strip()
                self.msg["error"] = tail or f"claude exited with code {self.proc.returncode}"

        self.wrap_up(status)
        self.conv["running"] = False
        self.app.turns.pop(self.conv["id"], None)
        if self.estimate:
            # Cut off before reporting a cost: the next reply's running total includes this one.
            self.app.publish_credits()

        # Whatever Claude Code didn't pick up goes out as the next message.
        queued = self.conv.pop("pending", [])
        if self.conv.get("source"):
            self.app.skip_own_writes(self.conv)
        self.emit(t="turn_end", msg=self.msg, pending=queued)
        self.app.store.touch(self.conv)
        self.app.store.save(self.conv, force=True)
        if self.app.on_turn_end:
            self.app.on_turn_end(self.conv, self.msg)
        self.app.credits_wake.set()

        # A stopped reply means stop everything, and a chat deleted mid-reply mustn't start again; the page
        # puts a stopped chat's queued text back in the box instead.
        if queued and not self.stopping and not self.app.closing and self.app.store.get(self.conv["id"]) is self.conv:
            text = "\n\n".join(m["text"] for m in queued if m["text"])
            attachments = [a for m in queued for a in m.get("attachments", [])]
            threading.Thread(target=self.app.send_quietly, args=(self.conv, text, attachments), daemon=True).start()

    def stop(self):
        """Ends the reply; returns the thread doing it, or None if there's nothing to end yet."""
        self.stopping = True
        if not self.proc or self.proc.poll() is not None:
            return None
        # Claude Code's own interrupt ends the reply cleanly and still reports its cost, on every system.
        # It would carry on with queued messages, though, so then the process is ended from outside.
        asked = self.input_open and not self.pending
        if asked:
            self.outbox.put({"type": "control_request", "request_id": uuid.uuid4().hex,
                             "request": {"subtype": "interrupt"}})
        self.close_input()
        ender = threading.Thread(target=self.end_process, args=(4 if asked else 0,), daemon=True)
        ender.start()
        return ender

    def end_process(self, grace):
        if grace:
            try:
                self.proc.wait(timeout=grace)
                return
            except subprocess.TimeoutExpired:
                pass
        if WINDOWS:
            end_tree(self.proc)
            return
        # start_new_session made the child its own process group leader.
        for sig, wait in ((signal.SIGINT, 4), (signal.SIGTERM, 4)):
            try:
                os.killpg(self.proc.pid, sig)
            except ProcessLookupError:
                return
            try:
                self.proc.wait(timeout=wait)
                return
            except subprocess.TimeoutExpired:
                continue
        end_tree(self.proc)


class App:
    def __init__(self):
        self.config = Config()
        self.hub = Hub()
        self.store = Store(self.hub)
        self.turns = {}
        self.models_cache = None
        self.on_turn_end = None
        self.remote_server = None
        self.remote_https = None
        self.remote_error = ""
        if MACOS:
            adopt_login_path()
        self.claude_version = claude_version()

        self.credits_live = None
        self.credits_error = ""
        self.credits_wake = threading.Event()
        self.credits_lock = threading.Lock()

        self.closing = False
        self.sessions_lock = threading.Lock()
        self.sessions_wake = threading.Event()
        self.sessions_cache = {}
        self.sessions_list = []
        self.live = {}
        self.readers = {}

        if SESSIONS_CACHE.exists():
            try:
                self.sessions_cache = read_json(SESSIONS_CACHE)
            except ValueError:
                pass

        threading.Thread(target=self.poll_credits, daemon=True).start()
        threading.Thread(target=self.poll_sessions, daemon=True).start()

    def poll_sessions(self):
        while True:
            try:
                self.refresh_sessions()
            except Exception as exc:  # a strange transcript mustn't stop the polling
                print("viola: session scan failed:", exc, flush=True)
            self.sessions_wake.wait(SESSIONS_POLL_SECONDS)
            self.sessions_wake.clear()

    def refresh_sessions(self):
        if not self.config["terminal_chats"]:
            self.publish_sessions()
            return
        with self.sessions_lock:
            fresh = sessions.scan(self.sessions_cache)
            if fresh != self.sessions_cache:
                self.sessions_cache = fresh
                write_json(SESSIONS_CACHE, fresh)
        self.live = sessions.live()
        self.publish_sessions()

    def publish_sessions(self):
        listing = self.terminal_sessions()
        if listing != self.sessions_list:
            self.sessions_list = listing
            self.hub.emit({"t": "sessions", "sessions": listing})

    def live_elsewhere(self):
        """Sessions open in a Claude Code process that Viola didn't start, checked fresh each time."""
        # A cached list would still hold Viola's own process for a while after a reply ends.
        self.live = sessions.live()
        ours = {turn.proc.pid for turn in list(self.turns.values()) if turn.proc}
        return {sid: info for sid, info in self.live.items() if info["pid"] not in ours}

    def terminal_sessions(self):
        if not self.config["terminal_chats"]:
            return []
        known = {c["session_id"] for c in list(self.store.convs.values())}
        hidden = set(self.config["hidden_sessions"])
        temp = tuple({os.path.join(os.path.normcase(folder), "") for folder in (tempfile.gettempdir(), "/tmp")})
        elsewhere = self.live_elsewhere()
        found = []
        for info in list(self.sessions_cache.values()):
            cwd = info["cwd"] or ""
            if (not info["prompt"] or info["id"] in known or info["id"] in hidden
                    or os.path.join(os.path.normcase(cwd), "").startswith(temp)):
                continue
            found.append({
                "id": info["id"],
                "title": (info["custom"] or info["title"] or info["prompt"])[:120],
                "updated": info["updated"],
                "created": info["created"] or info["updated"],
                "cwd": cwd,
                "terminal": True,
                "live": info["id"] in elsewhere,
            })
        found.sort(key=lambda c: c["updated"], reverse=True)
        return found

    def open_session(self, session_id):
        """Brings a terminal chat into Viola the first time it's opened."""
        if not self.config["terminal_chats"]:
            return None
        with self.sessions_lock:
            path = sessions.find(self.sessions_cache, session_id)
            info = self.sessions_cache.get(str(path)) if path else None
        if not info:
            return None
        conv = sessions.new_conv(info, self.config)
        conv["source"]["path"] = str(path)
        reader = sessions.Reader(conv)
        sessions.read_new(conv, reader)
        reader.settle(running=session_id in self.live_elsewhere())
        sessions.trim_history(conv)
        with self.store.lock:
            if session_id in self.store.convs:
                return self.store.convs[session_id]
            self.store.convs[conv["id"]] = conv
            self.readers[conv["id"]] = reader
            self.store.save(conv, force=True)
        self.hub.emit({"t": "conv_meta", "conv": self.store.summary(conv)})
        self.publish_sessions()
        return conv

    def sync(self, conv):
        """Catches an imported chat up with whatever happened in its terminal since Viola last looked."""
        if not conv.get("source") or conv["id"] in self.turns:
            return
        with self.store.lock:
            reader = self.readers.get(conv["id"]) or sessions.Reader(conv)
            changed = sessions.read_new(conv, reader)
            if changed is None:
                conv.update(messages=[], source=dict(conv["source"], offset=0))
                conv.pop("trimmed", None)
                reader = sessions.Reader(conv)
                changed = sessions.read_new(conv, reader)
                sessions.trim_history(conv)
            self.readers[conv["id"]] = reader
            running = conv["session_id"] in self.live_elsewhere()
            stuck = not running and any(b.get("state") == "running" for b in reader.tools.values())
            if not changed and not stuck:
                return
            reader.settle(running=running)
            self.store.save(conv, force=True)
        self.hub.emit({"t": "conv_meta", "conv": self.store.summary(conv)})

    def skip_own_writes(self, conv):
        # Viola already has the messages its own turn appended to the transcript.
        try:
            conv["source"]["offset"] = Path(conv["source"]["path"]).stat().st_size
        except OSError:
            pass

    def poll_credits(self):
        while True:
            self.refresh_credits()
            self.credits_wake.wait(CREDITS_POLL_SECONDS)
            self.credits_wake.clear()

    def refresh_credits(self):
        key = self.config["admin_key"]
        if not key or self.config["auth"] != "promo":
            self.credits_live = None
            return

        anchor = self.config["credits_anchor"]
        if anchor is None:
            self.credits_live = None
            self.credits_error = ""
        else:
            today = utc_day()
            first = next_day(anchor["day"])
            try:
                billed = billed_cents(key, first, today) if first < today else 0.0
            except urllib.error.HTTPError as exc:
                if exc.code == 403:
                    self.credits_error = ADMIN_FORBIDDEN
                else:
                    self.credits_error = f"Anthropic said {exc.code}: {exc.read().decode(errors='replace')[:200]}"
                self.credits_live = None
            except (OSError, ValueError, KeyError, TypeError) as exc:
                self.credits_error = f"Couldn't read billed costs ({exc})"
                self.credits_live = None
            else:
                self.apply_billed(anchor, billed, today)

        self.hub.emit({"t": "credits", **self.credits(), "cost": 0})

    def apply_billed(self, anchor, billed, today):
        with self.credits_lock:
            if self.config["credits_anchor"] != anchor:
                return  # the balance was reset while the report was loading
            # The report only has whole UTC days, so Viola's own costs stand in for the day the balance
            # was set and for today until those days close.
            by_day = self.config["spend_by_day"]
            local = by_day.get(anchor["day"], 0.0) - anchor["local_before"]
            if today != anchor["day"]:
                local += by_day.get(today, 0.0)
            self.config.update(credits=anchor["balance"] - billed / 100 - local)
        self.credits_error = ""
        self.credits_live = time.time()

    def set_balance(self, balance):
        with self.credits_lock:
            day = utc_day()
            anchor = None
            if balance is not None:
                anchor = {"balance": balance, "at": time.time(), "day": day,
                          "local_before": self.config["spend_by_day"].get(day, 0.0)}
            self.config.update(credits=balance, credits_anchor=anchor, spent_since_set=0.0)
        self.credits_wake.set()

    def spend(self, cost):
        if self.config["auth"] != "promo" or not cost:
            return
        with self.credits_lock:
            day = utc_day()
            anchor_day = (self.config["credits_anchor"] or {}).get("day", day)
            cutoff = utc_day(time.time() - 40 * 86400)
            by_day = {d: v for d, v in self.config["spend_by_day"].items() if d >= min(cutoff, anchor_day)}
            by_day[day] = by_day.get(day, 0.0) + cost
            balance = self.config["credits"]
            changes = {"spent_since_set": self.config["spent_since_set"] + cost, "spend_by_day": by_day}
            if balance is not None:
                changes["credits"] = balance - cost
            self.config.update(**changes)
        self.hub.emit({"t": "credits", **self.credits(), "cost": cost})

    def publish_credits(self):
        self.hub.emit({"t": "credits", **self.credits(), "cost": 0})

    def credits(self):
        return {
            "balance": self.config["credits"],
            "pending": sum(turn.estimate for turn in list(self.turns.values())),
            "spent": self.config["spent_since_set"],
            "enabled": self.config["auth"] == "promo",
            "live": self.credits_live,
            "error": self.credits_error if self.config["admin_key"] else "",
        }

    def send(self, conv, text, model=None, effort=None, mode=None, attachments=()):
        if mode and mode not in MODES:
            raise ValueError(f"Unknown permission mode: {mode}")
        attachments = [a for a in attachments if upload_path(a)]
        if not text and not attachments:
            raise ValueError("empty message")

        content, wire = message_content(text, attachments)
        with self.store.lock:
            for key, value in (("model", model), ("effort", effort), ("permission_mode", mode)):
                if value:
                    conv[key] = value

            user_msg = {"role": "user", "text": text, "ts": now_ms()}
            if attachments:
                user_msg["attachments"] = [{k: a[k] for k in ("id", "name", "kind", "size") if k in a}
                                           for a in attachments]

            turn = self.turns.get(conv["id"])
            if turn:
                conv.setdefault("pending", []).append(user_msg)
                turn.inject(user_msg, content, wire)
                turn.emit(t="pending", pending=conv["pending"])
                return

            elsewhere = self.live_elsewhere().get(conv["session_id"])
            if elsewhere:
                raise ValueError(
                    "This chat is open in a terminal right now. Reply there, or wait until it's closed, "
                    "so the two don't split it in half."
                )

            self.sync(conv)
            msg = {
                "role": "assistant",
                "blocks": [],
                "status": "streaming",
                "ts": now_ms(),
                "model": conv["model"],
                "effort": conv["effort"],
            }
            first = not conv["messages"]
            conv["messages"] += [user_msg, msg]
            conv["running"] = True
            turn = Turn(self, conv, msg)
            self.turns[conv["id"]] = turn
            turn.emit(t="turn_start", user=user_msg, msg=msg)
            self.store.touch(conv)

        try:
            turn.start(content, wire)
        except (OSError, ValueError) as exc:
            with self.store.lock:
                turn.result_error = f"Couldn't start claude: {exc}"
                turn.got_result = True
                turn.finish()
            return

        if first and conv["title"] == "New chat":
            conv["title"] = (text.strip().splitlines() or [attachments[0]["name"]])[0][:60] or "New chat"
            self.store.touch(conv)
            if self.config["auto_titles"]:
                threading.Thread(target=self.make_title, args=(conv, wire), daemon=True).start()

    def send_quietly(self, conv, text, attachments=()):
        try:
            self.send(conv, text, attachments=attachments)
        except ValueError as exc:
            print("viola: couldn't send queued message:", exc, flush=True)
            self.hub.emit({"t": "unsent", "conv_id": conv["id"], "text": text, "error": str(exc)})

    def make_title(self, conv, text):
        args = [
            claude_binary(), "-p", "--model", "haiku", "--effort", "low", "--tools", "",
            "--no-session-persistence", "--output-format", "json",
            "--system-prompt",
            "Reply with only a short title (2 to 6 words, sentence case, no quotes or punctuation at the end) "
            "for a chat that starts with the user's message below.",
        ]
        if self.config["auth"] == "promo":
            args.insert(2, "--bare")
        try:
            _, out = run_child(args, 60, text[:3000].encode(), env=child_env(self.config), cwd=str(Path.home()))
            result = json.loads(out)
        except (subprocess.TimeoutExpired, ValueError, OSError):
            return
        title = (result.get("result") or "").strip().strip('"').splitlines()
        if title and title[0] and not result.get("is_error") and not conv.get("renamed"):
            with self.store.lock:
                conv["title"] = title[0][:80]
                self.store.save(conv, force=True)
                self.store.touch(conv)
        self.spend(result.get("total_cost_usd") or 0.0)

    def models(self):
        if self.models_cache and time.time() - self.models_cache[0] < 3600:
            return self.models_cache[1]

        key, _ = resolve_api_key(self.config)
        models = None
        if key:
            try:
                with urllib.request.urlopen(anthropic_request("/v1/models?limit=100", key), timeout=10) as resp:
                    data = json.load(resp)["data"]
                models = []
                for m in data:
                    effort = m.get("capabilities", {}).get("effort", {})
                    efforts = [e for e in ALL_EFFORTS if isinstance(effort.get(e), dict) and effort[e].get("supported")]
                    models.append({
                        "id": m["id"],
                        "name": m["display_name"].removeprefix("Claude "),
                        "line": m.get("line", ""),
                        "efforts": efforts,
                    })
            except (OSError, ValueError, KeyError):
                models = None

        if not models:
            models = [dict(m, efforts=ALL_EFFORTS) for m in FALLBACK_MODELS]
        self.models_cache = (time.time(), models)
        return models

    def settings(self):
        key, source = resolve_api_key(self.config)
        data = {k: self.config[k] for k in (
            "name", "assistant_name", "auth", "model", "effort", "cwd", "permission_mode", "show_thinking",
            "auto_titles", "terminal_chats", "theme", "remote", "remote_port", "slash_commands",
        )}
        data["home"] = str(Path.home())
        data["sep"] = os.sep
        data["app_icon"] = LINUX
        data["claude_version"] = self.claude_version
        data["needs_setup"] = not self.claude_version or (self.config["auth"] == "promo" and not key)
        data["key_source"] = source
        data["key_hint"] = f"{key[:10]}…{key[-6:]}" if key else ""
        admin = self.config["admin_key"]
        data["admin_hint"] = f"{admin[:14]}…{admin[-4:]}" if admin else ""
        data["remote_url"] = self.remote_url()
        data["remote_error"] = self.remote_error
        return data

    def tailscale_self(self):
        try:
            out = subprocess.run([tailscale_binary(), "status", "--json"], capture_output=True, encoding="utf-8",
                                 errors="replace", timeout=8, **HIDDEN)
            data = json.loads(out.stdout)
        except (OSError, subprocess.TimeoutExpired, ValueError):
            return None, None
        me = data.get("Self") or {}
        dns = (me.get("DNSName") or "").rstrip(".")
        ipv4 = next((ip for ip in me.get("TailscaleIPs") or [] if "." in ip), None)
        return (dns if dns in (data.get("CertDomains") or []) else None), ipv4

    def tailscale_serve(self, *args):
        try:
            out = subprocess.run([tailscale_binary(), "serve", *args], capture_output=True, encoding="utf-8",
                                 errors="replace", timeout=30, **HIDDEN)
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.remote_error = f"tailscale serve failed: {exc}"
            return False
        if out.returncode:
            self.remote_error = (out.stderr or out.stdout).strip()[:300]
        return out.returncode == 0

    def remote_url(self):
        token = self.config["remote_token"]
        if self.remote_https:
            return f"https://{self.remote_https}:{self.config['remote_port']}/#token={token}"
        if self.remote_server:
            host, port = self.remote_server.server_address[:2]
            return f"http://{host}:{port}/#token={token}"
        return ""

    def reset_remote_link(self):
        """Makes a new phone link; returns this computer's new token too when the old link shared it."""
        old = self.config["remote_token"]
        changes = {"remote_token": secrets.token_urlsafe(24)}
        if old == self.config["token"]:
            changes["token"] = secrets.token_urlsafe(24)
        self.config.update(**changes)
        self.hub.drop(old)
        return changes.get("token")

    def stop_remote(self):
        if self.remote_https:
            self.tailscale_serve(f"--https={self.config['remote_port']}", "off")
            self.remote_https = None
        if self.remote_server:
            self.remote_server.shutdown()
            self.remote_server.server_close()
            self.remote_server = None

    def set_remote(self, enabled, home_network=True):
        """Shares Viola with the user's phone; home_network=False keeps it to Tailscale."""
        self.stop_remote()
        self.remote_error = ""
        if enabled:
            host, ip = self.tailscale_self()
            port = self.config["remote_port"]
            # HTTPS through `tailscale serve` makes the page a secure context, so copying and installing work on phones.
            # Without Tailscale, the home network still works for a phone on the same Wi-Fi.
            address = ip or (lan_address() if home_network else None)
            if not host and not ip and not home_network:
                self.remote_error = ("Sharing on the home network stays off after Viola restarts, since this "
                                     "computer may be on another network now. Turn it on again on one you trust.")
                self.config.update(remote=False)
                return
            if host and self.tailscale_serve("--bg", f"--https={port}", f"http://127.0.0.1:{self.config['port']}"):
                self.remote_https = host
                self.remote_error = ""
            elif address:
                try:
                    self.remote_server = make_server(self, address, port)
                    threading.Thread(target=self.remote_server.serve_forever, daemon=True).start()
                except OSError as exc:
                    self.remote_error = f"Couldn't listen on {address}:{port} ({exc.strerror})."
            else:
                self.remote_error = (
                    "This computer isn't on a network Viola can share on (no Tailscale and no home network)."
                )
        self.config.update(remote=bool(self.remote_https or self.remote_server))

    def set_app_icon(self, theme):
        """Makes the launcher and taskbar icon this theme's ("" for the classic one), for this user."""
        if not re.fullmatch(r"[a-z0-9-]*", theme):
            raise ValueError("Unknown theme")
        svg = WEB_DIR / "icons" / f"{theme}.svg" if theme else WEB_DIR / "icon.svg"
        if not svg.is_file():
            svg = WEB_DIR / "icon.svg"
        if not LINUX:
            return str(svg)
        hicolor = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "icons" / "hicolor"
        installed = hicolor / "scalable" / "apps" / "viola.svg"
        if installed.is_file() and installed.read_bytes() == svg.read_bytes():
            return str(svg)
        install_icon(svg, hicolor)
        os.utime(hicolor)
        # KDE keeps icons cached until it's told they changed; elsewhere this signal is simply ignored.
        try:
            subprocess.run(["dbus-send", "--session", "--type=signal", "/KIconLoader",
                            "org.kde.KIconLoader.iconChanged", "int32:0"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass
        return str(svg)

    def open_terminal(self, conv):
        resume = [claude_binary(), "--resume", conv["session_id"]]
        if self.config["auth"] == "subscription":
            resume.append("--remote-control")

        cwd = chat_folder(conv)
        env = child_env(self.config)
        if WINDOWS:
            # Started directly, so there's no command line for cmd to reinterpret; the window closes with Claude Code.
            subprocess.Popen(resume, cwd=cwd, env=env, creationflags=subprocess.CREATE_NEW_CONSOLE)
            return "a new console window"
        if MACOS:
            return open_mac_terminal(resume, cwd, env)
        # The key goes through a private file the script deletes, not the terminal's own environment, where
        # every new tab would inherit it; the shell left open afterwards drops it too.
        key = env.pop("ANTHROPIC_API_KEY", None)
        keyfile = None
        prelude = ""
        if key:
            fd, keyfile = tempfile.mkstemp(dir=DATA_DIR)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(key)
            prelude = f'export ANTHROPIC_API_KEY="$(cat {shlex.quote(keyfile)})"; rm -f {shlex.quote(keyfile)}; '
        script = prelude + shlex.join(resume) + "; unset ANTHROPIC_API_KEY; exec bash"
        terminals = [
            ("konsole", ["konsole", "--workdir", cwd, "-e", "bash", "-c", script]),
            ("ptyxis", ["ptyxis", "--new-window", "--working-directory", cwd, "--", "bash", "-c", script]),
            ("gnome-terminal", ["gnome-terminal", f"--working-directory={cwd}", "--", "bash", "-c", script]),
            ("kitty", ["kitty", "--directory", cwd, "bash", "-c", script]),
            ("alacritty", ["alacritty", "--working-directory", cwd, "-e", "bash", "-c", script]),
            ("foot", ["foot", "--working-directory", cwd, "bash", "-c", script]),
            ("xterm", ["xterm", "-e", "bash", "-c", script]),
        ]
        for name, args in terminals:
            if shutil.which(name):
                subprocess.Popen(args, cwd=cwd, env=env, start_new_session=True)
                return name
        if keyfile:
            os.unlink(keyfile)
        raise ValueError("No terminal emulator found")

    def shutdown(self):
        self.closing = True
        self.stop_remote()
        turns = list(self.turns.values())
        enders = [ender for ender in (turn.stop() for turn in turns) if ender]
        # A reply left running after Viola closes would keep spending where no one can see or stop it.
        deadline = time.time() + 6
        for ender in enders:
            ender.join(max(0.0, deadline - time.time()))
        for turn in turns:
            if turn.proc and turn.proc.poll() is None:
                end_tree(turn.proc)
        for conv in self.store.convs.values():
            self.store.save(conv, force=True)


class Handler(BaseHTTPRequestHandler):
    app: App = None
    body_read = False
    protocol_version = "HTTP/1.1"
    # Headers and body go out in separate writes; with Nagle on, the body waits ~40 ms for an ACK.
    disable_nagle_algorithm = True
    # Idle connections from the network close instead of holding a thread each.
    timeout = 60

    def log_message(self, *args):
        pass

    def send_body(self, body, content_type, status=200, cache="no-store", compress=True, headers=()):
        # Chats can be a few hundred kilobytes, which is slow over Tailscale unless compressed.
        packed = compress and len(body) > GZIP_MIN_BYTES and "gzip" in self.headers.get("Accept-Encoding", "")
        if packed:
            body = gzip.compress(body, 5)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for name, value in headers:
            self.send_header(name, value)
        if packed:
            self.send_header("Content-Encoding", "gzip")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data, status=200, headers=()):
        self.send_body(json.dumps(data).encode(), "application/json", status, headers=headers)

    def fail(self, status, message):
        # A body left unread would be taken for the next request on this connection, so the connection ends.
        unread = self.command in ("POST", "PATCH") and not self.body_read
        self.send_json({"error": message}, status, headers=[("Connection", "close")] if unread else ())

    def given_token(self, allow_query=False):
        token = self.headers.get("X-Viola-Token", "")
        if not token and allow_query:
            token = parse_qs(urlparse(self.path).query).get("token", [""])[0]
        return token.encode()

    def authorized(self, allow_query=False):
        token = self.given_token(allow_query)
        # Both are checked every time, so the comparison takes as long whichever one matches.
        local = secrets.compare_digest(token, self.app.config["token"].encode())
        remote = secrets.compare_digest(token, self.app.config["remote_token"].encode())
        return local or remote

    def from_this_computer(self):
        return secrets.compare_digest(self.given_token(), self.app.config["token"].encode())

    def read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 <= length <= UPLOAD_LIMIT:
            raise ValueError("That request is too big")
        self.body_read = True
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except ValueError:
            return {}

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            return self.api("GET", path)
        self.serve_static(path)

    def do_POST(self):
        self.api("POST", urlparse(self.path).path)

    def do_PATCH(self):
        self.api("PATCH", urlparse(self.path).path)

    def do_DELETE(self):
        self.api("DELETE", urlparse(self.path).path)

    def serve_static(self, path):
        if path == "/":
            path = "/index.html"
        target = (WEB_DIR / path.lstrip("/")).resolve()
        if WEB_DIR not in target.parents or not target.is_file():
            return self.fail(404, "not found")
        kind = MIME.get(target.suffix, "application/octet-stream")
        self.send_body(target.read_bytes(), kind, cache="no-cache",
                       compress=not kind.startswith(("font/", "image/png")),
                       headers=[("Content-Security-Policy", "frame-ancestors 'none'")])

    def api(self, method, path):
        self.body_read = False
        if path == "/api/ping":
            # Proves this is the user's own Viola before a window hands it the token.
            nonce = parse_qs(urlparse(self.path).query).get("nonce", [""])[0]
            return self.send_json({"app": "viola", "proof": ping_proof(self.app.config["token"], nonce)})
        if path == "/api/events" and method == "GET":
            if not self.authorized(allow_query=True):
                return self.fail(401, "bad token")
            return self.stream_events()
        if path.startswith("/api/files/") and method == "GET":
            # Images in the chat load as plain <img> tags, which can't send the token header.
            if not self.authorized(allow_query=True):
                return self.fail(401, "bad token")
            return self.serve_upload(path.split("/")[3:])
        if path == "/api/upload" and method == "POST":
            if not self.authorized():
                return self.fail(401, "bad token")
            return self.receive_upload()

        if not self.authorized():
            return self.fail(401, "bad token")
        app = self.app
        parts = path.strip("/").split("/")[1:]

        try:
            body = self.read_body() if method in ("POST", "PATCH") else {}
            if parts == ["state"]:
                return self.send_json({
                    "conversations": app.store.list(),
                    "sessions": app.terminal_sessions(),
                    "settings": app.settings(),
                    "credits": app.credits(),
                    "now": now_ms(),
                })
            if parts == ["sessions"]:
                app.sessions_wake.set()
                return self.send_json({"sessions": app.terminal_sessions()})
            if parts == ["dirs"]:
                return self.send_json(list_dirs(parse_qs(urlparse(self.path).query).get("path", ["~"])[0]))
            if parts == ["verbs"]:
                return self.send_json({"verbs": spinner_verbs()})
            if parts == ["models"]:
                return self.send_json({"models": app.models()})

            if parts == ["setup", "recheck"] and method == "POST":
                app.claude_version = claude_version()
                return self.send_json(app.settings())
            if parts == ["settings"] and method == "PATCH":
                return self.update_settings(body)
            if parts == ["app-icon"] and method == "POST":
                return self.send_json({"icon": app.set_app_icon(str(body.get("theme", "")))})
            if parts == ["remote", "reset"] and method == "POST":
                # A leaked phone link mustn't be able to replace itself.
                if not self.from_this_computer():
                    return self.fail(403, "Reset the link from Viola on your computer")
                token = app.reset_remote_link()
                settings = app.settings()
                app.hub.emit({"t": "settings", "settings": settings, "credits": app.credits()})
                return self.send_json(dict(settings, token=token))
            if parts == ["credits"] and method == "POST":
                balance = body.get("balance")
                app.set_balance(None if balance is None else float(balance))
                app.hub.emit({"t": "credits", **app.credits(), "cost": 0})
                return self.send_json(app.credits())

            if parts == ["conversations"] and method == "POST":
                mode = body.get("permission_mode")
                if mode and mode not in MODES:
                    raise ValueError(f"Unknown permission mode: {mode}")
                conv = app.store.create(app.config, body.get("cwd"), body.get("model"), body.get("effort"), mode)
                return self.send_json(conv)
            if len(parts) >= 2 and parts[0] == "conversations":
                conv = app.store.get(parts[1])
                if not conv and method == "GET" and not parts[2:]:
                    conv = app.open_session(parts[1])
                if not conv:
                    return self.fail(404, "no such conversation")
                return self.conversation_api(method, conv, parts[2:], body)
        except ValueError as exc:
            return self.fail(400, str(exc))

        self.fail(404, "unknown endpoint")

    def receive_upload(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if not 0 < length <= UPLOAD_LIMIT:
            return self.fail(413, f"Files can be up to {UPLOAD_LIMIT // (1024 * 1024)} MB")
        data = self.rfile.read(length)
        self.body_read = True
        name = unquote(self.headers.get("X-File-Name") or "file")
        return self.send_json(save_upload(name, data))

    def serve_upload(self, parts):
        path = upload_path({"id": parts[0], "name": unquote(parts[1])}) if len(parts) == 2 else None
        if not path:
            return self.fail(404, "no such file")
        # Windows reads guesses from the registry, which other programs sometimes get wrong.
        kind = IMAGE_TYPES.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        # An uploaded page or SVG must never run as part of Viola, where it could read the token.
        headers = [("Content-Security-Policy", "sandbox; default-src 'none'; img-src 'self'")]
        if path.suffix.lower() not in IMAGE_TYPES:
            headers.append(("Content-Disposition", "attachment"))
        self.send_body(path.read_bytes(), kind, cache="private, max-age=604800", compress=False, headers=headers)

    def conversation_api(self, method, conv, rest, body):
        app = self.app
        if not rest and method == "GET":
            app.sync(conv)
            live = app.live_elsewhere().get(conv["session_id"])
            # Following a terminal chat polls this; an unchanged transcript costs a few bytes, not the whole chat.
            known = parse_qs(urlparse(self.path).query).get("known", [None])[0]
            if known is not None and conv.get("source") and str(conv["source"]["offset"]) == known:
                return self.send_json({"unchanged": True, "live": live})
            with app.store.lock:
                data = json.dumps(dict(light(conv), live=live)).encode()
            return self.send_body(data, "application/json")

        if rest == ["block"] and method == "GET":
            query = parse_qs(urlparse(self.path).query)
            try:
                with app.store.lock:
                    block = conv["messages"][int(query["m"][0])]["blocks"][int(query["b"][0])]
                    data = json.dumps(block).encode()
            except (KeyError, IndexError, ValueError):
                return self.fail(404, "no such step")
            return self.send_body(data, "application/json")

        if not rest and method == "PATCH":
            with app.store.lock:
                if "title" in body:
                    title = str(body["title"]).strip()[:120]
                    if title and title != conv["title"]:
                        conv.update(title=title, renamed=True)
                for key in ("model", "effort"):
                    if body.get(key):
                        conv[key] = body[key]
                if body.get("permission_mode"):
                    if body["permission_mode"] not in MODES:
                        raise ValueError(f"Unknown permission mode: {body['permission_mode']}")
                    conv["permission_mode"] = body["permission_mode"]
                if body.get("cwd") and not conv["session_started"]:
                    conv["cwd"] = check_folder(body["cwd"])
                app.store.save(conv, force=True)
                app.hub.emit({"t": "conv_meta", "conv": app.store.summary(conv)})
                data = json.dumps(light(conv)).encode()
            return self.send_body(data, "application/json")

        if not rest and method == "DELETE":
            turn = app.turns.get(conv["id"])
            if turn:
                turn.stop()
            # The transcript stays in ~/.claude, so keep it from coming back as a terminal chat.
            hidden = app.config["hidden_sessions"]
            if conv["session_id"] not in hidden:
                app.config.update(hidden_sessions=hidden + [conv["session_id"]])
            app.store.delete(conv["id"])
            app.readers.pop(conv["id"], None)
            app.publish_sessions()
            return self.send_json({"ok": True})

        if rest == ["send"] and method == "POST":
            text = str(body.get("text", "")).strip()
            attachments = body.get("attachments") if isinstance(body.get("attachments"), list) else []
            app.send(conv, text, body.get("model"), body.get("effort"), body.get("permission_mode"), attachments)
            return self.send_json({"ok": True})

        if rest == ["stop"] and method == "POST":
            turn = app.turns.get(conv["id"])
            if turn:
                turn.stop()
            return self.send_json({"ok": True})

        if rest == ["terminal"] and method == "POST":
            if not conv["session_started"]:
                raise ValueError("Send a message first so there's a session to open")
            return self.send_json({"terminal": app.open_terminal(conv)})

        self.fail(404, "unknown endpoint")

    def update_settings(self, body):
        app = self.app
        allowed = {
            "name": str, "assistant_name": str, "auth": str, "model": str, "effort": str, "cwd": str,
            "permission_mode": str, "show_thinking": bool, "auto_titles": bool, "terminal_chats": bool,
            "theme": str, "api_key": str, "admin_key": str,
        }
        changes = {k: allowed[k](v) for k, v in body.items() if k in allowed}
        if changes.get("permission_mode", "auto") not in MODES:
            raise ValueError(f"Unknown permission mode: {changes['permission_mode']}")

        for name in ("api_key", "admin_key"):
            if name in changes:
                changes[name] = changes[name].strip()
        if changes.get("api_key"):
            check_key("/v1/models", changes["api_key"])
        if changes.get("admin_key"):
            check_admin_key(changes["admin_key"])
        if "cwd" in changes:
            changes["cwd"] = check_folder(changes["cwd"])
        if "auth" in changes or "api_key" in changes:
            app.models_cache = None

        app.config.update(**changes)
        if "admin_key" in changes or "auth" in changes:
            app.credits_wake.set()
        if "terminal_chats" in changes:
            app.sessions_wake.set()
        if "remote" in body:
            app.set_remote(bool(body["remote"]))

        settings = app.settings()
        app.hub.emit({"t": "settings", "settings": settings, "credits": app.credits()})
        self.send_json(settings)

    def stream_events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        q = self.app.hub.subscribe(self.given_token(allow_query=True).decode(errors="replace"))
        try:
            self.wfile.write(b": hello\n\n")
            self.wfile.flush()
            while True:
                try:
                    data = q.get(timeout=15)
                    if data is None:
                        return
                    self.wfile.write(f"data: {data}\n\n".encode())
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            self.app.hub.unsubscribe(q)
            self.close_connection = True


def open_mac_terminal(resume, cwd, env):
    """Opens a chat in the user's terminal app, through a script that deletes itself once it starts."""
    lines = ["#!/bin/sh", 'rm -f "$0"', f"cd {shlex.quote(cwd)} || exit"]
    # The terminal app starts the script with its own environment, not Viola's.
    if "ANTHROPIC_API_KEY" in env:
        lines.append(f"export ANTHROPIC_API_KEY={shlex.quote(env['ANTHROPIC_API_KEY'])}")
    lines += [shlex.join(resume), "unset ANTHROPIC_API_KEY", 'exec "${SHELL:-/bin/zsh}" -l']
    fd, script = tempfile.mkstemp(suffix=".command", dir=DATA_DIR)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    os.chmod(script, 0o700)
    subprocess.Popen(["open", script])
    return "Terminal"


def list_dirs(path):
    """The folders inside `path`, for the working-folder picker."""
    try:
        # Not resolved: Windows would turn a mapped drive into a network path that cmd.exe refuses to start in.
        folder = Path(os.path.abspath(os.path.expanduser(path or "~")))
        names = sorted((c.name for c in folder.iterdir() if not c.name.startswith(".") and os.path.isdir(c)),
                       key=str.lower)
    except FileNotFoundError:
        raise ValueError("That folder doesn't exist")
    except NotADirectoryError:
        raise ValueError("That's a file, not a folder")
    except PermissionError:
        raise ValueError("Viola isn't allowed to look inside that folder")
    except OSError:
        raise ValueError("Viola couldn't open that folder")
    return {"path": str(folder), "parent": str(folder.parent) if folder.parent != folder else None, "dirs": names}


def ping_proof(token, nonce):
    return hmac.new(token.encode(), nonce.encode(), "sha256").hexdigest()


def lan_address():
    """This computer's address on the home network, or None without one."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            # Connecting a UDP socket sends nothing; it only picks the interface a packet would leave from.
            probe.connect(("192.0.2.1", 9))
            return probe.getsockname()[0]
        except OSError:
            return None


class Server(ThreadingHTTPServer):
    daemon_threads = True
    # On Windows this option would let a second program listen on a port that's already taken.
    allow_reuse_address = not WINDOWS


def make_server(app, host, port):
    handler = type("BoundHandler", (Handler,), {"app": app})
    return Server((host, port), handler)
