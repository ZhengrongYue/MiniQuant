"""Render every seven-trading-day MiniQuant phase as an auditable GIF.

The displayed quantity is an adjusted-price unit, NOT an executable A-share
count. Simulated notional is units multiplied by the adjusted fill price.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "video" / "assets" / "NotoSansCJKsc-Regular.otf"
SIZE = (1600, 960)
INK = "#17324d"
MUTED = "#60758a"
BUY = "#087f8c"
SELL = "#c75b39"


def phase_trade_table(trades: pd.DataFrame, decisions: pd.DataFrame,
                      members: pd.DataFrame) -> pd.DataFrame:
    """Aggregate every executed order by seven-day phase, side and stock."""
    starts = pd.to_datetime(decisions.loc[decisions["rebalance"], "signal_date"])
    if starts.empty or not starts.is_monotonic_increasing:
        raise ValueError("Missing or unordered phase boundaries")
    frame = trades.copy()
    frame["phase"] = np.searchsorted(starts.to_numpy(), frame["signal_date"].to_numpy(), side="right") - 1
    if (frame["phase"] < 0).any() or (frame["phase"] >= len(starts)).any():
        raise ValueError("A trade has no matching phase")
    if not (frame["date"] > frame["signal_date"]).all():
        raise ValueError("Trade preceded its signal")
    frame["notional"] = frame["units"] * frame["adjusted_price"]
    names = members.drop_duplicates("code").set_index("code")["code_name"]
    frame["name"] = frame["code"].map(names)
    if frame["name"].isna().any() or not frame["notional"].gt(0).all():
        raise ValueError("Missing stock name or nonpositive simulated trade amount")
    result = frame.groupby(["phase", "side", "code", "name"], as_index=False).agg(
        adjusted_units=("units", "sum"),
        simulated_notional=("notional", "sum"),
        executions=("code", "size"),
    )
    if not np.isclose(result["simulated_notional"].sum(), frame["notional"].sum()):
        raise ValueError("Animated trade amounts do not reconcile to the ledger")
    return result.sort_values(["phase", "side", "simulated_notional"],
                              ascending=[True, True, False]).reset_index(drop=True)


def _font(size: int) -> ImageFont.FreeTypeFont:
    if not FONT.exists():
        raise FileNotFoundError(f"Bundled Chinese font missing: {FONT.name}")
    return ImageFont.truetype(str(FONT), size)


def _money(amount: float) -> str:
    if amount >= 10_000:
        return f"¥{amount / 10_000:,.1f} 万"
    return f"¥{amount:,.0f}"


def _side(draw: ImageDraw.ImageDraw, rows: pd.DataFrame, *, left: int,
          title: str, color: str, max_rows: int, max_notional: float) -> None:
    draw.rounded_rectangle((left, 218, left + 730, 815), radius=18,
                           fill="#ffffff", outline="#d9e2e9", width=2)
    draw.text((left + 24, 238), title, font=_font(32), fill=color)
    amount = rows["simulated_notional"].sum()
    draw.text((left + 445, 245), _money(amount), font=_font(27), fill=color)
    draw.text((left + 24, 291), "股票名称 / 代码", font=_font(21), fill=MUTED)
    draw.text((left + 382, 291), "复权单位", font=_font(21), fill=MUTED)
    draw.text((left + 552, 291), "模拟金额", font=_font(21), fill=MUTED)
    draw.line((left + 20, 326, left + 710, 326), fill="#d9e2e9", width=2)
    if rows.empty:
        draw.text((left + 250, 517), "本阶段无成交", font=_font(27), fill=MUTED)
        return
    row_height = min(43, 474 // max_rows)
    for i, row in enumerate(rows.itertuples(index=False)):
        y = 336 + i * row_height
        if i % 2 == 0:
            draw.rounded_rectangle((left + 12, y - 2, left + 717, y + row_height - 2),
                                   radius=5, fill="#f5f8fa")
        code = row.code.split(".")[-1]
        draw.text((left + 24, y), f"{row.name}  {code}", font=_font(20), fill=INK)
        draw.text((left + 385, y), f"{row.adjusted_units:,.1f}", font=_font(19), fill=MUTED)
        draw.text((left + 558, y), _money(row.simulated_notional), font=_font(19), fill=color)
        bar_width = int(300 * row.simulated_notional / max_notional)
        draw.rectangle((left + 24, y + row_height - 6,
                        left + 24 + bar_width, y + row_height - 3), fill=color)


def make_trade_animation(trades: pd.DataFrame, decisions: pd.DataFrame,
                         members: pd.DataFrame, nav: pd.DataFrame,
                         out_path: str | Path, duration_ms: int = 2500) -> pd.DataFrame:
    """Save a GIF with one frame per rebalance phase and return its audit table."""
    if duration_ms < 200:
        raise ValueError("Animation duration must allow the table to be read")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    table = phase_trade_table(trades, decisions, members)
    reset = decisions.reset_index(drop=True)
    boundaries = list(reset.index[reset["rebalance"]]) + [len(reset)]
    max_rows = max(1, int(table.groupby(["phase", "side"]).size().max()))
    if max_rows > 12:
        raise ValueError(f"More than 12 distinct names in a phase side: {max_rows}")
    max_notional = max(float(table["simulated_notional"].max()), 1.0)
    frames = []
    for phase, (begin, stop) in enumerate(zip(boundaries[:-1], boundaries[1:])):
        block = reset.iloc[begin:stop]
        signal_start = block["signal_date"].iloc[0]
        signal_end = block["signal_date"].iloc[-1]
        executed_end = block["execution_date"].iloc[-1]
        phase_nav = nav.loc[executed_end, "nav"] / nav.loc[signal_start, "nav"] - 1
        holdings = int(nav.loc[executed_end, "holdings"])
        selected = table.loc[table["phase"] == phase]
        buys = selected.loc[selected["side"] == "BUY"]
        sells = selected.loc[selected["side"] == "SELL"]

        image = Image.new("RGB", SIZE, "#f0f5f8")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, SIZE[0], 16), fill=BUY)
        draw.text((62, 47), "MiniQuant · 沪深300内选10只", font=_font(38), fill=INK)
        draw.text((62, 101),
                  f"第 {phase + 1:02d} / {len(boundaries)-1:02d} 阶段  |  信号 {signal_start.date()} — {signal_end.date()}"
                  f"  |  最后执行 {executed_end.date()}", font=_font(25), fill=MUTED)
        gain_color = BUY if phase_nav >= 0 else SELL
        draw.text((62, 156), f"阶段净值变化 {phase_nav:+.2%}", font=_font(27), fill=gain_color)
        draw.text((530, 157), f"期末持仓 {holdings} 只", font=_font(25), fill=INK)
        draw.text((825, 157), f"阶段成交 {int(selected['executions'].sum())} 笔", font=_font(25), fill=INK)
        _side(draw, buys, left=62, title="买入 BUY", color=BUY,
              max_rows=max_rows, max_notional=max_notional)
        _side(draw, sells, left=808, title="卖出 SELL", color=SELL,
              max_rows=max_rows, max_notional=max_notional)
        progress = (phase + 1) / (len(boundaries) - 1)
        draw.rounded_rectangle((62, 841, 1538, 853), radius=6, fill="#d2dfe7")
        draw.rounded_rectangle((62, 841, 62 + int(1476 * progress), 853),
                               radius=6, fill=BUY)
        draw.text((62, 870),
                  "交易量口径：金额＝后复权价格 × 复权单位；不是实盘成交股数、成交价格或成交承诺。",
                  font=_font(21), fill=MUTED)
        draw.text((62, 906), "同一股票在阶段内的多笔成交已按买卖方向分别汇总。",
                  font=_font(21), fill=MUTED)
        frames.append(image.convert("P", palette=Image.Palette.ADAPTIVE, colors=128))
    temp = out_path.with_name(out_path.stem + ".part.gif")
    frames[0].save(temp, save_all=True, append_images=frames[1:],
                   duration=duration_ms, loop=0, optimize=True, disposal=2)
    temp.replace(out_path)
    return table
