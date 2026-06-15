# Supernet — Web Content Extractor

[![Python](https://img.shields.io/badge/python-3.8+-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Platform](https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey)]()
[![Version](https://img.shields.io/badge/version-1.3.1-orange)]()

**Extract subtitles, text, media, GIFs, and tech analysis from any web page — 18 commands, one tool.**

```bash
pip install yt-dlp trafilatura feedparser qrcode[pil]
python supernet.py sub https://example.com/xxx
python supernet.py text https://example.com
python supernet.py audio https://example.com/xxx
python supernet.py video https://example.com/xxx
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
python supernet.py info https://example.com/video
python supernet.py qr https://example.com
```

---

## All 16 Commands

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

---

## Use Cases

### 🎓 Learn from online videos
```bash
# Get subtitles for study notes
python supernet.py sub https://example.com/xxx

# View video metadata before downloading
python supernet.py info https://example.com/xxx
```

### 📝 Extract clean article text
```bash
# Remove ads, nav, sidebars — just the content
python supernet.py text https://example.com/blog-post

# Save and share as QR code
python supernet.py qr https://example.com/blog-post
```

### 🎵 Download music
```bash
# MP3 (default 192kbps)
python supernet.py audio https://example.com/xxx

# Lossless FLAC
python supernet.py audio https://example.com/xxx flac

# High-quality AAC
python supernet.py audio https://example.com/xxx aac 320
```

### 🎬 Download videos
```bash
# Best quality MP4
python supernet.py video https://example.com/xxx

# 720p WebM
python supernet.py video https://example.com/xxx webm 720

# Whole playlist
python supernet.py playlist https://example.com/playlist?list=...
```

### 🌐 Analyze website technology
```bash
# Check what framework, libraries, and server a site uses
python supernet.py tech https://example.com

# Extract all media elements (images, GIFs, video, canvas)
python supernet.py media https://example.com
```

### 🔄 Convert media files
```bash
python supernet.py convert input.mp4 mp3
python supernet.py convert input.mkv mp4
python supernet.py convert input.wav flac
```

### 📦 Batch process
```bash
# Create urls.txt:
#   https://example.com/aaa
#   https://example.com/bbb
#   https://example.com

python supernet.py batch urls.txt sub
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
├── SKILL.md            # Claude Code skill definition
├── .env                # Proxy configuration
├── script/
│   ├── supernet.py      # Main CLI script
│   └── proxy_pool.py   # Proxy pool with rotation & health check
└── supernet-output/     # Downloaded files
```

---

## Contributing

Issues and pull requests are welcome. Feature ideas:

- `screenshot <url>` — Capture webpage screenshots (via Playwright)
- `compare <url1> <url2>` — Diff two pages
- `archive <url>` — Check Wayback Machine history
- `search <query>` — Search and download online videos

---

## License

MIT
