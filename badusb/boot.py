# boot.py — runs before code.py on CircuitPython
# Disables USB mass storage so CIRCUITPY drive doesn't show on target.
# The board still enumerates as HID keyboard.
#
# ⚠️ ONCE FLASHED: you can't edit files without factory reset.
#    Hold BOOT + tap RESET → release BOOT → reflash CircuitPython .uf2
#
# TEST WITHOUT THIS FIRST. Only deploy boot.py once code.py is verified.

import storage
storage.disable_usb_drive()
