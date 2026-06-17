#!/usr/bin/env python3
# Copyright (c) 2026 Haodong Gao (高浩东), Xi'an, China. MIT License.
"""Shared utility functions extracted from supernet.py."""

import os
import sys
import shutil
import time

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
