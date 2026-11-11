"""Reads Claude Code's own transcripts, so chats started in a terminal show up in Viola and can continue there."""

import json
import mmap
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
PROJECTS_DIR = CLAUDE_DIR / "projects"
LIVE_DIR = CLAUDE_DIR / "sessions"

HEAD_LIMIT = 8 * 1024 * 1024
TAIL_BYTES = 256 * 1024
MESSAGE_LIMIT = 240
TEXT_LIMIT = 8000
VIOLA_MODES = ("auto", "acceptEdits", "plan", "bypassPermissions")
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259
# Windows counts process times in 100 ns steps from 1601.
FILETIME_EPOCH_MS = 11_644_473_600_000

COMMAND = re.compile(r"<command-name>/?([^<]*)</command-name>[\s\S]*?(?:<command-args>([\s\S]*?)</command-args>)?")
PASTE_TAG = re.compile(r"</?pasted_content[^>]*>")
SUMMARY = re.compile(r"<summary>([\s\S]*?)</summary>")
SESSION_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def ms(stamp):
    try:
        return int(datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp() * 1000)
    except (AttributeError, ValueError):
        return None


def clip(text, limit=TEXT_LIMIT):
    return text if len(text) <= limit else text[:limit] + f"\n… ({len(text) - limit} more characters)"


def entries(raw):
    for line in raw.splitlines():
        # The request blobs are most of a transcript's bytes and never needed here.
        if not line.strip() or b'"type":"api-request' in line[:120]:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict):
            yield entry


def prompt_text(entry):
    """The words a person typed, or None for tool results, reminders and other plumbing."""
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain") or entry.get("isCompactSummary"):
        return None
    content = entry.get("message", {}).get("content")
    if isinstance(content, list):
        parts = []
        for item in content:
            if item.get("type") == "image":
                parts.append("[image]")
            elif item.get("type") == "text":
                text = item.get("text", "")
                if not text.startswith(("[Image: source:", "<coach-note>", "[Request interrupted")):
                    parts.append(text)
        content = "\n".join(parts) if parts else None
    if not isinstance(content, str) or not content.strip():
        return None
    command = COMMAND.search(content)
    if command and content.lstrip().startswith(("<command-", "<command-message>")):
        args = (command.group(2) or "").strip()
        return f"/{command.group(1).strip()}" + (f" {args}" if args else "")
    if content.startswith("<bash-input>"):
        return "! " + re.sub(r"</?bash-input>", "", content).strip()
    if content.lstrip().startswith("<") and not content.lstrip().startswith("<pasted_content"):
        return None
    return PASTE_TAG.sub("", content).strip() or None


def describe(path, stat):
    """One transcript's sidebar facts, read from its head and tail, or searched backward for a late title."""
    info = {"size": stat.st_size, "mtime": stat.st_mtime, "id": path.stem, "cwd": None, "prompt": None,
            "title": None, "custom": None, "created": None, "updated": int(stat.st_mtime * 1000)}

    with open(path, "rb") as fh:
        read = 0
        for line in fh:
            read += len(line)
            for entry in entries(line):
                info["cwd"] = info["cwd"] or entry.get("cwd")
                info["created"] = info["created"] or ms(entry.get("timestamp"))
                text = prompt_text(entry)
                if text and not text.startswith(("/", "! ")):
                    info["prompt"] = text.splitlines()[0][:120]
            if info["prompt"] or read > HEAD_LIMIT:
                break
        if not info["prompt"]:
            return info
        fh.seek(max(0, stat.st_size - TAIL_BYTES))
        tail = fh.read()

    for entry in entries(tail):
        kind = entry.get("type")
        if kind == "custom-title":
            info["custom"] = entry.get("customTitle")
        elif kind == "ai-title":
            info["title"] = entry.get("aiTitle")

    if not info["custom"] and not info["title"] and stat.st_size > TAIL_BYTES:
        with open(path, "rb") as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as whole:
            for kind, key in ((b'{"type":"custom-title"', "custom"), (b'{"type":"ai-title"', "title")):
                at = whole.rfind(kind)
                if at >= 0:
                    end = whole.find(b"\n", at)
                    for entry in entries(whole[at:end if end > 0 else len(whole)]):
                        info[key] = entry.get("customTitle") or entry.get("aiTitle")
    return info


def scan(cache):
    """Sidebar facts for every top-level transcript, reusing cached ones whose file hasn't changed."""
    fresh = {}
    for path in PROJECTS_DIR.glob("*/*.jsonl"):
        # Session ids reach Claude Code's command line, so only its own uuid-named files count.
        if not SESSION_ID.fullmatch(path.stem):
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        old = cache.get(str(path))
        if old and old["size"] == stat.st_size and old["mtime"] == stat.st_mtime:
            fresh[str(path)] = old
            continue
        try:
            fresh[str(path)] = describe(path, stat)
        except OSError:
            continue
    return fresh


def live():
    """Sessions that a running Claude Code process has open, by session id."""
    files = {}
    for path in LIVE_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("sessionId"):
                files[int(data["pid"])] = data
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            continue
    # A file can outlive its process, and the pid can go to another program, so each one is checked.
    if sys.platform == "win32":
        # The process that wrote the file started before its session did; a later owner of the pid didn't.
        alive = [pid for pid, data in files.items() if started_before(pid, data.get("startedAt"))]
    else:
        alive = [pid for pid, command in commands(files).items() if "claude" in command]
    return {files[pid]["sessionId"]: {"pid": pid, "status": files[pid].get("status"), "name": files[pid].get("name")}
            for pid in alive}


def commands(pids):
    """The command line of each pid that's still running."""
    found = {}
    if sys.platform.startswith("linux"):
        for pid in pids:
            try:
                found[pid] = Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="replace")
            except OSError:
                pass
        return found
    if not pids:
        return found
    try:
        out = subprocess.run(["ps", "-o", "pid=", "-o", "args=", "-p", ",".join(map(str, pids))],
                             capture_output=True, encoding="utf-8", errors="replace", timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return found
    for line in out.stdout.splitlines():
        pid, _, command = line.strip().partition(" ")
        if pid.isdigit():
            found[int(pid)] = command
    return found


def started_before(pid, stamp):
    """Whether a Windows process is running and started no later than `stamp` (ms since 1970)."""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel32.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    try:
        code = wintypes.DWORD()
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != STILL_ACTIVE:
            return False
        if not kernel32.GetProcessTimes(handle, *map(ctypes.byref, times)):
            return False
    finally:
        kernel32.CloseHandle(handle)
    if not isinstance(stamp, (int, float)):
        return True
    created = (times[0].dwHighDateTime << 32 | times[0].dwLowDateTime) // 10_000 - FILETIME_EPOCH_MS
    return created <= stamp + 2000


def find(cache, session_id):
    return next((Path(p) for p, info in cache.items() if info["id"] == session_id), None)


def stringify(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            item.get("text", "") if item.get("type") == "text" else "[image]"
            for item in content if isinstance(item, dict)
        )
    return json.dumps(content)


def trim_input(value):
    if isinstance(value, str):
        return clip(value)
    if isinstance(value, dict):
        return {k: trim_input(v) for k, v in value.items()}
    if isinstance(value, list):
        return [trim_input(v) for v in value[:200]]
    return value


class Reader:
    """Turns transcript entries into Viola messages, and carries on from where it stopped as the file grows."""

    def __init__(self, conv):
        self.conv = conv
        self.tools = {}
        self.api_blocks = set()
        for msg in conv["messages"]:
            for block in msg.get("blocks", []):
                if block.get("type") == "tool":
                    self.tools[block["id"]] = block

    @property
    def messages(self):
        return self.conv["messages"]

    def assistant(self, stamp):
        last = self.messages[-1] if self.messages else None
        if last and last["role"] == "assistant":
            return last
        msg = {"role": "assistant", "blocks": [], "status": "done", "ts": stamp, "model": self.conv["model"],
               "effort": self.conv["effort"]}
        self.messages.append(msg)
        return msg

    def notice(self, text, stamp):
        self.assistant(stamp)["blocks"].append({"type": "notice", "kind": "info", "text": text})

    def user(self, text, stamp):
        self.messages.append({"role": "user", "text": text, "ts": stamp})

    def feed(self, raw):
        for entry in entries(raw):
            if entry.get("isSidechain"):
                continue
            stamp = ms(entry.get("timestamp")) or self.conv["updated"]
            kind = entry.get("type")
            if kind == "user":
                self.feed_user(entry, stamp)
            elif kind == "assistant":
                self.feed_assistant(entry, stamp)
            elif kind == "system":
                self.feed_system(entry, stamp)
            elif kind == "attachment":
                attachment = entry.get("attachment") or {}
                prompt = attachment.get("prompt")
                if (attachment.get("type") == "queued_command" and isinstance(prompt, str)
                        and not prompt.startswith("<")):
                    self.user(PASTE_TAG.sub("", prompt).strip(), stamp)
            elif kind == "cost-state" and isinstance(entry.get("totalCostUSD"), (int, float)):
                self.conv["cost"] = self.conv["cost_seen"] = entry["totalCostUSD"]
            elif kind == "permission-mode" and entry.get("permissionMode") in VIOLA_MODES:
                self.conv["permission_mode"] = entry["permissionMode"]
            elif kind in ("custom-title", "ai-title") and not self.conv.get("renamed"):
                title = entry.get("customTitle") or entry.get("aiTitle")
                if title and (kind == "custom-title" or not self.conv.get("custom_title")):
                    self.conv["title"] = title[:120]
                    self.conv["custom_title"] = self.conv.get("custom_title") or kind == "custom-title"
            if kind in ("user", "assistant") and stamp:
                self.conv["updated"] = max(self.conv["updated"], stamp)

    def feed_user(self, entry, stamp):
        content = entry.get("message", {}).get("content")
        if isinstance(content, list):
            for item in content:
                if item.get("type") == "tool_result":
                    block = self.tools.get(item.get("tool_use_id"))
                    if block is not None:
                        block["result"] = clip(stringify(item.get("content")))
                        block["state"] = "error" if item.get("is_error") else "done"
                elif item.get("type") == "text" and item.get("text", "").startswith("[Request interrupted"):
                    last = self.messages[-1] if self.messages else None
                    if last and last["role"] == "assistant":
                        last["status"] = "interrupted"
        if isinstance(content, str) and content.startswith("[Request interrupted"):
            if self.messages and self.messages[-1]["role"] == "assistant":
                self.messages[-1]["status"] = "interrupted"
            return
        if isinstance(content, str) and content.startswith("<task-notification>"):
            summary = SUMMARY.search(content)
            self.notice(summary.group(1).strip() if summary else "A background task finished", stamp)
            return
        text = prompt_text(entry)
        if text:
            self.user(text, stamp)

    def feed_assistant(self, entry, stamp):
        message = entry.get("message") or {}
        msg = self.assistant(stamp)
        if message.get("model") and not message["model"].startswith("<"):
            msg["model"] = message["model"]
            self.conv["model"] = message["model"]
        if entry.get("effort"):
            msg["effort"] = self.conv["effort"] = entry["effort"]
        for index, item in enumerate(message.get("content") or []):
            if message.get("id") and entry.get("apiBlockIndex") is not None:
                key = (message["id"], entry["apiBlockIndex"] + index)
                if key in self.api_blocks:
                    continue
                self.api_blocks.add(key)
            kind = item.get("type")
            if kind == "text" and item.get("text", "").strip():
                msg["blocks"].append({"type": "text", "text": item["text"]})
            elif kind in ("thinking", "redacted_thinking"):
                took = entry.get("thinkingDurationMs") or 0
                msg["blocks"].append({"type": "thinking", "text": item.get("thinking") or "",
                                      "started": stamp - took, "ended": stamp})
            elif kind in ("tool_use", "server_tool_use"):
                block = {"type": "tool", "id": item.get("id"), "name": item.get("name", "tool"),
                         "input": trim_input(item.get("input")), "state": "running"}
                self.tools[block["id"]] = block
                msg["blocks"].append(block)

    def feed_system(self, entry, stamp):
        sub = entry.get("subtype")
        if sub == "compact_boundary":
            self.notice("Conversation compacted", stamp)
        elif sub == "turn_duration" and self.messages and self.messages[-1]["role"] == "assistant":
            self.messages[-1]["duration_ms"] = entry.get("durationMs")
        elif sub == "scheduled_task_fire":
            self.notice(entry.get("content") or "Scheduled task ran", stamp)
        elif sub == "model_refusal_no_fallback":
            self.notice("The model declined that request", stamp)

    def settle(self, running):
        """Marks tools that never got a result as finished, unless a terminal is still working on them."""
        if running:
            return
        for block in self.tools.values():
            if block["state"] == "running":
                block["state"] = "done"


def new_conv(info, config):
    created = info["created"] or info["updated"]
    return {
        "id": info["id"],
        "title": (info["custom"] or info["title"] or info["prompt"] or "Terminal chat")[:120],
        "created": created,
        "updated": created,
        "session_id": info["id"],
        "session_started": True,
        "cwd": info["cwd"] or str(Path.home()),
        "model": config["model"],
        "effort": config["effort"],
        "permission_mode": config["permission_mode"],
        "cost": 0.0,
        "cost_seen": 0.0,
        "seq": 0,
        "messages": [],
        "source": {"path": "", "offset": 0},
    }


def read_new(conv, reader):
    """Feeds what was appended to the transcript since the last read: True if anything changed, None if it shrank."""
    source = conv["source"]
    path = Path(source["path"])
    try:
        size = path.stat().st_size
    except OSError:
        return False
    if size < source["offset"]:
        return None
    if size == source["offset"]:
        return False
    with open(path, "rb") as fh:
        fh.seek(source["offset"])
        raw = fh.read(size - source["offset"])
    # A line still being written has no newline yet; it's read next time.
    end = raw.rfind(b"\n") + 1
    if not end:
        return False
    reader.feed(raw[:end])
    source["offset"] += end
    return True


def trim_history(conv):
    extra = len(conv["messages"]) - MESSAGE_LIMIT
    if extra <= 0:
        return
    while extra < len(conv["messages"]) and conv["messages"][extra]["role"] != "user":
        extra += 1
    conv["messages"] = conv["messages"][extra:]
    conv["trimmed"] = conv.get("trimmed", 0) + extra
