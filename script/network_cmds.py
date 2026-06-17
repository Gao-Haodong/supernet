"""Network commands extracted from supernet.py.

# Copyright (c) 2026 Haodong Gao (高浩东), Xi'an, China. MIT License.

Commands: dns, ip, whois, ssl, port, ping, trace, speedtest, geo, mylocation
"""

import os
import sys
import json
import socket
import ssl
import subprocess
import platform
import concurrent.futures
from datetime import datetime

from utils import _ensure_dep, OUTPUT_DIR


def cmd_dns(domain):
    """DNS lookup for a domain."""
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
    try:
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
    print(f"WHOIS -- {domain}")
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
    import certifi
    try:
        ctx = ssl.create_default_context(cafile=certifi.where())
        with socket.create_connection((domain, int(port)), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
    except Exception as e:
        print(f"SSL connection failed: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"SSL Certificate -- {domain}:{port}")
    print("-" * 50)
    print(f"  Subject:     {dict(x[0] for x in cert.get('subject', []))}")
    print(f"  Issuer:      {dict(x[0] for x in cert.get('issuer', []))}")
    print(f"  Serial:      {cert.get('serialNumber', '-')}")
    print(f"  Version:     {cert.get('version', '-')}")
    print(f"  Valid From:  {cert.get('notBefore', '-')}")
    print(f"  Valid Until: {cert.get('notAfter', '-')}")
    print(f"  SAN:         {', '.join(cert.get('subjectAltName', [('', '-')])[0][1:][0])}")
    print(f"  Algorithm:   {cert.get('signatureAlgorithm', '-')}")


def cmd_port(host, ports="21,22,23,25,53,80,110,143,443,445,993,995,1433,1521,3306,3389,5432,6379,8080,8443"):
    """Scan common ports on a host."""
    port_list = [int(p.strip()) for p in ports.split(",") if p.strip().isdigit()]
    open_ports = []

    def _scan(p):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            r = s.connect_ex((host, p))
            s.close()
            return p if r == 0 else None
        except Exception:
            return None

    print(f"Scanning {host} ({len(port_list)} ports)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        for result in ex.map(_scan, port_list):
            if result:
                open_ports.append(result)
    if open_ports:
        print(f"\nOpen ports ({len(open_ports)}):")
        for p in sorted(open_ports):
            svc = {21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS", 80: "HTTP",
                   110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB", 993: "IMAPS",
                   995: "POP3S", 1433: "MSSQL", 3306: "MySQL", 3389: "RDP",
                   5432: "PostgreSQL", 6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt"}.get(p, "")
            print(f"  {p:<5} {svc}")
    else:
        print("No open ports found")


def cmd_ping(host):
    """Ping a host."""
    param = "-n" if platform.system().lower() == "windows" else "-c"
    try:
        r = subprocess.run(["ping", param, "4", host], capture_output=True, text=True, timeout=30)
        print(r.stdout[-500:] if r.stdout else r.stderr[-500:])
    except FileNotFoundError:
        print("ping command not available on this system", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Ping timed out", file=sys.stderr)
        sys.exit(1)


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
        print("Install speedtest-cli: pip install speedtest-cli", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Speedtest failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_trace(host):
    """Traceroute to a host."""
    cmd = "tracert" if platform.system().lower() == "windows" else "traceroute"
    try:
        r = subprocess.run([cmd, host], capture_output=True, text=True, timeout=60)
        output = r.stdout or r.stderr
        print(output[:2000])
        if len(output) > 2000:
            print(f"... ({len(output)-2000} more chars)")
    except FileNotFoundError:
        print(f"{cmd} not available on this system", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Traceroute timed out", file=sys.stderr)
        sys.exit(1)


def cmd_geo(ip_addr=""):
    """IP geolocation lookup."""
    import requests as req
    url = f"https://ipapi.co/{ip_addr}/json/" if ip_addr else "https://ipapi.co/json/"
    try:
        d = req.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"}).json()
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)
    if d.get("error"):
        print(f"Error: {d.get('reason', '?')}", file=sys.stderr)
        sys.exit(1)
    print(f"IP: {d.get('ip', '-')}  City: {d.get('city', '-')}  Country: {d.get('country_name', '-')}")
    print(f"ISP: {d.get('org', '-')}  Lat/Lon: {d.get('latitude', '-')},{d.get('longitude', '-')}")


def cmd_mylocation():
    """Show current IP location."""
    cmd_geo()


CMDS = {
    "dns": cmd_dns,
    "ip": cmd_ip,
    "whois": cmd_whois,
    "ssl": cmd_ssl,
    "port": cmd_port,
    "ping": cmd_ping,
    "trace": cmd_trace,
    "speedtest": cmd_speedtest,
    "geo": cmd_geo,
    "mylocation": cmd_mylocation,
}
