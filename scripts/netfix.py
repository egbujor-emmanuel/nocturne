"""DNS fallback for networks whose resolver will not answer for Bitget.

The build machine sits behind a phone hotspot (192.168.43.1) whose DNS returns
nothing for api.bitget.com, and which also blocks the usual DNS-over-HTTPS
endpoints. The hosts are reachable - only the name lookup fails - so once we
have an address the connection succeeds normally.

Strategy, cheapest first:
  1. normal getaddrinfo
  2. addresses cached from a previous successful lookup
  3. DNS-over-HTTPS, if any resolver is reachable
  4. pinned last-known-good addresses

Whatever wins, we patch socket.getaddrinfo for that host only. Patching at the
resolver layer (rather than connecting to an IP directly) keeps the hostname in
both SNI and the Host header, so TLS and routing behave exactly as normal.

Import this before any module that talks to Bitget. It is a no-op on a healthy
network.
"""
import json
import os
import socket
import ssl
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "dns_cache.json")

HOSTS = ("api.bitget.com", "hackathon.bitgetops.com")

# Last-known-good, verified working from this machine by connecting directly
# with SNI. Cloudflare anycast; refreshed automatically whenever a real lookup
# succeeds, so these only matter when every resolver is unavailable.
PINNED = {
    "api.bitget.com": ["104.18.14.166", "104.18.15.166"],
}

DOH = (
    "https://1.1.1.1/dns-query?name={name}&type=A",
    "https://dns.google/resolve?name={name}&type=A",
    "https://cloudflare-dns.com/dns-query?name={name}&type=A",
)

_patched = {}
_orig_getaddrinfo = socket.getaddrinfo


def _load_cache():
    try:
        return json.load(open(CACHE))
    except Exception:
        return {}


def _save_cache(c):
    try:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        json.dump(c, open(CACHE, "w"), indent=1)
    except Exception:
        pass


def _resolves(host, timeout=5):
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        return [ai[4][0] for ai in _orig_getaddrinfo(host, 443, socket.AF_INET,
                                                     socket.SOCK_STREAM)]
    except Exception:
        return []
    finally:
        socket.setdefaulttimeout(old)


def _doh(host, timeout=8):
    ctx = ssl.create_default_context()
    for tpl in DOH:
        try:
            req = urllib.request.Request(
                tpl.format(name=host),
                headers={"accept": "application/dns-json", "User-Agent": "nocturne"})
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                d = json.load(r)
            ips = [a["data"] for a in d.get("Answer", []) if a.get("type") == 1]
            if ips:
                return ips
        except Exception:
            continue
    return []


def _install(host, ips):
    _patched[host] = ips

    def patched(h, port, family=0, type=0, proto=0, flags=0):
        if h in _patched:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))
                    for ip in _patched[h]]
        return _orig_getaddrinfo(h, port, family, type, proto, flags)

    socket.getaddrinfo = patched


def ensure(hosts=HOSTS, verbose=False):
    """Make sure each host resolves; returns {host: (source, ips)}."""
    cache = _load_cache()
    out = {}
    for host in hosts:
        ips = _resolves(host)
        if ips:
            cache[host] = ips
            out[host] = ("system", ips)
            continue
        ips = cache.get(host) or []
        src = "cache"
        if not ips:
            ips = _doh(host)
            src = "doh"
        if not ips:
            ips = PINNED.get(host, [])
            src = "pinned"
        if ips:
            _install(host, ips)
            out[host] = (src, ips)
        else:
            out[host] = ("unresolved", [])
    _save_cache(cache)
    if verbose:
        for h, (src, ips) in out.items():
            print("  %-28s %-10s %s" % (h, src, ", ".join(ips) or "NONE"))
    return out


# apply on import - a no-op when the network is healthy
ensure()

if __name__ == "__main__":
    print("DNS state:")
    res = ensure(verbose=True)
    print("\nconnectivity:")
    for h in HOSTS:
        url = ("https://api.bitget.com/api/v2/public/time"
               if h == "api.bitget.com" else "https://hackathon.bitgetops.com/v1/models")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "nocturne"})
            with urllib.request.urlopen(req, timeout=15) as r:
                print("  %-28s HTTP %s" % (h, r.status))
        except Exception as e:
            code = getattr(e, "code", None)
            print("  %-28s %s" % (h, ("HTTP %s" % code) if code else
                                  "%s: %s" % (type(e).__name__, str(e)[:60])))
