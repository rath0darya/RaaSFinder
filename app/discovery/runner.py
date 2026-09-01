from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from ..models import mask_url
from ..signals import detect_signals
from ..verifier import verify
from .snapshot import delete_snapshot, save_snapshot

USER_AGENT = "RaaSFinder/0.1 (+https://github.com/rath0darya/RaaSFinder)"
TIMEOUT = 12
MAX_RESULTS_PER_QUERY = 8
MAX_FETCHES = 18
MAX_BODY = 1_500_000

QUERIES = {
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
class Observation:
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


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def session(proxy: str | None = None) -> requests.Session:
    client = requests.Session()
    client.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    if proxy:
        client.proxies.update({"http": proxy, "https": proxy})
    return client


def unwrap(href: str) -> str:
    href = unquote(href.strip())
    parsed = urlparse(href)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        return unquote(parse_qs(parsed.query).get("uddg", [href])[0])
    return href


def links(html: str, onion_only: bool = False) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    found: list[str] = []
    for tag in soup.find_all("a", href=True):
        href = unwrap(tag["href"])
        if not href.startswith(("http://", "https://")):
            continue
        host = (urlparse(href).hostname or "").lower()
        if onion_only != host.endswith(".onion"):
            continue
        if host in {"duckduckgo.com", "html.duckduckgo.com", "ahmia.fi"}:
            continue
        if href not in found:
            found.append(href)
        if len(found) >= MAX_RESULTS_PER_QUERY:
            break
    return found


def search_ddg(client: requests.Session, query: str) -> list[str]:
    source = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    response = client.get(source, timeout=TIMEOUT)
    response.raise_for_status()
    return links(response.text)


def search_ahmia(client: requests.Session, query: str) -> list[str]:
    source = f"https://ahmia.fi/search/?q={quote_plus(query)}"
    response = client.get(source, timeout=TIMEOUT)
    response.raise_for_status()
    return links(response.text, onion_only=True)


def discover(client: requests.Session) -> list[tuple[str, str, str, str]]:
    candidates: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str]] = set()

    for query in QUERIES["clearweb"]:
        try:
            result_links = search_ddg(client, query)
        except requests.RequestException:
            continue
        source = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        for url in result_links:
            item = (url, "clearweb", "DuckDuckGo HTML", source)
            if (item[1], item[0]) not in seen:
                seen.add((item[1], item[0]))
                candidates.append(item)

    for query in QUERIES["forums"]:
        try:
            result_links = search_ddg(client, query)
        except requests.RequestException:
            continue
        source = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        for url in result_links:
            host = (urlparse(url).hostname or "").lower()
            if not any(token in host for token in ("reddit.com", "forum", "community", "discourse")):
                continue
            item = (url, "forums", "DuckDuckGo HTML", source)
            if (item[1], item[0]) not in seen:
                seen.add((item[1], item[0]))
                candidates.append(item)

    for query in QUERIES["onion_index"]:
        try:
            result_links = search_ahmia(client, query)
        except requests.RequestException:
            continue
        source = f"https://ahmia.fi/search/?q={quote_plus(query)}"
        for url in result_links:
            item = (url, "onion", "Ahmia", source)
            if (item[1], item[0]) not in seen:
                seen.add((item[1], item[0]))
                candidates.append(item)

    return candidates[:MAX_FETCHES]


def fetch_observation(client: requests.Session, item: tuple[str, str, str, str], snapshot_dir: Path) -> Observation | None:
    url, channel, source_name, source_url = item
    try:
        response = client.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "html" not in content_type.lower() and not url.endswith(("/", ".html", ".htm")):
            return None
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_content(chunk_size=32_768):
            if not chunk:
                continue
            remaining = MAX_BODY - size
            if remaining <= 0:
                break
            chunks.append(chunk[:remaining])
            size += len(chunks[-1])
            if size >= MAX_BODY:
                break
        html = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
    except requests.RequestException:
        return None

    snapshot = save_snapshot(html, snapshot_dir, name="page")
    try:
        soup = BeautifulSoup(html, "html.parser")
        for node in soup(["script", "style", "noscript"]):
            node.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:80_000]
        signals = detect_signals(f"{title}\n{text}")
        verification = verify(signals, independent_observations=1)
        if verification.status not in {"candidate", "verified"}:
            return None
        return Observation(
            url=url,
            channel=channel,
            source_name=source_name,
            source_url=source_url,
            title=title[:240],
            status=verification.status,
            confidence=verification.confidence,
            score=verification.score,
            signals=tuple(signal.name for signal in signals),
            observed_at=snapshot.observed_at,
            content_hash=snapshot.sha256,
            masked_url=mask_url(url),
        )
    finally:
        delete_snapshot(snapshot)


def upgrade_repeated(observations: list[Observation]) -> list[Observation]:
    groups: dict[tuple[str, tuple[str, ...]], list[Observation]] = {}
    for item in observations:
        groups.setdefault((item.title.lower(), item.signals), []).append(item)

    upgraded: list[Observation] = []
    for item in observations:
        peers = groups[(item.title.lower(), item.signals)]
        independent = len({peer.url for peer in peers})
        if independent >= 3 and item.score >= 8:
            status, confidence = "verified", "high"
        elif independent >= 2 and item.score >= 6:
            status, confidence = "verified", "medium"
        else:
            status, confidence = item.status, item.confidence
        upgraded.append(Observation(**{**asdict(item), "status": status, "confidence": confidence}))
    return upgraded


def run(output: Path) -> dict:
    clear = session()
    tor_proxy = os.environ.get("TOR_PROXY", "").strip()
    onion = session(tor_proxy) if tor_proxy else clear

    with tempfile.TemporaryDirectory(prefix="raasfinder-snapshots-") as temporary:
        snapshot_dir = Path(temporary)
        candidates = discover(clear)
        observations: list[Observation] = []
        for item in candidates:
            client = onion if item[1] == "onion" else clear
            observation = fetch_observation(client, item, snapshot_dir)
            if observation:
                observations.append(observation)
        observations = upgrade_repeated(observations)

    records = [asdict(item) for item in observations]
    data = {
        "generated_at": now(),
        "engine": {"mode": "zero-seed", "ai": False, "external_cti": False, "status": "ready"},
        "stats": {
            "verified_groups": sum(item["status"] == "verified" for item in records),
            "candidates": sum(item["status"] == "candidate" for item in records),
            "evidence_records": len(records),
            "observed_sources": len({item["source_name"] for item in records}),
        },
        "channels": {
            "clearweb": "ready",
            "forums": "ready",
            "onion": "ready" if tor_proxy else "proxy-required",
            "onion_index": "ready",
        },
        "observations": records,
    }
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    run(Path(os.environ.get("RAASFINDER_OUTPUT", "web/data.json")))
