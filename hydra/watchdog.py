"""
Hydra v4 — Process-level watchdog.
Spawns a SEPARATE watchdog process, not a daemon thread.
If the main process dies, the watchdog restarts it.
The watchdog also monitors itself — if the main process dies,
both die together, so we need cross-monitoring.

Pattern:
- Main process launches watchdog.exe (separate process)
- Watchdog monitors main PID via OpenProcess
- If main dies, watchdog relaunches it
- Main monitors watchdog PID — if watchdog dies, main relaunches it
- Both write their PIDs to a shared temp file
"""
import os
import sys
import time
import subprocess
import tempfile
import ctypes


def start_watchdog(cfg: dict, me: dict):
    """Launch watchdog as a separate process."""
    exe_path = _get_exe_path()
    watchdog_file = os.path.join(tempfile.gettempdir(), ".hydra_watchdog.txt")

    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0

        subprocess.Popen(
            [exe_path, "--watchdog", str(os.getpid())],
            startupinfo=si,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=0x00000008  # DETACHED_PROCESS
        )

        # Write our PID so watchdog can find us
        with open(watchdog_file, "w") as f:
            f.write(f"WATCHDOG_MAIN={os.getpid()}\n")
        ctypes.windll.kernel32.SetFileAttributesW(watchdog_file, 2)

    except:
        pass


def watchdog_entry(parent_pid: int):
    """
    Entry point when running as watchdog (--watchdog <pid>).
    Monitors the parent process and relaunches if it dies.
    """
    exe_path = _get_exe_path()
    parent_pid = int(parent_pid)

    while True:
        try:
            if not _process_alive(parent_pid):
                # Parent died — relaunch it
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 0

                new_proc = subprocess.Popen(
                    [exe_path, "--silent"],
                    startupinfo=si,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=0x00000008
                )

                # Update watchdog file
                watchdog_file = os.path.join(tempfile.gettempdir(), ".hydra_watchdog.txt")
                try:
                    with open(watchdog_file, "w") as f:
                        f.write(f"WATCHDOG_MAIN={new_proc.pid}\n")
                except:
                    pass

                parent_pid = new_proc.pid

            time.sleep(15)

        except:
            time.sleep(15)


def _process_alive(pid: int) -> bool:
    """Check if a process is still running via OpenProcess + GetExitCodeProcess."""
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x0400, False, pid)
        if not handle:
            return False
        exit_code = ctypes.c_uint(0)
        kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
        kernel32.CloseHandle(handle)
        return exit_code.value == 259  # STILL_ACTIVE
    except:
        return False


def _get_exe_path() -> str:
    """Get the path to our executable."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(sys.argv[0] if sys.argv else __file__)
