from __future__ import annotations

from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class FetchResult:
    url: str
    status: int
    content_type: str
    html: str


def fetch_public_page(url: str, timeout: float = 15.0) -> FetchResult:
    """Fetch a public HTML page without authentication or access-control bypass."""
    request = Request(
        url,
        headers={
            "User-Agent": "RaaSFinder/0.1 (+public-research-collector)",
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get_content_type()
            if content_type not in {"text/html", "application/xhtml+xml"}:
                raise ValueError(f"unsupported content type: {content_type}")
            body = response.read()
            return FetchResult(
                url=url,
                status=response.status,
                content_type=content_type,
                html=body.decode(response.headers.get_content_charset() or "utf-8", errors="replace"),
            )
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"public fetch failed for {url}: {exc}") from exc
