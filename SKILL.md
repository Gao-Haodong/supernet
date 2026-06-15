---
name: supernet
description: Extract subtitles, text, and media files from videos and web pages
---

# Supernet — Web Content Extractor

Run `script/supernet.py` with the command and URL.

## Command Mapping

| User Input | Execute | Description |
|------------|---------|-------------|
| `/supernet sub <url>` | `python script/supernet.py sub <url>` | Extract video subtitles |
| `/supernet text <url>` | `python script/supernet.py text <url>` | Extract web page text |
| `/supernet audio <url>` | `python script/supernet.py audio <url>` | Download audio (default MP3) |
| `/supernet video <url>` | `python script/supernet.py video <url>` | Download video (default MP4) |
| `/supernet info <url>` | `python script/supernet.py info <url>` | View video/page metadata |
| `/supernet list <url>` | `python script/supernet.py list <url>` | List available video formats |
| `/supernet thumbnail <url>` | `python script/supernet.py thumbnail <url>` | Download video thumbnail |
| `/supernet status <url>` | `python script/supernet.py status <url>` | Check website status |
| `/supernet headers <url>` | `python script/supernet.py headers <url>` | View HTTP response headers |
| `/supernet links <url>` | `python script/supernet.py links <url>` | Extract page links |
| `/supernet images <url>` | `python script/supernet.py images <url>` | Extract page image links |
| `/supernet media <url>` | `python script/supernet.py media <url>` | Extract images/GIFs/video/animations |
| `/supernet tech <url>` | `python script/supernet.py tech <url>` | Analyze web technology stack |
| `/supernet feed <url>` | `python script/supernet.py feed <url>` | Extract RSS/Atom feed |
| `/supernet qr <text>` | `python script/supernet.py qr <text>` | Generate QR code |
| `/supernet playlist <url>` | `python script/supernet.py playlist <url>` | List playlist entries |
| `/supernet convert <file> <fmt>` | `python script/supernet.py convert <file> <fmt>` | Convert local media file |
| `/supernet batch <file> <cmd>` | `python script/supernet.py batch <file> <cmd>` | Batch process URLs |

## Rules

1. Run `script/supernet.py` in the skill directory
2. Return script output to the user
3. Files saved to `supernet-output/` folder
