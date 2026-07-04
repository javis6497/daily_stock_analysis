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
    if config.recommendation.include_dynamic_a_shares:
        candidates.extend(_fetch_dynamic_a_share_candidates(config))
    if config.recommendation.include_dynamic_etfs:
        candidates.extend(_fetch_dynamic_etf_candidates(config))

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


def _fetch_dynamic_a_share_candidates(config: AppConfig) -> list[Instrument]:
    if config.data.provider.lower() != "akshare":
        return []
    try:
        import akshare as ak
    except ModuleNotFoundError:
        return []

    try:
        frame = ak.stock_zh_a_spot_em()
    except Exception:
        return []

    rows: list[tuple[float, Instrument]] = []
    for _, row in frame.iterrows():
        symbol = _text(row, "代码", "symbol")
        name = _text(row, "名称", "name")
        if not symbol or not name or _is_risky_stock_name(name):
            continue

        turnover = _number(row, "成交额", "amount")
        market_cap = _number(row, "总市值", "market_cap")
        pct_change = _number(row, "涨跌幅", "pct_change")
        pe = _number(row, "市盈率-动态", "动态市盈率", "pe")
        pb = _number(row, "市净率", "pb")

        if turnover < config.recommendation.min_turnover:
            continue
        if market_cap < config.recommendation.min_market_cap:
            continue
        if not (config.recommendation.min_pct_change <= pct_change <= config.recommendation.max_pct_change):
            continue
        if not (config.recommendation.min_pe < pe <= config.recommendation.max_pe):
            continue
        if not (config.recommendation.min_pb < pb <= config.recommendation.max_pb):
            continue

        rows.append(
            (
                turnover,
                Instrument(
                    symbol=symbol,
                    name=name,
                    market="cn",
                    asset_type="stock",
                    tags=("动态A股", "候选"),
                ),
            )
        )

    rows.sort(key=lambda item: item[0], reverse=True)
    limit = max(0, config.recommendation.dynamic_a_share_limit)
    return [instrument for _, instrument in rows[:limit]]


def _fetch_dynamic_etf_candidates(config: AppConfig) -> list[Instrument]:
    if config.data.provider.lower() != "akshare":
        return []
    try:
        import akshare as ak
    except ModuleNotFoundError:
        return []

    try:
        frame = ak.fund_etf_spot_em()
    except Exception:
        return []

    rows: list[tuple[float, Instrument]] = []
    for _, row in frame.iterrows():
        symbol = _text(row, "代码", "基金代码", "symbol")
        name = _text(row, "名称", "基金简称", "name")
        if not symbol or not name:
            continue

        turnover = _number(row, "成交额", "amount")
        pct_change = _number(row, "涨跌幅", "pct_change")
        if turnover < config.recommendation.min_etf_turnover:
            continue
        if abs(pct_change) > config.recommendation.max_candidate_single_day_pct * 100:
            continue

        rows.append(
            (
                turnover,
                Instrument(
                    symbol=symbol,
                    name=name,
                    market="cn",
                    asset_type="etf",
                    tags=(_candidate_group(name), "动态ETF", "候选"),
                ),
            )
        )

    rows.sort(key=lambda item: item[0], reverse=True)
    limit = max(0, config.recommendation.dynamic_etf_limit)
    return [instrument for _, instrument in rows[:limit]]


def _text(row, *keys: str) -> str:
    for key in keys:
        value = row.get(key) if hasattr(row, "get") else None
        if value is None:
            continue
        text = str(value).strip()
        if text and text.lower() != "nan":
            return text
    return ""


def _number(row, *keys: str) -> float:
    text = _text(row, *keys)
    if not text:
        return 0.0
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return 0.0


def _is_risky_stock_name(name: str) -> bool:
    upper_name = name.upper()
    return "ST" in upper_name or "退" in name


def _candidate_group(name: str) -> str:
    rules = (
        ("科技", ("科技", "芯片", "半导体", "计算机", "人工智能", "AI", "科创")),
        ("金融", ("证券", "券商", "银行", "保险", "金融")),
        ("消费", ("消费", "食品", "酒", "家电")),
        ("医药", ("医药", "医疗", "创新药", "生物")),
        ("新能源", ("新能源", "电池", "光伏", "锂电", "电力")),
        ("宽基", ("沪深", "中证", "上证", "创业板", "红利", "A500", "50ETF", "300ETF", "500ETF")),
        ("周期", ("煤炭", "钢铁", "有色", "化工")),
        ("军工", ("军工", "国防")),
    )
    upper_name = name.upper()
    for group, keywords in rules:
        if any(keyword in name or keyword in upper_name for keyword in keywords):
            return group
    return "主题"
