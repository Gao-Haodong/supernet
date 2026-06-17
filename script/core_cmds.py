#!/usr/bin/env python3
"""Core commands for the Supernet CLI tool."""

# Copyright (c) 2026 Haodong Gao (高浩东), Xi'an, China. MIT License.

import os, sys, re, tempfile, subprocess, shutil
from utils import OUTPUT_DIR, _get_ffmpeg, _get_proxy, _base_opts, _save_text, _try_ydl, _fmt_size, _ts, _ensure_dep

# ---------------------------------------------------------------------------
# Core commands (extracted from supernet.py)
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


# ---------------------------------------------------------------------------
# Command registry
# ---------------------------------------------------------------------------

CMDS = {
    "sub": cmd_sub, "text": cmd_text, "audio": cmd_audio, "video": cmd_video,
    "info": cmd_info, "list": cmd_list, "thumbnail": cmd_thumbnail,
    "convert": cmd_convert, "playlist": cmd_playlist, "batch": cmd_batch,
}
