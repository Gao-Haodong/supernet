#!/usr/bin/env python3
# Copyright (c) 2026 Haodong Gao (高浩东), Xi'an, China. MIT License.
"""Supernet - Extract subtitles, text, media, tech analysis, DNS, SSL, and more from any URL.

Usage:
  python supernet.py sub <url>          Extract video subtitles
  python supernet.py text <url>         Extract web page text
  python supernet.py audio <url>        Download audio (default MP3)
  python supernet.py video <url>        Download video (default MP4)
  python supernet.py info <url>         View video/page metadata
  python supernet.py list <url>         List available video formats
  python supernet.py thumbnail <url>    Download video thumbnail
  python supernet.py status <url>       Check website status
  python supernet.py headers <url>      View HTTP response headers
  python supernet.py links <url>        Extract page links
  python supernet.py images <url>       Extract page image links
  python supernet.py media <url>        Extract images/GIFs/video/animations
  python supernet.py tech <url>         Analyze web technology stack
  python supernet.py feed <url>         Extract RSS/Atom feed
  python supernet.py qr <text>          Generate QR code
  python supernet.py playlist <url>     List playlist entries
  python supernet.py convert <file> <fmt>  Convert local media file
  python supernet.py batch <file> <cmd> Batch process URLs from file
  python supernet.py dns <domain>       DNS lookup
  python supernet.py ip                 Show public IP
  python supernet.py whois <domain>     Domain WHOIS lookup
  python supernet.py ssl <domain>       SSL certificate info
  python supernet.py port <host>        Scan common ports
  python supernet.py shorten <url>      Shorten URL
  python supernet.py expand <url>       Expand shortened URL
  python supernet.py cookies <url>      View page cookies
  python supernet.py tables <url>       Extract HTML tables as CSV
  python supernet.py sitemap <url>      Extract sitemap URLs
  python supernet.py forms <url>        Extract form fields
  python supernet.py archive <url>      Wayback Machine snapshots
  python supernet.py wget <url>         Download page HTML
  python supernet.py csp <url>          Parse Content-Security-Policy
  python supernet.py emails <url>       Extract email addresses
  python supernet.py hsts <domain>      Check HSTS preload status
  python supernet.py json <url>         Fetch and format JSON
  python supernet.py http <method> <url>  Custom HTTP request
  python supernet.py diff <url1> <url2>  Compare two web pages
  python supernet.py hash <text>        Hash text (md5/sha1/sha256)
  python supernet.py base64 <text>      Base64 encode/decode
  python supernet.py uuid               Generate UUID
  python supernet.py timestamp          Show current time info
  python supernet.py favicon <url>      Download favicon
  python supernet.py ping <host>        Ping a host
  python supernet.py speedtest          Run network speed test
  python supernet.py trace <host>       Traceroute to host
  python supernet.py checksum <file>    Calculate file checksums
  python supernet.py type <file>        Detect file type
"""
import sys, os, json, re, time, tempfile, shutil, subprocess, textwrap, urllib.parse
from datetime import datetime

VERSION = "1.5.0"

# Load .env file for proxy config
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# Check proxy from env or .env file
if not os.environ.get("HTTP_PROXY") and not os.environ.get("HTTPS_PROXY"):
    for _p in ["http://127.0.0.1:7897", "http://127.0.0.1:7890",
               "http://127.0.0.1:10809", "http://127.0.0.1:1080"]:
        try:
            import urllib.request
            urllib.request.urlopen(_p, timeout=2)
            os.environ.setdefault("HTTP_PROXY", _p)
            os.environ.setdefault("HTTPS_PROXY", _p)
            break
        except Exception:
            pass

OUTPUT_DIR = os.path.join(os.getcwd(), "supernet-output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
TEXT_CACHE = {}

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _get_proxy():
    """Get a working proxy (from pool, fallback to env)."""
    try:
        from proxy_pool import get_proxy as _pool_proxy
        p = _pool_proxy()
        if p:
            return p
    except Exception:
        pass
    for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        val = os.environ.get(key, "").strip()
        if val and val.startswith(("http://", "socks")):
            if val.startswith("http://") and "@" not in val:
                return val
            if val.startswith("socks"):
                return val
    return None

def _get_ffmpeg():
    return shutil.which("ffmpeg") or shutil.which("ffmpeg.exe") or ""

def _base_opts(**extra):
    opts = {"quiet": True, "no_warnings": True,
            "socket_timeout": 30, "retries": 3, "extractor_retries": 3, "fragment_retries": 3,
            "http_headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            "sleep_interval": 2, "max_sleep_interval": 5,
            "ffmpeg_location": os.path.dirname(_get_ffmpeg()) if _get_ffmpeg() else ""}
    proxy = _get_proxy()
    if proxy:
        opts["proxy"] = proxy
        opts["_current_proxy"] = proxy
    cookie = os.path.join(OUTPUT_DIR, "..", "cookies.txt")
    if os.path.exists(cookie):
        opts["cookiefile"] = cookie
    opts.update(extra)
    return opts

def _save_text(text, filename):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Saved: {path}")

def _fmt_size(b):
    if not b:
        return "-"
    b = int(b)
    for u in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f}{u}"
        b /= 1024
    return f"{b:.1f}TB"

def _ts(seconds):
    if not seconds:
        return "-"
    s = int(seconds)
    return f"{s//60:02d}:{s%60:02d}"

def _ensure_dep(name, pip_name=None):
    try:
        __import__(name)
    except ImportError:
        pkg = pip_name or name
        print(f"Install required: pip install {pkg}", file=sys.stderr)
        sys.exit(1)

def _mark_proxy_bad(proxy_url=""):
    if not proxy_url:
        proxy_url = _get_proxy() or ""
    if proxy_url:
        try:
            from proxy_pool import get_pool
            get_pool().mark_bad(proxy_url)
        except Exception:
            pass

def _try_ydl(url, opts):
    """yt-dlp wrapper with proxy failover and retry."""
    import yt_dlp
    proxy_used = opts.get("_current_proxy", "")
    for attempt in range(3):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=opts.get("skip_download") is not True)
        except Exception as e:
            err = str(e)
            is_blocked = any(k in err for k in [
                "HTTP Error 403", "RequestBlocked", "Sign in to confirm",
                "blocking requests", "Too Many Requests", "502", "503",
                "Connection refused", "Connection reset",
            ])
            if is_blocked and proxy_used:
                _mark_proxy_bad(proxy_used)
                new_proxy = _get_proxy()
                if new_proxy and new_proxy != proxy_used:
                    opts["proxy"] = new_proxy
                    opts["_current_proxy"] = new_proxy
                    proxy_used = new_proxy
                    continue
            if attempt == 2:
                raise
    raise RuntimeError("yt-dlp failed after retries")

# ---------------------------------------------------------------------------
# Core commands
# ---------------------------------------------------------------------------

def cmd_sub(url):
    """Extract video subtitles."""
    import yt_dlp
    targets = ["en", "zh", "ja", "ko", "de", "fr", "es"]
    if re.search(r'(youtube\.com|youtu\.be)', url):
        try:
            from youtube_transcript_api import YouTubeTranscriptApi, formatters
            vid = re.search(r'(?:v=|youtu\.be/|shorts/)([\w-]+)', url)
            if vid:
                _yt_proxy = _get_proxy()
                if _yt_proxy:
                    from youtube_transcript_api.proxies import GenericProxyConfig
                    _pc = GenericProxyConfig(http_url=_yt_proxy, https_url=_yt_proxy)
                    _api = YouTubeTranscriptApi(proxy_config=_pc)
                else:
                    _api = YouTubeTranscriptApi()
                tl = list(_api.list(vid.group(1)))
                if tl:
                    t = tl[0]
                    td = t.fetch()
                    text = formatters.TextFormatter().format_transcript(td).strip()
                    _save_text(text, "subtitles.txt")
                    print(f"Subtitles ({len(text)} chars, lang: {t.language_code})")
                    print(text[:500] + ("..." if len(text) > 500 else ""))
                    return
        except Exception:
            pass
    with tempfile.TemporaryDirectory() as tmp:
        opts = _base_opts(skip_download=True, writesubtitles=True, writeautomaticsub=True,
                          subtitleslangs=targets, subtitlesformat="vtt",
                          outtmpl=os.path.join(tmp, "%(id)s.%(ext)s"))
        try:
            _try_ydl(url, opts)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        for f in os.listdir(tmp):
            if f.endswith(".vtt"):
                with open(os.path.join(tmp, f), "r", encoding="utf-8", errors="replace") as fh:
                    text = re.sub(r'<[^>]+>', '', fh.read())
                    text = re.sub(r'^\d+\n|\d{2}:\d{2}.*?-->.*?\n|WEBVTT\n|Kind:.*?\n|Language:.*?\n', '', text, flags=re.MULTILINE)
                    text = re.sub(r'\n{3,}', '\n\n', text).strip()
                _save_text(text, "subtitles.txt")
                print(f"Subtitles ({len(text)} chars)")
                print(text[:500] + ("..." if len(text) > 500 else ""))
                return
    print("No subtitles found", file=sys.stderr)
    sys.exit(1)

def cmd_text(url):
    """Extract web page text."""
    import trafilatura
    print("Fetching page...")
    html = trafilatura.fetch_url(url)
    if not html:
        print("Failed to fetch page", file=sys.stderr)
        sys.exit(1)
    text = trafilatura.extract(html)
    if not text or len(text.strip()) < 20:
        print("No usable text found", file=sys.stderr)
        sys.exit(1)
    TEXT_CACHE["text"] = text.strip()
    _save_text(text.strip(), "text.txt")
    print(f"Text ({len(text.strip())} chars)")
    print(text.strip()[:1000] + ("..." if len(text) > 1000 else ""))

def cmd_audio(url, fmt="mp3", quality="192"):
    """Download audio (mp3/aac/flac/wav/opus)."""
    import yt_dlp
    ffmpeg = _get_ffmpeg()
    if not ffmpeg:
        print("ffmpeg not found", file=sys.stderr)
        sys.exit(1)
    codec_map = {"mp3": "libmp3lame", "aac": "aac", "flac": "flac", "wav": "pcm_s16le", "opus": "libopus"}
    ext_map = {"mp3": "mp3", "aac": "m4a", "flac": "flac", "wav": "wav", "opus": "opus"}
    acodec = codec_map.get(fmt, "libmp3lame")
    out_ext = ext_map.get(fmt, "mp3")
    opts = _base_opts(format="bestaudio/best", fixup="never", postprocessors=[],
                      outtmpl=os.path.join(OUTPUT_DIR, "%(title)s.%(ext)s"))
    try:
        info = _try_ydl(url, opts)
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        sys.exit(1)
    title = info.get("title", "audio") if info else "audio"
    src = None
    for f in os.listdir(OUTPUT_DIR):
        if title[:20] in f and not f.endswith(tuple(ext_map.values())) and not f.endswith(".part"):
            src = os.path.join(OUTPUT_DIR, f)
            break
    if not src:
        print("Downloaded file not found", file=sys.stderr)
        sys.exit(1)
    out = os.path.join(OUTPUT_DIR, re.sub(r'[\\/*?:"<>|]', '_', title)[:80] + f".{out_ext}")
    args = [ffmpeg, "-i", src, "-vn", "-acodec", acodec]
    if fmt in ("mp3", "aac"):
        args += ["-ab", f"{quality}k"]
    if fmt == "flac":
        args += ["-compression_level", "5"]
    if fmt == "opus":
        args += ["-b:a", f"{quality}k"]
    args += ["-y", out]
    try:
        subprocess.run(args, check=True, capture_output=True, timeout=600)
    except Exception as e:
        print(f"Conversion failed: {e}", file=sys.stderr)
        sys.exit(1)
    os.remove(src)
    print(f"Audio: {out} ({os.path.getsize(out)/(1024*1024):.1f} MB)")

def cmd_video(url, ext="mp4", resolution="best"):
    """Download video (mp4/webm/mkv, best/1080/720/480)."""
    import yt_dlp
    fmt_map = {
        "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "1080": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]",
        "720": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]",
        "480": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]",
    }
    fmt = fmt_map.get(resolution, fmt_map["best"])
    if ext != "mp4":
        r = resolution if resolution != "best" else ""
        fmt = f"bestvideo[height<={r}]+bestaudio/best" if r else "bestvideo+bestaudio/best"
    opts = _base_opts(format=fmt, merge_output_format=ext,
                      outtmpl=os.path.join(OUTPUT_DIR, "%(title)s.%(ext)s"))
    try:
        info = _try_ydl(url, opts)
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        sys.exit(1)
    title = info.get("title", "video") if info else "video"
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith(f".{ext}") and title[:30] in f:
            print(f"Video: {os.path.join(OUTPUT_DIR, f)} ({os.path.getsize(os.path.join(OUTPUT_DIR, f))/(1024*1024):.1f} MB)")
            return
    print("Output not found", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Extra commands
# ---------------------------------------------------------------------------

def cmd_info(url):
    """View video/page metadata."""
    import yt_dlp, trafilatura
    has_media = False
    try:
        info = _try_ydl(url, _base_opts(skip_download=True, extract_flat=False))
        if info:
            has_media = True
            print("=" * 40)
            print(f"  Title:     {info.get('title', '-')}")
            print(f"  Duration:  {_ts(info.get('duration'))}")
            print(f"  Author:    {info.get('uploader', info.get('channel', '-'))}")
            print(f"  Quality:   {info.get('height', '-')}p")
            print(f"  Codec:     {info.get('vcodec', '-')}")
            if info.get('bitrate'):
                print(f"  Bitrate:   {info.get('bitrate')} kbps")
            print(f"  Formats:   {len(info.get('formats', []))}")
            subs = list((info.get('subtitles') or {}).keys())
            if subs:
                print(f"  Subtitles: {', '.join(subs[:10])}")
            auto_subs = list((info.get('automatic_captions') or {}).keys())
            if auto_subs:
                print(f"  Auto caps: {', '.join(auto_subs[:5])}...")
            thumbs = info.get('thumbnails', [])
            if thumbs:
                print(f"  Thumbnail: {thumbs[-1].get('url', '-')[:80]}")
            print(f"  URL:       {info.get('webpage_url', url)}")
            print("=" * 40)
    except Exception:
        pass
    if not has_media:
        try:
            html = trafilatura.fetch_url(url)
            if html:
                text = trafilatura.extract(html)
                m = re.search(r'<title>(.*?)</title>', html[:2000], re.I)
                title = m.group(1) if m else ""
                m2 = re.search(r'name=["\']description["\'] content=["\'](.*?)["\']', html[:2000], re.I)
                desc = m2.group(1) if m2 else ""
                print("=" * 40)
                print(f"  Title:  {title or '-'}")
                if desc:
                    print(f"  Desc:   {desc[:100]}")
                print(f"  Text:   {len(text.strip()) if text else 0} chars")
                print(f"  URL:    {url}")
                print("=" * 40)
                if text:
                    TEXT_CACHE["text"] = text.strip()
                return
        except Exception:
            pass
        print("Cannot parse URL", file=sys.stderr)
        sys.exit(1)

def cmd_list(url):
    """List available video formats."""
    import yt_dlp
    try:
        info = _try_ydl(url, _base_opts(skip_download=True))
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)
    fmts = info.get("formats", [])
    if not fmts:
        print("No format info", file=sys.stderr)
        sys.exit(1)
    print(f"{len(fmts)} formats - {info.get('title', '')[:50]}")
    print("-" * 70)
    print(f"{'ID':<8} {'Resolution':<12} {'Bitrate':<10} {'Video Codec':<14} {'Audio Codec':<14} {'Size':<10}")
    print("-" * 70)
    for f in fmts:
        fid = f.get("format_id", "-")
        res = f"{f.get('height', '-') or '-'}p" if f.get("vcodec", "none") != "none" else "audio"
        br = f"{f.get('tbr', '-')}k" if f.get('tbr') else "-"
        vc = (f.get("vcodec") or "-")[:12]
        ac = (f.get("acodec") or "-")[:12]
        sz = _fmt_size(f.get("filesize") or f.get("filesize_approx"))
        print(f"{fid:<8} {res:<12} {br:<10} {vc:<14} {ac:<14} {sz:<10}")

def cmd_thumbnail(url):
    """Download video thumbnail."""
    import yt_dlp, requests as req
    try:
        info = _try_ydl(url, _base_opts(skip_download=True))
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)
    thumbs = info.get("thumbnails", []) if info else []
    if not thumbs:
        print("No thumbnails", file=sys.stderr)
        sys.exit(1)
    best = max(thumbs, key=lambda t: (t.get("width", 0) or 0) * (t.get("height", 0) or 0))
    url_t = best.get("url", "")
    if not url_t:
        print("No thumbnail URL", file=sys.stderr)
        sys.exit(1)
    ext = url_t.split("?")[0].split(".")[-1] if "." in url_t.split("?")[0] else "jpg"
    out = os.path.join(OUTPUT_DIR, f"thumbnail.{ext}")
    resp = req.get(url_t, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    if resp.status_code != 200:
        print("Download failed", file=sys.stderr)
        sys.exit(1)
    with open(out, "wb") as f:
        f.write(resp.content)
    print(f"Thumbnail: {out} ({len(resp.content)/1024:.1f} KB, {best.get('width','?')}x{best.get('height','?')})")

def cmd_status(url):
    """Check website status."""
    import requests as req
    try:
        start = time.time()
        resp = req.get(url, timeout=30, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        elapsed = (time.time() - start) * 1000
    except Exception as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        sys.exit(1)
    print("=" * 40)
    print(f"  URL:      {resp.url}")
    print(f"  Status:   {resp.status_code} {resp.reason}")
    print(f"  Time:     {elapsed:.0f} ms")
    print(f"  Redirect: {len(resp.history)} hops")
    for i, r in enumerate(resp.history):
        print(f"    {i+1}. {r.status_code} -> {r.url}")
    print(f"  Type:     {resp.headers.get('Content-Type', '-')}")
    print(f"  Server:   {resp.headers.get('Server', '-')}")
    print(f"  Size:     {_fmt_size(len(resp.content))}")
    print("=" * 40)

def cmd_headers(url):
    """View HTTP response headers."""
    import requests as req
    try:
        resp = req.head(url, timeout=30, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"HTTP Headers - {resp.url}")
    print("-" * 50)
    for k, v in sorted(resp.headers.items()):
        print(f"  {k}: {v}")

def cmd_links(url):
    """Extract page links."""
    _ensure_dep("bs4", "beautifulsoup4")
    from bs4 import BeautifulSoup
    import requests as req
    try:
        resp = req.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)
    soup = BeautifulSoup(resp.text, "html.parser")
    base_url = resp.url
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("#") or href.startswith("javascript:"):
            continue
        full = urllib.parse.urljoin(base_url, href)
        links.add(full)
    links = sorted(links)
    netloc = urllib.parse.urlparse(base_url).netloc
    internal = [l for l in links if urllib.parse.urlparse(l).netloc == netloc]
    external = [l for l in links if urllib.parse.urlparse(l).netloc != netloc]
    print(f"{len(links)} links ({len(internal)} internal, {len(external)} external)")
    print("-" * 50)
    for l in links[:30]:
        print(f"  {l}")
    if len(links) > 30:
        print(f"  ... and {len(links)-30} more")

def cmd_images(url):
    """Extract page image links."""
    _ensure_dep("bs4", "beautifulsoup4")
    from bs4 import BeautifulSoup
    import requests as req
    try:
        resp = req.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)
    soup = BeautifulSoup(resp.text, "html.parser")
    base_url = resp.url
    imgs = []
    for img in soup.find_all("img", src=True):
        src = img["src"]
        if src.startswith("data:"):
            continue
        full = urllib.parse.urljoin(base_url, src)
        alt = img.get("alt", "")[:40]
        imgs.append((full, alt))
    print(f"{len(imgs)} images")
    print("-" * 50)
    for src, alt in imgs[:20]:
        print(f"  {src}")
        if alt:
            print(f"    alt: {alt}")
    if len(imgs) > 20:
        print(f"  ... and {len(imgs)-20} more")

def cmd_feed(url):
    """Extract RSS/Atom feed."""
    _ensure_dep("feedparser")
    import feedparser, requests as req
    from bs4 import BeautifulSoup
    try:
        resp = req.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)
    soup = BeautifulSoup(resp.text, "html.parser")
    feed_urls = []
    for link in soup.find_all("link", type=re.compile(r"application/(rss|atom)\+xml")):
        href = link.get("href", "")
        if href:
            feed_urls.append(urllib.parse.urljoin(url, href))
    if not feed_urls:
        feed_urls = [url]
    for fu in feed_urls:
        f = feedparser.parse(fu)
        if not f.entries:
            continue
        print(f"Feed: {f.feed.get('title', fu)} ({len(f.entries)} entries)")
        if hasattr(f.feed, 'description') and f.feed.description:
            print(f"  Desc: {f.feed.description[:100]}")
        for entry in f.entries[:10]:
            pub = (entry.get("published") or entry.get("updated") or "")[:10]
            title = entry.get("title", "-")[:60]
            link = entry.get("link", "")
            print(f"  [{pub}] {title}")
            if link:
                print(f"    {link}")
        if len(f.entries) > 10:
            print(f"  ... and {len(f.entries)-10} more")
        return
    print("No feed found", file=sys.stderr)
    sys.exit(1)

def cmd_qr(*args):
    """Generate QR code."""
    _ensure_dep("qrcode")
    import qrcode
    text = " ".join(args) if args else ""
    if not text:
        print("Enter text to encode", file=sys.stderr)
        sys.exit(1)
    size = 256
    if len(args) > 1 and args[-1].isdigit():
        text = " ".join(args[:-1])
        size = int(args[-1])
    out = os.path.join(OUTPUT_DIR, f"qr_{datetime.now():%H%M%S}.png")
    img = qrcode.make(text, box_size=size // 25, border=2)
    img.save(out)
    print(f"QR code: {out} ({size}x{size})")

def cmd_playlist(url, limit=0):
    """List playlist entries."""
    import yt_dlp
    limit = int(limit) if limit else 0
    try:
        info = _try_ydl(url, _base_opts(skip_download=True, extract_flat=True))
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)
    entries = info.get("entries", []) if info else []
    if not entries:
        print("Not a playlist or empty", file=sys.stderr)
        sys.exit(1)
    print(f"Playlist: {info.get('title', '-')} ({len(entries)} videos)")
    print("-" * 60)
    for i, entry in enumerate(entries[:limit] if limit else entries):
        title = (entry.get("title", "-")[:50] if entry else "-") if entry else "-"
        dur = _ts(entry.get("duration")) if entry and entry.get("duration") else "-"
        vid = entry.get("id", "-") if entry else "-"
        print(f"  {i+1:>3}. [{dur}] {title}  ({vid})")
    if limit and limit < len(entries):
        print(f"  ... and {len(entries)-limit} more")

def cmd_convert(filepath, fmt="mp3", quality="192"):
    """Convert local media file."""
    ffmpeg = _get_ffmpeg()
    if not ffmpeg:
        print("ffmpeg not found", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    audio_fmts = {"mp3": "libmp3lame", "aac": "aac", "flac": "flac", "wav": "pcm_s16le", "opus": "libopus"}
    video_fmts = {"mp4", "webm", "mkv"}
    base = os.path.splitext(os.path.basename(filepath))[0]
    if fmt in video_fmts:
        out = os.path.join(OUTPUT_DIR, f"{base}.{fmt}")
        args = [ffmpeg, "-i", filepath,
                "-c:v", "libx264" if fmt == "mp4" else "libvpx" if fmt == "webm" else "libx264",
                "-c:a", "aac" if fmt == "mp4" else "libvorbis" if fmt == "webm" else "aac",
                "-y", out]
    elif fmt in audio_fmts:
        out = os.path.join(OUTPUT_DIR, f"{base}.{fmt}")
        args = [ffmpeg, "-i", filepath, "-vn", "-acodec", audio_fmts[fmt]]
        if fmt in ("mp3", "aac"):
            args += ["-ab", f"{quality}k"]
        if fmt == "flac":
            args += ["-compression_level", "5"]
        if fmt == "opus":
            args += ["-b:a", f"{quality}k"]
        args += ["-y", out]
    else:
        print(f"Unsupported format: {fmt}", file=sys.stderr)
        sys.exit(1)
    try:
        subprocess.run(args, check=True, capture_output=True, timeout=600)
    except Exception as e:
        print(f"Conversion failed: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Converted: {out} ({os.path.getsize(out)/(1024*1024):.1f} MB)")

def cmd_batch(filepath, command="sub"):
    """Batch process URLs from file."""
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    urls = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
    if not urls:
        print("No valid URLs in file", file=sys.stderr)
        sys.exit(1)
    print(f"{len(urls)} URLs, running: {command}")
    print("=" * 40)
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] {url[:80]}")
        try:
            subprocess.run([sys.executable, __file__, command, url], timeout=300, check=False)
        except Exception as e:
            print(f"  Failed: {e}")
    print(f"\nBatch done ({len(urls)} URLs)")

def cmd_media(url, download=False):
    """Extract images, GIFs, video, and animation elements from a page."""
    _ensure_dep("bs4", "beautifulsoup4")
    from bs4 import BeautifulSoup
    import requests as req
    try:
        resp = req.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)
    soup = BeautifulSoup(resp.text, "html.parser")
    base_url = resp.url

    results = {"images": [], "gifs": [], "videos": [], "svg": [], "canvas": [], "lazy": []}

    # Static images
    for img in soup.find_all("img", src=True):
        src = img["src"]
        if src.startswith("data:"):
            continue
        full = urllib.parse.urljoin(base_url, src)
        is_gif = ".gif" in src.lower()
        is_lazy = img.get("loading") == "lazy" or img.get("data-src")
        target = "gifs" if is_gif else "lazy" if is_lazy else "images"
        results[target].append(full)

    # Picture elements
    for pic in soup.find_all("picture"):
        for source in pic.find_all("source", srcset=True):
            for src in source["srcset"].split(","):
                url_part = src.strip().split(" ")[0]
                if url_part:
                    results["images"].append(urllib.parse.urljoin(base_url, url_part))

    # Video elements
    for video in soup.find_all("video"):
        for src in video.find_all("source", src=True):
            results["videos"].append(urllib.parse.urljoin(base_url, src["src"]))
        if video.get("src"):
            results["videos"].append(urllib.parse.urljoin(base_url, video["src"]))

    # SVG
    for svg in soup.find_all("svg"):
        if svg.get("viewBox") or svg.get("width"):
            results["svg"].append(f"<svg viewBox=\"{svg.get('viewBox','')}\" ...>")

    # Canvas
    for canvas in soup.find_all("canvas"):
        w = canvas.get("width", "?")
        h = canvas.get("height", "?")
        results["canvas"].append(f"<canvas {w}x{h}>")

    # Print results
    total = sum(len(v) for v in results.values())
    print(f"Found {total} media elements on {resp.url}")
    print("-" * 50)

    for category, items in results.items():
        if not items:
            continue
        label = {"images": "Images", "gifs": "GIFs", "videos": "Videos",
                 "svg": "SVGs", "canvas": "Canvas", "lazy": "Lazy-loaded"}[category]
        print(f"\n{label} ({len(items)}):")
        for item in items[:10]:
            print(f"  {item[:120]}")
        if len(items) > 10:
            print(f"  ... and {len(items)-10} more")

    # Save URLs to file
    all_urls = []
    for cat in ("images", "gifs", "videos", "lazy"):
        all_urls.extend(results[cat])
    if all_urls:
        _save_text("\n".join(all_urls), "media_urls.txt")
        print(f"\nAll URLs saved")


TECH_SIGNATURES = [
    # Frameworks
    ("Next.js", ["__NEXT_DATA__", "nextjs", "next/"]),
    ("React", ["react.js", "react-dom", "data-reactroot", "createElement"]),
    ("Vue.js", ["vue.js", "vue.min.js", "data-v-", "v-bind", "v-model"]),
    ("Angular", ["angular.js", "ng-app", "ng-controller", "ng-if"]),
    ("Svelte", ["svelte", "__svelte"]),
    ("Nuxt.js", ["nuxt"]),
    ("Gatsby", ["gatsby"]),
    ("Django", ["django", "csrfmiddlewaretoken"]),
    ("Ruby on Rails", ["rails", "csrf-param"]),
    ("Laravel", ["laravel", "livewire"]),
    ("Spring Boot", ["spring"]),
    ("Flask", ["flask"]),
    # CMS
    ("WordPress", ["wp-content", "wp-includes", "wordpress"]),
    ("Drupal", ["drupal"]),
    ("Joomla", ["joomla"]),
    ("Shopify", ["shopify", "myshopify"]),
    # Libraries
    ("jQuery", ["jquery"]),
    ("Bootstrap", ["bootstrap"]),
    ("Tailwind CSS", ["tailwind"]),
    ("Font Awesome", ["fontawesome", "font-awesome"]),
    ("Three.js", ["three.js"]),
    ("D3.js", ["d3.js"]),
    ("GSAP", ["gsap"]),
    # Analytics
    ("Google Analytics", ["ga.js", "gtag", "analytics.js"]),
    ("Cloudflare", ["cloudflare"]),
    # CDN / Hosting
    ("GitHub Pages", ["github.io"]),
    ("Netlify", ["netlify"]),
    ("Vercel", ["vercel"]),
    # Server
    ("Nginx", ["nginx"]),
    ("Apache", ["apache"]),
    ("IIS", ["iis"]),
    ("Caddy", ["caddy"]),
    ("Node.js", ["node.js", "nodejs"]),
    ("Python", ["python"]),
    ("Java", ["java"]),
    ("Go", ["golang"]),
]


def cmd_tech(url):
    """Analyze web technology stack."""
    import requests as req
    from bs4 import BeautifulSoup
    try:
        resp = req.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)

    soup = BeautifulSoup(resp.text, "html.parser")
    html_text = resp.text.lower()
    headers = resp.headers
    result = []

    # Signature matching
    for tech_name, signatures in TECH_SIGNATURES:
        for sig in signatures:
            if sig in html_text or sig in resp.text:
                result.append(tech_name)
                break

    # HTTP header detection
    server = headers.get("Server", "")
    if server:
        result.append(f"Server: {server}")
    powered = headers.get("X-Powered-By", "")
    if powered:
        result.append(powered)

    # Meta generator
    meta_gen = soup.find("meta", attrs={"name": "generator"})
    if meta_gen and meta_gen.get("content"):
        result.append(f"Generator: {meta_gen['content']}")

    # Content-Type
    ct = headers.get("Content-Type", "")
    if ct:
        result.append(f"Content-Type: {ct.split(';')[0].strip()}")

    # Compression
    encoding = headers.get("Content-Encoding", "")
    if encoding:
        result.append(f"Encoding: {encoding}")

    # Security headers
    for h in ("Strict-Transport-Security", "Content-Security-Policy",
              "X-Frame-Options", "X-Content-Type-Options"):
        if headers.get(h):
            result.append(f"Security: {h}")

    # Deduplicate and print
    seen = set()
    print(f"Technology Analysis — {resp.url}")
    print("-" * 50)
    for item in result:
        if item not in seen:
            seen.add(item)
            print(f"  {item}")
    print(f"\n{len(seen)} technologies detected")


# ---------------------------------------------------------------------------
# Network commands
# ---------------------------------------------------------------------------

def cmd_dns(domain):
    """DNS lookup for a domain."""
    import socket
    record_types = {
        "A": socket.AF_INET, "AAAA": socket.AF_INET6,
        "CNAME": socket.AF_INET, "MX": socket.AF_INET,
    }
    print(f"DNS records for {domain}")
    print("-" * 40)
    for rtype, af in record_types.items():
        try:
            results = sorted(set(
                addr[-1][0] for addr in socket.getaddrinfo(domain, 0, af, socket.SOCK_STREAM)
            ))
            if results:
                print(f"  {rtype:<6} {', '.join(results[:5])}")
                if len(results) > 5:
                    print(f"         ... and {len(results)-5} more")
        except Exception:
            pass
    # MX records (manual via socket)
    try:
        import subprocess
        # Fallback: show resolved IPs
        ip = socket.gethostbyname(domain)
        print(f"  IP:     {ip}")
    except Exception as e:
        print(f"  Error:  {e}")

def cmd_ip():
    """Show current public IP address."""
    import requests as req
    services = ["https://api.ipify.org", "https://icanhazip.com", "https://checkip.amazonaws.com"]
    for svc in services:
        try:
            r = req.get(svc, timeout=10)
            if r.status_code == 200:
                print(f"Public IP: {r.text.strip()}")
                return
        except Exception:
            pass
    print("Could not determine public IP", file=sys.stderr)
    sys.exit(1)

def cmd_whois(domain):
    """Domain WHOIS lookup."""
    try:
        import whois
        w = whois.whois(domain)
    except ImportError:
        # Fallback: use subprocess
        import subprocess
        try:
            r = subprocess.run(["whois", domain], capture_output=True, text=True, timeout=30)
            print(r.stdout[:2000] if r.stdout else "No WHOIS data")
            return
        except Exception as e:
            print(f"whois not available. Install: pip install whois", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"WHOIS lookup failed: {e}", file=sys.stderr)
        sys.exit(1)
    items = [
        ("Domain", w.get("domain_name")),
        ("Registrar", w.get("registrar")),
        ("Creation", w.get("creation_date")),
        ("Expiry", w.get("expiration_date")),
        ("Name Servers", w.get("name_servers")),
        ("Org", w.get("org") or w.get("organization")),
        ("Country", w.get("country")),
        ("Email", w.get("emails") or w.get("admin_email")),
    ]
    print(f"WHOIS — {domain}")
    print("-" * 40)
    for label, val in items:
        if val:
            if isinstance(val, list):
                val = ", ".join(str(v)[:50] for v in val[:3])
            elif hasattr(val, '__iter__'):
                val = str(val)[:50]
            print(f"  {label:<15} {val}")

def cmd_ssl(domain, port="443"):
    """SSL certificate information."""
    import socket, ssl
    import certifi
    from datetime import datetime
    try:
        ctx = ssl.create_default_context(cafile=certifi.where())
        with socket.create_connection((domain, int(port)), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
    except Exception as e:
        print(f"SSL connection failed: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"SSL Certificate — {domain}:{port}")
    print("-" * 50)
    print(f"  Subject:     {dict(x[0] for x in cert.get('subject', []))}")
    print(f"  Issuer:      {dict(x[0] for x in cert.get('issuer', []))}")
    print(f"  Serial:      {cert.get('serialNumber', '-')}")
    print(f"  Version:     {cert.get('version', '-')}")
    print(f"  Valid From:  {cert.get('notBefore', '-')}")
    print(f"  Valid Until: {cert.get('notAfter', '-')}")
    print(f"  SAN:         {', '.join(cert.get('subjectAltName', [('','-')])[0][1:][0])}")
    print(f"  Algorithm:   {cert.get('signatureAlgorithm', '-')}")

def cmd_port(host, ports="21,22,23,25,53,80,110,143,443,445,993,995,1433,1521,3306,3389,5432,6379,8080,8443"):
    """Scan common ports on a host."""
    import socket, concurrent.futures
    port_list = [int(p.strip()) for p in ports.split(",") if p.strip().isdigit()]
    open_ports = []
    def _scan(p):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            r = s.connect_ex((host, p))
            s.close()
            return p if r == 0 else None
        except: return None
    print(f"Scanning {host} ({len(port_list)} ports)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        for result in ex.map(_scan, port_list):
            if result:
                open_ports.append(result)
    if open_ports:
        print(f"\nOpen ports ({len(open_ports)}):")
        for p in sorted(open_ports):
            svc = {21:"FTP",22:"SSH",23:"Telnet",25:"SMTP",53:"DNS",80:"HTTP",
                   110:"POP3",143:"IMAP",443:"HTTPS",445:"SMB",993:"IMAPS",
                   995:"POP3S",1433:"MSSQL",3306:"MySQL",3389:"RDP",
                   5432:"PostgreSQL",6379:"Redis",8080:"HTTP-Alt",8443:"HTTPS-Alt"}.get(p,"")
            print(f"  {p:<5} {svc}")
    else:
        print("No open ports found")

# ---------------------------------------------------------------------------
# URL commands
# ---------------------------------------------------------------------------

def cmd_shorten(url):
    """Shorten a URL using TinyURL."""
    import requests as req
    try:
        r = req.get(f"https://tinyurl.com/api-create.php?url={req.utils.quote(url)}", timeout=10)
        if r.status_code == 200 and r.text.strip():
            print(f"Original: {url}")
            print(f"Short:    {r.text.strip()}")
            return
    except Exception:
        pass
    print("URL shortening failed", file=sys.stderr)
    sys.exit(1)

def cmd_expand(url):
    """Expand a shortened URL to its real destination."""
    import requests as req
    try:
        r = req.get(url, timeout=10, allow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0"})
        print(f"Short:    {url}")
        print(f"Expands to: {r.url}")
        print(f"Redirects: {len(r.history)} hops")
        for i, hop in enumerate(r.history):
            print(f"  {i+1}. {hop.status_code} -> {hop.url}")
    except Exception as e:
        print(f"Expand failed: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_cookies(url):
    """View cookies set by a page."""
    import requests as req
    try:
        r = req.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)
    cookies = r.cookies
    if not cookies:
        print("No cookies set by this page")
        return
    print(f"Cookies for {r.url}")
    print("-" * 50)
    for c in cookies:
        print(f"  {c.name}")
        print(f"    Value:    {c.value[:60]}{'...' if len(c.value) > 60 else ''}")
        print(f"    Domain:   {c.domain}")
        print(f"    Path:     {c.path}")
        print(f"    Secure:   {c.secure}")
        print(f"    HTTPOnly: {c.has_nonstandard_attr('HttpOnly') or False}")
        if c.expires:
            from datetime import datetime
            print(f"    Expires:  {datetime.fromtimestamp(c.expires)}")

# ---------------------------------------------------------------------------
# Page commands
# ---------------------------------------------------------------------------

def cmd_tables(url):
    """Extract HTML tables as CSV."""
    _ensure_dep("bs4", "beautifulsoup4")
    from bs4 import BeautifulSoup
    import requests as req
    try:
        resp = req.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)
    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        print("No tables found on this page", file=sys.stderr)
        sys.exit(1)
    print(f"Found {len(tables)} table(s) on {resp.url}")
    for i, table in enumerate(tables):
        rows = table.find_all("tr")
        data = []
        for row in rows:
            cells = row.find_all(["th", "td"])
            data.append([cell.get_text(strip=True) for cell in cells])
        if not data:
            continue
        print(f"\n--- Table {i+1} ({len(data)} rows, {len(data[0])} cols) ---")
        for row in data[:15]:
            print("  " + " | ".join(row[:8]))
        if len(data) > 15:
            print(f"  ... ({len(data)-15} more rows)")
        # Save to CSV
        csv_path = os.path.join(OUTPUT_DIR, f"table_{i+1}.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            for row in data:
                f.write(",".join(f'"{c}"' for c in row) + "\n")
        print(f"  Saved: {csv_path}")

def cmd_sitemap(url):
    """Extract links from sitemap.xml."""
    import requests as req
    import xml.etree.ElementTree as ET
    sitemap_url = url.rstrip("/") + "/sitemap.xml"
    try:
        resp = req.get(sitemap_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            print(f"No sitemap found at {sitemap_url}", file=sys.stderr)
            sys.exit(1)
        root = ET.fromstring(resp.content)
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [loc.text for loc in root.findall(".//s:loc", ns) if loc.text]
        if not urls:
            urls = [loc.text for loc in root.findall(".//loc") if loc.text]
        print(f"Sitemap: {len(urls)} URLs")
        for u in urls[:30]:
            print(f"  {u}")
        if len(urls) > 30:
            print(f"  ... and {len(urls)-30} more")
        _save_text("\n".join(urls), "sitemap_urls.txt")
    except ET.ParseError:
        print("Invalid sitemap XML", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_forms(url):
    """Extract form fields from a page."""
    _ensure_dep("bs4", "beautifulsoup4")
    from bs4 import BeautifulSoup
    import requests as req
    try:
        resp = req.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)
    soup = BeautifulSoup(resp.text, "html.parser")
    forms = soup.find_all("form")
    if not forms:
        print("No forms found", file=sys.stderr)
        sys.exit(1)
    print(f"Found {len(forms)} form(s) on {resp.url}")
    for i, form in enumerate(forms):
        action = form.get("action", "(self)")
        method = form.get("method", "GET").upper()
        print(f"\n--- Form {i+1} (method={method}, action={action}) ---")
        for inp in form.find_all(["input", "textarea", "select"]):
            name = inp.get("name", "")
            if not name:
                continue
            typ = inp.get("type", "text") if inp.name == "input" else inp.name
            val = inp.get("value", "")
            required = inp.get("required", False)
            flags = " *" if required else ""
            placeholder = inp.get("placeholder", "")
            ph = f' [{placeholder}]' if placeholder else ""
            print(f"  {name:<20} type={typ:<10} value={val[:30]}{ph}{flags}")

def cmd_archive(url):
    """Check Wayback Machine for historical snapshots."""
    import requests as req, json
    try:
        cdx_url = f"https://web.archive.org/cdx/search/cdx?url={req.utils.quote(url)}&output=json&limit=5"
        r = req.get(cdx_url, timeout=30)
        data = r.json()
    except Exception as e:
        print(f"Wayback Machine query failed: {e}", file=sys.stderr)
        sys.exit(1)
    if len(data) <= 1:
        print("No archived snapshots found")
        return
    print(f"Wayback Machine — {url}")
    print("-" * 50)
    latest = None
    for entry in data[1:]:
        ts = entry[1]
        year = ts[:4]
        date = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}"
        status = entry[4]
        arch_url = f"https://web.archive.org/web/{ts}/{entry[2]}"
        print(f"  [{year}] {date} [{status}] {arch_url[:100]}")
        if not latest:
            latest = arch_url
    if latest:
        print(f"\nLatest: {latest}")

def cmd_wget(url):
    """Download full page HTML."""
    import requests as req
    try:
        resp = req.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)
    from datetime import datetime
    fn = f"page_{datetime.now():%Y%m%d_%H%M%S}.html"
    path = os.path.join(OUTPUT_DIR, fn)
    with open(path, "w", encoding="utf-8") as f:
        f.write(resp.text)
    print(f"Saved: {path} ({len(resp.text):,} bytes)")

# ---------------------------------------------------------------------------
# Security commands
# ---------------------------------------------------------------------------

def cmd_csp(url):
    """Parse Content-Security-Policy headers."""
    import requests as req
    try:
        resp = req.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr); sys.exit(1)
    csp = resp.headers.get("Content-Security-Policy", "")
    if not csp:
        print("No Content-Security-Policy header found")
        return
    print(f"CSP for {resp.url}")
    print("-" * 50)
    for directive in csp.split(";"):
        d = directive.strip()
        if d:
            name, _, value = d.partition(" ")
            print(f"  {name}")
            for val in value.split():
                print(f"    {val}")

def cmd_emails(url):
    """Extract email addresses from a page."""
    _ensure_dep("bs4", "beautifulsoup4")
    from bs4 import BeautifulSoup
    import requests as req
    try:
        resp = req.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr); sys.exit(1)
    emails = set(re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', resp.text))
    if not emails:
        print("No email addresses found")
        return
    print(f"Found {len(emails)} email(s) on {resp.url}")
    for e in sorted(emails):
        print(f"  {e}")

def cmd_hsts(domain):
    """Check HSTS preload status."""
    import requests as req
    try:
        resp = req.get(f"https://{domain}", timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        hsts = resp.headers.get("Strict-Transport-Security", "")
        print(f"HSTS for {domain}")
        print("-" * 40)
        print(f"  Header:      {'Present' if hsts else 'Not set'}")
        if hsts:
            print(f"  Value:       {hsts}")
            print(f"  Preload:     {'Yes' if 'preload' in hsts else 'No'}")
        print(f"  HTTPS:       {'Yes' if resp.url.startswith('https') else 'No'}")
        print(f"  Status:      {resp.status_code}")
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr); sys.exit(1)

# ---------------------------------------------------------------------------
# Dev tool commands
# ---------------------------------------------------------------------------

def cmd_json(url):
    """Fetch and format JSON response."""
    import requests as req
    try:
        resp = req.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        data = resp.json()
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr); sys.exit(1)
    print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
    _save_text(json.dumps(data, indent=2, ensure_ascii=False), "response.json")

def cmd_http(method, url, body=""):
    """Send custom HTTP request."""
    import requests as req
    method = method.upper()
    try:
        if method in ("GET", "HEAD", "DELETE", "OPTIONS"):
            resp = req.request(method, url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        else:
            resp = req.request(method, url, data=body or None, timeout=30,
                               headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
        print(f"{method} {url}")
        print(f"Status: {resp.status_code} {resp.reason}")
        print(f"Time:   {resp.elapsed.total_seconds()*1000:.0f} ms")
        print("-" * 50)
        for k, v in resp.headers.items():
            print(f"  {k}: {v}")
        if resp.text:
            print(f"\nBody ({len(resp.text)} bytes):")
            print(resp.text[:1000])
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr); sys.exit(1)

def cmd_diff(url1, url2):
    """Compare two web pages."""
    import requests as req, difflib
    try:
        r1 = req.get(url1, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r2 = req.get(url2, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr); sys.exit(1)
    lines1 = r1.text.splitlines()
    lines2 = r2.text.splitlines()
    diff = list(difflib.unified_diff(lines1, lines2, fromfile=url1, tofile=url2, n=3))
    if not diff:
        print("Pages are identical")
        return
    print(f"Differences ({len(diff)} lines changed)")
    print("-" * 50)
    for line in diff[:50]:
        if line.startswith("+") and not line.startswith("+++"):
            print(f"\033[32m{line}\033[0m", end="\n")
        elif line.startswith("-") and not line.startswith("---"):
            print(f"\033[31m{line}\033[0m", end="\n")
        else:
            print(line)
    if len(diff) > 50:
        print(f"... and {len(diff)-50} more diffs")

def cmd_hash(*args):
    """Hash text (md5, sha1, sha256)."""
    import hashlib
    text = " ".join(args) if args else ""
    if not text:
        print("Enter text to hash", file=sys.stderr); sys.exit(1)
    print(f"Text: {text}")
    print("-" * 40)
    for algo in ("md5", "sha1", "sha256", "sha512"):
        h = hashlib.new(algo, text.encode()).hexdigest()
        print(f"  {algo.upper():<10} {h}")

def cmd_base64(*args):
    """Base64 encode or decode."""
    text = " ".join(args) if args else ""
    if not text:
        print("Enter text to encode", file=sys.stderr); sys.exit(1)
    import base64 as b64
    print(f"Text: {text}")
    print("-" * 40)
    print(f"  Encoded:  {b64.b64encode(text.encode()).decode()}")
    try:
        print(f"  Decoded:  {b64.b64decode(text).decode()}")
    except Exception:
        pass

def cmd_uuid():
    """Generate a UUID."""
    import uuid
    print(f"UUID v4:   {uuid.uuid4()}")
    print(f"UUID v1:   {uuid.uuid1()}")

def cmd_timestamp():
    """Show current time info."""
    from datetime import datetime, timezone
    now = datetime.now()
    utc = datetime.now(timezone.utc)
    print(f"Local:     {now}")
    print(f"UTC:       {utc}")
    print(f"Unix:      {int(now.timestamp())}")
    print(f"ISO:       {now.isoformat()}")

def cmd_favicon(url):
    """Download website favicon."""
    import requests as req
    try:
        r = req.get(f"https://www.google.com/s2/favicons?domain={url}&sz=256",
                     timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            print("No favicon found", file=sys.stderr); sys.exit(1)
        ext = "png"
        path = os.path.join(OUTPUT_DIR, f"favicon.{ext}")
        with open(path, "wb") as f:
            f.write(r.content)
        print(f"Saved: {path} ({len(r.content)/1024:.1f} KB)")
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr); sys.exit(1)

# ---------------------------------------------------------------------------
# Network tool commands
# ---------------------------------------------------------------------------

def cmd_ping(host):
    """Ping a host."""
    import subprocess, platform
    param = "-n" if platform.system().lower() == "windows" else "-c"
    try:
        r = subprocess.run(["ping", param, "4", host], capture_output=True, text=True, timeout=30)
        print(r.stdout[-500:] if r.stdout else r.stderr[-500:])
    except FileNotFoundError:
        print("ping command not available on this system", file=sys.stderr); sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Ping timed out", file=sys.stderr); sys.exit(1)

def cmd_speedtest():
    """Run a network speed test."""
    try:
        import speedtest
        st = speedtest.Speedtest()
        print("Testing download speed...")
        dl = st.download() / 1_000_000
        print(f"Download: {dl:.1f} Mbps")
        print("Testing upload speed...")
        ul = st.upload() / 1_000_000
        print(f"Upload:   {ul:.1f} Mbps")
        print(f"Ping:     {st.results.ping:.0f} ms")
    except ImportError:
        print("Install speedtest-cli: pip install speedtest-cli", file=sys.stderr); sys.exit(1)
    except Exception as e:
        print(f"Speedtest failed: {e}", file=sys.stderr); sys.exit(1)

def cmd_trace(host):
    """Traceroute to a host."""
    import subprocess, platform
    cmd = "tracert" if platform.system().lower() == "windows" else "traceroute"
    try:
        r = subprocess.run([cmd, host], capture_output=True, text=True, timeout=60)
        output = r.stdout or r.stderr
        print(output[:2000])
        if len(output) > 2000:
            print(f"... ({len(output)-2000} more chars)")
    except FileNotFoundError:
        print(f"{cmd} not available on this system", file=sys.stderr); sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Traceroute timed out", file=sys.stderr); sys.exit(1)

# ---------------------------------------------------------------------------
# File commands
# ---------------------------------------------------------------------------

def cmd_checksum(filepath):
    """Calculate file checksums."""
    import hashlib
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}", file=sys.stderr); sys.exit(1)
    size = os.path.getsize(filepath)
    print(f"File: {filepath} ({size:,} bytes)")
    print("-" * 40)
    for algo in ("md5", "sha1", "sha256"):
        h = hashlib.new(algo)
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        print(f"  {algo.upper():<10} {h.hexdigest()}")

def cmd_type(filepath):
    """Detect file type."""
    import struct
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}", file=sys.stderr); sys.exit(1)
    with open(filepath, "rb") as f:
        head = f.read(16)
    sigs = {
        b"\x89PNG\r\n\x1a\n": "PNG Image",
        b"\xff\xd8\xff": "JPEG Image",
        b"GIF8": "GIF Image",
        b"RIFF": "WebP / AVI",
        b"\x25PDF": "PDF Document",
        b"PK\x03\x04": "ZIP / DOCX / XLSX",
        b"\x1f\x8b": "GZIP Archive",
        b"%!PS": "PostScript",
        b"\x00\x00\x00\x18ftyp": "MP4 Video",
        b"\x00\x00\x00\x1cftyp": "MP4 Video",
        b"\x1a\x45\xdf\xa3": "WebM / MKV Video",
        b"ID3": "MP3 Audio",
        b"\xff\xfb": "MP3 Audio",
        b"OggS": "OGG Audio/Video",
        b"\x42\x4d": "BMP Image",
        b"\x49\x49\x2a\x00": "TIFF Image",
        b"\x4d\x4d\x00\x2a": "TIFF Image",
        b"\xca\xfe\xba\xbe": "Java Class",
        b"\xcf\xfa\xed\xfe": "Mach-O Binary",
        b"\x7fELF": "ELF Binary",
        b"MZ": "Windows Executable",
    }
    name = "Unknown"
    for sig, desc in sigs.items():
        if head.startswith(sig):
            name = desc; break
    ext = os.path.splitext(filepath)[1].lower()
    print(f"File: {os.path.basename(filepath)}")
    print(f"Size: {os.path.getsize(filepath):,} bytes")
    print(f"Type: {name}")
    print(f"Ext:  {ext or '(none)'}")


# ---------------------------------------------------------------------------
# Math commands
# ---------------------------------------------------------------------------

def cmd_calc(*args):
    """Evaluate a math expression."""
    expr = " ".join(args) if args else ""
    if not expr:
        print("Enter an expression", file=sys.stderr); sys.exit(1)
    allowed = set("0123456789+-*/.()%^ ")
    if not all(c in allowed for c in expr):
        print("Only basic math allowed", file=sys.stderr); sys.exit(1)
    try:
        result = eval(expr, {"__builtins__": {}}, {"abs": abs, "round": round, "int": int, "float": float})
        print(f"{expr} = {result}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr); sys.exit(1)

def cmd_units(value, fro="", to=""):
    """Convert between units."""
    try: val = float(value)
    except ValueError: print("Invalid number", file=sys.stderr); sys.exit(1)
    fro, to = fro.lower(), to.lower()
    conv = {("m","km"):0.001,("km","m"):1000,("m","cm"):100,("cm","m"):0.01,
            ("m","mm"):1000,("mm","m"):0.001,("m","ft"):3.28084,("ft","m"):0.3048,
            ("km","mi"):0.621371,("mi","km"):1.60934,
            ("kg","g"):1000,("g","kg"):0.001,("kg","lb"):2.20462,("lb","kg"):0.453592,
            ("c","f"):"ctof",("f","c"):"ftoc"}
    key = (fro, to)
    if key in conv:
        if conv[key] == "ctof": r = val*9/5+32
        elif conv[key] == "ftoc": r = (val-32)*5/9
        else: r = val*conv[key]
        print(f"{val} {fro} = {r:.4f} {to}")
    else: print(f"Cannot convert {fro} -> {to}", file=sys.stderr); sys.exit(1)

def cmd_color(h):
    """Convert hex color. Usage: color #FF0000"""
    h = h.lstrip("#")
    if len(h) != 6: print("Use #RRGGBB", file=sys.stderr); sys.exit(1)
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    rn, gn, bn = r/255, g/255, b/255
    mx, mn = max(rn,gn,bn), min(rn,gn,bn)
    l = (mx+mn)/2
    if mx==mn: s,h_ang=0,0
    else:
        d=mx-mn; s=d/(2-mx-mn) if l>.5 else d/(mx+mn)
        if mx==rn: h_ang=((gn-bn)/d+(6 if gn<bn else 0))*60
        elif mx==gn: h_ang=((bn-rn)/d+2)*60
        else: h_ang=((rn-gn)/d+4)*60
    print(f"HEX: #{h.upper()}\nRGB: rgb({r},{g},{b})\nHSL: hsl({h_ang:.0f},{s*100:.0f}%,{l*100:.0f}%)")

def cmd_roman(n):
    """Convert to Roman numerals."""
    try: n=int(n)
    except: print("Enter integer", file=sys.stderr); sys.exit(1)
    if n<1 or n>3999: print("Use 1-3999", file=sys.stderr); sys.exit(1)
    v=[(1000,"M"),(900,"CM"),(500,"D"),(400,"CD"),(100,"C"),(90,"XC"),
       (50,"L"),(40,"XL"),(10,"X"),(9,"IX"),(5,"V"),(4,"IV"),(1,"I")]
    r=""
    for x,s in v:
        while n>=x: r+=s; n-=x
    print(f"Roman: {r}")

# ---------------------------------------------------------------------------
# Text commands
# ---------------------------------------------------------------------------

def cmd_count(*args):
    """Count characters and words."""
    t=" ".join(args) if args else ""
    if not t: print("Enter text",file=sys.stderr);sys.exit(1)
    print(f"Chars:{len(t)} Words:{len(t.split())} Lines:{t.count(chr(10))+1}")

def cmd_reverse(*args):
    """Reverse text."""
    t=" ".join(args) if args else ""
    if not t: print("Enter text",file=sys.stderr);sys.exit(1)
    print(f"{t} -> {t[::-1]}")

def cmd_sort(*args):
    """Sort words alphabetically."""
    t=" ".join(args) if args else ""
    if not t: print("Enter text",file=sys.stderr);sys.exit(1)
    for w in sorted(t.split()): print(f"  {w}")

def cmd_case(*args):
    """Convert text case."""
    t=" ".join(args) if args else ""
    if not t: print("Enter text",file=sys.stderr);sys.exit(1)
    print(f"Upper:{t.upper()}\nLower:{t.lower()}\nTitle:{t.title()}")

# ---------------------------------------------------------------------------
# Codec commands
# ---------------------------------------------------------------------------

def cmd_url(*args):
    """URL encode/decode."""
    import urllib.parse
    t=" ".join(args) if args else ""
    if not t: print("Enter text",file=sys.stderr);sys.exit(1)
    print(f"Encoded:{urllib.parse.quote(t)}\nDecoded:{urllib.parse.unquote(t)}")

def cmd_hex(*args):
    """Hex encode/decode."""
    t=" ".join(args) if args else ""
    if not t: print("Enter text",file=sys.stderr);sys.exit(1)
    print(f"Hex:{t.encode().hex()}")
    try: print(f"Decoded:{bytes.fromhex(t).decode()}")
    except: pass

def cmd_html(*args):
    """HTML entity encode/decode."""
    import html
    t=" ".join(args) if args else ""
    if not t: print("Enter text",file=sys.stderr);sys.exit(1)
    print(f"Escaped:{html.escape(t)}\nUnescaped:{html.unescape(t)}")

def cmd_rot13(*args):
    """ROT13 encode/decode."""
    t=" ".join(args) if args else ""
    if not t: print("Enter text",file=sys.stderr);sys.exit(1)
    tr=str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                     "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm")
    print(f"ROT13: {t.translate(tr)}")

# ---------------------------------------------------------------------------
# Geo commands
# ---------------------------------------------------------------------------

def cmd_geo(ip_addr=""):
    """IP geolocation lookup."""
    import requests as req
    url = f"https://ipapi.co/{ip_addr}/json/" if ip_addr else "https://ipapi.co/json/"
    try:
        d = req.get(url,timeout=15,headers={"User-Agent":"Mozilla/5.0"}).json()
    except Exception as e: print(f"Failed:{e}",file=sys.stderr);sys.exit(1)
    if d.get("error"): print(f"Error:{d.get('reason','?')}",file=sys.stderr);sys.exit(1)
    print(f"IP:{d.get('ip','-')} City:{d.get('city','-')} Country:{d.get('country_name','-')}")
    print(f"ISP:{d.get('org','-')} Lat/Lon:{d.get('latitude','-')},{d.get('longitude','-')}")

def cmd_mylocation():
    """Show current IP location."""
    cmd_geo()

# ---------------------------------------------------------------------------
# Random commands
# ---------------------------------------------------------------------------

def cmd_rand(*args):
    """Generate random number."""
    import random as r
    if not args: print(f"Random:{r.randint(0,999)}")
    elif len(args)==1: print(f"Random:{r.randint(0,int(args[0]))}")
    else: print(f"Random:{r.randint(int(args[0]),int(args[1]))}")

def cmd_password(*args):
    """Generate random password."""
    import random,string
    n=int(args[0]) if args and args[0].isdigit() else 16
    c=string.ascii_letters+string.digits+"!@#$%^&*"
    print(f"Password ({n}): {''.join(random.choice(c) for _ in range(n))}")

def cmd_token(*args):
    """Generate random token."""
    import secrets
    n=int(args[0]) if args and args[0].isdigit() else 32
    print(f"Token ({n}): {secrets.token_hex(n//2+1)[:n]}")

# ---------------------------------------------------------------------------
# Calendar commands
# ---------------------------------------------------------------------------

def cmd_calendar(*args):
    """Display calendar for a year."""
    import calendar as cal
    y=int(args[0]) if args else datetime.now().year
    print(cal.TextCalendar().formatyear(y))

def cmd_countdown(*args):
    """Countdown to a date (YYYY-MM-DD)."""
    from datetime import datetime
    s=" ".join(args) if args else ""
    if not s: print("Enter date YYYY-MM-DD",file=sys.stderr);sys.exit(1)
    try: t=datetime.strptime(s,"%Y-%m-%d")
    except: print("Use YYYY-MM-DD",file=sys.stderr);sys.exit(1)
    d=(t-datetime.now()).days
    print(f"{abs(d)} days {'until' if d>=0 else 'ago'} {s}")

def cmd_week(*args):
    """Show day of week for a date."""
    from datetime import datetime
    s=" ".join(args) if args else datetime.now().strftime("%Y-%m-%d")
    try: dt=datetime.strptime(s,"%Y-%m-%d")
    except: print("Use YYYY-MM-DD",file=sys.stderr);sys.exit(1)
    print(f"{s} is {['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'][dt.weekday()]}")


# ---------------------------------------------------------------------------
# AI commands
# ---------------------------------------------------------------------------

def cmd_translate(*args):
    """Translate text (free API, no key). Usage: translate hello es"""
    if len(args) < 2:
        print("Usage: translate <text> <lang>", file=sys.stderr); sys.exit(1)
    target = args[-1]; text = " ".join(args[:-1])
    import requests as req, urllib.parse
    try:
        r = req.get(f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text)}&langpair=en|{target}", timeout=15)
        t = r.json().get("responseData", {}).get("translatedText", "")
        if t: print(f"({target}) {t}")
        else: print("Translation failed", file=sys.stderr); sys.exit(1)
    except Exception as e: print(f"Error: {e}", file=sys.stderr); sys.exit(1)

def cmd_sentiment(*args):
    """Basic sentiment analysis."""
    text = " ".join(args) if args else ""
    if not text: print("Enter text", file=sys.stderr); sys.exit(1)
    pos = {"good","great","excellent","amazing","love","beautiful","happy","best","awesome","brilliant","perfect","success","joy","grateful"}
    neg = {"bad","terrible","awful","horrible","hate","ugly","worst","poor","sad","angry","failure","disaster","miserable","tragic"}
    words = set(text.lower().split())
    p, n = len(words & pos), len(words & neg)
    s = (p - n) / (p + n) if (p + n) else 0
    label = "Positive" if s > 0.3 else "Negative" if s < -0.3 else "Neutral"
    print(f"{label} (score:{s:.2f})")

def cmd_detect(*args):
    """Detect language of text."""
    text = " ".join(args) if args else ""
    if not text: print("Enter text", file=sys.stderr); sys.exit(1)
    try:
        from langdetect import detect as ld, DetectorFactory
        DetectorFactory.seed = 0
        print(f"Language: {ld(text)}")
    except ImportError:
        import re
        cjk = len(re.findall(r'[一-鿿]', text))
        cyr = len(re.findall(r'[Ѐ-ӿ]', text))
        if cjk > len(text)*0.1: print("Language: zh")
        elif cyr > len(text)*0.1: print("Language: ru")
        else: print("Language: en (install langdetect for accuracy)")

def cmd_ask(*args):
    """Ask Claude AI (needs ANTHROPIC_API_KEY in .env)."""
    prompt = " ".join(args) if args else ""
    if not prompt: print("Enter question", file=sys.stderr); sys.exit(1)
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path): load_dotenv(env_path)
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key: print("Set ANTHROPIC_API_KEY in .env", file=sys.stderr); sys.exit(1)
    try:
        from anthropic import Anthropic
        r = Anthropic(api_key=key).messages.create(
            model="claude-sonnet-4-20250514", max_tokens=2048,
            system="Answer concisely.",
            messages=[{"role": "user", "content": prompt}])
        print(f"A: {next((b.text for b in r.content if hasattr(b,'text')),'')}")
    except Exception as e: print(f"AI error: {e}", file=sys.stderr); sys.exit(1)

def cmd_summarize(url):
    """Summarize a URL using AI (needs ANTHROPIC_API_KEY)."""
    import trafilatura
    print("Fetching...")
    html = trafilatura.fetch_url(url)
    if not html: print("Failed", file=sys.stderr); sys.exit(1)
    text = trafilatura.extract(html)
    if not text or len(text) < 50: print("Not enough text", file=sys.stderr); sys.exit(1)
    text = text[:8000]
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path): load_dotenv(env_path)
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key: print("Set ANTHROPIC_API_KEY in .env", file=sys.stderr); sys.exit(1)
    try:
        from anthropic import Anthropic
        r = Anthropic(api_key=key).messages.create(
            model="claude-sonnet-4-20250514", max_tokens=1024,
            system="Summarize in 3-5 bullet points.",
            messages=[{"role": "user", "content": f"Summarize:\n{text}"}])
        print(f"Summary:\n{next((b.text for b in r.content if hasattr(b,'text')),'')}")
    except Exception as e: print(f"AI error: {e}", file=sys.stderr); sys.exit(1)


# ---------------------------------------------------------------------------
# Search & Crawl commands
# ---------------------------------------------------------------------------

def cmd_search(*args):
    """Search the web (free, no API key)."""
    query = " ".join(args) if args else ""
    if not query: print("Enter query", file=sys.stderr); sys.exit(1)
    try:
        from duckduckgo_search import DDGS
        results = list(DDGS().text(query, max_results=10))
        print(f"Results for: {query}")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r.get('title','?')}\n     {r.get('href','')}\n     {(r.get('body','') or '')[:80]}\n")
        if not results: print("No results")
    except Exception as e:
        print(f"Search failed: {e}", file=sys.stderr)

def cmd_crawl(url, max_pages=10):
    """Crawl a website up to N pages."""
    import requests as req
    from bs4 import BeautifulSoup
    import trafilatura
    visited, to_visit, base = set(), [url], urllib.parse.urlparse(url).netloc
    pages = []
    while to_visit and len(visited) < int(max_pages):
        cur = to_visit.pop(0)
        if cur in visited: continue
        visited.add(cur)
        try:
            r = req.get(cur, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
            if r.status_code != 200: continue
            t = trafilatura.extract(r.text)
            if t: pages.append(t[:500]); print(f"  [{len(visited)}] {cur[:70]}")
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                h = urllib.parse.urljoin(cur, a["href"])
                if urllib.parse.urlparse(h).netloc == base and h not in visited: to_visit.append(h)
        except: pass
    print(f"\nCrawled {len(pages)} pages")
    if pages: _save_text("\n\n".join(pages), "crawl_output.txt")

def cmd_spider(url):
    """Map all internal links of a site."""
    import requests as req
    from bs4 import BeautifulSoup
    try: resp = req.get(url, timeout=30, headers={"User-Agent":"Mozilla/5.0"})
    except Exception as e: print(f"Failed:{e}", file=sys.stderr); sys.exit(1)
    soup = BeautifulSoup(resp.text, "html.parser")
    base, domain = resp.url, urllib.parse.urlparse(resp.url).netloc
    links = sorted({urllib.parse.urljoin(base, a["href"]) for a in soup.find_all("a", href=True)
                   if urllib.parse.urlparse(urllib.parse.urljoin(base, a["href"])).netloc == domain})
    print(f"{len(links)} internal links")
    for l in links: print(f"  {l}")
    if links: _save_text("\n".join(links), "spider_links.txt")


# ---------------------------------------------------------------------------
# Data commands
# ---------------------------------------------------------------------------

def cmd_btc():
    """Bitcoin price."""
    import requests as req
    try:
        d = req.get("https://api.coindesk.com/v1/bpi/currentprice.json", timeout=15).json()
        print(f"Bitcoin: ${d['bpi']['USD']['rate']}")
    except Exception as e: print(f"Error: {e}", file=sys.stderr)

def cmd_eth():
    """Ethereum price."""
    import requests as req
    try:
        d = req.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd", timeout=15).json()
        print(f"Ethereum: ${d.get('ethereum',{}).get('usd','?')}")
    except Exception as e: print(f"Error: {e}", file=sys.stderr)

def cmd_weather(*args):
    """Weather for a city."""
    import requests as req
    city = " ".join(args) if args else "London"
    try:
        r = req.get(f"https://wttr.in/{city}?format=%C+%t+%w&m", timeout=15).text.strip()
        print(f"{city.title()}: {r}")
    except Exception as e: print(f"Error: {e}", file=sys.stderr)

def cmd_hn():
    """Hacker News top stories."""
    import requests as req
    try:
        ids = req.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15).json()[:10]
        for i, sid in enumerate(ids, 1):
            item = req.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=15).json()
            print(f"  {i}. {item.get('title','?')}\n     {item.get('url',f'https://news.ycombinator.com/item?id={sid}')}\n")
    except Exception as e: print(f"Error: {e}", file=sys.stderr)

def cmd_news(*args):
    """Top news headlines."""
    import requests as req
    topic = " ".join(args) if args else "technology"
    try:
        d = req.get(f"https://gnews.io/api/v4/top-headlines?topic={topic}&lang=en&max=10&token=test", timeout=15).json()
        for a in d.get("articles", [])[:10]:
            print(f"  {a.get('title','?')}\n     {a.get('url','')}\n")
    except: print(f"No news for '{topic}'", file=sys.stderr)

# ---------------------------------------------------------------------------
# Security commands
# ---------------------------------------------------------------------------

def cmd_jwt(*args):
    """Decode JWT token."""
    import base64, json
    t = args[0] if args else ""
    if not t or len(t.split(".")) != 3: print("Invalid JWT", file=sys.stderr); sys.exit(1)
    for name, part in [("Header",t.split(".")[0]),("Payload",t.split(".")[1])]:
        try:
            p = part + "="*(4-len(part)%4)
            print(f"{name}: {json.dumps(json.loads(base64.urlsafe_b64decode(p)),indent=2,ensure_ascii=False)}")
        except: print(f"{name}: (decode failed)")

def cmd_validate(*args):
    """Validate email format."""
    import re
    e = " ".join(args) if args else ""
    if not e: print("Enter email", file=sys.stderr); sys.exit(1)
    v = bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', e))
    print(f"{e} -> {'Valid' if v else 'Invalid'}")

# ---------------------------------------------------------------------------
# Format commands
# ---------------------------------------------------------------------------

def cmd_csv(filepath):
    """View CSV file."""
    import csv
    if not os.path.exists(filepath): print("Not found", file=sys.stderr); sys.exit(1)
    with open(filepath, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    print(f"{len(rows)} rows, {len(rows[0])} cols")
    for i, row in enumerate(rows[:20]):
        print(f"  {' | '.join(row[:6])}")
    if len(rows) > 20: print(f"  ... {len(rows)-20} more")

def cmd_xml(*args):
    """Format XML."""
    import xml.dom.minidom
    t = " ".join(args) if args else ""
    if not t: print("Enter XML", file=sys.stderr); sys.exit(1)
    try: print(xml.dom.minidom.parseString(t).toprettyxml(indent="  ")[:2000])
    except Exception as e: print(f"Bad XML: {e}", file=sys.stderr)

def cmd_rest(method, url, *args):
    """REST API client."""
    import requests as req, json
    body = " ".join(args) if args else None
    h = {"User-Agent":"Mozilla/5.0"}
    if body:
        try: body = json.loads(body); h["Content-Type"]="application/json"
        except: pass
    try:
        r = req.request(method.upper(), url, json=body if isinstance(body,dict) else None,
                       data=body if isinstance(body,str) else None, timeout=30, headers=h)
        print(f"{method.upper()} {url}\nStatus: {r.status_code}\n{r.text[:2000]}")
    except Exception as e: print(f"Failed: {e}", file=sys.stderr)

# ---------------------------------------------------------------------------
# System commands
# ---------------------------------------------------------------------------

def cmd_sysinfo():
    """Show system information."""
    import platform, socket
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Host: {socket.gethostname()} | Python {platform.python_version()} | CWD: {os.getcwd()}")

def cmd_env(*args):
    """Show env vars."""
    k = " ".join(args) if args else ""
    if k: print(f"{k}={os.environ.get(k,'(not set)')}")
    else:
        for k,v in sorted(os.environ.items()):
            if any(s in k.upper() for s in ["PATH","HOME","USER","SHELL","PROXY","KEY"]):
                print(f"  {k}={v[:60]}{'...' if len(v)>60 else ''}")

def cmd_which(*args):
    """Find a command."""
    import shutil
    c = " ".join(args) if args else ""
    if not c: print("Enter command", file=sys.stderr); sys.exit(1)
    p = shutil.which(c)
    print(f"{c} -> {p}" if p else f"{c}: not found")


# ---------------------------------------------------------------------------
# Finance commands
# ---------------------------------------------------------------------------

def cmd_stock(symbol):
    """Stock price (Yahoo Finance)."""
    try:
        import yfinance as yf
        s = yf.Ticker(symbol); info = s.info or {}
        p = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose","?")
        n = info.get("shortName") or info.get("longName") or symbol
        c = info.get("currency","USD")
        print(f"{n} ({symbol.upper()})\nPrice: {p} {c}")
    except ImportError: print("Install: pip install yfinance",file=sys.stderr); sys.exit(1)
    except Exception as e: print(f"Error: {e}",file=sys.stderr)

def cmd_market():
    """Major global market indices."""
    try:
        import yfinance as yf
        indices = {"S&P500":"^GSPC","NASDAQ":"^IXIC","Dow Jones":"^DJI",
                   "FTSE100":"^FTSE","Nikkei225":"^N225","Hang Seng":"^HSI",
                   "Shanghai":"000001.SS","Sensex":"^BSESN"}
        for name,sym in indices.items():
            try:
                s = yf.Ticker(sym).info or {}
                p = s.get("regularMarketPrice") or s.get("currentPrice") or "-"
                print(f"  {name:<12} {p}")
            except: print(f"  {name:<12} -")
    except ImportError: print("Install: pip install yfinance",file=sys.stderr); sys.exit(1)

def cmd_forex(fro="USD", to="CNY"):
    """Currency exchange rate."""
    import requests as req
    try:
        d = req.get(f"https://api.exchangerate-api.com/v4/latest/{fro.upper()}",timeout=15).json()
        print(f"1 {fro.upper()} = {d['rates'].get(to.upper(),'?')} {to.upper()}")
    except Exception as e: print(f"Error: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Knowledge commands
# ---------------------------------------------------------------------------

def cmd_define(word):
    """Dictionary definition."""
    import requests as req
    try:
        r = req.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}",timeout=15).json()
        if isinstance(r,list) and r:
            print(f"{r[0].get('word',word)}")
            for m in r[0].get("meanings",[])[:2]:
                for d in m.get("definitions",[])[:2]:
                    print(f"  [{m['partOfSpeech']}] {d['definition']}")
                    if d.get("example"): print(f"    eg: {d['example']}")
        else: print(f"No definition for '{word}'")
    except: print(f"No definition for '{word}'",file=sys.stderr)

def cmd_wiki(*args):
    """Wikipedia summary."""
    import requests as req, urllib.parse
    q = " ".join(args) if args else ""
    if not q: print("Enter topic",file=sys.stderr); sys.exit(1)
    try:
        d = req.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(q)}",timeout=15).json()
        if "extract" in d: print(f"{d['title']}\n{d['extract'][:1500]}")
        else: print(f"No article for '{q}'")
    except: print("Wikipedia failed",file=sys.stderr)

def cmd_quote():
    """Random quote."""
    import requests as req
    try:
        d = req.get("https://api.quotable.io/random",timeout=15).json()
        print(f'"{d.get("content","")}"  - {d.get("author","")}')
    except: print("Fetch failed",file=sys.stderr)

def cmd_fact():
    """Random fact."""
    import requests as req
    try:
        print(req.get("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en",timeout=15).json().get("text",""))
    except: print("Fetch failed",file=sys.stderr)

def cmd_synonym(word):
    """Find synonyms."""
    import requests as req
    try:
        w = req.get(f"https://api.datamuse.com/words?rel_syn={word}",timeout=15).json()
        if w: print(f"Synonyms: "+", ".join(x["word"] for x in w[:15]))
        else: print(f"No synonyms for '{word}'")
    except: print("Lookup failed",file=sys.stderr)

def cmd_anagram(*args):
    """Find anagrams."""
    import requests as req
    w = "".join(args).replace(" ","") if args else ""
    if not w: print("Enter word",file=sys.stderr); sys.exit(1)
    try:
        r = req.get(f"https://api.datamuse.com/words?rel_anag={w}",timeout=15).json()
        if r: print(f"Anagrams: "+", ".join(x["word"] for x in r[:20]))
        else: print("No anagrams")
    except: print("Lookup failed",file=sys.stderr)


# ---------------------------------------------------------------------------
# URL/Web detail commands
# ---------------------------------------------------------------------------

def cmd_urlparse(url):
    """Parse URL components."""
    from urllib.parse import urlparse
    p = urlparse(url); print(f"Scheme:{p.scheme}\nHost:{p.hostname}\nPath:{p.path or '/'}\nQuery:{p.query or 'none'}")

def cmd_params(url):
    """Extract query parameters."""
    from urllib.parse import urlparse, parse_qs
    qs = parse_qs(urlparse(url).query)
    if qs:
        for k,v in qs.items(): print(f"  {k} = {', '.join(v)}")
    else: print("No params")

def cmd_robots(url):
    """Fetch robots.txt."""
    import requests as req
    base = f"{urlparse.urlparse(url).scheme}://{urlparse.urlparse(url).hostname}"
    try:
        r = req.get(f"{base}/robots.txt",timeout=15,headers={"User-Agent":"Mozilla/5.0"})
        print(r.text[:1500] if r.status_code==200 else f"HTTP {r.status_code}")
    except Exception as e: print(f"Error: {e}",file=sys.stderr)

def cmd_keywords(url):
    """Extract meta tags."""
    import requests as req
    from bs4 import BeautifulSoup
    try:
        r = req.get(url,timeout=15,headers={"User-Agent":"Mozilla/5.0"})
        s = BeautifulSoup(r.text,"html.parser")
        for n in ["keywords","description","author"]:
            t = s.find("meta",attrs={"name":n})
            if t and t.get("content"): print(f"{n.title()}: {t['content'][:200]}")
        if s.title: print(f"Title: {s.title.string[:100]}")
    except: print("Failed",file=sys.stderr)

def cmd_encoding(url):
    """Check page encoding."""
    import requests as req
    try:
        r = req.get(url,timeout=15,headers={"User-Agent":"Mozilla/5.0"})
        print(f"Detected:{r.encoding}\nApparent:{r.apparent_encoding}")
    except: print("Failed",file=sys.stderr)

def cmd_validate(url):
    """Validate URL accessibility."""
    import requests as req
    try:
        r = req.head(url,timeout=10,headers={"User-Agent":"Mozilla/5.0"})
        print(f"Status:{r.status_code}\nType:{r.headers.get('Content-Type','').split(';')[0]}")
    except: print("Unreachable",file=sys.stderr)

def cmd_mime(url):
    """Check MIME type."""
    import requests as req
    try:
        r = req.head(url,timeout=10,headers={"User-Agent":"Mozilla/5.0"})
        for h in ["Content-Type","Content-Length","Last-Modified","Server"]:
            v = r.headers.get(h,"")
            if v: print(f"{h}: {v}")
    except: print("Failed",file=sys.stderr)

def cmd_social(url):
    """Find social links."""
    import requests as req
    from bs4 import BeautifulSoup
    try:
        r = req.get(url,timeout=15,headers={"User-Agent":"Mozilla/5.0"})
        domains = ["twitter","facebook","instagram","linkedin","youtube","github"]
        found = set()
        for a in BeautifulSoup(r.text,"html.parser").find_all("a",href=True):
            for d in domains:
                if f"{d}." in a["href"].lower(): found.add(d)
        print(f"Social: {', '.join(sorted(found)) if found else 'none'}")
    except: print("Failed",file=sys.stderr)

def cmd_lang(url):
    """Detect page language."""
    import requests as req
    from bs4 import BeautifulSoup
    try:
        r = req.get(url,timeout=15,headers={"User-Agent":"Mozilla/5.0"})
        s = BeautifulSoup(r.text,"html.parser")
        lang = s.find("html").get("lang","") if s.find("html") else ""
        print(f"HTML lang: {lang or 'unknown'}\nEncoding: {r.apparent_encoding}")
    except: print("Failed",file=sys.stderr)

def cmd_pingback(url):
    """Check pingback/XML-RPC."""
    import requests as req, re
    try:
        r = req.get(url,timeout=15,headers={"User-Agent":"Mozilla/5.0"})
        pb = re.search(r'pingback href="([^"]+)"',r.text,re.I)
        print(f"Pingback: {pb.group(1) if pb else 'none'}")
        base = f"{r.url.split('//')[0]}//{r.url.split('/')[2]}"
        for ep in ["/xmlrpc.php","/wp-json/"]:
            try:
                c = req.head(base+ep,timeout=5,headers={"User-Agent":"Mozilla/5.0"}).status_code
                if c < 500: print(f"  {ep} (HTTP {c})")
            except: pass
    except: print("Failed",file=sys.stderr)


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def print_usage():
    print(textwrap.dedent(f"""\
    Supernet - Web Content Extractor

    Usage:
      python supernet.py sub <url>          Extract video subtitles
      python supernet.py text <url>         Extract web page text
      python supernet.py audio <url>        Download audio (default MP3)
      python supernet.py video <url>        Download video (default MP4)
      python supernet.py info <url>         View video/page metadata
      python supernet.py list <url>         List available video formats
      python supernet.py thumbnail <url>    Download video thumbnail
      python supernet.py status <url>       Check website status
      python supernet.py headers <url>      View HTTP response headers
      python supernet.py links <url>        Extract page links
      python supernet.py images <url>       Extract page image links
      python supernet.py media <url>        Extract images/GIFs/video/animations
      python supernet.py tech <url>         Analyze web technology stack
      python supernet.py feed <url>         Extract RSS/Atom feed
      python supernet.py qr <text>          Generate QR code
      python supernet.py playlist <url>     List playlist entries
      python supernet.py convert <file> <fmt>  Convert local media file
      python supernet.py batch <file> <cmd> Batch process URLs from file
      python supernet.py dns <domain>       DNS lookup
      python supernet.py ip                 Show public IP address
      python supernet.py whois <domain>     Domain WHOIS lookup
      python supernet.py ssl <domain>       SSL certificate info
      python supernet.py port <host>        Scan common ports
      python supernet.py shorten <url>      Shorten URL (TinyURL)
      python supernet.py expand <url>       Expand shortened URL
      python supernet.py cookies <url>      View page cookies
      python supernet.py tables <url>       Extract HTML tables as CSV
      python supernet.py sitemap <url>      Extract sitemap URLs
      python supernet.py forms <url>        Extract form fields
      python supernet.py archive <url>      Wayback Machine snapshots
      python supernet.py wget <url>         Download page HTML

    Output: {OUTPUT_DIR}
    """))

CMDS = {
    "sub": cmd_sub, "text": cmd_text, "audio": cmd_audio, "video": cmd_video,
    "info": cmd_info, "list": cmd_list, "thumbnail": cmd_thumbnail,
    "status": cmd_status, "headers": cmd_headers,
    "links": cmd_links, "images": cmd_images, "media": cmd_media,
    "feed": cmd_feed, "tech": cmd_tech,
    "qr": cmd_qr, "playlist": cmd_playlist,
    "convert": cmd_convert, "batch": cmd_batch,
    "dns": cmd_dns, "ip": cmd_ip, "whois": cmd_whois,
    "ssl": cmd_ssl, "port": cmd_port,
    "shorten": cmd_shorten, "expand": cmd_expand, "cookies": cmd_cookies,
    "tables": cmd_tables, "sitemap": cmd_sitemap, "forms": cmd_forms,
    "archive": cmd_archive, "wget": cmd_wget,
    "csp": cmd_csp, "emails": cmd_emails, "hsts": cmd_hsts,
    "json": cmd_json, "http": cmd_http, "diff": cmd_diff,
    "hash": cmd_hash, "base64": cmd_base64, "uuid": cmd_uuid,
    "timestamp": cmd_timestamp, "favicon": cmd_favicon,
    "ping": cmd_ping, "speedtest": cmd_speedtest, "trace": cmd_trace,
    "checksum": cmd_checksum, "type": cmd_type,
    "calc": cmd_calc, "units": cmd_units, "color": cmd_color, "roman": cmd_roman,
    "count": cmd_count, "reverse": cmd_reverse, "sort": cmd_sort, "case": cmd_case,
    "url": cmd_url, "hex": cmd_hex, "html": cmd_html, "rot13": cmd_rot13,
    "geo": cmd_geo, "mylocation": cmd_mylocation,
    "rand": cmd_rand, "password": cmd_password, "token": cmd_token,
    "calendar": cmd_calendar, "countdown": cmd_countdown, "week": cmd_week,
    "translate": cmd_translate, "sentiment": cmd_sentiment, "detect": cmd_detect,
    "ask": cmd_ask, "summarize": cmd_summarize,
    "search": cmd_search, "crawl": cmd_crawl, "spider": cmd_spider,
    "btc": cmd_btc, "eth": cmd_eth, "weather": cmd_weather,
    "hn": cmd_hn, "news": cmd_news,
    "jwt": cmd_jwt, "validate": cmd_validate,
    "csv": cmd_csv, "xml": cmd_xml, "rest": cmd_rest,
    "sysinfo": cmd_sysinfo, "env": cmd_env, "which": cmd_which,
    "stock": cmd_stock, "market": cmd_market, "forex": cmd_forex,
    "define": cmd_define, "wiki": cmd_wiki, "quote": cmd_quote,
    "fact": cmd_fact, "synonym": cmd_synonym, "anagram": cmd_anagram,
    "urlparse": cmd_urlparse, "params": cmd_params, "robots": cmd_robots,
    "keywords": cmd_keywords, "encoding": cmd_encoding, "validate": cmd_validate,
    "mime": cmd_mime, "social": cmd_social, "lang": cmd_lang, "pingback": cmd_pingback,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print_usage()
        sys.exit(1 if len(sys.argv) < 2 else 0)
    if sys.argv[1] in ("--version", "-V"):
        print(f"supernet version {VERSION}")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd not in CMDS:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
    try:
        CMDS[cmd](*sys.argv[2:])
    except TypeError as e:
        print(f"Argument error: {e}", file=sys.stderr)
        sys.exit(1)
