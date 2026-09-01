from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoverySource:
    """A public discovery channel, represented by an operator-supplied URL."""

    name: str
    channel: str
    url: str
    enabled: bool = True


# No group names, onion addresses, or threat-actor seeds are embedded here.
# Operators supply public index/search URLs through configuration at runtime.
DEFAULT_SOURCES: tuple[DiscoverySource, ...] = ()


def enabled_sources(sources: tuple[DiscoverySource, ...] = DEFAULT_SOURCES) -> tuple[DiscoverySource, ...]:
    return tuple(source for source in sources if source.enabled)
