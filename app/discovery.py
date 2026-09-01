from __future__ import annotations

import json
import os
import re
import tempfile
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from .models import mask_url, sha256_text, snapshot_path
from .signals import detect_signals
from .verifier import verify

USER_AGENT = "RaaSFinder/0.1 (+https://github.com/rath0darya/RaaSFinder)"
TIMEOUT = 12
MAX_SEARCH_RESULTS = 8
MAX_PAGE_FETCHES = 18
MAX_TEXT_CHARS = 80_000

SEARCH_QUERIES = {
    "clearweb": (
        '"ransomware as a service" affiliate',
        '"ransomware" "affiliate program"',
        '"ransomware" "victim" "leak site"',
    ),
    "forums": (
        'site:reddit.com ransomware affiliate',
        '"ransomware" "affiliate" forum',
        '"ransomware" "victim" forum',
    ),
    "onion_index": (
        "ransomware affiliate",
        "ransomware leak",
        "ransomware service",
    ),
}


@dataclass(frozen=True)
class Candidate:
    url: str
    channel: str
    source_name: str
    source_url: str
    query: str


@dataclass(frozen=True)
class Result:
    url: str
    channel: str
    source_name: str
    source_url: str
    title: str
    status: str
    confidence: str
    score: int
    signals: tuple[str, ...]
    observed_at: str
    content_hash: str
    masked_url: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    proxy = os.environ.get("TOR_PROXY", "").strip()
    if proxy:
        session.proxies.update({"http": proxy, "https": proxy})
    return session


def _unwrap_search_url(href: str) -> str:
    href = unquote(href.strip())
    parsed = urlparse(href)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        if target:
            return unquote(target)
    return href


def _extract_links(html: str, onion_only: bool = False) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for tag in soup.find_all("a", href=True):
        href = _unwrap_search_url(tag.get("href", ""))
        if not href.startswith(("http://", "https://")):
            continue
        parsed = urlparse(href)
        host = (parsed.hostname or "").lower()
        if onion_only and not host.endswith(".onion"):
            continue
        if not onion_only and host.endswith(".onion"):
            continue
        if host in {"duckduckgo.com", "html.duckduckgo.com", "ahmia.fi"}:
            continue
        if href not in links:
            links.append(href)
    return links[:MAX_SEARCH_RESULTS]


def _ddg_search(session: requests.Session, query: str) -> list[str]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    return _extract_links(response.text)


def _ahmia_search(session: requests.Session, query: str) -> list[str]:
    url = f"https://ahmia.fi/search/?q={quote_plus(query)}"
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    return _extract_links(response.text, onion_only=True)


def discover_candidates(session: requests.Session) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[str, str]] = set()

    for query in SEARCH_QUERIES["clearweb"]:
        try:
            links = _ddg_search(session, query)
        except requests.RequestException:
            continue
        source = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        for link in links:
            item = Candidate(link, "clearweb", "DuckDuckGo HTML", source, query)
            if (item.channel, item.url) not in seen:
                seen.add((item.channel, item.url))
                candidates.append(item)

    for query in SEARCH_QUERIES["forums"]:
        try:
            links = _ddg_search(session, query)
        except requests.RequestException:
            continue
        source = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        for link in links:
            host = (urlparse(link).hostname or "").lower()
            if not ("reddit.com" in host or "forum" in host or "community" in host or "discourse" in host):
                continue
            item = Candidate(link, "forums", "DuckDuckGo HTML", source, query)
            if (item.channel, item.url) not in seen:
                seen.add((item.channel, item.url))
                candidates.append(item)

    for query in SEARCH_QUERIES["onion_index"]:
        try:
            links = _ahmia_search(session, query)
        except requests.RequestException:
            continue
        source = f"https://ahmia.fi/search/?q={quote_plus(query)}"
        for link in links:
            item = Candidate(link, "onion", "Ahmia", source, query)
            if (item.channel, item.url) not in seen:
                seen.add((item.channel, item.url))
                candidates.append(item)

    return candidates[:MAX_PAGE_FETCHES]


def fetch_and_analyze(session: requests.Session, candidate: Candidate, snapshot_root: Path) -> Result | None:
    try:
        response = session.get(candidate.url, timeout=TIMEOUT, allow_redirects=True, stream=True)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "html" not in content_type.lower() and not candidate.url.endswith(("/", ".html", ".htm")):
            return None
        body = response.content[:1_500_000]
        html = body.decode(response.encoding or "utf-8", errors="replace")
    except requests.RequestException:
        return None

    content_hash = sha256_text(html)
    snapshot_root.mkdir(parents=True, exist_ok=True)
    path = snapshot_path(snapshot_root, content_hash)
    path.write_text(html, encoding="utf-8", errors="replace")

    try:
        soup = BeautifulSoup(html, "html.parser")
        for node in soup(["script", "style", "noscript"]):
            node.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:MAX_TEXT_CHARS]
        signals = detect_signals(f"{title}\n{text}")
        verification = verify(signals, independent_observations=1)
        return Result(
            url=candidate.url,
            channel=candidate.channel,
            source_name=candidate.source_name,
            source_url=candidate.source_url,
            title=title[:240],
            status=verification.status,
            confidence=verification.confidence,
            score=verification.score,
            signals=tuple(s.name for s in signals),
            observed_at=utc_now(),
            content_hash=content_hash,
            masked_url=mask_url(candidate.url),
        )
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def _verify_repeated(results: list[Result]) -> list[Result]:
    grouped: dict[tuple[str, tuple[str, ...]], list[Result]] = defaultdict(list)
    for result in results:
        grouped[(result.title.lower(), result.signals)].append(result)

    upgraded: list[Result] = []
    for result in results:
        peers = grouped[(result.title.lower(), result.signals)]
        independent = len({item.source_name + ":" + item.url for item in peers})
        if independent >= 3 and result.score >= 8:
            status, confidence = "verified", "high"
        elif independent >= 2 and result.score >= 6:
            status, confidence = "verified", "medium"
        else:
            status, confidence = result.status, result.confidence
        upgraded.append(Result(**{**asdict(result), "status": status, "confidence": confidence}))
    return upgraded


def run(output: Path) -> dict:
    session = _session()
    with tempfile.TemporaryDirectory(prefix="raasfinder-snapshots-") as tmp:
        snapshot_root = Path(tmp)
        candidates = discover_candidates(session)
        results: list[Result] = []
        for candidate in candidates:
            result = fetch_and_analyze(session, candidate, snapshot_root)
            if result and result.status in {"candidate", "verified"}:
                results.append(result)
        results = _verify_repeated(results)

    observations = [asdict(item) for item in results]
    verified = sum(item["status"] == "verified" for item in observations)
    channels = {name: "ready" for name in ("clearweb", "forums", "onion", "onion_index")}
    if not any(item["channel"] == "onion" for item in observations):
        channels["onion"] = "no-results" if os.environ.get("TOR_PROXY") else "proxy-required"

    data = {
        "generated_at": utc_now(),
        "engine": {"mode": "zero-seed", "ai": False, "external_cti": False, "status": "ready"},
        "stats": {
            "verified_groups": verified,
            "candidates": sum(item["status"] == "candidate" for item in observations),
            "evidence_records": len(observations),
            "observed_sources": len({item["source_name"] for item in observations}),
        },
        "channels": channels,
        "observations": observations,
    }
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    run(Path(os.environ.get("RAASFINDER_OUTPUT", "web/data.json")))
