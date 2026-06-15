#!/usr/bin/env python3
"""Supernet - Extract subtitles, text, and media files from videos and web pages.

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
"""
import sys, os, json, re, time, tempfile, shutil, subprocess, textwrap, urllib.parse
from datetime import datetime

VERSION = "1.3.1"

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
