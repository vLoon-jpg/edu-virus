# Graph Report - edu-virus  (2026-06-26)

## Corpus Check
- 6 files · ~8,753 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 117 nodes · 166 edges · 16 communities (9 shown, 7 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 16|Community 16]]

## God Nodes (most connected - your core abstractions)
1. `main()` - 12 edges
2. `c2_loop()` - 8 edges
3. `interactive_mode()` - 5 edges
4. `msgbox()` - 5 edges
5. `fetch_url()` - 5 edges
6. `get_drives()` - 5 edges
7. `cmd_ping()` - 5 edges
8. `cmd_selfdestruct()` - 5 edges
9. `execute_command()` - 5 edges
10. `msgbox()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `c2_loop()` --calls--> `fetch_url()`  [EXTRACTED]
  educational_virus.py → educational_virus.py  _Bridges community 9 → community 2_
- `cmd_wallpaper()` --calls--> `fetch_url()`  [EXTRACTED]
  educational_virus.py → educational_virus.py  _Bridges community 9 → community 6_

## Import Cycles
- None detected.

## Communities (16 total, 7 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.14
Nodes (17): api_agents(), api_fetch(), api_history(), api_send(), cmd_config(), cmd_latest(), dashboard(), fetch_gist_content() (+9 more)

### Community 1 - "Community 1"
Cohesion: 0.13
Nodes (26): demo_intro(), flash_screen(), get_drives(), is_admin(), main(), module_file_effects(), module_message_boxes(), module_persistence() (+18 more)

### Community 2 - "Community 2"
Cohesion: 0.32
Nodes (8): c2_loop(), execute_command(), _is_new_command(), _mark_done(), parse_commands(), Parse paste text into list of commands.     Accepts: JSON object, JSON array, or, Parse and execute a single command. Returns result string or None., Main C2 loop — Gist for commands + ngrok URL, primary via ngrok.

### Community 3 - "Community 3"
Cohesion: 0.31
Nodes (9): format_command(), interactive_mode(), main(), Show all available commands., Interactive command console., Upload to Pastebin.          To get an API key:       1. Go to https://pastebin., Format a command string for the virus to parse.          JSON format (preferred), show_help() (+1 more)

### Community 4 - "Community 4"
Cohesion: 0.20
Nodes (6): cmd_mouse(), cmd_reversetxt(), cmd_tray(), [5] Jiggle the mouse for N seconds., [6] Open/close CD/DVD tray., [8] Reverse contents of .txt files in a folder (creates .bak originals).

### Community 5 - "Community 5"
Cohesion: 0.15
Nodes (14): cmd_help(), cmd_ping(), cmd_replicate(), cmd_selfdestruct(), cmd_unpersist(), get_drives(), is_admin(), msgbox() (+6 more)

### Community 6 - "Community 6"
Cohesion: 0.50
Nodes (4): cmd_wallpaper(), [4] Change desktop wallpaper (saves original first)., Save current wallpaper path to backup file (before changing it)., save_original_wallpaper()

### Community 7 - "Community 7"
Cohesion: 0.50
Nodes (4): cmd_typer(), Send a single keystroke via keybd_event, handling Shift for uppercase     and sp, [2] Simulate typing text keystroke by keystroke., send_key()

### Community 9 - "Community 9"
Cohesion: 0.50
Nodes (4): fetch_paste(), fetch_url(), Fetch a URL with SSL workaround + cachebuster for CDN staleness., Fetch the raw Gist content.

## Knowledge Gaps
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `c2_loop()` connect `Community 2` to `Community 9`, `Community 4`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Why does `msgbox()` connect `Community 5` to `Community 4`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **What connects `Upload to Pastebin.          To get an API key:       1. Go to https://pastebin.`, `Format a command string for the virus to parse.          JSON format (preferred)`, `Show all available commands.` to the rest of the system?**
  _42 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.12535612535612536 - nodes in this community are weakly interconnected._