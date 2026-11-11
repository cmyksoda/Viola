#!/usr/bin/env python3
"""Viola: a small desktop window for chatting with Claude Code on API credits."""

import argparse
import hmac
import json
import os
import secrets
import subprocess
import sys
import threading
import urllib.request
import webbrowser

import server

ICON = server.WEB_DIR / "icon.svg"


def existing_instance(port, token):
    """True if this user's Viola already answers on the port; exits if something else does."""
    nonce = secrets.token_hex(16)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping?nonce={nonce}", timeout=1) as resp:
            answer = json.load(resp)
    except (OSError, ValueError):
        return False
    # Another account's program could be listening there, and the window would hand it the token.
    proof = answer.get("proof") if isinstance(answer, dict) else None
    if proof is None and isinstance(answer, dict) and answer.get("app") == "viola":
        sys.exit(f"An older version of Viola is still running on port {port}. Quit it, then open Viola again.")
    if not hmac.compare_digest(str(proof), server.ping_proof(token, nonce)):
        sys.exit(f"Something else is using port {port}, so Viola can't start. Close it, or change \"port\" in "
                 f"{server.CONFIG_PATH}.")
    return True


def applescript_string(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def notify(conv, msg):
    status = msg.get("status")
    body = "Finished replying" if status == "done" else f"Stopped ({status})"
    if server.MACOS:
        command = ["osascript", "-e",
                   f"display notification {applescript_string(body)} "
                   f"with title {applescript_string(conv['title'])}"]
    else:
        command = ["notify-send", "--app-name=Viola", f"--icon={ICON}", "--", conv["title"], body]
    try:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def run_window(url, app):
    """The GTK window on Linux. Returns False when WebKitGTK isn't installed."""
    # WebKit's DMA-BUF renderer can't allocate buffers on NVIDIA drivers, leaving the window blank.
    os.environ.setdefault("WEBKIT_DISABLE_DMABUF_RENDERER", "1")
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("WebKit2", "4.1")
    except (ImportError, ValueError):
        return False
    from gi.repository import GLib

    # Must happen before GTK starts, or Wayland gets "python3" as the app id and KDE finds no icon.
    GLib.set_prgname("viola")
    GLib.set_application_name("Viola")
    from gi.repository import Gio, Gtk, WebKit2

    window = Gtk.Window(title="Viola")
    window.set_default_size(1240, 840)
    if ICON.exists():
        try:
            window.set_icon_from_file(str(ICON))
        except GLib.Error:
            pass

    view = WebKit2.WebView()
    settings = view.get_settings()
    settings.set_enable_developer_extras(True)
    settings.set_javascript_can_access_clipboard(True)
    settings.set_enable_back_forward_navigation_gestures(False)

    def open_outside(uri):
        if uri.startswith(("http://", "https://", "mailto:")):
            Gio.AppInfo.launch_default_for_uri(uri, None)

    def on_policy(_view, decision, kind):
        if kind == WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION:
            open_outside(decision.get_navigation_action().get_request().get_uri())
            decision.ignore()
            return True
        if kind == WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
            uri = decision.get_navigation_action().get_request().get_uri()
            if not uri.startswith(url.split("#")[0]):
                open_outside(uri)
                decision.ignore()
                return True
        return False

    # The page asks for the theme's icon ("" for the classic one) when "Match app icon to theme" is on.
    def on_icon(_manager, result):
        theme = result.get_js_value().to_string()
        icon = server.WEB_DIR / "icons" / f"{theme}.svg"
        try:
            window.set_icon_from_file(str(icon if theme.replace("-", "").isalnum() and icon.exists() else ICON))
        except GLib.Error:
            pass

    manager = view.get_user_content_manager()
    manager.connect("script-message-received::violaIcon", on_icon)
    manager.register_script_message_handler("violaIcon")

    view.connect("decide-policy", on_policy)
    view.load_uri(url)
    window.add(view)

    if app:
        def on_turn_end(conv, msg):
            def check():
                if not window.is_active():
                    notify(conv, msg)
                return False

            GLib.idle_add(check)

        app.on_turn_end = on_turn_end

    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()
    return True


def run_webview(url, app):
    """The window on macOS (Safari's engine) and Windows (Edge's). Returns False without pywebview."""
    try:
        import webview
    except ImportError:
        return False
    window = webview.create_window("Viola", url, width=1240, height=840)

    if app and server.MACOS:
        def on_turn_end(conv, msg):
            def check():
                try:
                    focused = window.evaluate_js("document.hasFocus()")
                except Exception:  # the window may be closing
                    return
                if not focused:
                    notify(conv, msg)

            threading.Thread(target=check, daemon=True).start()

        app.on_turn_end = on_turn_end

    if server.MACOS:
        try:
            from AppKit import NSApplication, NSImage

            image = NSImage.alloc().initWithContentsOfFile_(str(server.WEB_DIR / "icon-512.png"))
            NSApplication.sharedApplication().setApplicationIconImage_(image)
        except Exception:  # only the Dock icon depends on it
            pass
    try:
        # Not private, so the page's own storage (theme, sidebar) lasts between runs.
        webview.start(private_mode=False, storage_path=str(server.DATA_DIR / "webview"))
    except Exception as exc:  # e.g. Windows without the Edge WebView2 runtime
        print(f"Viola couldn't open its window ({exc}), so it opens in your browser instead.", flush=True)
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-only", action="store_true", help="run the backend without a window")
    parser.add_argument("--browser", action="store_true", help="open in the default browser instead of a window")
    args = parser.parse_args()

    config = server.Config()
    port = config["port"]
    url = f"http://127.0.0.1:{port}/#token={config['token']}"

    app = None
    httpd = None
    if existing_instance(port, config["token"]):
        if args.server_only:
            sys.exit(f"Viola is already running on port {port}")
    else:
        app = server.App()
        httpd = server.make_server(app, "127.0.0.1", port)
        if app.config["remote"]:
            # The computer may be on someone else's network now, so only Tailscale sharing comes back by itself.
            app.set_remote(True, home_network=False)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()

    open_window = run_window if server.LINUX else run_webview
    try:
        if args.server_only:
            print(f"Viola listening on {url}", flush=True)
            threading.Event().wait()
        elif args.browser or not open_window(url, app):
            if not args.browser:
                needs = "WebKitGTK 4.1 and PyGObject" if server.LINUX else "pywebview"
                print(f"Viola is opening in your browser. For a window of its own, install {needs}.", flush=True)
            webbrowser.open(url)
            if httpd:
                threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        if app:
            app.shutdown()


if __name__ == "__main__":
    main()
