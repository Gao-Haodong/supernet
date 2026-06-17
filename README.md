# Supernet — Super Net Skill for Web

[![Python](https://img.shields.io/badge/python-3.8+-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Platform](https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey)]()
[![Version](https://img.shields.io/badge/version-1.5.0-orange)]()

**Extract subtitles, text, media, tech, DNS, SSL, AI, and more — 101 commands, one tool.**

```bash
pip install yt-dlp trafilatura feedparser qrcode[pil]
python script/main.py sub https://example.com/xxx
python script/main.py text https://example.com
python script/main.py audio https://example.com/xxx
python script/main.py video https://example.com/xxx
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install yt-dlp trafilatura feedparser qrcode[pil]

# 2. Clone or copy the script
git clone https://github.com/Gao-Haodong/supernet.git
cd supernet/script

# 3. Try it
python script/main.py info https://example.com/video
python script/main.py qr https://example.com
```

---

## All 101 Commands

### Core
| Command | Description |
|---------|-------------|
| `sub <url>` | Extract video subtitles |
| `text <url>` | Extract web page text |
| `audio <url> [fmt] [q]` | Download audio (mp3/aac/flac/wav/opus) |
| `video <url> [ext] [res]` | Download video (mp4/webm/mkv, best/1080/720/480) |

### Info & Analysis
| Command | Description |
|---------|-------------|
| `info <url>` | View video/page metadata |
| `list <url>` | List all available video formats |
| `status <url>` | Check website HTTP status + response time |
| `headers <url>` | View HTTP response headers |

### Web Page
| Command | Description |
|---------|-------------|
| `links <url>` | Extract all page links |
| `images <url>` | Extract all page image URLs |
| `media <url>` | Extract images/GIFs/video/animations |
| `tech <url>` | Analyze web technology stack |
| `feed <url>` | Extract RSS/Atom feed entries |
| `qr <text>` | Generate QR code image |

### Media & Batch
| Command | Description |
|---------|-------------|
| `thumbnail <url>` | Download video thumbnail |
| `playlist <url>` | List playlist entries |
| `convert <file> <fmt>` | Convert local media file (mp3/aac/flac/mp4/webm) |
| `batch <file> <cmd>` | Batch process URLs from a text file |

### Network & Domain
| Command | Description |
|---------|-------------|
| `dns <domain>` | DNS lookup |
| `ip` | Show public IP address |
| `whois <domain>` | Domain WHOIS lookup |
| `ssl <domain> [port]` | SSL certificate details |
| `port <host> [ports]` | Scan common ports |

### URL Tools
| Command | Description |
|---------|-------------|
| `shorten <url>` | Shorten URL |
| `expand <url>` | Expand shortened URL |
| `cookies <url>` | View page cookies |

### Page Analysis
| Command | Description |
|---------|-------------|
| `tables <url>` | Extract HTML tables as CSV |
| `sitemap <url>` | Extract sitemap URLs |
| `forms <url>` | Extract form fields |
| `archive <url>` | Wayback Machine snapshots |
| `wget <url>` | Download page HTML |
| `csp <url>` | Parse Content-Security-Policy |
| `emails <url>` | Extract email addresses |
| `hsts <domain>` | Check HSTS preload status |
| `json <url>` | Fetch and format JSON |
| `http <method> <url>` | Custom HTTP request |
| `diff <url1> <url2>` | Compare two web pages |

### Dev Tools
| Command | Description |
|---------|-------------|
| `hash <text>` | Hash text (md5/sha1/sha256) |
| `base64 <text>` | Base64 encode/decode |
| `uuid` | Generate UUID |
| `timestamp` | Current time info |
| `favicon <url>` | Download favicon |

### Network Tools
| Command | Description |
|---------|-------------|
| `ping <host>` | Ping a host |
| `speedtest` | Network speed test |
| `trace <host>` | Traceroute to host |

### File Tools
| Command | Description |
|---------|-------------|
| `checksum <file>` | Calculate file checksums |
| `type <file>` | Detect file type |

### Math
| Command | Description |
|---------|-------------|
| `calc <expr>` | Evaluate math expression |
| `units <val> <from> <to>` | Convert units (m/ft/kg/lb) |
| `color #RRGGBB` | Convert hex to RGB/HSL |
| `roman <n>` | Convert to Roman numerals |

### Text
| Command | Description |
|---------|-------------|
| `count <text>` | Count chars/words/lines |
| `reverse <text>` | Reverse text |
| `sort <words>` | Sort words |
| `case <text>` | Convert text case |

### Codec
| Command | Description |
|---------|-------------|
| `url <text>` | URL encode/decode |
| `hex <text>` | Hex encode/decode |
| `html <text>` | HTML entity encode/decode |
| `rot13 <text>` | ROT13 encode/decode |

### Geo
| Command | Description |
|---------|-------------|
| `geo [ip]` | IP geolocation lookup |
| `mylocation` | Show current IP location |

### Random
| Command | Description |
|---------|-------------|
| `rand [min] [max]` | Random number |
| `password [len]` | Random password |
| `token [len]` | Random token |

### Calendar
| Command | Description |
|---------|-------------|
| `calendar [year]` | Display calendar |
| `countdown <date>` | Days until/since a date |
| `week <date>` | Day of week for a date |

### AI
| Command | Description | Key Required |
|---------|-------------|-------------|
| `translate <text> <lang>` | Translate text (free API) | No |
| `sentiment <text>` | Basic sentiment analysis | No |
| `detect <text>` | Language detection | No |
| `ask <question>` | Ask Claude AI | Yes |
| `summarize <url>` | Summarize a web page | Yes |

### Search & Crawl
| Command | Description |
|---------|-------------|
| `search <query>` | Search the web (DuckDuckGo, free) |
| `crawl <url> [pages]` | Crawl a site up to N pages |
| `spider <url>` | Map all internal links of a site |

### Real-time Data
| Command | Description |
|---------|-------------|
| `btc` | Bitcoin price |
| `eth` | Ethereum price |
| `weather <city>` | Weather forecast |
| `hn` | Hacker News top stories |
| `news [topic]` | Top news headlines |

### Security
| Command | Description |
|---------|-------------|
| `jwt <token>` | Decode JWT token |
| `validate <email>` | Validate email format |

### Data Tools
| Command | Description |
|---------|-------------|
| `csv <file>` | View CSV file |
| `xml <text>` | Format XML |
| `rest <method> <url>` | REST API client |

### System
| Command | Description |
|---------|-------------|
| `sysinfo` | System information |
| `env [key]` | Show environment variables |
| `which <cmd>` | Find command path |

### Finance
| Command | Description |
|---------|-------------|
| `stock <symbol>` | Stock price (Yahoo Finance) |
| `market` | Major global indices |
| `forex <from> <to>` | Currency exchange rate |

### Knowledge
| Command | Description |
|---------|-------------|
| `define <word>` | Dictionary definition |
| `wiki <query>` | Wikipedia summary |
| `quote` | Random quote |
| `fact` | Random fact |
| `synonym <word>` | Find synonyms |
| `anagram <word>` | Find anagrams |

### URL & Web Details
| Command | Description |
|---------|-------------|
| `urlparse <url>` | Parse URL components |
| `params <url>` | Extract query parameters |
| `robots <url>` | Fetch robots.txt |
| `keywords <url>` | Extract meta tags |
| `encoding <url>` | Check page encoding |
| `validate <url>` | Validate URL accessibility |
| `mime <url>` | Check MIME type |
| `social <url>` | Find social media links |
| `lang <url>` | Detect page language |
| `pingback <url>` | Check XML-RPC endpoints |

---

## Use Cases

### 🎓 Learn from online videos
```bash
# Get subtitles for study notes
python script/main.py sub https://example.com/xxx

# View video metadata before downloading
python script/main.py info https://example.com/xxx
```

### 📝 Extract clean article text
```bash
# Remove ads, nav, sidebars — just the content
python script/main.py text https://example.com/blog-post

# Save and share as QR code
python script/main.py qr https://example.com/blog-post
```

### 🎵 Download music
```bash
# MP3 (default 192kbps)
python script/main.py audio https://example.com/xxx

# Lossless FLAC
python script/main.py audio https://example.com/xxx flac

# High-quality AAC
python script/main.py audio https://example.com/xxx aac 320
```

### 🎬 Download videos
```bash
# Best quality MP4
python script/main.py video https://example.com/xxx

# 720p WebM
python script/main.py video https://example.com/xxx webm 720

# Whole playlist
python script/main.py playlist https://example.com/playlist?list=...
```

### 🌐 Analyze website technology
```bash
# Check what framework, libraries, and server a site uses
python script/main.py tech https://example.com

# Extract all media elements (images, GIFs, video, canvas)
python script/main.py media https://example.com
```

### 🔄 Convert media files
```bash
python script/main.py convert input.mp4 mp3
python script/main.py convert input.mkv mp4
python script/main.py convert input.wav flac
```

### 📦 Batch process
```bash
# Create urls.txt:
#   https://example.com/aaa
#   https://example.com/bbb
#   https://example.com

python script/main.py batch urls.txt sub
```

---

## Proxy

Access restricted content by configuring a proxy:

```bash
# Environment variables
export HTTP_PROXY=http://127.0.0.1:7897
export HTTPS_PROXY=http://127.0.0.1:7897

# Or create .env file in the script directory:
#   HTTP_PROXY=http://127.0.0.1:7897
#   HTTPS_PROXY=http://127.0.0.1:7897

# For multiple proxies (auto rotation + health check):
#   PROXY_POOL=http://proxy1:port,http://proxy2:port
```

The built-in proxy pool automatically:
- Discovers proxies from `.env` and environment variables
- Health-checks each proxy before use
- Rotates via round-robin
- Cooldowns failed proxies (60s) and retries

---

## Requirements

- Python 3.8+
- [ffmpeg](https://ffmpeg.org/) (required for audio conversion)

| Package | Purpose |
|---------|---------|
| `yt-dlp` | Media & subtitle download (1000+ sites) |
| `trafilatura` | Web page text extraction |
| `feedparser` | RSS/Atom feed parsing |
| `qrcode[pil]` | QR code generation |
| `yfinance` | Stock/finance data |
| `duckduckgo_search` | Web search |
| `anthropic` | AI commands (ask, summarize) |

---

## FAQ

### Q: What video/audio formats are supported?
Audio: MP3, AAC (.m4a), FLAC, WAV, OPUS. Video: MP4, WebM, MKV. Resolutions: best, 1080p, 720p, 480p.

### Q: How do I use a proxy?
Set `HTTP_PROXY` in `.env` or environment variables. For multiple proxies, configure `PROXY_POOL` with comma-separated URLs. The built-in proxy pool handles health checks and rotation.

### Q: How do I use cookies for authenticated content?
Export cookies from your browser (Netscape format) as `cookies.txt` and place it in the script directory.

---

## Output

All downloaded files are saved to `supernet-output/` in the current directory.

```
supernet-output/
├── subtitles.txt
├── text.txt
├── thumbnail.jpg
├── video_title.mp4
├── audio_title.mp3
└── qr_143022.png
```

---

## File Structure

```
supernet/
├── README.md           # This file
├── SKILL.md            # Skill definition
├── .env                # Proxy configuration
├── LICENSE             # MIT License
├── install.sh          # One-command installer
└── script/
    ├── main.py         # CLI entry point
    ├── utils.py        # Shared helpers
    ├── core_cmds.py    # Core commands
    ├── web_cmds.py     # Web analysis
    ├── tools_cmds.py   # Utilities
    ├── network_cmds.py # Network tools
    ├── finance_cmds.py # Finance
    ├── ai_cmds.py      # AI commands
    └── proxy_pool.py   # Proxy rotation
└── supernet-output/    # Downloaded files
```

---

## Contributing

Issues and pull requests are welcome. Feature ideas:

- `screenshot <url>` — Capture webpage screenshots (via Playwright)
- `compare <url1> <url2>` — Diff two pages

---

## License

MIT
