"""Viola's backend end to end, against a stand-in claude, on whichever system runs the tests."""

import http.client
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

# The sandbox goes first: server reads the environment it sets up when it's imported.
import sandbox
from sandbox import BASE, FAKE, HOME, LOG, ROOT, WINDOWS, app, httpd
import viola
import server
import sessions


def tearDownModule():
    sandbox.close()


def api(method, path, body=None):
    request = urllib.request.Request(
        f"{BASE}/api/{path}", method=method, data=None if body is None else json.dumps(body).encode(),
        headers={"X-Viola-Token": app.config["token"], "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as resp:
        return json.load(resp)


def claude_log():
    if not LOG.exists():
        return []
    return [json.loads(line) for line in LOG.read_text(encoding="utf-8").splitlines()]


def running(pid):
    if WINDOWS:
        return sessions.started_before(pid, None)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


class Events:
    def __init__(self, token=None):
        self.queue = queue.Queue()
        self.ended = threading.Event()
        self.stream = urllib.request.urlopen(f"{BASE}/api/events?token={token or app.config['token']}", timeout=60)
        threading.Thread(target=self.read, daemon=True).start()

    def read(self):
        try:
            for line in self.stream:
                if line.startswith(b"data: "):
                    self.queue.put(json.loads(line[6:]))
        except (OSError, ValueError):
            pass
        self.ended.set()

    def wait(self, test, timeout=15):
        end = time.time() + timeout
        while time.time() < end:
            try:
                event = self.queue.get(timeout=end - time.time())
            except queue.Empty:
                break
            if test(event):
                return event
        raise AssertionError("the expected event never came")


# One stream for every test: closing one waits for the server's next keep-alive.
events = Events()


class Turns(unittest.TestCase):
    def setUp(self):
        self.conv = api("POST", "conversations", {"cwd": str(HOME)})

    def turn_end(self, timeout=15):
        return events.wait(lambda e: e.get("t") == "turn_end" and e.get("conv_id") == self.conv["id"], timeout)

    def first_delta(self):
        events.wait(lambda e: e.get("t") == "delta" and e.get("conv_id") == self.conv["id"])

    def send(self, text):
        api("POST", f"conversations/{self.conv['id']}/send", {"text": text})

    def test_reply(self):
        self.send("hi")
        msg = self.turn_end()["msg"]
        self.assertEqual(msg["status"], "done")
        self.assertEqual("".join(b["text"] for b in msg["blocks"] if b["type"] == "text"), "Hello from the test stub.")
        args = [entry["args"] for entry in claude_log() if "--settings" in entry.get("args", [])][-1]
        self.assertEqual(json.loads(args[args.index("--settings") + 1]), {"showThinkingSummaries": True})

    def test_second_message_resumes(self):
        self.send("one")
        self.turn_end()
        self.send("two")
        self.assertEqual(self.turn_end()["msg"]["status"], "done")
        args = [entry["args"] for entry in claude_log() if "--resume" in entry.get("args", [])]
        self.assertIn(api("GET", f"conversations/{self.conv['id']}")["session_id"],
                      [a[a.index("--resume") + 1] for a in args])

    def test_stop_asks_claude_code(self):
        self.send("slow")
        self.first_delta()
        started = time.time()
        api("POST", f"conversations/{self.conv['id']}/stop")
        msg = self.turn_end()["msg"]
        self.assertEqual(msg["status"], "interrupted")
        # Ended by the interrupt, well before the outside fallback would have started.
        self.assertLess(time.time() - started, 3)
        self.assertGreater(msg.get("cost", 0), 0)
        self.assertTrue(any('"interrupt"' in entry.get("stdin", "") for entry in claude_log()))

    def test_missing_folder(self):
        gone = HOME / "unplugged"
        gone.mkdir()
        conv = api("POST", "conversations", {"cwd": str(gone)})
        gone.rmdir()
        api("POST", f"conversations/{conv['id']}/send", {"text": "hi"})
        msg = events.wait(lambda e: e.get("t") == "turn_end" and e.get("conv_id") == conv["id"])["msg"]
        self.assertEqual(msg["status"], "error")
        self.assertIn("isn't there right now", msg["error"])
        with self.assertRaises(urllib.error.HTTPError):
            api("POST", "conversations", {"cwd": str(gone)})

    def test_stop_before_claude_starts(self):
        turn = server.Turn(app, self.conv, {"blocks": []})
        self.assertIsNone(turn.stop())
        self.assertTrue(turn.stopping)

    def test_closing_viola_ends_replies(self):
        self.send("slow")
        self.first_delta()
        proc = app.turns[self.conv["id"]].proc
        with mock.patch.object(app, "closing", False):
            app.shutdown()
        self.assertIsNotNone(proc.poll())
        app.closing = False
        self.turn_end()

    def test_a_big_message_never_blocks_viola(self):
        self.send("lazy")
        self.first_delta()
        # Far more than a pipe holds, so writing it waits until Claude Code reads again.
        self.send("x" * 400_000)
        started = time.time()
        api("GET", "state")
        self.assertLess(time.time() - started, 1.5)
        api("POST", f"conversations/{self.conv['id']}/stop")
        self.turn_end()

    def test_stop_with_a_queued_message(self):
        self.send("slow")
        self.first_delta()
        self.send("and then this")
        pid = max(entry["pid"] for entry in claude_log() if "args" in entry)
        api("POST", f"conversations/{self.conv['id']}/stop")
        end = self.turn_end()
        self.assertEqual(end["msg"]["status"], "interrupted")
        # Stop means stop: the queued message goes back to the page instead of starting another reply.
        self.assertEqual([m["text"] for m in end["pending"]], ["and then this"])
        time.sleep(1)
        self.assertFalse(api("GET", f"conversations/{self.conv['id']}").get("running"))
        self.assertFalse(running(pid))
        texts = [m.get("text") for m in api("GET", f"conversations/{self.conv['id']}")["messages"]
                 if m["role"] == "user"]
        self.assertEqual(texts, ["slow"])


class LiveSessions(unittest.TestCase):
    def test_only_running_claude_counts(self):
        folder = Path(os.environ["CLAUDE_CONFIG_DIR"]) / "sessions"
        folder.mkdir(parents=True, exist_ok=True)
        claude = subprocess.Popen([sys.executable, str(FAKE)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL)
        other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        gone = subprocess.Popen([sys.executable, "-c", "pass"])
        gone.wait()
        now = int(time.time() * 1000) + 1000
        try:
            for pid, session, started in ((claude.pid, "alive", now), (other.pid, "reused", 1000),
                                          (gone.pid, "gone", now)):
                (folder / f"{pid}.json").write_text(
                    json.dumps({"pid": pid, "sessionId": session, "startedAt": started}))
            # macOS has no /proc and asks ps instead, which works on Linux too.
            for platform in [sys.platform] + ([] if WINDOWS else ["darwin"]):
                with mock.patch.object(sys, "platform", platform):
                    found = sessions.live()
                self.assertIn("alive", found, platform)
                self.assertNotIn("reused", found, platform)
                self.assertNotIn("gone", found, platform)
        finally:
            for proc in (claude, other):
                proc.kill()
                proc.wait()
            for path in folder.glob("*.json"):
                path.unlink()


class Pieces(unittest.TestCase):
    def test_list_dirs(self):
        root = HOME / "pick"
        for name in ("B", "a", ".hidden"):
            (root / name).mkdir(parents=True)
        (root / "file.txt").write_text("x")
        data = server.list_dirs(str(root))
        self.assertEqual(data["dirs"], ["a", "B"])
        self.assertEqual(Path(data["parent"]), root.parent)
        # A link keeps the name it was opened by, so its chats match ones started there in a terminal.
        if not WINDOWS:
            (HOME / "linked").symlink_to(root)
            self.assertEqual(server.list_dirs(str(HOME / "linked"))["path"], str(HOME / "linked"))
        for bad in (root / "missing", root / "file.txt"):
            with self.assertRaises(ValueError):
                server.list_dirs(str(bad))
        self.assertIsNone(server.list_dirs(os.path.abspath(os.sep))["parent"])

    def test_upload_names(self):
        for name, saved in (("photo.png", "photo.png"), ("con.txt", "_con.txt"),
                            ("x" * 300 + ".txt", "x" * 100 + ".txt"), ("..", "file")):
            info = server.save_upload(name, b"hi")
            self.assertEqual(info["name"], saved)
            self.assertEqual(server.upload_path(info).read_bytes(), b"hi")

    def test_key_from_a_shell_file(self):
        rc = HOME / ".zshrc"
        rc.write_text('export VIOLA_API_KEY="sk-from-zshrc"\n')
        try:
            self.assertEqual(server.resolve_api_key({"api_key": ""}), ("sk-from-zshrc", "~/.zshrc"))
            with mock.patch.dict(os.environ, VIOLA_API_KEY="sk-from-env"):
                self.assertEqual(server.resolve_api_key({"api_key": ""}), ("sk-from-env", "VIOLA_API_KEY"))
            self.assertEqual(server.resolve_api_key({"api_key": "sk-app"}), ("sk-app", "app settings"))
        finally:
            rc.unlink()

    def test_parent_session_markers(self):
        markers = {"CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": "x", "CLAUDE_CODE_CHILD_SESSION": "1"}
        mine = {"CLAUDE_CODE_GIT_BASH_PATH": r"C:\Git\bin\bash.exe", "CLAUDE_CODE_USE_BEDROCK": "1"}
        with mock.patch.dict(os.environ, {**markers, **mine, "VIOLA_API_KEY": "sk-viola"}):
            env = server.child_env(app.config)
        self.assertFalse(set(markers) & set(env))
        self.assertEqual({k: env[k] for k in mine}, mine)
        self.assertNotIn("VIOLA_API_KEY", env)
        self.assertEqual(env["ANTHROPIC_API_KEY"], "sk-viola")

    def test_json_round_trip(self):
        path = HOME / "data.json"
        data = {"text": "héllo ☃ 日本", "lone": "\ud800"}
        server.write_json(path, data)
        self.assertEqual(server.read_json(path), data)

    def test_someone_else_on_the_port(self):
        impostor = server.make_server(app, "127.0.0.1", 0)
        impostor.RequestHandlerClass.app = mock.Mock(config={"token": "not-yours"})
        threading.Thread(target=impostor.serve_forever, daemon=True).start()
        try:
            with self.assertRaises(SystemExit):
                viola.existing_instance(impostor.server_address[1], app.config["token"])
        finally:
            impostor.shutdown()
            impostor.server_close()

    def test_reset_link(self):
        def call(path, token, method="POST"):
            body = b"{}" if method == "POST" else None
            request = urllib.request.Request(f"{BASE}/api/{path}", method=method, data=body,
                                             headers={"X-Viola-Token": token, "Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=10) as resp:
                return json.load(resp)

        # Settings from before the phone had its own token keep the phone's old link working.
        app.config.update(remote_token=app.config["token"])
        shared = app.config["token"]
        stream = Events(shared)
        first = call("remote/reset", shared)
        self.assertTrue(first["token"])
        self.assertNotEqual(first["token"], shared)
        stream.ended.wait(10)
        self.assertTrue(stream.ended.is_set())
        with self.assertRaises(urllib.error.HTTPError):
            call("state", shared, "GET")

        # From then on only the phone's token changes, and only this computer may change it.
        local, phone = app.config["token"], app.config["remote_token"]
        self.assertNotEqual(local, phone)
        self.assertTrue(call("state", phone, "GET")["settings"])
        with self.assertRaises(urllib.error.HTTPError) as refused:
            call("remote/reset", phone)
        self.assertEqual(refused.exception.code, 403)
        self.assertIsNone(call("remote/reset", local)["token"])
        self.assertEqual(app.config["token"], local)
        with self.assertRaises(urllib.error.HTTPError):
            call("state", phone, "GET")
        # The shared stream the other tests listen on was opened with the old token.
        global events
        events = Events()

    def test_bad_tokens_are_refused(self):
        for token in ("wrong", "ünïcode"):
            connection = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=10)
            connection.putrequest("GET", "/api/state")
            connection.putheader("X-Viola-Token", token.encode("utf-8"))
            connection.endheaders()
            self.assertEqual(connection.getresponse().status, 401, token)

    def test_unread_body_closes_the_connection(self):
        connection = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=10)
        smuggled = b"GET /api/ping HTTP/1.1\r\nHost: x\r\n\r\n"
        connection.request("POST", "/api/settings", body=smuggled, headers={"X-Viola-Token": "wrong"})
        response = connection.getresponse()
        response.read()
        self.assertEqual(response.status, 401)
        self.assertTrue(response.will_close)

    def test_private_files(self):
        info = server.save_upload("page.html", b"<script>alert(1)</script>")
        connection = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=10)
        connection.request("GET", f"/api/files/{info['id']}/page.html?token={app.config['token']}")
        response = connection.getresponse()
        response.read()
        self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")
        self.assertIn("sandbox", response.getheader("Content-Security-Policy"))
        self.assertEqual(response.getheader("Content-Disposition"), "attachment")
        if not WINDOWS:
            self.assertEqual(server.upload_path(info).stat().st_mode & 0o777, 0o600)
            self.assertEqual(server.DATA_DIR.stat().st_mode & 0o777, 0o700)
            self.assertEqual(server.CONFIG_PATH.stat().st_mode & 0o777, 0o600)
            app.store.create(app.config)
            self.assertTrue(all(p.stat().st_mode & 0o077 == 0 for p in server.CONV_DIR.glob("*.json")))

    def test_terminal_chats_stay_off_until_turned_on(self):
        folder = Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects" / "-some-project"
        folder.mkdir(parents=True, exist_ok=True)
        session = "0f0f0f0f-1111-2222-3333-444444444444"
        line = {"type": "user", "message": {"content": "hello from a terminal"}, "cwd": str(ROOT),
                "timestamp": "2026-10-28T00:00:00Z"}
        (folder / f"{session}.jsonl").write_text(json.dumps(line) + "\n")
        (folder / "not-a-session.jsonl").write_text(json.dumps(line) + "\n")
        try:
            app.config.update(terminal_chats=False)
            app.refresh_sessions()
            self.assertEqual(api("GET", "state")["sessions"], [])
            with self.assertRaises(urllib.error.HTTPError):
                api("GET", f"conversations/{session}")
            app.config.update(terminal_chats=True)
            app.refresh_sessions()
            self.assertEqual([s["id"] for s in api("GET", "state")["sessions"]], [session])
            self.assertEqual(api("GET", f"conversations/{session}")["messages"][0]["text"], "hello from a terminal")
        finally:
            app.config.update(terminal_chats=False)
            api("DELETE", f"conversations/{session}")

    def test_static_files_stay_inside_web(self):
        connection = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=10)
        for path, status in (("/", 200), ("/app.js", 200), ("/../server.py", 404), ("/..%2fserver.py", 404),
                             ("/..\\server.py", 404)):
            connection.request("GET", path)
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, status, path)

    def test_settings_describe_the_system(self):
        settings = api("GET", "state")["settings"]
        self.assertEqual(settings["sep"], os.sep)
        self.assertEqual(settings["claude_version"], "9.9.9")

    @unittest.skipIf(WINDOWS, "the macOS terminal script is a shell script")
    def test_mac_terminal_script(self):
        folder = HOME / "it's a folder"
        folder.mkdir()
        out = HOME / "terminal-out.txt"
        probe = ("import os, sys; "
                 "open(sys.argv[1], 'w').write(os.getcwd() + '|' + os.environ.get('ANTHROPIC_API_KEY', ''))")
        with mock.patch.object(server.subprocess, "Popen") as popen:
            server.open_mac_terminal([sys.executable, "-c", probe, str(out)], str(folder),
                                     {"ANTHROPIC_API_KEY": "sk-1 2"})
        script = popen.call_args[0][0][1]
        subprocess.run(["sh", script], env=dict(os.environ, SHELL=shutil.which("true")), check=True)
        self.assertEqual(out.read_text(), f"{folder.resolve()}|sk-1 2")
        self.assertFalse(os.path.exists(script))

    @unittest.skipUnless(WINDOWS, "Windows' terminal command")
    def test_windows_terminal_command(self):
        conv = {"session_id": "abc", "cwd": str(HOME)}
        with mock.patch.object(server, "claude_binary", return_value=r"C:\Program Files\R&D\claude.exe"), \
                mock.patch.object(server.subprocess, "Popen") as popen:
            app.open_terminal(conv)
        self.assertEqual(popen.call_args[0][0], [r"C:\Program Files\R&D\claude.exe", "--resume", "abc"])
        self.assertEqual(popen.call_args[1]["creationflags"], subprocess.CREATE_NEW_CONSOLE)

    def test_viola_runs_as_a_server(self):
        with socket_port() as port:
            app.config.update(port=port)
        env = dict(os.environ, PYTHONUNBUFFERED="1")
        proc = subprocess.Popen([sys.executable, str(ROOT / "viola.py"), "--server-only"], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            self.assertIn(f"127.0.0.1:{port}", proc.stdout.readline())
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping?nonce=abc", timeout=10) as resp:
                answer = json.load(resp)
            self.assertEqual(answer["proof"], server.ping_proof(app.config["token"], "abc"))
            # A second window attaches to it instead of starting another backend.
            self.assertTrue(viola.existing_instance(port, app.config["token"]))
        finally:
            proc.kill()
            proc.wait()
            proc.stdout.close()


class socket_port:
    def __enter__(self):
        import socket

        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        return self.sock.getsockname()[1]

    def __exit__(self, *exc):
        self.sock.close()


if __name__ == "__main__":
    unittest.main()
