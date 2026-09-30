"""Build MiniQuant's frozen, balanced, real OHLCV teaching sample."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


SOURCE = "https://github.com/mlin21/stockPredictor/blob/main/sp500_stocks.csv"
UPSTREAM = "https://www.kaggle.com/datasets/andrewmvd/sp-500-stocks"
META_SOURCE = "https://github.com/Jiahao30/Stock-Analysis-Project/blob/main/data_resources/sp500_companies.csv"
FORCED = ("AAPL", "AMZN", "MMM")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prices", required=True, type=Path)
    parser.add_argument("--companies", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    columns = ["Date", "Symbol", "Adj Close", "Close", "High", "Low", "Open", "Volume"]
    source = pd.read_csv(args.prices, usecols=columns)
    companies = pd.read_csv(args.companies, usecols=["Symbol", "Sector"])
    source["Date"] = pd.to_datetime(source["Date"], errors="coerce")
    if source["Date"].isna().any():
        raise ValueError("日期解析失败")
    if source.duplicated(["Date", "Symbol"]).any():
        raise ValueError("原始文件含重复日期-股票")

    group = source.groupby("Symbol").agg(
        rows=("Date", "size"),
        adj_valid=("Adj Close", "count"),
        valid_price=("Close", "count"),
        positive_volume=("Volume", lambda x: (x > 0).sum()),
        last_date=("Date", "max"),
    )
    full_days = source["Date"].nunique()
    final_date = source["Date"].max()
    eligible = group.index[
        (group.rows == full_days)
        & (group.adj_valid == full_days)
        & (group.valid_price == full_days)
        & (group.positive_volume == full_days)
        & (group.last_date == final_date)
    ]
    sector_table = companies.drop_duplicates("Symbol").set_index("Symbol")["Sector"]
    by_sector = sector_table.reindex(eligible).dropna().groupby(sector_table.reindex(eligible).dropna())
    rng = np.random.default_rng(20260930)
    selected: set[str] = set()
    sector_counts: dict[str, int] = {}
    for sector, members in by_sector:
        choices = sorted(members.index)
        if len(choices) < 6:
            raise ValueError(f"{sector} 合格股票少于 6 支")
        picked = sorted(rng.choice(choices, size=6, replace=False).tolist())
        for forced in FORCED:
            if forced in choices and forced not in picked:
                picked[-1] = forced
        selected.update(picked)
        sector_counts[sector] = len(picked)
    names = sorted(selected)
    if len(names) != 66 or not set(FORCED) <= set(names):
        raise ValueError(f"股票池构造异常：{len(names)} 支")

    bars = source[source.Symbol.isin(names)].copy()
    bars = bars.rename(columns={
        "Date": "date", "Symbol": "ticker", "Adj Close": "adj_close",
        "Close": "close", "High": "high", "Low": "low", "Open": "open", "Volume": "volume",
    })
    numeric = ["adj_close", "close", "high", "low", "open", "volume"]
    if bars[numeric].isna().any().any() or not np.isfinite(bars[numeric].to_numpy()).all():
        raise ValueError("选中行情存在缺失或无穷大")
    if not (bars[["adj_close", "close", "high", "low", "open"]] > 0).all().all():
        raise ValueError("价格非正")
    if not (bars.volume > 0).all():
        raise ValueError("成交量非正")
    if not (bars.high >= bars[["open", "close", "low"]].max(axis=1)).all():
        raise ValueError("最高价关系错误")
    if not (bars.low <= bars[["open", "close", "high"]].min(axis=1)).all():
        raise ValueError("最低价关系错误")
    factor = bars.adj_close / bars.close
    for field in ("open", "high", "low"):
        bars["adj_" + field] = bars[field] * factor
    bars = bars.sort_values(["date", "ticker"]).reset_index(drop=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    bars.to_parquet(args.out, index=False)

    manifest = {
        "kind": "real historical US stock daily OHLCV; frozen teaching snapshot",
        "source_url": SOURCE,
        "upstream_dataset": UPSTREAM,
        "sector_metadata_source": META_SOURCE,
        "source_sha256": sha256(args.prices),
        "sector_metadata_sha256": sha256(args.companies),
        "sha256": sha256(args.out),
        "rows": len(bars),
        "tickers": names,
        "sectors": sector_counts,
        "first_date": bars.date.min().date().isoformat(),
        "last_date": bars.date.max().date().isoformat(),
        "adjustment": "adj OHLC = raw OHLC times same-day adj_close/close; this approximates total-return prices",
        "selection": "six eligible current-constituent stocks per present-day sector; random seed 20260930; AAPL, AMZN, MMM forced for teaching",
        "limitations": "survivorship and current-sector bias; adjusted opens are not executable quotes; no delisted names or historical memberships",
    }
    args.out.with_name("manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: manifest[key] for key in ("rows", "first_date", "last_date", "sha256")}, ensure_ascii=False))
    print("tickers", len(names), names)


if __name__ == "__main__":
    main()
