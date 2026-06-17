#!/usr/bin/env python3
# Copyright (c) 2026 Haodong Gao (高浩东), Xi'an, China. MIT License.
"""Tool commands extracted from supernet.py — math, text, codec, crypto, geo, system, data, knowledge, web."""

import os
import sys
import re
import json
import time
import hashlib
import base64
import urllib.parse
from datetime import datetime

from utils import OUTPUT_DIR, _save_text, _ensure_dep, _fmt_size, _get_ffmpeg


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


# ---------------------------------------------------------------------------
# Data commands
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


def cmd_validate_email(*args):
    """Validate email format."""
    import re
    e = " ".join(args) if args else ""
    if not e: print("Enter email", file=sys.stderr); sys.exit(1)
    v = bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', e))
    print(f"{e} -> {'Valid' if v else 'Invalid'}")


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
# Command registry
# ---------------------------------------------------------------------------

CMDS = {
    "calc": cmd_calc,
    "units": cmd_units,
    "color": cmd_color,
    "roman": cmd_roman,
    "count": cmd_count,
    "reverse": cmd_reverse,
    "sort": cmd_sort,
    "case": cmd_case,
    "url": cmd_url,
    "hex": cmd_hex,
    "html": cmd_html,
    "rot13": cmd_rot13,
    "hash": cmd_hash,
    "base64": cmd_base64,
    "uuid": cmd_uuid,
    "timestamp": cmd_timestamp,
    "csv": cmd_csv,
    "xml": cmd_xml,
    "rest": cmd_rest,
    "define": cmd_define,
    "wiki": cmd_wiki,
    "quote": cmd_quote,
    "fact": cmd_fact,
    "synonym": cmd_synonym,
    "anagram": cmd_anagram,
    "jwt": cmd_jwt,
    "validate": cmd_validate_email,
    "rand": cmd_rand,
    "password": cmd_password,
    "token": cmd_token,
    "calendar": cmd_calendar,
    "countdown": cmd_countdown,
    "week": cmd_week,
    "sysinfo": cmd_sysinfo,
    "env": cmd_env,
    "which": cmd_which,
    "urlparse": cmd_urlparse,
    "params": cmd_params,
    "shorten": cmd_shorten,
    "expand": cmd_expand,
    "geo": cmd_geo,
    "mylocation": cmd_mylocation,
}
