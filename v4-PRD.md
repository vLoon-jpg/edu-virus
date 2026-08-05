# edu-virus v4 PRD — 25 Questions

Answer these to spec out the next version. Put an `x` in `[ ]` for yes,
write "nah" for no, or scribble notes. Whatever works.


## C2 & Connectivity

- [x] **1. Ngrok live dashboard?**
  Instant commands (2s) + web panel with one-click buttons vs current Gist polling (3-5s delay + manual `./edu-virus` CLI).
  Notes:

- [x] **2. Discord webhook feedback?**
  Bot posts to Discord when victim comes online, command results, screenshots, agent heartbeats. Already have Telegram — want Discord too?
  Notes:

- [x] **3. Multi-agent / lab-wide?**
  Multiple infected machines, target by agent ID, coordinated pranks (all screens flash at once, synchronized chaos).
  Max agents expected:

---

## Persistence & Stealth

- [x] **4. Scheduled Task persistence?**
  Survives reboots better than registry RUN key. Runs even if user hasn't logged in yet.
  Notes:

- [x] **5. EXE disguise name?**
  Currently `svchost.exe`. Other options: `WindowsUpdate.exe`, `OneDriveSync.exe`, `RuntimeBroker.exe`, `SearchIndexer.exe`.
  Pick one:

- [x] **6. Alternate Data Streams (ADS)?**
  Hide the EXE behind a legitimate file (e.g. `readme.txt:svchost.exe`). Invisible in Explorer, `dir`, and basic AV scans.
  Notes:

- [x] **7. Startup folder backup?**
  Copy to `shell:startup` as second persistence path in case registry key gets cleaned.
  Notes:

---

## Payload Modules

- [x] **8. New modules — which ones?**

  - [x] Fake BSOD overlay (dismissable fullscreen)
  - [x] Audio playback (random sounds, creepy whispers, TTS messages)
  - [x] Browser pranks (open 50 tabs, Rickroll, change homepage)
  - [ ] Fake Windows Update (fullscreen "Installing 1 of 147...")
  - [x] Keyboard remap (swap keys, random caps lock flicker)
  - [x] Clipboard manipulation (replace copied text with nonsense)
  - [x] Webcam flash (turn on briefly — scare factor)
  - [x] Monitor flip (rotate screen 180°)
  - [x] Taskbar hide / desktop icons disappear
  - [x] Other: modifyable pop up message

  Notes on which ones:

- [x] **9. Embedded wallpaper?**
  Bake a custom wallpaper image into the EXE so it works offline. What image?
  Notes:

- [ ] **10. "Professor Mode"?**
  Special trigger (specific command or time) that switches to presentation-optimized modules vs background stealth mode.
  Notes:

---

## Defense Evasion

- [x] **11. AMSI bypass?**
  Patch AMSI before PowerShell calls so Kaspersky can't scan the script content.
  Notes:

- [x] **12. UPX packing?**
  Compress the EXE to reduce size + change hash (evades signature matching).
  Notes:

- [x] **13. Randomized C2 polling?**
  Instead of fixed 30s, random 20-50s intervals to avoid pattern detection.
  Notes:

- [x] **14. Process hollowing / DLL sideloading?**
  Advanced — spawn a real Windows process, hollow it, inject. Very stealthy but complex.
  Notes:

- [x] **15. VM / sandbox detection?**
  Detect VirtualBox, VMware, Sandboxie, Windows Sandbox. If detected: either self-destruct or play dead (professor can't analyze it).
  Notes: if its a vm self destruct so it wont be reverse engineered, i dont want anyone knowing our webhook, make it so when they got the virus, they cannot reverse engineer it

---

## Self-Replication

- [x] **16. Network share scanning?**
  Scan `\\COMPUTER\Public\`, mounted network drives, drop payload if writeable.
  Notes:

- [x] **17. Worm mode — auto-infect lab PCs?**
  If infected machine can write to other lab PCs via network share, auto-drop + execute.
  Notes:

- [x] **18. "Typhoid Mary" — auto-infect USB drives?**
  When ANY USB is plugged into infected machine, auto-plant payload. Including professor's drive.
  Notes:

---

## OPSEC & Anti-Forensics

- [x] **19. Log wiping?**
  Clear PowerShell history, event logs (if elevated), recent files MRU, prefetch files.
  Notes:

- [x] **20. Timestomping?**
  Modify EXE creation/modified date to look old (e.g., "Created: January 2024").
  Notes:

- [ ] **21. Timed self-destruct?**
  Auto-delete all traces after X days. How many days?
  Notes:

- [x] **22. Encrypted C2?**
  XOR or AES the Gist content so even if professor finds the raw URL, it's garbage.
  Notes:

---

## Dev Experience

- [ ] **23. One-click build script?**
  `./build.sh` → compile EXE, update Gist, start ngrok, open dashboard. Full deploy pipeline.
  Notes:

- [x] **24. Mobile controller upgrades?**
  Telegram bot already gives shell. Want: `/agents` list, `/screenshot`, `/status`, command buttons?
  Notes:

- [x] **25. "Patient Zero" — auto-flash BadUSB?**
  When a Pico/RP2040 is plugged into infected machine, auto-flash the BadUSB payload onto it.
  Notes: maybe in another kind, like infect any connected computer (maybe via lan cabble?)

---

## Bonus (anything else?)

Anything I missed that you want in v4:


---

## Reconnaissance

- [ ] **26. System survey on first run?**
  Gather: hostname, username, OS version, installed AV, screen resolution, active USB devices, network shares. Send back to C2 so you know what you're dealing with.
  Notes:

- [ ] **27. Professor fingerprinting?**
  Detect professor's username / hostname specifically? Don't prank him until you're ready, or ONLY prank him?
  Notes:

- [ ] **28. Network topology mapping?**
  Scan LAN — what other machines are reachable? IP ranges, open SMB shares, other infected agents?
  Notes:

- [ ] **29. Browser credential check?**
  Check if Chrome/Firefox password stores exist (NOT steal them — just report "yes, accessible"). Tells you if credential theft is possible if you escalate later.
  Notes:

---

## Privilege & Access

- [ ] **30. Privilege escalation attempt?**
  Try common UAC bypasses, unquoted service paths, AlwaysInstallElevated, fodhelper? Or stay user-level?
  Notes:

- [ ] **31. Admin detection + flag?**
  Don't escalate — just detect if already admin. If admin: unlock more aggressive modules (log wiping, scheduled tasks, full system persistence).
  Notes:

- [ ] **32. Token impersonation?**
  If admin: steal SYSTEM token, spawn shell as SYSTEM. Maximum access.
  Notes:

---

## Architecture & Modularity

- [ ] **33. Plugin system vs monolith?**
  Keep everything baked into one EXE, or download modules on demand? Plugin system = smaller initial payload, less AV exposure. Monolith = works offline.
  Notes:

- [ ] **34. Config file vs hardcoded?**
  Keep C2 URLs, webhook URLs, tokens in `config.json` (easy to update without recompile) or hardcoded (can't be read by forensics)?
  Notes:

- [ ] **35. Versioning & auto-update?**
  Virus checks for new version on Gist, downloads + replaces itself? So you can update all agents at once.
  Notes:

---

## Anti-Debugging & Anti-Tamper

- [ ] **36. Anti-kill mechanisms?**
  Dual process watchdog — two processes that restart each other if killed. Harder to terminate.
  Notes:

- [ ] **37. Anti-debugging?**
  Detect debugger attached (IsDebuggerPresent, CheckRemoteDebuggerPresent, NtGlobalFlag). If debugged: self-destruct or behave normally.
  Notes:

- [ ] **38. Process protection?**
  Protect process from Task Manager kill? (needs admin — set SeDebugPrivilege, or register as critical process)
  Notes:

- [ ] **39. Obfuscated strings?**
  All strings (URLs, webhook, token) encoded with XOR/base64 so `strings virus.exe` reveals nothing.
  Notes:

- [ ] **40. Anti-reverse-engineering?**
  Detect if EXE is being unpacked, run in a sandbox, or analyzed. Refuse to run. "They cannot reverse engineer it" — how aggressive?
  Notes:

---

## Triggers & Targeting

- [ ] **41. Time-based activation?**
  Only run during school hours (8AM-3PM)? Only run when professor is likely present?
  Notes:

- [ ] **42. User-based targeting?**
  Run differently depending on which user is logged in. Professor gets different treatment than students.
  Notes:

- [ ] **43. Idle detection?**
  Only execute visible pranks when user is idle (no mouse/keyboard for 5 min)? Stealthy during active use.
  Notes:

- [ ] **44. USB trigger?**
  Specific module activates when a specific USB device is plugged in (professor's known USB VID/PID)?
  Notes:

---

## Staged Payload Delivery

- [ ] **45. Stage 1 dropper vs Stage 2 implant?**
  Small initial EXE that downloads the full payload. Tradeoff: needs internet but AV-exposed surface is tiny.
  Notes:

- [ ] **46. In-memory execution?**
  Download modules as PowerShell scripts or .NET assemblies, execute entirely in memory. Nothing touches disk.
  Notes:

- [ ] **47. LOLBin delivery?**
  Use legitimate Windows binaries to download/execute (mshta, rundll32, regsvr32, msbuild)? Harder for AV to flag.
  Notes:

---

## Network & Lateral Movement

- [ ] **48. LAN cable infection?** (from your note on #25)
  Detect LAN connection, scan for open SMB/Admin shares, attempt to copy + execute via WMI or PsExec?
  Notes:

- [ ] **49. ARP spoofing / MITM?**
  Redirect lab traffic through infected machine? Capture unencrypted traffic? Risky — very noisy.
  Notes:

- [ ] **50. Bluetooth spread?**
  Scan for nearby Bluetooth devices, attempt to send payload? Limited range but novel vector.
  Notes:

---

## Data & Feedback

- [ ] **51. Screenshot capture?**
  Take screenshot on demand, send to Telegram/Discord. See what's on their screen.
  Notes:

- [ ] **52. Keylogger?** (educational — local only, no exfil?)
  Log keystrokes to a local file. Demonstrate the technique without stealing real passwords. Or full keylogger?
  Notes:

- [ ] **53. Microphone recording?**
  Record ambient audio on demand? Short clips sent to C2.
  Notes:

- [ ] **54. File listing?**
  List interesting files (Desktop, Documents, Downloads) — report filenames only, no content theft.
  Notes:

---

## Build & Deploy Pipeline

- [ ] **55. Staged build profiles?**
  Build configs: `dev` (verbose, console visible), `stealth` (silent, hidden), `professor-demo` (flashy, show-off mode)?
  Notes:

- [ ] **56. Release bundling?**
  Auto-zip EXE + BadUSB files + README into one deploy package per release?
  Notes:

- [ ] **57. AV testing pipeline?**
  After build, auto-upload to VirusTotal? (risky — exposes your hash. Alternative: local Windows Defender scan)
  Notes:

---

## Attribution Protection

- [ ] **58. Webhook/token protection?**
  If EXE is reverse-engineered, Discord webhook + Telegram token are exposed. Mitigations: encrypt-at-rest, fetch from C2 on first run, use throwaway webhooks that can be rotated?
  Notes:

- [ ] **59. Proxy C2 traffic?**
  Route all C2 through TOR or a free proxy so network logs don't point to your GitHub/Discord?
  Notes:

- [ ] **60. Burner infrastructure?**
  Use temporary webhooks, disposable Gists, rotating ngrok URLs? If one gets burned, rotate.
  Notes:

---

## Testing & QA

- [ ] **61. Test VM target?**
  Set up a Windows 10 VM matching school environment (Kaspersky, no admin, US keyboard, school WiFi simulation)?
  Notes:

- [ ] **62. Silent test mode?**
  A flag that runs all modules in "test mode" — visible console output, doesn't actually change anything, just prints what it WOULD do?
  Notes:

- [ ] **63. Crash reporting?**
  If virus crashes, write crash log to temp? Helps debug remote infections you can't see.
  Notes:

---

## Bonus Round 2

Any other wild ideas:

