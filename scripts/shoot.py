"""Automatic screenshots of the live dashboard during dark sessions.

The demo video needs footage of the market while it is shut, and that window
opens Friday 20:00 ET and closes Monday 09:30. Rather than depend on a human
being awake inside it, this captures the live page on a schedule and commits
the images, so the visual evidence exists whether anyone records or not.

Runs headless Edge (or Chrome). Called from the capture cycle; it only fires
during a DARK session and at most once per hour.
"""
import os
import subprocess
import sys
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from session import classify, ET, DARK

URL = "https://egbujor-emmanuel.github.io/nocturne/"
SHOTS = os.path.join(ROOT, "shots")
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",          # GitHub Actions ubuntu runner
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
]


def browser():
    for b in BROWSERS:
        if os.path.exists(b):
            return b
    return None


def shoot(path, width=1500, height=2400, wait_ms=6000):
    """Render the live page to a PNG. Uses classic --headless: --headless=new
    hangs indefinitely on this Edge build. virtual-time-budget lets the fetch
    and chart JS finish, otherwise the shot is the empty loading state."""
    b = browser()
    if not b:
        return False, "no browser found"
    args = [b, "--headless", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
            "--no-first-run", "--no-default-browser-check",
            "--virtual-time-budget=%d" % wait_ms,
            "--window-size=%d,%d" % (width, height),
            "--screenshot=%s" % path, URL]
    try:
        subprocess.run(args, capture_output=True, timeout=120,
                       creationflags=CREATE_NO_WINDOW)
    except Exception as e:
        return False, "%s: %s" % (type(e).__name__, str(e)[:60])
    if os.path.exists(path) and os.path.getsize(path) > 20000:
        return True, "%d bytes" % os.path.getsize(path)
    return False, "no image written"


def due(now=None):
    """Only during a dark session, and at most one shot per hour."""
    now = now or dt.datetime.now(dt.timezone.utc)
    if classify(now) not in DARK:
        return None
    et = now.astimezone(ET)
    name = et.strftime("%Y-%m-%d_%H00_ET") + ".png"
    path = os.path.join(SHOTS, name)
    return None if os.path.exists(path) else path


def main(force=False):
    os.makedirs(SHOTS, exist_ok=True)
    if force:
        et = dt.datetime.now(ET)
        path = os.path.join(SHOTS, et.strftime("%Y-%m-%d_%H%M_ET") + "_manual.png")
    else:
        path = due()
        if not path:
            print("not due (session not dark, or this hour already captured)")
            return 0
    ok, detail = shoot(path)
    print("%s %s  %s" % ("shot" if ok else "FAILED", os.path.basename(path), detail))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(force="--force" in sys.argv))
