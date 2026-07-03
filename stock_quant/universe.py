from __future__ import annotations

from .config import AppConfig
from .models import Instrument


DEFAULT_RECOMMENDATION_UNIVERSE = (
    Instrument("510300", "沪深300ETF", "cn", "etf", tags=("宽基", "候选")),
    Instrument("510500", "中证500ETF", "cn", "etf", tags=("宽基", "候选")),
    Instrument("159915", "创业板ETF", "cn", "etf", tags=("成长", "候选")),
    Instrument("588000", "科创50ETF", "cn", "etf", tags=("科技", "候选")),
    Instrument("512880", "证券ETF", "cn", "etf", tags=("金融", "候选")),
    Instrument("512000", "券商ETF", "cn", "etf", tags=("金融", "候选")),
    Instrument("512660", "军工ETF", "cn", "etf", tags=("主题", "候选")),
    Instrument("512760", "芯片ETF", "cn", "etf", tags=("科技", "候选")),
    Instrument("159995", "芯片ETF", "cn", "etf", tags=("科技", "候选")),
    Instrument("600519", "贵州茅台", "cn", "stock", tags=("消费", "候选")),
    Instrument("300750", "宁德时代", "cn", "stock", tags=("新能源", "候选")),
    Instrument("600036", "招商银行", "cn", "stock", tags=("银行", "候选")),
    Instrument("601318", "中国平安", "cn", "stock", tags=("金融", "候选")),
    Instrument("600276", "恒瑞医药", "cn", "stock", tags=("医药", "候选")),
    Instrument("000333", "美的集团", "cn", "stock", tags=("家电", "候选")),
)


def build_recommendation_pool(config: AppConfig) -> list[Instrument]:
    if not config.recommendation.enabled:
        return []

    watch_symbols = {instrument.symbol for instrument in config.watchlist}
    candidates: list[Instrument] = []
    candidates.extend(config.candidate_pool)
    if config.recommendation.include_default_universe:
        candidates.extend(DEFAULT_RECOMMENDATION_UNIVERSE)

    result: list[Instrument] = []
    seen: set[str] = set()
    for instrument in candidates:
        if config.recommendation.exclude_watchlist and instrument.symbol in watch_symbols:
            continue
        if instrument.symbol in seen:
            continue
        result.append(instrument)
        seen.add(instrument.symbol)
    return result
