# Educational Virus — Classroom Malware Demo

**Author:** Levy (vLoon)
**Purpose:** Educational demonstration of malware concepts for classroom assignment.

---

## Overview

This project demonstrates how a real-world trojan/C2 (Command & Control) system works — using entirely **harmless, reversible** techniques. It's built for a classroom competition where each student presents their "virus" and the professor evaluates the design.

## Files

| File | Purpose |
|------|---------|
| `educational_virus.py` | The "trojan" — runs on target machine, polls a paste URL for commands |
| `controller.py` | Controller tool — formats commands for the paste |
| `README.md` | This documentation |

## How It Works (C2 Architecture)

```
[You] ──(update paste)──> [Pastebin/Gist] <──(poll every 30s)── [Target PC]
```

1. You create a paste (Pastebin, GitHub Gist, Ghostbin, etc.)
2. The virus polls that paste's RAW URL every 30 seconds
3. You update the paste with command codes
4. The virus reads, executes, and waits for the next command

No server needed. No port forwarding. Works on any network.

## Setup

### 1. Already Done

The virus is pre-configured with your C2 Gist:

```
https://gist.github.com/vLoon-jpg/99a46fc04b180fffdafc03584c0d5a2e
```

The initial command is `help` — the virus shows the full command list on first boot.

### 2. Send Commands (Quick Way)

```bash
cd C:\Users\LENOVO\projects\edu-virus
./edu-virus ping
./edu-virus popup "Hey" "Class!"
./edu-virus notepad 5 "You got pranked!"
./edu-virus kill
```

### 3. Run the Virus

```bash
python educational_virus.py
```

A message box confirms the virus loaded with the Agent ID.

### 4. Send Commands

```bash
# Show command reference
python controller.py <paste_url> help

# Ping the agent (shows info)
python controller.py <paste_url> ping

# Popup message
python controller.py <paste_url> popup Hello from the professor

# Open 5 Notepad windows
python controller.py <paste_url> notepad 5|You got pranked!

# Interactive mode
python controller.py <paste_url> --interactive
```

Or manually: copy the output into your paste, replacing everything.

## All Available Commands

### Basic
| Command | Example | Effect |
|---------|---------|--------|
| `help` | `help` | Show all commands |
| `ping` | `ping` | Show agent info via message box |
| `popup` | `popup\|Title\|Text` | Display a Windows message box |
| `notepad` | `notepad\|3\|hello` | Open N Notepad windows with text |
| `type` | `type\|hello world` | Simulate keystroke typing |

### Visual
| Command | Example | Effect |
|---------|---------|--------|
| `wallpaper` | `wallpaper\|<image_url>` | Change desktop wallpaper |
| `restore_wallpaper` | `restore_wallpaper` | Restore original wallpaper |
| `flash` | `flash\|red\|5` | Flash screen with color |
| `cursor` | `cursor\|spiral` | Move cursor in pattern |

### Annoyance
| Command | Example | Effect |
|---------|---------|--------|
| `mouse` | `mouse\|15` | Jiggle mouse for N seconds |
| `tray` | `tray\|open` | Open/close CD/DVD tray |
| `reversetxt` | `reversetxt\|C:\\folder` | Reverse .txt files (creates .bak) |
| `replicate` | `replicate` | Copy to USB drives / folders |

### Persistence
| Command | Example | Effect |
|---------|---------|--------|
| `persist` | `persist` | Add to HKCU startup |
| `unpersist` | `unpersist` | Remove from startup |

### Tactical
| Command | Example | Effect |
|---------|---------|--------|
| `target:ID\|cmd` | `target:abc\|popup\|hi` | Send to specific agent only |
| `selfdestruct` | `selfdestruct` | **Remove all traces + delete self** |

## Targeting Specific Machines

Every agent gets a unique 8-character ID (shown on startup). To hit one machine:

```
target:abc12345|popup|Hello only this machine!
```

To hit ALL machines, just use the command without targeting.

## Ethical & Safety Notes

1. **Everything is reversible** — .txt files are backed up (.bak), wallpaper is saved, registry is cleaned on unpersist
2. **Kill switch** — `selfdestruct` removes everything
3. **No data theft** — nothing reads/sends your files
4. **No network spread** — replication only writes to locally connected drives
5. **No encryption** — no ransomware features

## Comparison with Real Malware Concepts

| Concept | Real Malware | Our Demo |
|---------|-------------|----------|
| C2 Communication | HTTP/DNS/IRC polling | Pastebin URL polling |
| Command Encoding | AES/RSA encrypted | Plain text or base64 |
| Persistence | Registry, scheduled tasks, services | HKCU Run key |
| Self-Replication | Network propagation + worms | Copy to USB drives |
| Anti-Analysis | VM detection, anti-debug | (none — educational) |
| Obfuscation | Packers, polymorphism | (none — educational) |
| Payload | Data theft, ransomware, botnet | Popups, wallpaper, mouse |

---

*Built for educational purposes. Only run on systems you own.*
