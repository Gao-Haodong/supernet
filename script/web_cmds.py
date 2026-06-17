#!/usr/bin/env python3
"""Web/URL analysis commands extracted from supernet.py.

# Copyright (c) 2026 Haodong Gao (高浩东), Xi'an, China. MIT License.

Commands: status, headers, links, images, media, tech, feed, csp,
          keywords, encoding, lang, social, pingback, robots, mime,
          validate, tables, sitemap, forms, archive, wget, crawl,
          spider, cookies, qr
"""

import os
import sys
import re
import time
import json
import urllib.parse
from datetime import datetime

from utils import OUTPUT_DIR, _save_text, _fmt_size, _ensure_dep


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
    print(f"Technology Analysis -- {resp.url}")
    print("-" * 50)
    for item in result:
        if item not in seen:
            seen.add(item)
            print(f"  {item}")
    print(f"\n{len(seen)} technologies detected")


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


def cmd_keywords(url):
    """Extract meta tags."""
    import requests as req
    from bs4 import BeautifulSoup
    try:
        r = req.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        s = BeautifulSoup(r.text, "html.parser")
        for n in ["keywords", "description", "author"]:
            t = s.find("meta", attrs={"name": n})
            if t and t.get("content"):
                print(f"{n.title()}: {t['content'][:200]}")
        if s.title:
            print(f"Title: {s.title.string[:100]}")
    except Exception:
        print("Failed", file=sys.stderr)


def cmd_encoding(url):
    """Check page encoding."""
    import requests as req
    try:
        r = req.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        print(f"Detected:{r.encoding}\nApparent:{r.apparent_encoding}")
    except Exception:
        print("Failed", file=sys.stderr)


def cmd_lang(url):
    """Detect page language."""
    import requests as req
    from bs4 import BeautifulSoup
    try:
        r = req.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        s = BeautifulSoup(r.text, "html.parser")
        lang = s.find("html").get("lang", "") if s.find("html") else ""
        print(f"HTML lang: {lang or 'unknown'}\nEncoding: {r.apparent_encoding}")
    except Exception:
        print("Failed", file=sys.stderr)


def cmd_social(url):
    """Find social links."""
    import requests as req
    from bs4 import BeautifulSoup
    try:
        r = req.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        domains = ["twitter", "facebook", "instagram", "linkedin", "youtube", "github"]
        found = set()
        for a in BeautifulSoup(r.text, "html.parser").find_all("a", href=True):
            for d in domains:
                if f"{d}." in a["href"].lower():
                    found.add(d)
        print(f"Social: {', '.join(sorted(found)) if found else 'none'}")
    except Exception:
        print("Failed", file=sys.stderr)


def cmd_pingback(url):
    """Check pingback/XML-RPC."""
    import requests as req, re
    try:
        r = req.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        pb = re.search(r'pingback href="([^"]+)"', r.text, re.I)
        print(f"Pingback: {pb.group(1) if pb else 'none'}")
        base = f"{r.url.split('//')[0]}//{r.url.split('/')[2]}"
        for ep in ["/xmlrpc.php", "/wp-json/"]:
            try:
                c = req.head(base+ep, timeout=5, headers={"User-Agent": "Mozilla/5.0"}).status_code
                if c < 500:
                    print(f"  {ep} (HTTP {c})")
            except Exception:
                pass
    except Exception:
        print("Failed", file=sys.stderr)


def cmd_robots(url):
    """Fetch robots.txt."""
    import requests as req
    base = f"{urllib.parse.urlparse(url).scheme}://{urllib.parse.urlparse(url).hostname}"
    try:
        r = req.get(f"{base}/robots.txt", timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        print(r.text[:1500] if r.status_code == 200 else f"HTTP {r.status_code}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


def cmd_mime(url):
    """Check MIME type."""
    import requests as req
    try:
        r = req.head(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        for h in ["Content-Type", "Content-Length", "Last-Modified", "Server"]:
            v = r.headers.get(h, "")
            if v:
                print(f"{h}: {v}")
    except Exception:
        print("Failed", file=sys.stderr)


def cmd_validate(url):
    """Validate URL accessibility."""
    import requests as req
    try:
        r = req.head(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        print(f"Status:{r.status_code}\nType:{r.headers.get('Content-Type', '').split(';')[0]}")
    except Exception:
        print("Unreachable", file=sys.stderr)


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
    print(f"Wayback Machine -- {url}")
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


def cmd_crawl(url, max_pages=10):
    """Crawl a website up to N pages."""
    import requests as req
    from bs4 import BeautifulSoup
    import trafilatura
    visited, to_visit, base = set(), [url], urllib.parse.urlparse(url).netloc
    pages = []
    while to_visit and len(visited) < int(max_pages):
        cur = to_visit.pop(0)
        if cur in visited:
            continue
        visited.add(cur)
        try:
            r = req.get(cur, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                continue
            t = trafilatura.extract(r.text)
            if t:
                pages.append(t[:500])
                print(f"  [{len(visited)}] {cur[:70]}")
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                h = urllib.parse.urljoin(cur, a["href"])
                if urllib.parse.urlparse(h).netloc == base and h not in visited:
                    to_visit.append(h)
        except Exception:
            pass
    print(f"\nCrawled {len(pages)} pages")
    if pages:
        _save_text("\n\n".join(pages), "crawl_output.txt")


def cmd_spider(url):
    """Map all internal links of a site."""
    import requests as req
    from bs4 import BeautifulSoup
    try:
        resp = req.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print(f"Failed:{e}", file=sys.stderr)
        sys.exit(1)
    soup = BeautifulSoup(resp.text, "html.parser")
    base, domain = resp.url, urllib.parse.urlparse(resp.url).netloc
    links = sorted({urllib.parse.urljoin(base, a["href"]) for a in soup.find_all("a", href=True)
                    if urllib.parse.urlparse(urllib.parse.urljoin(base, a["href"])).netloc == domain})
    print(f"{len(links)} internal links")
    for l in links:
        print(f"  {l}")
    if links:
        _save_text("\n".join(links), "spider_links.txt")


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


CMDS = {
    "status": cmd_status,
    "headers": cmd_headers,
    "links": cmd_links,
    "images": cmd_images,
    "media": cmd_media,
    "tech": cmd_tech,
    "feed": cmd_feed,
    "csp": cmd_csp,
    "keywords": cmd_keywords,
    "encoding": cmd_encoding,
    "lang": cmd_lang,
    "social": cmd_social,
    "pingback": cmd_pingback,
    "robots": cmd_robots,
    "mime": cmd_mime,
    "validate": cmd_validate,
    "tables": cmd_tables,
    "sitemap": cmd_sitemap,
    "forms": cmd_forms,
    "archive": cmd_archive,
    "wget": cmd_wget,
    "crawl": cmd_crawl,
    "spider": cmd_spider,
    "cookies": cmd_cookies,
    "qr": cmd_qr,
}
