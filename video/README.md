# MiniQuant 长版视频教程

[MiniQuant_30min.mp4](MiniQuant_30min.mp4) 是与主 Notebook 配套的约 34 分钟中文视频。35 个镜头分为 10 章：金融产品、A 股/美股/港股交易机制、真实数据、统计与因子、标签与模型、组合与回测、红队审计、A 股盘口/逐笔、500 元操作实验、岗位作品。新版在 IC、标签、回撤和 OFI 等术语前先给直觉和小例子；画面文字也同步改为易读表达。代码细节仍以 `MiniQuant.ipynb` 为准。

- `scenes.json`：全部讲稿、画面要点与引用框架图路径。
- `build_video.py`：生成配音、画面、逐句字幕、章节信息并合成 MP4。
- `narration.txt`：方便校对、后期改稿的旁白纯文本。
- `MiniQuant_30min.srt`：独立字幕；MP4 内也有可开关的中文字幕。
- `CHAPTERS.md`：章节时间码。

在项目根目录重建：

```bash
python video/build_video.py
```

依赖 `requirements.txt` 中的 `edge-tts`、Pillow，以及系统 `PATH` 中的 ffmpeg/ffprobe 和 `video/assets/NotoSansCJKsc-Regular.otf`。如果 ffmpeg/ffprobe 不在 `PATH`，可设置 `MINIQUANT_FFMPEG` 与 `MINIQUANT_FFPROBE`；需要代理时设置 `MINIQUANT_TTS_PROXY`。网络配音需能访问 TTS 服务；其他幻灯片和编码步骤本地运行。默认完成后清理中间文件；调试时设置 `MINIQUANT_KEEP_BUILD=1` 保留 `video/output`。字体许可见 `video/assets/OFL.txt`。

500 元章节讲的是**核验账户、限价委托、费用与复盘**，没有承诺 60% 收益，也不展示真实账户或推荐具体证券代码。券商官方入口及交易规则来源见 Notebook 第 14 章；视频涉及的费用和价格数字仅为教学算例。
