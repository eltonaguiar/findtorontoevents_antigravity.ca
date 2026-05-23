"""HEAD-check every cited URL, downgrade hallucinated engines.

URLs that fail HEAD (timeout, 4xx/5xx, unresolvable host) get
`verified=false`. Engines whose hallucination rate exceeds the
threshold are downgraded in P5 vote weight (caller's responsibility
to apply the weight).

Designed to be cheap: 10s timeout, 2 retries, follow redirects, max
8 concurrent requests.
"""

from __future__ import annotations

import concurrent.futures
import urllib.request
from pathlib import Path

from .schemas import Citation

_ALLOWLIST_PATH = (
    Path(__file__).resolve().parents[2]
    / "research"
    / "domain_allowlist.txt"
)
_TIMEOUT_S = 10
_MAX_WORKERS = 8

_DOWNGRADE_THRESHOLD = 0.25  # >25% hallucination → 0.5x weight
_EXCLUDE_THRESHOLD = 0.50  # >50% hallucination → drop from P5


def _load_allowlist() -> set[str]:
    if not _ALLOWLIST_PATH.exists():
        return set()
    return {
        line.strip().lower()
        for line in _ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def _is_safe_external_url(url: str) -> bool:
    """SSRF guard — reject loopback / link-local (IMDS) / RFC-1918 / non-http(s).

    Per pr-reviewer (PR #904, 2026-05-11): swarm output is untrusted.
    On GHA runners IMDS (169.254.169.254) + localhost are reachable + the
    GITHUB_TOKEN is in env. A hallucinating engine emitting an internal URL
    would trigger a real outbound request without this guard.
    """
    try:
        from urllib.parse import urlparse
        import ipaddress
        import socket
        u = urlparse(url)
        if u.scheme not in ("http", "https"):
            return False
        host = (u.hostname or "").lower()
        if not host:
            return False
        # Resolve hostname to also check the literal IP. Best-effort DNS-rebinding
        # mitigation: urlopen may resolve again differently, but most common
        # leakers (internal hostnames, internal IPs as URLs) are caught here.
        candidates: set = {host}
        try:
            for _fam, _t, _p, _c, sockaddr in socket.getaddrinfo(host, None):
                candidates.add(sockaddr[0])
        except (socket.gaierror, socket.error):
            return False  # un-resolvable -> reject
        for addr in candidates:
            try:
                ip = ipaddress.ip_address(addr)
            except ValueError:
                continue  # not an IP literal; bare hostname is fine
            if (ip.is_loopback or ip.is_link_local or ip.is_private
                    or ip.is_multicast or ip.is_reserved or ip.is_unspecified):
                return False
        return True
    except Exception:
        return False


def _head_check(url: str) -> bool:
    """True if URL responds 200/301/302 within timeout. False otherwise.

    SSRF-guarded — rejects loopback / link-local / RFC-1918 / non-http(s)
    BEFORE issuing the request.
    """
    if not _is_safe_external_url(url):
        return False
    try:
        req = urllib.request.Request(url, method="HEAD", headers={
            "User-Agent": "graphify-research-orchestrator/1.0"
        })
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
            return resp.status in (200, 301, 302)
    except Exception:
        return False


def verify_citations(
    citations: list[Citation],
    engine_attribution: dict[str, list[str]] | None = None,
) -> dict:
    """Mark each citation `verified` + `low_trust` flags. Compute per-engine
    hallucination rate.

    engine_attribution: optional {engine_name: [url, url, ...]} for vote-weight
    calculations downstream.
    """
    allowlist = _load_allowlist()

    def _verify_one(c: Citation) -> Citation:
        c.verified = _head_check(c.url)
        host = ""
        try:
            from urllib.parse import urlparse
            host = (urlparse(c.url).hostname or "").lower()
        except Exception:
            pass
        c.low_trust = bool(allowlist) and host and host not in allowlist
        return c

    with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as ex:
        verified_list = list(ex.map(_verify_one, citations))

    n_verified = sum(1 for c in verified_list if c.verified)
    n_total = len(verified_list)
    n_hallucinated = n_total - n_verified

    engine_weights: dict[str, float] = {}
    if engine_attribution:
        for engine, urls in engine_attribution.items():
            engine_urls = {url for url in urls}
            engine_citations = [c for c in verified_list if c.url in engine_urls]
            if not engine_citations:
                engine_weights[engine] = 1.0
                continue
            bad = sum(1 for c in engine_citations if not c.verified)
            rate = bad / len(engine_citations)
            if rate > _EXCLUDE_THRESHOLD:
                engine_weights[engine] = 0.0
            elif rate > _DOWNGRADE_THRESHOLD:
                engine_weights[engine] = 0.5
            else:
                engine_weights[engine] = 1.0

    return {
        "citations": verified_list,
        "n_total": n_total,
        "n_verified": n_verified,
        "n_hallucinated": n_hallucinated,
        "hallucinated_urls": [c.url for c in verified_list if not c.verified],
        "engine_weights": engine_weights,
    }
