from __future__ import annotations

import re
from bs4 import BeautifulSoup


def parse_html(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return title[:500], text[:500_000]
