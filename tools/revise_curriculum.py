"""Idempotent 2026-09-30 MiniQuant curriculum gap revision.

Run on the remote Quant project with the quant Python environment. This is a
one-time, explicit notebook migration; source cells use a unique marker.
"""

from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / 'MiniQuant.ipynb'
nb = nbf.read(PATH, as_version=4)
MARKER = '<!-- curriculum-audit-20260930 -->'
if any(MARKER in c.source for c in nb.cells):
    print('curriculum revision already present; no changes')
    raise SystemExit(0)

def md(s): return nbf.v4.new_markdown_cell(s.strip())
def code(s): return nbf.v4.new_code_cell(s.strip())
def before(prefix, cells):
    i = next(i for i, c in enumerate(nb.cells) if c.cell_type == 'markdown' and c.source.startswith(prefix))
    nb.cells[i:i] = cells

nb.cells[0].source += "\n\n" + MARKER + "\n**给 AI 算法工程师的阅读提示**：Python、回归、分类和神经网络原理只需快速复习；本书时间主要投入数据口径、事件顺序、标签、因子检验、组合、成交与复盘。先问‘这个数在当时能否知道、能否交易’，再问模型能否拟合。"

before('## 2. 数据地基', [md('''### 第一关验收：先理解交易，再看模型

用自己的话解释：限价单为何可能排队；买一/卖一价差和冲击成本有什么区别；A 股现货、ETF、股指期货、商品期货在交易单位、保证金、卖空、结算与交易时段上为什么不能共用一套执行规则。能画出“委托→交易所撮合→回报→持仓”的路径，再进入数据章。**这些是市场制度问题，不是神经网络问题。**''')])

before('## 专题 A：经典均线', [
    md('''### 金融收益为何难学：重尾、异方差与时间依赖

同样叫“样本”，财经时间序列通常不满足独立同分布：收益可能有厚尾、波动聚集和制度切换；价格差分也不会自动变成正态。画正态曲线之前，先检查尾部频率、偏度、峰度和波动在不同时段的变化。我们在真实 AMZN 日收益上检验一个**描述性**问题，不把统计检验的 p 值当作交易信号。'''),
    code('''from scipy.stats import jarque_bera, skew, kurtosis
amzn_r = close_ret["AMZN"].dropna()
z = (amzn_r - amzn_r.mean()) / amzn_r.std(ddof=1)
tail_rate = (z.abs() > 3).mean()
diagnostics = pd.Series({"偏度": skew(amzn_r), "超额峰度": kurtosis(amzn_r),
                         "|z|>3 实际比例": tail_rate,
                         "正态参考比例": 0.0027,
                         "JB 检验 p": jarque_bera(amzn_r).pvalue})
display(diagnostics.to_frame("真实 AMZN 日收益"))
assert 0 <= tail_rate <= 1'''),
    md('''**区分四个概念**：价格的一阶差分 $P_t-P_{t-1}$ 有货币单位；简单收益 $P_t/P_{t-1}-1$ 无量纲；对数收益 $\log P_t-\log P_{t-1}$ 近似可加；按成交金额取样的 Dollar Bar 改变的是**采样轴**。差分与自定义轴不是同一个操作，任何“更接近正态”的说法都要在训练期和后续样本分别检验。''')
])

before('## 5. 标签、可得性', [
    md('''### 第二关验收：因子不是越多越好

金融假设型特征先说明机制：例如盘口失衡反映哪一侧短期供需、何时可能失效；数学变换型特征则如滚动均值、差分、PCA，能压缩或变换输入，却不自动产生可交易原因。非时间轴上的“过去 5 根 Bar”覆盖的日历时间不固定，因此滚动窗口必须同时报告 Bar 数与实际历时。信息熵 $H=-\sum p_i\log_2p_i$ 可描述方向分布的不确定性，但估计样本少时偏差大；不能把高熵或低熵直接当成 alpha。'''),
    code('''# 真实日行情上的一个非价格因子：过去 20 日平均成交额相对自身历史的变化。
dollar_turnover = bars.assign(dollar_turnover=bars.close * bars.volume).pivot(
    index="date", columns="ticker", values="dollar_turnover")
liquidity_ratio = dollar_turnover.rolling(20, min_periods=20).mean() / \
                  dollar_turnover.rolling(120, min_periods=120).mean()
print("流动性变化因子在 2024-08-30 可得的股票数:", int(liquidity_ratio.iloc[-1].notna().sum()))
assert liquidity_ratio.iloc[:119].isna().all().all()
# 这仍非真实盘口因子，也未处理 A 股停牌、涨跌停和点时股票池。''')
])

before('## 6. 两个基线', [
    md('''### 标签工程：答案的形状决定模型回答什么

同一价格路径可以产生不同标签：固定持有期收益适合回归，超过训练期阈值的上/平/下适合分类；止盈/止损/超时三道屏障对应路径依赖事件标签；趋势扫描则寻找未来窗口的趋势方向。**标签允许事后看未来，但特征和筛选阈值不能。** 标签密度是每单位时间触发多少事件，过密会造成高度重叠；过疏又使有效样本太少。分类平衡不应靠反复查看测试期来“调”阈值。'''),
    code('''# 用既有真实 AMZN 收盘价演示固定期限三分类；这里只是标签设计比较。
amzn = wide_close["AMZN"]
future5 = amzn.shift(-5) / amzn - 1
train_cut = train.date.max()
threshold = future5.loc[:dates[train_end_i-5]].abs().quantile(.60)  # 标签终点也留在训练期
three_way = pd.Series(np.select([future5 > threshold, future5 < -threshold],
                                [1, -1], default=0), index=amzn.index)
three_way[future5.isna()] = np.nan
print("训练期阈值:", round(float(threshold), 4))
display(three_way.loc[train.date.min():train_cut].value_counts(normalize=True).sort_index()
        .rename("训练期标签密度").to_frame())
assert three_way.iloc[-5:].isna().all()'''),
    md('''**路径型标签的边界**：如果只存日收盘，就不知道日内先碰止盈还是先碰止损；用日线 high/low 也可能同时碰到两道屏障，需保守处理或更细粒度数据。未来 5 日标签在相邻日期共享大部分价格路径；随机分行交叉验证会让相近答案同时落入训练与验证。'''),
    code('''# 用显式的标签区间演示 purge：训练事件的结束时间不得碰到验证区间。
toy_events = pd.DataFrame({"start": pd.to_datetime(["2024-01-02","2024-01-04","2024-01-08"]),
                           "end":   pd.to_datetime(["2024-01-05","2024-01-10","2024-01-09"])})
valid_start, valid_end = pd.Timestamp("2024-01-08"), pd.Timestamp("2024-01-12")
overlap = (toy_events.start <= valid_end) & (toy_events.end >= valid_start)
display(toy_events.assign(overlaps_validation=overlap))
assert overlap.tolist() == [False, True, True]
# 实际 walk-forward 还须逐折重拟合预处理器，并为延迟与相关性留 embargo。''')
])

before('## 专题 C：因子分析', [
    md('''### 降维不是免费压缩：训练与实时推理必须同构

相关因子过多会使估计不稳。过滤法删除常数、高缺失和高相关列；PCA 把原特征旋转成少数方向；正则化在不显式降维时限制系数。PCA 最大化输入方差，不保证最大化预测能力，也会损失解释性。选择维度、标准化器和 PCA 只能拟合训练期；上线时每个原始特征仍要按相同顺序、单位和时刻到达，缺一项不能随意补 0。'''),
    code('''from sklearn.decomposition import PCA
compressed = make_pipeline(StandardScaler(), PCA(n_components=2), Ridge(alpha=10.0))
compressed.fit(train[feature_names], train.target)
test["pca_score"] = compressed.predict(test[feature_names])
print("PCA 训练期累计解释方差:", round(float(compressed.named_steps["pca"].explained_variance_ratio_.sum()), 3))
print("原 Ridge 测试 IC:", round(float(daily_ic(test, "score").mean()), 4),
      "PCA+Ridge 测试 IC:", round(float(daily_ic(test, "pca_score").mean()), 4))
assert test.pca_score.notna().all()'''),
    md('''**验收**：能解释“输入维度减少”与“实时原始字段减少”为什么不是一回事；能给出模型包所需的列名顺序、训练期统计量、版本号、缺失回退和延迟预算。测试 IC 没改善时，不为 PCA 额外复杂度找借口。''')
])

before('## 8. 从信号到组合', [
    md('''### 多模型/多轴组合：先看增量，再谈“集成”

因子分数、线性模型、树模型可按预先固定的权重合成；不同采样轴的模型必须先对齐到**同一个决策时刻**，且不能把尚未结束的 Bar 当已知。看单模型与组合的 IC、相关性、换手、成本后收益和市场状态；若两个模型错误高度同向，平均并不能分散风险。这里做固定 50/50 排名融合，**不在测试期优化权重**。'''),
    code('''rank_ridge = test.groupby("date").score.rank(pct=True)
rank_rule = test.groupby("date").rule_score.rank(pct=True)
test["fixed_blend"] = .5 * rank_ridge + .5 * rank_rule
ic_check = pd.Series({name: daily_ic(test, col).mean()
                      for name, col in [("Ridge", "score"), ("规则", "rule_score"),
                                        ("固定融合", "fixed_blend")]})
display(ic_check.rename("测试期平均 IC").to_frame().round(4))
assert test.fixed_blend.between(0, 1).all()''')
])

before('## 9. 可交易回测', [
    md('''### 从目标权重到成交：一笔订单的诚实故事

模型建议买 10,000 股时，卖一只有 3,000 股，不能把 10,000 股全按卖一成交。下面依次消耗可见卖档，计算实际成交量、均价与剩余未成交；这是**确定性教学撮合**，不包含其他参与者抢单、撤单、隐藏量、队列优先或延迟。'''),
    code('''ask_levels = [(10.00, 3000), (10.01, 4000), (10.03, 1000)]
remaining, spent = 10_000, 0.0
for price, available in ask_levels:
    take = min(remaining, available)
    spent += take * price
    remaining -= take
filled = 10_000 - remaining
vwap = spent / filled
print(f"申请 10,000 股；成交 {filled:,} 股；未成交 {remaining:,} 股；成交均价 {vwap:.4f}")
assert (filled, remaining) == (8000, 2000)
assert vwap > ask_levels[0][0]'''),
    md('''**订单状态机**：NEW → PARTIALLY_FILLED → FILLED，或从未完成状态进入 CANCELED/REJECTED。回报可能重复、乱序或晚到；持仓只能根据成交回报更新，不能根据“已发送”更新。纸面交易和实盘共用规则时，仍须独立实现券商接口、风控与合规校验；本课不发送真实订单。''')
])

before('## 10. 绩效与基准', [
    md('''### 容量：资金扩大后，信号可能被自己的订单吃掉

净收益不能随资金规模线性放大。先用日均成交额估算一个粗略参与率上界，再用真实盘口、盘口深度和冲击模型细化。下面假设单笔目标占资金 10%、最多参与某股票当日成交额 5%；它只说明数量级，**不能作为真实 A 股可交易容量**。'''),
    code('''adv_by_stock = dollar_turnover.loc[:train.date.max()].tail(20).mean()
capacity_ticker = (adv_by_stock - adv_by_stock.median()).abs().idxmin()
sample_adv = adv_by_stock[capacity_ticker]
print("选取训练期成交额接近样本中位数的股票:", capacity_ticker)
capacity_rows=[]
for capital in [1e6,1e8,1e9,1e10]:
    target_notional=.10*capital
    crude_cap=.05*sample_adv
    capacity_rows.append((capital,target_notional,min(1,crude_cap/target_notional)))
display(pd.DataFrame(capacity_rows,columns=["资金(美元)","目标订单名义金额(美元)","粗略可参与比例"]))
# 训练期成交额只是历史代理；订单簿深度、价格限制和冲击需另测。''')
])

before('### Alpha / Beta 归因', [
    md('''### Calmar：不要把宣传门槛当研究目标

Calmar = 同一评价窗口的复合年化收益 / 最大回撤绝对值。回撤接近零时比值可能不稳定；改变窗口和估值频率也会改变数字。图三写的“Calmar 超过 3”是未经本项目验证的结果主张，**不是 MiniQuant 必须达成的目标**；筛选参数去凑门槛会造成回测过拟合。'''),
    code('''calmar = results["年化收益"] / results["最大回撤"].abs().replace(0, np.nan)
display(calmar.rename("同测试期 Calmar").to_frame().round(3))
assert np.isfinite(calmar.dropna()).all()''')
])

before('## 模型岗：从盘口因子', [
    md('''## 非时间轴：时间、笔数、成交量与成交金额

时钟 Bar 每隔固定分钟结束；Tick Bar 每固定成交笔数结束；Volume Bar 每累计固定股数结束；Dollar Bar 每累计固定成交金额结束。后者在活跃时更频繁、冷清时更稀疏，改变了“一个样本”的定义。阈值只能用训练期估计，不能为了测试收益反复调；采样不能抹掉原始事件时间，仍需按 `available_at` 连接公告与盘口特征。图中的 **C₁ 自定义轴没有定义式或原始代码**，本课不猜其含义；下面给出可核对的成交金额轴。

参考原始研究：[Easley、López de Prado、O’Hara 的 Volume Clock](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2034858)。'''),
    code('''# 教学逐笔表：人为构造，只检验“何时结束一根 Bar”的算法。
toy_trades = pd.DataFrame({
    "time": pd.date_range("2024-01-02 09:30:00", periods=18, freq="11s"),
    "price": [10,10.01,10.01,10.02,10.02,10.03,10.03,10.02,10.01,
              10.00,10.01,10.02,10.03,10.04,10.04,10.03,10.02,10.01],
    "qty": [100,150,80,200,120,180,90,240,160,100,300,80,170,130,220,110,190,140]})
toy_trades["notional"] = toy_trades.price * toy_trades.qty
def make_dollar_bars(trades: pd.DataFrame, threshold: float) -> pd.DataFrame:
    if threshold <= 0: raise ValueError("threshold 必须为正")
    rows=[]; bucket=[]; cash=0.0
    for row in trades.itertuples(index=False):
        bucket.append(row); cash += row.notional
        if cash >= threshold:
            prices=[x.price for x in bucket]
            rows.append({"end_time":row.time,"open":prices[0],"high":max(prices),
                         "low":min(prices),"close":prices[-1],"qty":sum(x.qty for x in bucket),
                         "notional":cash,"trade_count":len(bucket)})
            bucket=[]; cash=0.0
    # 未满门槛的末尾事件不输出；跨日重置与否必须成为显式策略。
    return pd.DataFrame(rows)
dollar_bars = make_dollar_bars(toy_trades, threshold=3000)
display(dollar_bars)
assert (dollar_bars.notional >= 3000).all()
assert dollar_bars.end_time.is_monotonic_increasing'''),
    md('''**轴与特征的关系**：Dollar Bar 是采样/聚合方式，盘口不平衡是特征，两者可组合。若在 Dollar Bar 上算“过去 3 根的收益”，对应实际历时会变动；若要与时钟模型融合，先按决策时刻对齐。样本数少不能声称 Bar 收益比时钟收益更正态；只可报告同训练/测试切分下的偏度、尾部、预测与成本指标。'''),
    code('''from scipy.stats import entropy
bar_sign = np.sign(dollar_bars.close.diff().dropna())
counts = bar_sign.value_counts(normalize=True)
print("教学 Dollar Bar 收益方向熵(bit):", round(float(entropy(counts, base=2)), 3))
print("每根 Bar 的实际历时(秒):", dollar_bars.end_time.diff().dt.total_seconds().dropna().tolist())
assert dollar_bars.trade_count.sum() <= len(toy_trades)''')
])

before('## 因子岗与策略岗', [
    md('''### 二级决策模型（meta-labeling）放在什么位置？

一级模型给方向或候选交易；二级模型只判断“这笔候选是否值得做/做多大”，可以纳入价差、队列、信号置信度和风险限额。训练二级模型时，一级分数必须来自当时可得的**滚动样本外预测**；把一级模型在自身训练集上的拟合分数拿来训练二级模型会再次泄漏。二级模型的增益要用扣成本和同一订单约束检验，不以宣传材料声称的 Calmar 为目标。'''),
    md('''### 实时推理与策略安全边界

离线训练产物要包含模型、预处理器、特征 schema、训练结束时间和版本哈希。在线流程依次检查**消息序号 → 事件时间/接收时间 → 特征完整性 → 推理耗时 → 信号有效期 → 交易限制 → 订单状态回报**。超时或缺字段应丢弃信号/退回预设安全基线，不能盲目用旧盘口。研究回放能证明状态机对给定事件正确，却不能证明生产环境排队、网络、风控和券商行为一致。

为 ETF、股指期货、商品期货迁移模型时，要重新定义交易单位、保证金/杠杆、合约到期与换月、交易时段和可卖空性；不能把股票的标签、成交与成本原样套用。所谓“通用模型”需要跨标的、跨市场状态的样本外证据；“专用模型”也要防止只记住单只股票。'''),
    md('''### 第三关验收：从数据到策略的 12 个问题

1. 原始事件是否有缺口、重复、乱序、修订？2. 非时间 Bar 何时结束，未结束 Bar 能否使用？3. 决策时间、接收时间和可成交时间是否不同？4. 金融机制与纯数学变换能否区分？5. 标签密度和持有窗口如何影响样本独立性？6. purge/embargo 删掉了哪些训练事件？7. PCA 在上线时还需要哪些原始列？8. 模型融合是否真的增加独立信息？9. 目标权重如何变成部分成交的持仓？10. 成本与订单规模上升时结果如何变化？11. 哪些情形触发停止发单？12. 实验记录能否复现所有试过的参数，而非只展示最好的一次？

**验收方式**：每题写出一个定义、一个失败反例、一个可运行检查。图三的业绩数字不作为通过条件。''')
])

nb.cells[-1].source += '\n- 补充阅读：[Volume Clock 原始论文](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2034858)、[回测过拟合原始研究](https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2326253)、[PCA 官方文档](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html)、[CFA Institute 的最大回撤与 Calmar 解释](https://blogs.cfainstitute.org/insideinvesting/2013/02/12/sculpting-investment-portfolios-maximum-drawdown-and-optimal-portfolio-strategy/)。'
for cell in nb.cells:
    if cell.cell_type == 'code': cell.execution_count=None; cell.outputs=[]
nbf.validate(nb)
nbf.write(nb, PATH)
print('revised cells', len(nb.cells))
