from __future__ import annotations

from dataclasses import dataclass

from bs4 import BeautifulSoup

from .candidates import Candidate, extract_candidates


@dataclass(frozen=True)
class ParsedPage:
    title: str
    text: str
    links: tuple[Candidate, ...]


def parse_html(html: str, channel: str = "clearweb") -> ParsedPage:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    text = " ".join(soup.stripped_strings)
    links = tuple(extract_candidates(text, channel=channel))
    return ParsedPage(title=title, text=text, links=links)
