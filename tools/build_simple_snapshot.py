"""Freeze public 2026 A-share bars and Eastmoney reports for simple_framework.ipynb.

Run from a machine that can reach BaoStock TCP/10030 and Eastmoney HTTPS.
The private snapshot can be copied to an offline CodeLab, but is not published.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import baostock as bs
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "private"
EASTMONEY_API = "https://datacenter-web.eastmoney.com/api/data/v1/get"
REPORT_DATES = ("2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30")
BAR_FIELDS = "date,code,open,high,low,close,volume,amount,tradestatus,peTTM,isST"


def rows(result, label: str) -> pd.DataFrame:
    if result.error_code != "0":
        raise RuntimeError(f"{label}: {result.error_code} {result.error_msg}")
    records = []
    while result.next():
        records.append(result.get_row_data())
    return pd.DataFrame(records, columns=result.fields)


def eastmoney_page(report_date: str, page: int, retries: int = 3) -> dict:
    params = {
        "sortColumns": "UPDATE_DATE,SECURITY_CODE",
        "sortTypes": "-1,-1",
        "pageSize": "500",
        "pageNumber": str(page),
        "reportName": "RPT_LICO_FN_CPD",
        "columns": "ALL",
        "filter": f"(REPORTDATE='{report_date}')",
    }
    url = EASTMONEY_API + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 MiniQuant educational snapshot",
            "Referer": "https://data.eastmoney.com/bbsj/",
        },
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.load(response)
            if payload.get("success") is not True or not payload.get("result"):
                raise ValueError(f"Eastmoney response changed: {payload.get('message')}")
            return payload["result"]
        except (OSError, ValueError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"Eastmoney {report_date} page {page}") from exc
            time.sleep(1.5 * (attempt + 1))
    raise AssertionError("unreachable")


def fetch_reports(codes: set[str]) -> pd.DataFrame:
    all_rows = []
    for report_date in REPORT_DATES:
        first = eastmoney_page(report_date, 1)
        pages = int(first["pages"])
        expected_count = int(first["count"])
        raw = list(first.get("data") or [])
        for page in range(2, pages + 1):
            raw.extend(eastmoney_page(report_date, page).get("data") or [])
            time.sleep(0.08)
        if len(raw) != expected_count:
            raise ValueError(f"Eastmoney {report_date}: expected {expected_count}, got {len(raw)}")
        kept = [r for r in raw if str(r.get("SECURITY_CODE", "")).zfill(6) in codes]
        all_rows.extend(kept)
        print(f"Eastmoney {report_date}: {len(raw)} raw / {len(kept)} in universe", flush=True)
    if not all_rows:
        raise ValueError("No reports matched the chosen stocks")
    out = pd.DataFrame(all_rows)
    keep = [
        "SECURITY_CODE", "SECURITY_NAME_ABBR", "TRADE_MARKET", "REPORTDATE",
        "NOTICE_DATE", "UPDATE_DATE", "BASIC_EPS", "PARENT_NETPROFIT",
        "TOTAL_OPERATE_INCOME", "BOARD_NAME",
    ]
    missing = set(keep).difference(out.columns)
    if missing:
        raise ValueError(f"Eastmoney missing columns: {sorted(missing)}")
    return out[keep]


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temp = path.with_name(path.name + ".part")
    frame.to_csv(temp, index=False, compression="gzip" if path.suffix == ".gz" else None)
    temp.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--end", default=date.today().isoformat(), help="Inclusive download end, YYYY-MM-DD")
    args = parser.parse_args()
    end = min(date.fromisoformat(args.end), date.today()).isoformat()
    DATA.mkdir(exist_ok=True)

    login = bs.login()
    if login.error_code != "0":
        raise RuntimeError(f"BaoStock login failed: {login.error_msg}. Use BaoStock >=0.9.4 on a reachable network.")
    try:
        members = rows(bs.query_hs300_stocks(date="2026-01-05"), "HS300 members")
        if not 250 <= len(members) <= 350:
            raise ValueError(f"Unexpected HS300 member count: {len(members)}")
        tickers = sorted(members["code"].unique())
        bars = []
        for number, code in enumerate(tickers, 1):
            result = bs.query_history_k_data_plus(
                code, BAR_FIELDS, start_date="2025-12-01", end_date=end,
                frequency="d", adjustflag="1",  # 后复权 hfq OHLC, not executable quotes
            )
            frame = rows(result, code)
            if not frame.empty:
                bars.append(frame)
            if number % 25 == 0:
                print(f"BaoStock bars: {number}/{len(tickers)}", flush=True)
        benchmark = rows(
            bs.query_history_k_data_plus(
                "sh.000300", "date,code,open,close", start_date="2025-12-01",
                end_date=end, frequency="d", adjustflag="3",
            ),
            "CSI300 index",
        )
        shanghai = rows(
            bs.query_history_k_data_plus(
                "sh.000001", "date,code,open,close", start_date="2025-12-01",
                end_date=end, frequency="d", adjustflag="3",
            ),
            "Shanghai Composite index",
        )
    finally:
        bs.logout()

    daily = pd.concat(bars, ignore_index=True)
    daily = daily.sort_values(["date", "code"]).reset_index(drop=True)
    if daily.duplicated(["date", "code"]).any():
        raise ValueError("Duplicate date/code in BaoStock bars")
    if daily.empty or max(daily["date"]) < "2026-08-01":
        raise ValueError("BaoStock did not return sufficiently recent 2026 bars")
    reports = fetch_reports({code.split(".")[1] for code in tickers})
    members_path = DATA / "simple_2026_members.csv.gz"
    bars_path = DATA / "simple_2026_bars.csv.gz"
    benchmark_path = DATA / "simple_2026_benchmark.csv.gz"
    shanghai_path = DATA / "simple_2026_shanghai.csv.gz"
    reports_path = DATA / "simple_2026_reports.csv.gz"
    for frame, path in [
        (members, members_path), (daily, bars_path),
        (benchmark, benchmark_path), (shanghai, shanghai_path), (reports, reports_path),
    ]:
        atomic_csv(frame, path)
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_end": end,
        "latest_bar_date": max(daily["date"]),
        "first_bar_date": min(daily["date"]),
        "universe": "CSI 300 constituents returned for 2026-01-05; fixed thereafter",
        "stock_count": len(tickers),
        "bar_rows": len(daily),
        "report_rows": len(reports),
        "bar_source": "BaoStock query_history_k_data_plus, adjustflag=1 (post-adjusted/hfq)",
        "report_source": "Eastmoney data center RPT_LICO_FN_CPD (public website endpoint)",
        "benchmark_source": "BaoStock sh.000300 price index, not total-return index",
        "market_context_source": "BaoStock sh.000001 Shanghai Composite price index; context only",
        "limitations": [
            "Eastmoney public endpoint and retrospective revisions are not an immutable point-in-time database.",
            "BaoStock PE history and adjusted prices require independent production-grade point-in-time validation.",
            "Post-adjusted (hfq) OHLC is an economic-return proxy, not a real order price or share count.",
            "The sample universe is CSI 300, so top 10 means top 10 within that universe, not all A shares.",
        ],
        "files": {path.name: sha256(path) for path in [members_path, bars_path, benchmark_path, shanghai_path, reports_path]},
    }
    manifest_path = DATA / "simple_2026_manifest.json"
    temp = manifest_path.with_name(manifest_path.name + ".part")
    temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    temp.replace(manifest_path)
    print(json.dumps({k: manifest[k] for k in ["latest_bar_date", "stock_count", "bar_rows", "report_rows"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
