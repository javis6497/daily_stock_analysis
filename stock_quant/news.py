from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import Instrument


@dataclass(frozen=True)
class NewsItem:
    title: str
    source: str
    url: str
    published_at: str


def filter_news(
    items: Iterable[NewsItem],
    instruments: Iterable[Instrument],
    keywords: Iterable[str],
    max_items: int = 8,
) -> list[NewsItem]:
    tokens = [keyword for keyword in keywords if keyword]
    for instrument in instruments:
        tokens.append(instrument.name)
        tokens.append(instrument.symbol)

    matched: list[NewsItem] = []
    for item in items:
        haystack = f"{item.title} {item.source}"
        if not tokens or any(token in haystack for token in tokens):
            matched.append(item)
        if len(matched) >= max_items:
            break
    return matched


def sample_news() -> list[NewsItem]:
    return [
        NewsItem(
            title="政策利好推动宽基指数基金关注度提升",
            source="样例资讯",
            url="https://example.com/policy-index-fund",
            published_at="2026-07-03 08:00",
        ),
        NewsItem(
            title="市场成交回暖，资金继续关注高流动性 ETF",
            source="样例资讯",
            url="https://example.com/etf-flow",
            published_at="2026-07-03 08:15",
        ),
    ]
