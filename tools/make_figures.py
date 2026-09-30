"""Render original, book-friendly knowledge diagrams for MiniQuant."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parent.parent
ROOT = PROJECT / "figs"
ROOT.mkdir(exist_ok=True)
FONT = str(PROJECT / "video" / "assets" / "NotoSansCJKsc-Regular.otf")

def font(size):
    return ImageFont.truetype(FONT, size)

def canvas(title, subtitle):
    im = Image.new("RGB", (1600, 900), "#f8fafc")
    d = ImageDraw.Draw(im)
    d.text((80, 50), title, font=font(50), fill="#12233d")
    d.text((82, 120), subtitle, font=font(24), fill="#52647e")
    d.line((80, 168, 1520, 168), fill="#ccd8e5", width=3)
    return im, d

def box(d, xy, title, lines, color="#eaf2ff"):
    d.rounded_rectangle(xy, radius=20, fill=color, outline="#8eaacb", width=2)
    x0, y0, x1, y1 = xy
    d.text((x0 + 24, y0 + 22), title, font=font(29), fill="#123259")
    for i, line in enumerate(lines):
        d.text((x0 + 24, y0 + 76 + i * 43), line, font=font(23), fill="#354b66")

def arrow(d, a, b):
    d.line((a, b), fill="#2874ad", width=5)
    x, y = b
    if a[0] != b[0]:
        d.polygon([(x, y), (x - 14, y - 10), (x - 14, y + 10)], fill="#2874ad")
    else:
        d.polygon([(x, y), (x - 10, y - 14), (x + 10, y - 14)], fill="#2874ad")

im, d = canvas("量化研究闭环", "每一步都记录输入、时间戳、假设与可复现证据")
steps = [
    ("问题与假设", ["经济机制 / 反证条件"]),
    ("点时数据", ["历史股票池 / 发布时刻"]),
    ("因子与标签", ["当时可得 / 未来结果"]),
    ("时间验证", ["训练 → 验证 → 测试"]),
    ("组合与回测", ["权重 / 成本 / 容量"]),
    ("审计与复盘", ["归因 / 稳健性 / 失败"]),
]
for i, (name, lines) in enumerate(steps):
    col, row = (i % 3 if i < 3 else 5 - i), i // 3
    x, y = 80 + col * 510, 220 + row * 235
    box(d, (x, y, x + 440, y + 175), f"{i+1:02d}  {name}", lines)
    if i < 2:
        arrow(d, (x + 450, y + 88), (x + 495, y + 88))
    if i in (3, 4):
        d.line((x - 10, y + 88, x - 55, y + 88), fill="#2874ad", width=5)
        d.polygon([(x - 55, y + 88), (x - 41, y + 78), (x - 41, y + 98)], fill="#2874ad")
    if col == 2 and row == 0:
        arrow(d, (x + 220, y + 185), (x + 220, y + 225))
d.text((82, 740), "失败时沿数据、时间、交易、统计四条路径回溯；漂亮回测不是终点。", font=font(26), fill="#9b3b35")
im.save(ROOT / "01_research_loop.png")

im, d = canvas("信息可得性与交易时间线", "特征只能使用决策时已经公开且已处理的数据")
ys = 330
d.line((170, ys, 1430, ys), fill="#2c638f", width=8)
points = [
    (200, "t 日盘中", ["成交逐步形成"]),
    (550, "t 日收盘后", ["收盘价、因子确认", "产生目标权重"]),
    (920, "t+1 开盘", ["按可成交价格建仓"]),
    (1290, "t+2 开盘", ["平仓并计算标签"]),
]
for x, label, lines in points:
    d.ellipse((x-12, ys-12, x+12, ys+12), fill="#e05d4f")
    d.text((x-105, ys-100), label, font=font(28), fill="#153759")
    for j, line in enumerate(lines):
        d.text((x-105, ys+45+j*42), line, font=font(23), fill="#415672")
box(d, (135, 580, 720, 760), "可用于 t 日决策", ["t 日及更早的已发布字段", "历史训练样本及其已兑现标签"], "#e5f6ec")
box(d, (875, 580, 1460, 760), "不能用于 t 日决策", ["t+1 / t+2 实际价格与收益", "事后修订值、未来成分股"], "#fff0ed")
im.save(ROOT / "02_availability_timeline.png")

im, d = canvas("三种常见回测偏差：症状、原因、检查", "把风险转成可执行的检查，而不是泛泛提醒")
headers = [(90, "偏差"), (440, "错误做法"), (930, "可执行检查")]
for x, title in headers:
    d.text((x, 220), title, font=font(30), fill="#14375a")
rows = [
    ("未来函数", "用 t+1 价格做 t 日特征", "截断 t 之后数据，重算因子一致"),
    ("幸存者偏差", "拿现存股票回测 2010 年", "逐日历史成分股与退市样本"),
    ("交易成本低估", "只算毛收益或零滑点", "按换手×单边费率做敏感性表"),
    ("多重试验", "反复挑测试期最优参数", "冻结测试集并记录所有实验"),
]
for i, (name, wrong, check) in enumerate(rows):
    y = 290 + i * 125
    d.rounded_rectangle((75, y, 1525, y+105), radius=16, fill="#ffffff" if i % 2 else "#eaf2fa", outline="#d5e0eb", width=2)
    d.text((90, y+28), name, font=font(27), fill="#173b62")
    d.text((440, y+28), wrong, font=font(23), fill="#7a3e3d")
    d.text((930, y+28), check, font=font(23), fill="#205b4c")
im.save(ROOT / "03_backtest_bias_checks.png")

im, d = canvas("四种采样轴：改变“一个样本”的定义", "采样轴决定何时封闭一根 Bar；因子和未来标签是另外两件事")
for x, title in [(80, "采样轴"), (360, "结束条件"), (850, "适用动机与边界")]:
    d.text((x, 220), title, font=font(29), fill="#14375a")
axis_rows = [
    ("时间 Bar", "每满 1 分钟", "易与日历对齐；活跃度不均"),
    ("Tick Bar", "每满 N 笔成交", "按成交频次取样；拆单会影响笔数"),
    ("Volume Bar", "累计 N 股成交", "按交易量取样；不同价格价值不同"),
    ("Dollar Bar", "累计金额达到阈值", "按成交金额取样；阈值须训练期确定"),
]
for i, (name, trigger, note) in enumerate(axis_rows):
    y = 290 + i * 112
    d.rounded_rectangle((72, y, 1528, y + 90), radius=14,
                        fill="#ffffff" if i % 2 else "#eaf2fa", outline="#d5e0eb", width=2)
    d.text((80, y + 24), name, font=font(25), fill="#173b62")
    d.text((360, y + 24), trigger, font=font(24), fill="#38526e")
    d.text((850, y + 24), note, font=font(23), fill="#205b4c")
d.text((82, 790), "共同底线：保留事件时间；未结束的 Bar 不可偷看；不要把图中未定义的 C1 当成标准算法。", font=font(24), fill="#9b3b35")
im.save(ROOT / "04_sampling_axes.png")

# 05: three independent axes for a beginner reading a ticker.
im, d = canvas("先看底层，再看包装，最后看市场", "同一经济风险可装进不同产品；同一产品在不同市场受不同交易规则约束")
cols = [
    ("01 底层风险：赚赔从何来？", ["企业股权 → 股价、分红", "债务承诺 → 利息、违约", "商品/指数 → 价格波动"], "#e9f4ff"),
    ("02 产品包装：持有什么？", ["股票/债券：直接权利", "基金/ETF：一篮子份额", "期货/期权：衍生合约"], "#e8f7ee"),
    ("03 市场规则：怎样交易？", ["A 股：板块、T+1 卖出", "美股：交收 T+1", "港股：交收通常 T+2"], "#fff1e9"),
]
for i, (title, lines, color) in enumerate(cols):
    x = 75 + i * 510
    box(d, (x, 250, x + 455, 590), title, lines, color)
    if i < 2:
        arrow(d, (x + 460, 420), (x + 500, 420))
box(d, (90, 660, 1510, 800), "研究合约：先回答五个问题", ["代码代表什么权利？标的是什么？计价货币？何时可交易/交收？历史数据是否点时可得？"], "#f3f1ff")
im.save(ROOT / "05_product_market_map.png")

print("created", *(str(p) for p in sorted(ROOT.glob("*.png"))))
