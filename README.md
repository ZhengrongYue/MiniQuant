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

新增 [simple_framework.ipynb](simple_framework.ipynb)：用 2026 年真实 A 股日线与东方财富财报，走通“清洗 → 低 PE 选股 → MA10 择时 → 下一开盘回测 → 绩效与成本分析”，再比较一个较长均线的轻量变体与分段结果。它还读取上证综指作市场背景，始终以沪深 300 作正式回测基准。先读它，再进入主教材的高频和模型章节会更容易。配套抓取与回测实现分别位于 `tools/build_simple_snapshot.py`、`tools/simple_framework_core.py`。在可连接 BaoStock 与东方财富的网络运行 `python tools/build_simple_snapshot.py --end 2026-10-03`，然后运行 Notebook；程序以实际最后交易日为准，休市日不会凭空产生行情。东方财富原始财报快照保存在 `data/private/`，按其使用条款不随公开仓库发布；请在自己的环境获取。行情使用 BaoStock `adjustflag=1` **后复权（hfq）**，仅供收益研究；复权价格和分数份额不是可直接下单的报价与股数。Notebook 也对比了 BaoStock 与 TuShare Pro 的接口与权限，不声称已对两源进行实测误差比较。

`data/real_equities.parquet` 含 66 支美股 2010-01-04 至 2024-08-30 的 243,540 行真实日行情；`data/manifest.json` 保存来源、筛选、哈希和局限。原始公开 CSV 来自 [stockPredictor 的 S&P 500 文件](https://github.com/mlin21/stockPredictor/blob/main/sp500_stocks.csv)，上游说明指向 [Kaggle S&P 500 Stocks](https://www.kaggle.com/datasets/andrewmvd/sp-500-stocks)；行业元数据来自 [Stock-Analysis-Project](https://github.com/Jiahao30/Stock-Analysis-Project)。Kaggle 原数据集标注为 CC0，两个 GitHub 来源仓库标注为 MIT；本项目保留来源链接及原始文件摘要，发布前仍应按实际使用范围复核上游条款。`tools/build_real_snapshot.py` 可从原始 CSV 重建冻结子集，须提供 `--prices`、`--companies` 和 `--out`。不要把当前 S&P 500 样本回看 2010 年的结果当无偏历史回测；也不要把推算的复权开盘价当可成交报价。

A 股盘口/逐笔数据通常需要交易所或供应商授权。Notebook 的微型事件表和快照是**明确标注的教学夹具**，不是虚构为“真实样本”的行情。真实 Level-2 接入时，应先按对应交易所与接口版本验证字段、序号、订单关联、可得时刻和完整性，再做因子与策略结论。

## 500 元实盘操作实验

Notebook 第 14 章提供正规券商 App 官方入口核验、纸面模拟、100 份 ETF 限价订单、最低佣金敏感性计算和交割单复盘。500 元到 800 元等于 60% 收益，**不是**本教程的保证或验收标准；课程以正确识别风险、执行规则和如实记录成本作为验收。任何真实交易均须以本人风险承受能力和当期交易所、券商规则为准。

## 视频

`video/scenes.json` 保存 35 个逐镜头脚本；`video/build_video.py` 使用 edge-tts、Noto Sans CJK 与 ffmpeg 渲染约 34 分钟的中文旁白、逐句字幕、章节信息和 `video/MiniQuant_30min.mp4`。视频也按“例子与直觉 → 专业术语 → 使用边界”的顺序讲解。详见 [video/README.md](video/README.md)。

## 来源与许可

课程从金融产品、A 股/美股/港股差异讲起，吸收旧 `quant-tutorial`、`ref.txt` 与 [Datawhale whale-quant](https://github.com/datawhalechina/whale-quant) 的主题，使用重新组织的原创解释、代码和框架图。旧本地参考文件在完成覆盖审计后已清理；历史主题映射保留在 `tools/COVERAGE.md`，运行无需原目录。whale-quant 使用 CC BY-NC-SA 4.0；若未来出版，须对外部图文、数据源及许可逐项审核。
