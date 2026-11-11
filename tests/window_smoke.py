"""Opens Viola's own window on macOS or Windows, checks that the page started, and closes it.

Needs pywebview and a desktop, so it runs on CI machines rather than with the unit tests.
"""

import sys
import threading
import time

import sandbox
import viola

URL = f"{sandbox.BASE}/#token={sandbox.app.config['token']}"
greeting = []


def check():
    import webview

    end = time.time() + 60
    while time.time() < end and not greeting:
        try:
            # The welcome greeting appears once the page has loaded its state from the backend.
            text = webview.windows[0].evaluate_js("document.getElementById('greeting-text').textContent")
            if text:
                greeting.append(text)
        except Exception:  # the window or page may not be there yet
            pass
        time.sleep(0.5)
    if webview.windows:
        webview.windows[0].destroy()


threading.Thread(target=check, daemon=True).start()
opened = viola.run_webview(URL, sandbox.app)
sandbox.close()
print(f"window opened: {opened}, greeting: {greeting}")
sys.exit(0 if opened and greeting else 1)
