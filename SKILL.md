---
name: supernet
description: Extract subtitles, text, media, web tech, DNS, SSL, WHOIS, and more from any URL
---

# Supernet — Super Net Skill for Web

Run `script/main.py` with the command and URL.

## Command Mapping

| User Input | Execute | Description |
|------------|---------|-------------|
| `/supernet sub <url>` | `python script/main.py sub <url>` | Extract video subtitles |
| `/supernet text <url>` | `python script/main.py text <url>` | Extract web page text |
| `/supernet audio <url>` | `python script/main.py audio <url>` | Download audio (default MP3) |
| `/supernet video <url>` | `python script/main.py video <url>` | Download video (default MP4) |
| `/supernet info <url>` | `python script/main.py info <url>` | View video/page metadata |
| `/supernet list <url>` | `python script/main.py list <url>` | List available video formats |
| `/supernet thumbnail <url>` | `python script/main.py thumbnail <url>` | Download video thumbnail |
| `/supernet status <url>` | `python script/main.py status <url>` | Check website status |
| `/supernet headers <url>` | `python script/main.py headers <url>` | View HTTP response headers |
| `/supernet links <url>` | `python script/main.py links <url>` | Extract page links |
| `/supernet images <url>` | `python script/main.py images <url>` | Extract page image links |
| `/supernet media <url>` | `python script/main.py media <url>` | Extract images/GIFs/video/animations |
| `/supernet tech <url>` | `python script/main.py tech <url>` | Analyze web technology stack |
| `/supernet feed <url>` | `python script/main.py feed <url>` | Extract RSS/Atom feed |
| `/supernet qr <text>` | `python script/main.py qr <text>` | Generate QR code |
| `/supernet playlist <url>` | `python script/main.py playlist <url>` | List playlist entries |
| `/supernet convert <file> <fmt>` | `python script/main.py convert <file> <fmt>` | Convert local media file |
| `/supernet batch <file> <cmd>` | `python script/main.py batch <file> <cmd>` | Batch process URLs |
| `/supernet dns <domain>` | `python script/main.py dns <domain>` | DNS lookup |
| `/supernet ip` | `python script/main.py ip` | Show public IP |
| `/supernet whois <domain>` | `python script/main.py whois <domain>` | Domain WHOIS lookup |
| `/supernet ssl <domain>` | `python script/main.py ssl <domain>` | SSL certificate info |
| `/supernet port <host>` | `python script/main.py port <host>` | Scan common ports |
| `/supernet shorten <url>` | `python script/main.py shorten <url>` | Shorten URL |
| `/supernet expand <url>` | `python script/main.py expand <url>` | Expand shortened URL |
| `/supernet cookies <url>` | `python script/main.py cookies <url>` | View page cookies |
| `/supernet tables <url>` | `python script/main.py tables <url>` | Extract HTML tables as CSV |
| `/supernet sitemap <url>` | `python script/main.py sitemap <url>` | Extract sitemap URLs |
| `/supernet forms <url>` | `python script/main.py forms <url>` | Extract form fields |
| `/supernet archive <url>` | `python script/main.py archive <url>` | Wayback Machine snapshots |
| `/supernet wget <url>` | `python script/main.py wget <url>` | Download page HTML |

## File Structure

```
supernet/
├── SKILL.md          # Skill definition
├── README.md         # Usage docs
├── .env              # Proxy config
├── LICENSE           # MIT License
├── install.sh        # One-command installer
└── script/
    ├── main.py       # CLI entry point
    ├── utils.py      # Shared helpers
    ├── core_cmds.py  # Core commands
    ├── web_cmds.py   # Web analysis
    ├── tools_cmds.py # Utilities
    ├── network_cmds.py  # Network tools
    ├── finance_cmds.py  # Finance
    ├── ai_cmds.py       # AI commands
    └── proxy_pool.py    # Proxy rotation
```

## Rules

1. Run `python script/main.py <cmd> <args>` from the project root
2. Return script output to the user
3. Files saved to `script/supernet-output/` folder
