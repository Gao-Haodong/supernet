"""Finance and market commands extracted from supernet.py.

# Copyright (c) 2026 Haodong Gao (高浩东), Xi'an, China. MIT License.

Commands: stock, market, forex, btc, eth, weather, hn, news
"""

import json
import os
import sys
import urllib.parse

from utils import _ensure_dep


def cmd_stock(symbol):
    """Stock price (Yahoo Finance)."""
    _ensure_dep("yfinance", "yfinance")
    import yfinance as yf
    try:
        s = yf.Ticker(symbol)
        info = s.info or {}
        p = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose", "?")
        n = info.get("shortName") or info.get("longName") or symbol
        c = info.get("currency", "USD")
        print(f"{n} ({symbol.upper()})\nPrice: {p} {c}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


def cmd_market():
    """Major global market indices."""
    _ensure_dep("yfinance", "yfinance")
    import yfinance as yf
    indices = {
        "S&P500": "^GSPC",
        "NASDAQ": "^IXIC",
        "Dow Jones": "^DJI",
        "FTSE100": "^FTSE",
        "Nikkei225": "^N225",
        "Hang Seng": "^HSI",
        "Shanghai": "000001.SS",
        "Sensex": "^BSESN",
    }
    for name, sym in indices.items():
        try:
            s = yf.Ticker(sym).info or {}
            p = s.get("regularMarketPrice") or s.get("currentPrice") or "-"
            print(f"  {name:<12} {p}")
        except Exception:
            print(f"  {name:<12} -")


def cmd_forex(fro="USD", to="CNY"):
    """Currency exchange rate."""
    import requests as req
    try:
        d = req.get(
            f"https://api.exchangerate-api.com/v4/latest/{fro.upper()}",
            timeout=15,
        ).json()
        print(f"1 {fro.upper()} = {d['rates'].get(to.upper(), '?')} {to.upper()}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


def cmd_btc():
    """Bitcoin price."""
    import requests as req
    try:
        d = req.get(
            "https://api.coindesk.com/v1/bpi/currentprice.json", timeout=15
        ).json()
        print(f"Bitcoin: ${d['bpi']['USD']['rate']}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


def cmd_eth():
    """Ethereum price."""
    import requests as req
    try:
        d = req.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
            timeout=15,
        ).json()
        print(f"Ethereum: ${d.get('ethereum', {}).get('usd', '?')}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


def cmd_weather(*args):
    """Weather for a city."""
    import requests as req
    city = " ".join(args) if args else "London"
    try:
        r = req.get(
            f"https://wttr.in/{urllib.parse.quote(city)}?format=%C+%t+%w&m",
            timeout=15,
        ).text.strip()
        print(f"{city.title()}: {r}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


def cmd_hn():
    """Hacker News top stories."""
    import requests as req
    try:
        ids = req.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15
        ).json()[:10]
        for i, sid in enumerate(ids, 1):
            item = req.get(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=15
            ).json()
            print(
                f"  {i}. {item.get('title', '?')}\n"
                f"     {item.get('url', f'https://news.ycombinator.com/item?id={sid}')}\n"
            )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


def cmd_news(*args):
    """Top news headlines."""
    import requests as req
    topic = " ".join(args) if args else "technology"
    try:
        d = req.get(
            f"https://gnews.io/api/v4/top-headlines?topic={topic}&lang=en&max=10&token=test",
            timeout=15,
        ).json()
        for a in d.get("articles", [])[:10]:
            print(f"  {a.get('title', '?')}\n     {a.get('url', '')}\n")
    except Exception:
        print(f"No news for '{topic}'", file=sys.stderr)


CMDS = {
    "stock": cmd_stock,
    "market": cmd_market,
    "forex": cmd_forex,
    "btc": cmd_btc,
    "eth": cmd_eth,
    "weather": cmd_weather,
    "hn": cmd_hn,
    "news": cmd_news,
}
