"""AI and search commands extracted from supernet.py.

# Copyright (c) 2026 Haodong Gao (高浩东), Xi'an, China. MIT License.

Commands: translate, sentiment, detect, ask, summarize, search
"""

import json
import os
import sys
import urllib.parse

from utils import _ensure_dep


def cmd_translate(*args):
    """Translate text (free API, no key). Usage: translate hello es"""
    if len(args) < 2:
        print("Usage: translate <text> <lang>", file=sys.stderr); sys.exit(1)
    target = args[-1]; text = " ".join(args[:-1])
    import requests as req
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


CMDS = {
    "translate": cmd_translate,
    "sentiment": cmd_sentiment,
    "detect": cmd_detect,
    "ask": cmd_ask,
    "summarize": cmd_summarize,
    "search": cmd_search,
}
