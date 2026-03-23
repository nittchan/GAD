"""
DataSourceConnector protocol — multi-source data fetching with priority fallback.

Each peril can have multiple data sources. The fetcher tries them in priority order
and uses the first successful result. If all sources fail, the trigger shows "no data."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class RawReading:
    """Raw data from a source, before evaluation."""
    source: str
    data: dict
    confidence: float = 1.0  # 0.0 to 1.0


@dataclass
class SourceConfig:
    """Configuration for a single data source."""
    name: str
    priority: int  # lower = preferred
    fetch_fn: Callable[..., Optional[dict]]
    enabled: bool = True
    rate_limit_note: str = ""


@dataclass
class MultiSourceResult:
    """Result from multi-source fetching."""
    data: dict | None
    source_used: str
    sources_tried: list[str] = field(default_factory=list)
    all_failed: bool = False


def fetch_with_fallback(
    sources: list[SourceConfig],
    **kwargs: Any,
) -> MultiSourceResult:
    """
    Try sources in priority order. Return first success.
    All sources are tried if earlier ones fail.
    """
    sources_tried = []
    for src in sorted(sources, key=lambda s: s.priority):
        if not src.enabled:
            continue
        sources_tried.append(src.name)
        try:
            result = src.fetch_fn(**kwargs)
            if result is not None:
                return MultiSourceResult(
                    data=result,
                    source_used=src.name,
                    sources_tried=sources_tried,
                )
        except Exception:
            continue

    return MultiSourceResult(
        data=None,
        source_used="none",
        sources_tried=sources_tried,
        all_failed=True,
    )
