#!/usr/bin/env python3
# Copyright (c) 2026 Haodong Gao (高浩东), Xi'an, China. MIT License.
"""Supernet - CLI entry point.

Usage:
  python main.py <command> <args>
  python main.py --help
  python main.py --version
"""
import sys, os, textwrap

# Import utils (loads .env, sets up output dir)
from utils import VERSION, OUTPUT_DIR

# Import all command modules
from core_cmds import CMDS as CORE_CMDS
from web_cmds import CMDS as WEB_CMDS
from tools_cmds import CMDS as TOOLS_CMDS

# Optional modules (gracefully skip if not installed)
_optional_modules = []

try:
    from network_cmds import CMDS as NET_CMDS
    _optional_modules.append(("network_cmds", NET_CMDS))
except ImportError:
    pass

try:
    from finance_cmds import CMDS as FIN_CMDS
    _optional_modules.append(("finance_cmds", FIN_CMDS))
except ImportError:
    pass

try:
    from ai_cmds import CMDS as AI_CMDS
    _optional_modules.append(("ai_cmds", AI_CMDS))
except ImportError:
    pass

# Merge all CMDS dicts
CMDS = {}
CMDS.update(CORE_CMDS)
CMDS.update(WEB_CMDS)
CMDS.update(TOOLS_CMDS)
for name, mod_cmds in _optional_modules:
    CMDS.update(mod_cmds)


def print_usage():
    print(textwrap.dedent(f"""\
    Supernet - Web Content Extractor v{VERSION}

    Usage:
      python main.py <command> <args>

    Core commands:
      sub, text, audio, video, info, list, thumbnail
      convert, playlist, batch

    Web analysis:
      status, headers, links, images, media, tech, feed
      csp, keywords, encoding, lang, social, pingback
      robots, mime, validate, cookies, qr
      tables, sitemap, forms, archive, wget, crawl, spider

    Network & Finance:
      dns, ip, whois, ssl, port, ping, trace, speedtest
      stock, market, forex, btc, eth, weather, hn, news

    AI & Knowledge:
      ask, summarize, translate, sentiment, detect, search
      define, wiki, quote, fact, synonym, anagram

    Utilities:
      calc, units, color, roman, hash, base64, uuid, timestamp
      urlparse, params, shorten, expand
      sysinfo, env, which, geo, mylocation
      rand, password, token, calendar, countdown, week
      jwt, validate, csv, xml, rest
      count, reverse, sort, case, url, hex, html, rot13

    Output: {OUTPUT_DIR}
    Options:
      --version, -V    Show version
      --help, -h       Show this help

    Full docs: https://github.com/Gao-Haodong/supernet
    """))


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print_usage()
        sys.exit(1 if len(sys.argv) < 2 else 0)

    if sys.argv[1] in ("--version", "-V"):
        print(f"Supernet v{VERSION}")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd not in CMDS:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(f"Run 'python main.py --help' for available commands", file=sys.stderr)
        sys.exit(1)

    try:
        CMDS[cmd](*sys.argv[2:])
    except TypeError as e:
        print(f"Argument error: {e}", file=sys.stderr)
        sys.exit(1)
