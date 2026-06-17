#!/usr/bin/env python3
# Copyright (c) 2026 Haodong Gao (高浩东), Xi'an, China. MIT License.
"""Proxy pool — auto discovery, health check, rotation。

Usage:
 from proxy_pool import ProxyPool
 pool = ProxyPool()
 proxy = pool.get() # Getmore availableproxy
 pool.mark_bad(proxy) # Mark proxy as bad (cooldown)
"""

import os, sys, time, threading, urllib.request
from datetime import datetime, timedelta

# Auto .env file
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
 with open(_env_path, "r", encoding="utf-8", errors="ignore") as f:
 for line in f:
 line = line.strip()
 if line and not line.startswith("#") and "=" in line:
 k, v = line.split("=", 1)
 os.environ.setdefault(k.strip(), v.strip())

# Cooldown in seconds after marking bad
COOLDOWN_SECONDS = 60
# Health check timeout
CHECK_TIMEOUT = 5
# Check target URL
CHECK_URL = "https://www.example.com"
CHECK_URL_ALT = "https://www.example.com"


class ProxyPool:
 """Thread-safe proxy pool with discovery, health check, rotation。"""

 def __init__(self):
 self._lock = threading.Lock()
 self._proxies: list[str] = [] # All known proxies
 self._index = 0 # Current round-robin index
 self._bad_until: dict[str, float] = {} # proxy -> unblock timestamp

 self._discover()

 # ─── Discovery ─────────────────────────────────────

 def _discover(self):
 """FrommoresourcesDiscovery availableproxy（config，Auto）。"""
 sources = []

 # 1. PROXY_POOL env var (comma-separated, highest)
 env_pool = os.environ.get("PROXY_POOL", "")
 if env_pool:
 sources.extend([p.strip() for p in env_pool.split(",") if p.strip()])

 # 2. HTTP_PROXY / HTTPS_PROXY env vars
 for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
 val = os.environ.get(key, "").strip()
 if val and val not in sources:
 sources.append(val)

 # 3. PROXY_POOL in .env file
 _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
 if os.path.exists(_env_path):
 with open(_env_path, "r", encoding="utf-8", errors="ignore") as f:
 for line in f:
 line = line.strip()
 if line.startswith("PROXY_POOL="):
 vals = line.split("=", 1)[1].strip()
 for p in vals.split(","):
 p = p.strip()
 if p and p not in sources:
 sources.append(p)

 # Deduplicate and filter
 seen = set()
 for p in sources:
 if p in seen: continue
 seen.add(p)
 if p.startswith(("http://", "socks")):
 self._proxies.append(p)

 # Background health check
 if self._proxies:
 self._check_all_async()

 # ─── Health Check ─────────────────────────────────

 def _check_one(self, proxy: str) -> bool:
 """testmoreproxy if available。"""
 for url in (CHECK_URL, CHECK_URL_ALT):
 try:
 req = urllib.request.Request(url, method="HEAD")
 req.add_header("User-Agent", "Mozilla/5.0")
 handler = urllib.request.ProxyHandler({
 "http": proxy, "https": proxy
 })
 opener = urllib.request.build_opener(handler)
 opener.open(req, timeout=CHECK_TIMEOUT)
 return True
 except Exception:
 continue
 return False

 def _check_all_async(self):
 """Check all proxies async。"""
 def _run():
 for p in self._proxies[:]:
 ok = self._check_one(p)
 if not ok:
 with self._lock:
 self._bad_until[p] = time.time() + COOLDOWN_SECONDS
 threading.Thread(target=_run, daemon=True).start()

 def check_now(self, proxy: str) -> bool:
 """Test proxy synchronously。"""
 ok = self._check_one(proxy)
 with self._lock:
 if ok:
 self._bad_until.pop(proxy, None)
 else:
 self._bad_until[proxy] = time.time() + COOLDOWN_SECONDS
 return ok

 # ─── Get ─────────────────────────────────────

 def get(self, quick_check: bool = True) -> str | None:
 """ round-robinReturnmore availableproxy。

 Args:
 quick_check: ifforcandidatedoquickconnectivitytest（avoidReturndeadproxy）
 """
 with self._lock:
 now = time.time()
 # Clean expired cooldowns
 expired = [p for p, t in self._bad_until.items() if t <= now]
 for p in expired:
 del self._bad_until[p]

 if not self._proxies:
 return None

 # Round-robin from current position
 for _ in range(len(self._proxies)):
 self._index = (self._index + 1) % len(self._proxies)
 candidate = self._proxies[self._index]
 if candidate in self._bad_until:
 continue
 if quick_check:
 # Quick port test
 if not self._quick_test(candidate):
 self._bad_until[candidate] = now + COOLDOWN_SECONDS
 continue
 return candidate

 # proxy，timeshortestmore
 best = min(self._bad_until.items(), key=lambda x: x[1])
 wait = max(0, best[1] - now)
 if wait <= 5:
 return best[0]
 return None

 @staticmethod
 def _quick_test(proxy: str) -> bool:
 """Quick port test (no HTTP)。"""
 try:
 from urllib.parse import urlparse
 parsed = urlparse(proxy)
 host = parsed.hostname or "127.0.0.1"
 port = parsed.port or 80
 import socket
 s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
 s.settimeout(2)
 s.connect((host, port))
 s.close()
 return True
 except Exception:
 return False

 def get_all(self) -> list[str]:
 """ReturnAll known proxies。"""
 with self._lock:
 return list(self._proxies)

 def mark_bad(self, proxy: str, cooldown: int = COOLDOWN_SECONDS):
 """Mark bad with cooldown。"""
 with self._lock:
 self._bad_until[proxy] = time.time() + cooldown

 def add(self, proxy: str):
 """Manuallyaddmoreproxy。"""
 with self._lock:
 if proxy not in self._proxies:
 self._proxies.append(proxy)

 def status(self) -> dict:
 """Return pool status。"""
 with self._lock:
 now = time.time()
 total = len(self._proxies)
 bad = len(self._bad_until)
 cooling = {p: max(0, t - now) for p, t in self._bad_until.items()}
 return {
 "total": total,
 "available": total - bad,
 "cooldown": bad,
 "list": list(self._proxies),
 "bad": cooling,
 }


# Global singleton
_pool = None


def get_pool() -> ProxyPool:
 """Getglobalproxysingleton。"""
 global _pool
 if _pool is None:
 _pool = ProxyPool()
 return _pool


def get_proxy() -> str | None:
 """Shorthand：Getmore availableproxy。"""
 return get_pool().get()
