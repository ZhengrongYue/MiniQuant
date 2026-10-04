# MiniQuant

[MiniQuant.ipynb](MiniQuant.ipynb) 是主教材：面向有 AI/大模型背景、没有炒股经验、希望申请量化研究实习的读者。AI 模型原理从简，重点学习市场、数据、非时间采样、因子、标签、验证、组合、成交和风控的完整链路，最后进入 A 股盘口、逐笔委托/成交与因子岗、模型岗、策略岗作品。详细来源映射见 [课程覆盖表](tools/COVERAGE.md)，按课程图逐项查漏和章节验收见 [课程验收表](tools/CURRICULUM_AUDIT.md)。

## 怎样读这份教程

每个关键概念先用日常语言和小例子建立直觉，再给专业名称、精确定义、代码和失效条件。第一次读时，遇到 IC、复权、横截面、OFI 等词，不必立刻记公式：先问“它在回答什么问题、在下单前能否知道、算错会造成什么后果”。第 1 章有术语翻译表；第 5 章前把因子、信号、订单、标签串成一条时间线；第二篇先用摊位买卖例子解释盘口。代码和公式保留，便于读懂后复核，而不是靠比喻替代严谨性。

## 安装与运行

使用 Python 3.10 或更高版本。在项目根目录创建环境并安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m ipykernel install --user --name miniquant --display-name MiniQuant
jupyter lab MiniQuant.ipynb
```

在 Jupyter 中选择 `MiniQuant` 内核，从头顺序运行 Notebook。默认读取仓库中的冻结行情，不需要实时外网。图位于 `figs/`；成片、字幕与制作脚本位于 `video/`。如果安装环境需要代理或镜像，请按自己的网络环境配置，不要把私有源地址写入仓库。

## 数据与再现

新增 [simple_framework.ipynb](simple_framework.ipynb)：可独立运行、适合按模块写成文章的“API 获取行情与财报 → PE 选 10 只 → MA5/MA15 双均线 → 10 万元风险仓位与盈利比例等额加仓 → 浮动止盈/止损 → 回测指标图与交易 GIF”案例。总资金乘总风险比例得到可亏金额，再除以股价乘个股价格风险比例得到股数；组合计划风险上限 3%、单只账户风险上限 1%，先用 1.5×ATR 与 2.5% 初始止损估计仓位；开盘价相对首次买价达到 +2%/+4% 时各排队等额加仓一次，下一开盘重新核验且当天不能有止损、退出或新买信号；上涨 8% 后改用自最高收盘价回撤 2.5% 的止盈条件。佣金示例为买卖各万三、每笔最低 5 元，卖出印花税用万分之五，过户费双边十万分之一；笔记本也对比截图中的旧印花税千分之一。新增完整参数地图，分组选股、均线、风险仓位、分批、退出和费用，并提供可选的“训练集确认逻辑 → 开发集调参 → 冻结参数后检查测试集”实验单元。全部必要函数都在 Notebook 内，不导入 `tools`；首次运行从 BaoStock 与东方财富获取数据并缓存在相对目录 `data/private/`。若 CodeLab 不能直连 BaoStock TCP 服务，可在能连接的机器运行同一 Notebook，随后转入缓存。缓存按上游使用条款不随公开仓库发布。行情使用 BaoStock `adjustflag=1` **后复权（hfq）**，仅供收益研究；复权价格和分数份额不是可直接下单的报价与股数。[GIF 动画](figs/simple_framework_trades.gif)列出每次 5 日调池阶段的模拟交易。

`data/real_equities.parquet` 含 66 支美股 2010-01-04 至 2024-08-30 的 243,540 行真实日行情；`data/manifest.json` 保存来源、筛选、哈希和局限。原始公开 CSV 来自 [stockPredictor 的 S&P 500 文件](https://github.com/mlin21/stockPredictor/blob/main/sp500_stocks.csv)，上游说明指向 [Kaggle S&P 500 Stocks](https://www.kaggle.com/datasets/andrewmvd/sp-500-stocks)；行业元数据来自 [Stock-Analysis-Project](https://github.com/Jiahao30/Stock-Analysis-Project)。Kaggle 原数据集标注为 CC0，两个 GitHub 来源仓库标注为 MIT；本项目保留来源链接及原始文件摘要，发布前仍应按实际使用范围复核上游条款。`tools/build_real_snapshot.py` 可从原始 CSV 重建冻结子集，须提供 `--prices`、`--companies` 和 `--out`。不要把当前 S&P 500 样本回看 2010 年的结果当无偏历史回测；也不要把推算的复权开盘价当可成交报价。

A 股盘口/逐笔数据通常需要交易所或供应商授权。Notebook 的微型事件表和快照是**明确标注的教学夹具**，不是虚构为“真实样本”的行情。真实 Level-2 接入时，应先按对应交易所与接口版本验证字段、序号、订单关联、可得时刻和完整性，再做因子与策略结论。

## 500 元实盘操作实验

Notebook 第 14 章提供正规券商 App 官方入口核验、纸面模拟、100 份 ETF 限价订单、最低佣金敏感性计算和交割单复盘。500 元到 800 元等于 60% 收益，**不是**本教程的保证或验收标准；课程以正确识别风险、执行规则和如实记录成本作为验收。任何真实交易均须以本人风险承受能力和当期交易所、券商规则为准。

## 视频

`video/scenes.json` 保存 35 个逐镜头脚本；`video/build_video.py` 使用 edge-tts、Noto Sans CJK 与 ffmpeg 渲染约 34 分钟的中文旁白、逐句字幕、章节信息和 `video/MiniQuant_30min.mp4`。视频也按“例子与直觉 → 专业术语 → 使用边界”的顺序讲解。详见 [video/README.md](video/README.md)。

## 来源与许可

课程从金融产品、A 股/美股/港股差异讲起，吸收旧 `quant-tutorial`、`ref.txt` 与 [Datawhale whale-quant](https://github.com/datawhalechina/whale-quant) 的主题，使用重新组织的原创解释、代码和框架图。旧本地参考文件在完成覆盖审计后已清理；历史主题映射保留在 `tools/COVERAGE.md`，运行无需原目录。whale-quant 使用 CC BY-NC-SA 4.0；若未来出版，须对外部图文、数据源及许可逐项审核。

本次 2026-01-05 至 2026-09-30 的默认图表采用开发集选参方案：完整区间收益约 +3.27%、复合年化换算约 +4.61%、最大回撤约 4.94%；同期沪深 300 价格指数约 −6.54%、年化 −9.03%、最大回撤 14.11%。训练（1—3 月）、开发（4—6 月）、测试（7—9 月）的每日收益日期不重叠；测试段策略约 −1.57%。此前已查看过测试时段，因此它仅是切分教学演示，不能当作真正未见过的盲测或实盘依据。
