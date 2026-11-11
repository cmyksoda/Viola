"""A stand-in for the claude program that speaks just enough stream-json for Viola's tests."""

import json
import os
import queue
import sys
import threading
import time

args = sys.argv[1:]
log_path = os.environ.get("VIOLA_TEST_LOG")


def log(kind, value):
    if log_path:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"pid": os.getpid(), kind: value}) + "\n")


def out(event):
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def option(name):
    return args[args.index(name) + 1] if name in args else None


log("args", args)
if "--version" in args:
    print("9.9.9 (Claude Code)")
    sys.exit(0)
if option("--output-format") == "json":
    sys.stdin.read()
    print(json.dumps({"result": "Test chat title", "total_cost_usd": 0.0001, "is_error": False}))
    sys.exit(0)

session = option("--session-id") or option("--resume")
lines = queue.Queue()


def read_input():
    for line in sys.stdin:
        log("stdin", line.strip()[:200])
        lines.put(json.loads(line))
        # Like a Claude Code busy with a tool: what's sent meanwhile waits in the pipe.
        if "lazy" in line:
            time.sleep(3)
    lines.put(None)


threading.Thread(target=read_input, daemon=True).start()
total = 0.0
waiting = []


class Interrupted(Exception):
    pass


def pause(seconds):
    """Sleeps, answering an interrupt the way Claude Code does, and keeping user messages for later."""
    end = time.time() + seconds
    while True:
        try:
            event = lines.get(timeout=max(0.0, end - time.time()))
        except queue.Empty:
            return
        if event is None:
            lines.put(None)
            time.sleep(max(0.0, end - time.time()))
            return
        if event.get("type") == "control_request":
            out({"type": "control_response",
                 "response": {"subtype": "success", "request_id": event["request_id"], "response": {}}})
            if event["request"]["subtype"] == "interrupt":
                raise Interrupted
        else:
            waiting.append(event)


def finish(text, cost):
    global total
    total += cost
    out({"type": "result", "subtype": "success", "is_error": False, "result": text, "total_cost_usd": total,
         "usage": {"input_tokens": 10, "cache_read_input_tokens": 100, "cache_creation_input_tokens": 0,
                   "output_tokens": 5}})


def answer(event, first):
    content = event["message"]["content"]
    prompt = (content if isinstance(content, str)
              else " ".join(b.get("text", "") for b in content if b.get("type") == "text"))
    if first:
        out({"type": "system", "subtype": "init", "session_id": session, "slash_commands": ["compact"]})
    out({"type": "user", "isReplay": True, "message": {"role": "user", "content": content}})
    api = f"msg_{time.time_ns()}"
    out({"type": "stream_event", "api_message_id": api,
         "event": {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}})
    words = ["Hello ", "from ", "the ", "test ", "stub."]
    try:
        for word in words:
            out({"type": "stream_event", "api_message_id": api,
                 "event": {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": word}}})
            pause(0.01)
        if "slow" in prompt or "lazy" in prompt:
            # Silent, like Claude Code waiting on the API, so only a real stop can end it.
            pause(60)
    except Interrupted:
        out({"type": "user",
             "message": {"role": "user", "content": [{"type": "text", "text": "[Request interrupted by user]"}]}})
        finish("", 0.002)
        return
    out({"type": "stream_event", "api_message_id": api, "event": {"type": "content_block_stop", "index": 0}})
    finish("".join(words), 0.001)


first = True
while True:
    event = waiting.pop(0) if waiting else lines.get()
    if event is None:
        break
    if event.get("type") == "control_request":
        out({"type": "control_response",
             "response": {"subtype": "success", "request_id": event["request_id"], "response": {}}})
        continue
    answer(event, first)
    first = False
