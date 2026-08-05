# boot.py — runs before code.py
# Disables USB mass storage so CIRCUITPY drive doesn't show on target
# The Pico still works as HID keyboard, just no file access
# 
# WARNING: Once you flash this, you can't edit files on the Pico 
# without factory reset! Only use on the deploy version.
#
# To recover: hold BOOTSEL → reflash CircuitPython .uf2

import storage
import usb_cdc

# Disable USB drive (CIRCUITPY) — target sees only keyboard
storage.disable_usb_drive()

# Optional: disable serial too for full stealth
# usb_cdc.disable()
