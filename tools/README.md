# MiniQuant 辅助资料与构建工具

主教材和运行入口在项目根目录。本目录收纳可选构建脚本与课程核对资料，日常从头运行 `MiniQuant.ipynb` 不需要先运行这些脚本。

- `COVERAGE.md`：旧课程与 MiniQuant 的知识点对应关系。
- `CURRICULUM_AUDIT.md`：课程图逐项验收与边界。
- `build_real_snapshot.py`：从已取得的原始 CSV 重建冻结日行情，需要显式传入 `--prices`、`--companies`、`--out`。
- `build_simple_snapshot.py`：可选的批量抓取脚本；`simple_framework.ipynb` 已内置相同的数据获取流程，不依赖此脚本。
- `simple_framework_core.py`：可选的复用版选股、信号、回测和绩效函数；教学 Notebook 已内置必要代码。
- `make_trade_animation.py`：可选的独立 GIF 生成脚本；教学 Notebook 已内置动画代码。
- `make_figures.py`：重绘 `figs/` 中的知识图。
- `revise_curriculum.py`：历史一次性 Notebook 迁移脚本，已有标记时直接退出。

从项目根目录运行 `python tools/make_figures.py`。视频制作脚本留在 `video/`，因为它属于视频产物自身。
