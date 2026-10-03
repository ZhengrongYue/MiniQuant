"""Small, inspectable event-driven backtest used by simple_framework.ipynb.

The model uses adjusted prices as an economic-return proxy. It does not model
exchange matching, 100-share lots, price limits, or cash dividends separately.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "private"


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_snapshot(data_dir: Path = DATA_DIR):
    """Load a locally frozen snapshot and fail on a missing or altered input."""
    manifest_path = data_dir / "simple_2026_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Missing {manifest_path}. Run python tools/build_simple_snapshot.py "
            "on a network that can reach BaoStock and Eastmoney."
        )
    manifest = json.loads(manifest_path.read_text())
    for name, digest in manifest["files"].items():
        path = data_dir / name
        if not path.exists() or _digest(path) != digest:
            raise ValueError(f"Snapshot file missing or hash changed: {name}")
    bars = pd.read_csv(data_dir / "simple_2026_bars.csv.gz", dtype={"code": str})
    reports = pd.read_csv(
        data_dir / "simple_2026_reports.csv.gz", dtype={"SECURITY_CODE": str}
    )
    members = pd.read_csv(data_dir / "simple_2026_members.csv.gz", dtype={"code": str})
    benchmark = pd.read_csv(data_dir / "simple_2026_benchmark.csv.gz")
    return bars, reports, members, benchmark, manifest


def clean_inputs(bars, reports, members, benchmark, ma_window=10):
    """Apply an explicit schema; return clean tables and a small rejection audit."""
    if ma_window < 2:
        raise ValueError("ma_window must be at least 2")
    bars = bars.copy()
    reports = reports.copy()
    members = members.copy()
    benchmark = benchmark.copy()
    audit = {}

    if bars.duplicated(["date", "code"]).any():
        raise ValueError("BaoStock date/code is not unique")
    bars["date"] = pd.to_datetime(bars["date"], errors="coerce")
    for col in ("open", "high", "low", "close", "volume", "amount", "peTTM"):
        bars[col] = pd.to_numeric(bars[col], errors="coerce")
    for col in ("tradestatus", "isST"):
        bars[col] = pd.to_numeric(bars[col], errors="coerce")
    invalid_price = (
        bars["date"].isna() | (bars[["open", "high", "low", "close"]] <= 0).any(axis=1)
        | (bars["high"] < bars[["open", "close"]].max(axis=1))
        | (bars["low"] > bars[["open", "close"]].min(axis=1))
        | (bars["volume"] < 0)
    )
    audit["bad_price_rows"] = int(invalid_price.sum())
    if invalid_price.any():
        raise ValueError(f"Invalid OHLC/volume in {invalid_price.sum()} rows")
    audit["suspended_rows"] = int((bars["tradestatus"] != 1).sum())
    audit["invalid_pe_rows"] = int((~bars["peTTM"].between(0, 30, inclusive="neither")).sum())
    bars = bars.sort_values(["code", "date"]).reset_index(drop=True)
    group = bars.groupby("code", sort=False)["close"]
    bars["ma"] = group.transform(lambda s: s.rolling(ma_window, min_periods=ma_window).mean())
    bars["prev_close"] = group.shift(1)
    bars["prev_ma"] = bars.groupby("code", sort=False)["ma"].shift(1)
    tradable = (bars["tradestatus"] == 1) & (bars["volume"] > 0)
    bars["cross_up"] = tradable & (bars["close"] > bars["ma"]) & (
        bars["prev_close"] <= bars["prev_ma"]
    )
    bars["cross_down"] = tradable & (bars["close"] < bars["ma"]) & (
        bars["prev_close"] >= bars["prev_ma"]
    )
    bars["below_ma"] = tradable & (bars["close"] < bars["ma"])
    bars["below_ma_2"] = bars.groupby("code", sort=False)["below_ma"].transform(
        lambda s: s.rolling(2, min_periods=2).sum().eq(2)
    )

    reports["code6"] = reports["SECURITY_CODE"].str.zfill(6)
    for col in ("REPORTDATE", "NOTICE_DATE", "UPDATE_DATE"):
        reports[col] = pd.to_datetime(reports[col], errors="coerce").dt.normalize()
    for col in ("BASIC_EPS", "PARENT_NETPROFIT", "TOTAL_OPERATE_INCOME"):
        reports[col] = pd.to_numeric(reports[col], errors="coerce")
    bad_report = (
        ~reports["code6"].str.fullmatch(r"\d{6}", na=False)
        | reports[["REPORTDATE", "NOTICE_DATE", "UPDATE_DATE"]].isna().any(axis=1)
        | (reports["REPORTDATE"] > reports["NOTICE_DATE"])
    )
    audit["bad_report_rows"] = int(bad_report.sum())
    reports = reports.loc[~bad_report].copy()
    # A retrospective correction can change a value. Use the later date as a
    # conservative *earliest usable* date; this is still not a true PIT archive.
    reports["available_on"] = reports[["NOTICE_DATE", "UPDATE_DATE"]].max(axis=1)
    audit["missing_eps_rows"] = int(reports["BASIC_EPS"].isna().sum())
    reports = reports.drop_duplicates(["code6", "REPORTDATE", "available_on"], keep="last")

    members = members.drop_duplicates("code")
    if len(members) != 300:
        raise ValueError(f"Expected 300 fixed index constituents, got {len(members)}")
    benchmark["date"] = pd.to_datetime(benchmark["date"], errors="coerce")
    for col in ("open", "close"):
        benchmark[col] = pd.to_numeric(benchmark[col], errors="coerce")
    if benchmark["date"].isna().any() or (benchmark[["open", "close"]] <= 0).any().any():
        raise ValueError("Bad benchmark date/price")
    benchmark = benchmark.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    return bars, reports, members, benchmark, audit


def latest_public_report(reports: pd.DataFrame, decision_date: pd.Timestamp) -> pd.DataFrame:
    """Strictly earlier published/revised rows only; same-day reports are excluded."""
    known = reports.loc[
        (reports["available_on"] < decision_date)
        & (reports["BASIC_EPS"] > 0)
    ]
    return known.sort_values(["code6", "REPORTDATE", "available_on"]).drop_duplicates(
        "code6", keep="last"
    )


def select_pool(day_bars: pd.DataFrame, reports: pd.DataFrame, day: pd.Timestamp, size=100):
    """Select lowest positive PE among tradable members with known reports."""
    report_codes = set(latest_public_report(reports, day)["code6"])
    eligible = day_bars.loc[
        day_bars["peTTM"].between(0, 30, inclusive="neither")
        & (day_bars["tradestatus"] == 1)
        & (day_bars["volume"] > 0)
        & (day_bars["isST"] == 0)
        & day_bars["ma"].notna()
        & day_bars["code"].str[-6:].isin(report_codes)
    ].sort_values(["peTTM", "code"])
    chosen = eligible.head(size)
    return list(chosen["code"]), len(eligible)


def build_decisions(bars, reports, benchmark, first="2026-01-05", every=7,
                    exit_confirm_days=1):
    """At each close, update the 7-day PE pool and daily MA position state."""
    dates = list(benchmark.loc[benchmark["date"] >= pd.Timestamp(first), "date"])
    if exit_confirm_days not in (1, 2):
        raise ValueError("This teaching implementation supports 1 or 2 exit confirmation days")
    by_day = {day: frame for day, frame in bars.groupby("date", sort=False)}
    pool: set[str] = set()
    active: set[str] = set()
    records = []
    for i, day in enumerate(dates[:-1]):  # last close has no next open in the snapshot
        day_bars = by_day.get(day)
        if day_bars is None:
            raise ValueError(f"Missing all stock bars on {day.date()}")
        rebalance = i % every == 0
        eligible_count = None
        if rebalance:
            pool_list, eligible_count = select_pool(day_bars, reports, day)
            pool = set(pool_list)
        exit_flag = "cross_down" if exit_confirm_days == 1 else "below_ma_2"
        down = set(day_bars.loc[day_bars[exit_flag], "code"])
        up = set(day_bars.loc[day_bars["cross_up"], "code"])
        active = (active & pool) - down
        active |= up & pool
        records.append({
            "signal_date": day, "execution_date": dates[i + 1],
            "rebalance": rebalance, "eligible_count": eligible_count,
            "pool_count": len(pool), "active_count": len(active),
            "pool": frozenset(pool), "active": frozenset(active),
        })
    return pd.DataFrame(records)


def run_backtest(bars, benchmark, decisions, cost_bps=10.0,
                 initial_cash=1_000_000.0, rebalance_band=0.0):
    """Next-open orders with failed fills on suspended or zero-volume stocks.

    Units are fractional *adjusted-price units*, not actual A-share lots.
    Reweight equally only when the active set changes or the 7-day pool resets.
    rebalance_band skips trades that only correct a small weight drift.
    """
    if cost_bps < 0:
        raise ValueError("cost_bps must be nonnegative")
    if not 0 <= rebalance_band < 1:
        raise ValueError("rebalance_band must be in [0, 1)")
    cost_rate = cost_bps / 10_000
    day_map = {day: frame.set_index("code") for day, frame in bars.groupby("date", sort=False)}
    dates = list(benchmark.loc[benchmark["date"] >= decisions.iloc[0]["signal_date"], "date"])
    cash = float(initial_cash)
    units: dict[str, float] = {}
    last_price: dict[str, float] = {}
    previous_desired: set[str] = set()
    history = [{"date": dates[0], "nav": 1.0, "equity": cash,
                "cost": 0.0, "turnover": 0.0, "holdings": 0, "blocked": 0}]
    trades = []
    for decision in decisions.itertuples(index=False):
        day = decision.execution_date
        current = day_map[day]
        for code, row in current.iterrows():
            if np.isfinite(row["open"]) and row["open"] > 0:
                last_price[code] = float(row["open"])
        if any(code not in last_price for code in units):
            raise ValueError(f"Missing mark price for a holding on {day.date()}")
        before = cash + sum(qty * last_price[code] for code, qty in units.items())
        desired = set(decision.active)
        rebalance = bool(decision.rebalance or desired != previous_desired or set(units) != desired)
        fees = 0.0
        turnover = 0.0
        blocked = 0
        if rebalance:
            target = before * 0.99 / len(desired) if desired else 0.0

            def can_trade(code):
                if code not in current.index:
                    return False
                row = current.loc[code]
                return bool(row["tradestatus"] == 1 and row["volume"] > 0 and row["open"] > 0)

            # Sell first. Failed exits remain in the portfolio and consume capital.
            for code in sorted(list(units)):
                value = units[code] * last_price[code]
                if code in desired and value <= target * (1 + rebalance_band):
                    continue
                sell_value = max(0.0, value - (target if code in desired else 0.0))
                if sell_value < 1e-6:
                    continue
                if not can_trade(code):
                    blocked += 1
                    continue
                qty = min(units[code], sell_value / last_price[code])
                notional = qty * last_price[code]
                fee = notional * cost_rate
                units[code] -= qty
                if units[code] < 1e-10:
                    units.pop(code)
                cash += notional - fee
                fees += fee
                turnover += notional / before
                trades.append((day, decision.signal_date, code, "SELL", qty, last_price[code], fee))

            for code in sorted(desired):
                if not can_trade(code):
                    blocked += 1
                    continue
                value = units.get(code, 0.0) * last_price[code]
                if value >= target * (1 - rebalance_band):
                    continue
                need = max(0.0, target - value)
                notional = min(need, cash / (1 + cost_rate))
                if notional < 1e-6:
                    continue
                qty = notional / last_price[code]
                fee = notional * cost_rate
                units[code] = units.get(code, 0.0) + qty
                cash -= notional + fee
                fees += fee
                turnover += notional / before
                trades.append((day, decision.signal_date, code, "BUY", qty, last_price[code], fee))
        after = cash + sum(qty * last_price[code] for code, qty in units.items())
        if cash < -1e-6 or after <= 0:
            raise ValueError(f"Invalid cash/equity on {day.date()}")
        history.append({
            "date": day, "nav": after / initial_cash, "equity": after,
            "cost": fees / initial_cash, "turnover": turnover,
            "holdings": len(units), "blocked": blocked,
        })
        previous_desired = desired
    nav = pd.DataFrame(history).set_index("date")
    trade_cols = ["date", "signal_date", "code", "side", "units", "adjusted_price", "fee"]
    trades = pd.DataFrame(trades, columns=trade_cols)
    benchmark_open = benchmark.set_index("date")["open"].reindex(nav.index)
    if benchmark_open.isna().any():
        raise ValueError("Benchmark calendar is incomplete")
    nav["benchmark_nav"] = benchmark_open / benchmark_open.iloc[0]
    nav["return"] = nav["nav"].pct_change()
    nav["benchmark_return"] = nav["benchmark_nav"].pct_change()
    nav["drawdown"] = nav["nav"] / nav["nav"].cummax() - 1
    return nav, trades


def performance_metrics(nav, annual_rf=0.0):
    """All risk ratios use the same daily return window and 252-day convention."""
    daily = nav[["return", "benchmark_return"]].dropna()
    r = daily["return"]
    b = daily["benchmark_return"]
    n = len(r)
    if n < 2:
        raise ValueError("Need at least two daily returns")
    total = nav["nav"].iloc[-1] / nav["nav"].iloc[0] - 1
    annual = (1 + total) ** (252 / n) - 1 if total > -1 else -1.0
    simple_annual = total * 252 / n
    calendar_days = (nav.index[-1] - nav.index[0]).days
    calendar_simple = total * 365 / calendar_days
    calendar_compound = (1 + total) ** (365 / calendar_days) - 1 if total > -1 else -1.0
    rf_daily = (1 + annual_rf) ** (1 / 252) - 1
    excess = r - rf_daily
    active = r - b
    vol = r.std(ddof=1) * np.sqrt(252)
    tracking_error = active.std(ddof=1) * np.sqrt(252)
    benchmark_excess = b - rf_daily
    beta = excess.cov(benchmark_excess) / benchmark_excess.var(ddof=1)
    alpha_daily = excess.mean() - beta * benchmark_excess.mean()
    mdd = float(nav["drawdown"].min())
    return {
        "起止": f"{nav.index[0].date()} → {nav.index[-1].date()}",
        "交易日收益样本数": n,
        "总收益率": total,
        "简单年化收益率": simple_annual,
        "复合年化收益率": annual,
        "日历天数": calendar_days,
        "简单年化收益率（365日）": calendar_simple,
        "复合年化收益率（365日）": calendar_compound,
        "基准总收益率": float(nav["benchmark_nav"].iloc[-1] - 1),
        "年化波动率": vol,
        "最大回撤": mdd,
        "Beta": beta,
        "Alpha（日回归截距×252）": alpha_daily * 252,
        "夏普比率": excess.mean() / excess.std(ddof=1) * np.sqrt(252),
        "信息比率": active.mean() / active.std(ddof=1) * np.sqrt(252),
        "Calmar": annual / abs(mdd) if mdd < 0 else np.nan,
        "累计换手（单边权重之和）": float(nav["turnover"].sum()),
        "累计费用/初始本金": float(nav["cost"].sum()),
        "未成交委托次数": int(nav["blocked"].sum()),
    }
