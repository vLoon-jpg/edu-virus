#!/usr/bin/env python3
"""
Hydra v4 — XOR string encoder.
Encodes strings so you can paste them into build.py REAL_CONFIG or core.py.

Usage:
    python xor_encoder.py                    # interactive mode
    python xor_encoder.py "your string here"  # encode one string
    python xor_encoder.py --file urls.txt    # encode all lines from file
"""
import sys
import os

_XK = bytes([0x5E, 0x3F, 0xA1, 0x77, 0x12, 0x8C, 0x4B, 0xE9,
             0x6D, 0x2A, 0xF3, 0x55, 0x1C, 0x9E, 0x7F, 0xD0])


def xor_encode(text):
    """XOR-encode a string and return the Python bytes literal."""
    data = text.encode() if isinstance(text, str) else text
    key = _XK * (len(data) // len(_XK) + 1)
    result = bytes(a ^ b for a, b in zip(data, key[:len(data)]))
    return str(result)[2:-1]  # strip b'...'


def xor_decode(data):
    """Decode XOR-encoded bytes back to text."""
    if isinstance(data, str):
        # Handle escaped Python bytes literal
        data = bytes(data, 'utf-8').decode('unicode_escape').encode('latin-1')
    key = _XK * (len(data) // len(_XK) + 1)
    return bytes(a ^ b for a, b in zip(data, key[:len(data)])).decode()


def _print_encoded(text):
    encoded = xor_encode(text)
    print(f"\n  Input:  {text}")
    print(f"  Encoded: {encoded}")
    print(f"  Paste as: _d(b'{encoded}')")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--file":
        # Batch encode from file
        if len(sys.argv) < 3:
            print("Usage: python xor_encoder.py --file <path>")
            sys.exit(1)
        with open(sys.argv[2], "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    _print_encoded(line)
    elif len(sys.argv) > 1 and sys.argv[1] == "--decode":
        # Decode mode
        if len(sys.argv) < 3:
            print("Usage: python xor_encoder.py --decode <bytes_string>")
            sys.exit(1)
        try:
            raw = sys.argv[2].encode('latin-1')
            print(xor_decode(raw))
        except Exception as e:
            print(f"Decode failed: {e}")
    elif len(sys.argv) > 1:
        # Encode one string
        _print_encoded(sys.argv[1])
    else:
        # Interactive
        print("Hydra v4 XOR Encoder")
        print("Enter strings to encode (Ctrl+C to exit)\n")
        try:
            while True:
                text = input("String to encode: ").strip()
                if text:
                    _print_encoded(text)
        except (KeyboardInterrupt, EOFError):
            print("\nDone.")
