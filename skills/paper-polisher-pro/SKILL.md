---
name: paper-polisher
version: 6.2.0
author: DoctorQ Lab
description: >-
  论文润色与论文AI率检测：句子级改写建议（哪几句像AI、各自怎么改进——只指位与策略，不代改）、
  去AI味自查、智能降重建议、术语标准化与同概念异写一致性检查、翻译腔检查、段落级人机归因、
  期刊口径预检（分学科语境）、学术写作规范自查（全半角/数字/缩写/单位）。
  不适用：PDF/文档翻译（用 doc-holmes）、查重（用知网等机构系统）、直接执行降AI改写（用 paper-rewriter）、
  100字以内文本（按铁律不出判定）。
  中英双语，100%本地运行，零上传，零凭证（AST 结构化零网络自证+随包单元测试套件）。
  v3：重校准多层级规则引擎（11核心层＋篇章/平滑度启发层）＋词频谱层＋长度路由融合＋可选监督层（本地Qwen3-0.6B ONNX，
  留出集AUROC 1.0）＋大模型指纹归因（GLM/DeepSeek/Qwen/Kimi/MiniMax/GPT/Claude/Gemini）
  ＋指纹保鲜流水线。基础引擎指标可由随包留出集评测复现；监督层列为作者侧留出集实测（模型不随包）。
tags: [ai-detection, deai, academic-writing, paraphrase, paper-polish]
metadata:
  displayName: 论文润色·智能降重｜学术表达优化
---

# Paper Polisher Pro v3（论文降AI润色一站式工具）

AI 痕迹检测（AI率）· 去AI化改写 · 术语标准化 · 翻译腔检查 · 质量报告 · AIGC 合规标识检查 · 段落级归因 · 期刊口径预检。
100% 本地运行，零上传，零凭证，纯标准库（可选 onnxruntime 增强层）。

> ## ⛔ 铁律
> 1. **只报可复现的数字**。所有指标必须来自 `eval/run_eval.py` 的留出集（test split）评测；旧版文档中"100% 检出率 / F1 98.3%"等无数据支撑的宣称已删除。
> 2. **短文本不出判定**。不足 100 字的文本输出 `risk=unknown`（学界教训：短文本误报失控）。
> 3. **指纹只归因、不进分数**（2026-08-15 实测：指纹注入检测层使人类误报翻倍）。
> 4. **校准与评测分离**。频谱/权重/阈值只用 calib 半构建，test 半永远留作最终评测（v3 开发中曾出现 0.9972 的假 AUROC，切分后真实值 0.9187）。

## TL;DR（30 秒上手）

- **是什么**：100% 本地的中文学术文本 AI 率自查+润色工具箱（可选监督层获得最佳精度；英文走纯规则仅供参考）。
- **三条命令**：`python3 scripts/pp.py quickstart`（零模型零文件一键体验）｜ `python3 scripts/pp.py detect draft.txt --format json` ｜ 逐句改写建议：`python3 scripts/pp.py fix draft.txt` ｜ 全流程自查报告：`python3 scripts/pp.py workflow draft.txt` ｜ 环境自检：`python3 scripts/pp.py doctor`（统一入口路由全部子命令）
- **实测数字**（留出集、绑定模型指纹 2631df3d388b）：老代 AUROC 0.9998 / 当打代 0.9400；人类误报@medium 2.3%。
- **边界**：<100 字按铁律 `risk=unknown` ｜ 降级档医学语域会系统性高估 ｜ 人机混写文档的文档级分数不可单独采信（段落归因才是可操作信号）｜ 仅供作者自查——不用于规避机构 AI 检测。
- **接下来看**：场景级怎么用见 `references/best-practices.md` ｜ 下方能力边界矩阵 ｜ 快速开始里有端到端示例 ｜ FAQ 分五组（判定边界→模式安装→输出解读→安全验证→工具工作流），按需跳转 ｜ 完整历史在 `CHANGELOG.md`。

### 30 秒任务路由

| 你想… | 跑 | 深文档 |
|---|---|---|
| 检查文稿 AI 率 | `pp.py detect draft.txt --format json` | 下方性能表+能力边界矩阵 |
| 看哪几句像 AI | `pp.py fix draft.txt` | `pp_fix_suggest.py --help` |
| 对比改稿前后 | `pp.py rewrite-check 原稿 改稿` | FAQ：改写建议 |
| 翻译 PDF 保持排版 | 非本工具——用 doc-holmes | 相关工具 |
| 查写作体例规范 | `pp.py norm draft.txt` | FAQ：规范自查 |
| 整个论文目录批量 | `ai_detector.py --batch DIR --csv s.csv --report r.html` | FAQ：批量 CSV |
| 验证零上传承诺 | `pp.py verify` + `pp.py test` | 安全与行为声明 |
| 期刊口径预检（分学科） | `ai_detector.py draft.txt --profile journal` | 期刊口径节 |
| 环境排障 | `pp.py doctor` / `pp.py freshness --status` | FAQ：模式与安装 |
| 一张可视化仪表盘看全部结果 | `pp.py html-report draft.workflow.json -o report.html` | 各脚本速查：pp_report_html.py |
| 跨多轮改稿追踪同一文稿 | `pp.py trend 轮次目录/ -o trend.html` | 各脚本速查：pp_trend.py |
| 不知道该用哪个命令 | `pp.py recommend "把这段的AI率降一降"` | `pp.py recommend --help` |

### 三条最重要的限制（完整细节见下方矩阵）

1. **降级档对医学语域系统性高估**——纯规则 @medium 档人类误报：医学约 59% vs 普通文本约 2%；医学文本只采信 @high 判定，或安装监督层。
2. **人机混写文档**——文档级 AUROC 0.52-0.54（均值稀释的原理性局限）；段落归因只作人工复核排序，绝不当自动判定用。
3. **数据覆盖范围**——术语库 2,344 条偏医学/学术（非医学文本标准率读低是覆盖面所致，非故障）；文体层按学术语域校准（口语/叙事输入仅供参考）。逐工具适用域见子功能矩阵。

## 学术诚信

本工具供**作者自查与改进自己的写作质量**（句式更清晰、术语一致、文风自然），不用于规避所在机构的 AIGC 检测，更不支持把 AI 生成内容伪装成人类写作。请遵循所在机构的 AI 使用与披露政策；随包的 `aigc_label_check.py` 用于帮助你**合规**满足标识与披露要求（如《人工智能生成合成内容标识办法》2025-09）——是帮你规范声明，不是帮你隐藏。每份 AI 痕迹报告（ai_detector.py / deai_gate.py）均带 `integrity_notice` 学术诚信提示。

## 实测性能（C-ReD + DetectRL-ZH 语料留出集 test 半，n=5,251）

> 语料口径说明（v4.8.0）：下表 v3.0 时代数字测于**全量**留出 test 半（n=5,251）；**随包**抽样语料为子集——其 test 半 n=1,304，可复现分语料数字：纯规则（PP_NO_SUP）老代 0.8985 / 当打代 0.7149，融合 0.9998 / 0.9400（`eval/results/v480_rules_*.json`、`v35ctl_*.json`；缓存键同时绑定模型指纹与引擎档位）。

| 指标 | v2.0 基线 | v3.0 规则+谱 | v3.1 +监督层 | **v3.4 监督层+编辑回归v2** |
|---|---|---|---|---|
| AUROC（test 半） | 0.7046 | 0.9187 | 0.9997 | **1.0** |
| TPR@FPR5% | 30.4% | 49.0% | 99.95% | **100%** |
| TPR@FPR1% | 16.7% | 24.9% | 99.88% | **100%** |
| 人类 FPR @校准p99 | 未测 | 未测 | 3.56% (30/844) | **0.71% (6/844)** |
| 改写/混合攻击 AUROC | 0.64 | 0.89 | 1.0（语料内） | **1.0** |
| 攻击"AI辅助"类召回 | — | — | 71.1% | **86.6%** |
| OOD 平实体/影评体召回 | — | — | 1/6 | **5/6 纯监督 · 6/6 本地融合** |

> **v4.4.0 指纹绑定重测**（现行监督模型 md5 `2631df3d388b`）：AUROC **0.9998**（test 半，n_base=927）、TPR@FPR1% 99.4%、人类误报@medium 2.3%——`eval/results/v35ctl_oldgen.json`。上表各列为版本时代记录（早期模型谱系；v4.4.0 之前模型二进制未做指纹绑定）。

**你跑的是哪一档？** 安装包默认运行 **v3.0 规则+词频谱引擎**（上表 0.9187 列，全量留出集实测；v4.4.0 起每份评测结果携带部署模型 md5 指纹 `model_fp`，现行绑定数字见 `eval/results/v35ctl_*.json`）；右侧两列需要可选的本地监督层模型。引擎会如实告知当前档位：监督层缺席/被关闭/语言门控跳过时，每份报告都带 `degraded_mode` / `degraded_notice` 字段与降级警示。

### 能力边界矩阵（信任任何检测器前先读）

| 场景 | 表现 |
|---|---|
| 中文学术文本 + 完整监督层 | 最佳档（留出集 AUROC 0.9998，人类误报@medium 2.3%——v4.4.0 指纹绑定） |
| 基础包（无模型，纯规则+谱） | AUROC 0.9187；**医学语域被系统性高估**（纯规则 @medium 档人类误报：医学文本约 59%、普通文本约 2%）→ 医学文本只采信 @high 档 |
| 英文文本 | 语言门控按设计跳过中文训练的监督层，纯规则英文骨架评分，结论仅供参考 |
| 人机混写文档 | 文档级 AUROC 0.52-0.54（平均原理性局限）；段落级 AUROC 0.69，**校准最优工作点 P=0.60、覆盖 63%**（`references/para_thresholds.json`）——低于自动判定可用线；`pp_workflow.py`/`paragraph_report.py` 排序仅供人工复核 |
| 编辑程度回归头 | ρ=0.540——仅作报告元数据，不参与判级 |
| **当打代模型（2026-09 采样）** | **AUROC 0.9400**（v4.4.0 指纹绑定重测，443 篇当打代评测集：9 家族 312 篇当打代 AI + 131 篇人类留出）vs 老代留出 0.9998——经核实的温和代际沟。此前的 0.6542 vs 0.9022 系测量伪象（陈旧分数缓存复放+模型谱系未验证）；两类故障自 v4.4.0 起结构性杜绝（每份结果 JSON 带 `model_fp`）
| 口语/叙事语域文本 | 文体层按学术语域校准，学术域外文体分仅供参考 |

### 子功能适用域矩阵（每个子工具的校准域）

| 子工具 | 校准域 | 域外行为 |
|---|---|---|
| ai_detector / deai_gate | 中文学术散文（留出集校准） | 降级档医学语域系统性高估；英文纯规则仅供参考；口语/叙事输入会带语域提示 |
| paragraph_report / pp_rewrite_check | 同上口径（逐段） | 局限相同；rewrite_check 在同一口径下对比两稿 |
| pp_fix_suggest | 中文 AI 写作模式库（学术语域） | 英文仅有连接词/节律等基础检查；findings 是文风观察而非检测结论 |
| term_check | 中文医学/学术术语库（2,344 条） | 非医学文本的标准率读数偏低——这是词库覆盖范围所致，不是错误；--auto-fix 保留语境 |
| translation_smell_check | 中文学术散文（翻译腔模式） | 英文式行文：输出如实列出盲区新词，不假装覆盖 |
| style_distance | 学术语域文体测量 | 学术域外文体分仅供参考（输出已注明） |
| style_norm | 机械体例核对——语域无关 | 设计上不评分；短样本上的统计类检查天然弱，输出已注明 |
| aigc_label_check | 文件元数据 / C2PA / 显式标识声明 | 不是内容检测器；核对标识合规性而非作者身份 |
| quality_report | 稿件可读性/质量多维度 | 非 AI 率度量；启发式为通用口径非期刊定制 |
| docx_text | .docx 文本抽取（保留段落） | 不是 PDF 转换器——PDF 被拒并给转存建议（零依赖无法保证中文 PDF 抽取） |
| batch（--batch） | .txt/.md/.docx，单文件 <5MB | >5MB 按设计跳过；加密/纯图片 docx 明确报错而非静默空输出 |

## 安全与行为声明

- **本地运行**：全部功能 100% 在本机执行，全代码库零网络调用（无任何网络客户端库、无外部网络工具调用）。结构化自证：`python3 scripts/pp_verify.py`（AST 级扫描，exit 0=零网络调用且全部脚本可编译）。旧式文本 grep `grep -rEin "urllib|requests|socket|http" scripts/` 会显示少量报告页脚 URL **字符串**——那是字符串常量里的数据不是网络代码；AST 自证能区分两者。
- **零上传零凭证**：不读取、不传输任何凭证、密钥或个人数据；仅有的两个环境变量 `PP_NO_SUP`（跳过监督层）与 `PP_LANG`（设为 en 时 pp.py 入口面切英文）均为本地行为开关。
- **无持久化**：不创建系统定时任务、不注册自启动、不修改系统配置；临时文件（层间 JSON/探针文本）用后即删。
- **无远程代码执行**：不加载远程模型/脚本；可选监督层模型由用户自行放置于本机路径。
- **数据边界**：仅读写用户指定文件、系统临时目录与自身包内数据目录（校准/保鲜产物）；报告只输出到用户指定位置。
- **学术诚信**：见上方专节——供作者自查与写作质量改进，按机构政策规范披露，不用于规避检测。

### 退出码契约（v5.8.0 起稳定）

| 退出码 | 含义 | 典型场景 |
|---|---|---|
| 0 | 成功 | 报告产出 · `verify` 零网络通过 · `test` 套件全绿 |
| 1 | 运行完成但未通过 | 引擎运行时异常（消息带恢复建议）· `test` 失败 · `verify` 漂移 · `freshness` 基线漂移 |
| 2 | 用法或输入错误 | 未知子命令 · 文件不存在 · 文本不足 100 字 · 输入 JSON 无法解析 |
| 3 | 环境不满足 | `pp_setup.py` 装模/校验失败——先跑 `pp.py doctor` |

编程接口同构：`pp_api` 对非法输入抛 `ValueError`（↔ 退出码 2）、对运行失败抛 `RuntimeError`（↔ 退出码 1），消息均带恢复建议。以上退出码是稳定性承诺——后续版本不会挪作他用。

## 反模式（每条带正确做法）

- **不要喂 <100 字** 的文本期待判定——`risk=unknown` 是设计行为（短文本误报不可控）。✅ 替代：提交 300 字以上；或用规范自查（`pp.py norm`）——它不出判定、短样本可用。
- **不要在降级档信任医学文本的分数**——纯规则对医学语域系统性高估（@medium 人类误报约 59%）。✅ 替代：装监督层；或只采信 `@high` 档并以段落归因为主。
- **不要把分数当知网/万方等价物**——阈值基于自有留出集校准。✅ 替代：把分数当相对分诊，结合期刊口径预检看分布视角。
- **不要替换或重量化模型文件**——实测概率漂移。✅ 替代：只走作者签发指纹的 `pp_setup.py`；暂无模型就留在如实披露的降级档。
- **不要用它规避机构 AI 检测**——每份报告都带诚信声明。✅ 替代：用 findings 改进写作本身，并按机构政策披露。
- **不要对 >5MB 文件跑批量**——按设计跳过。✅ 替代：先切分，或对导出的文本/docx 版本批量。
- **不要在输入未变时重复同一分析、或重跑已被拒绝的调用**——不产生新信息还烧时间。✅ 替代：先改变一个输入（文本/引擎档位/检查范围）或先解除阻塞（缺模型/编码问题）再重试。

## 快速开始

```bash
# 零模型零文件一键体验（v5.0.0）
python scripts/pp.py quickstart
# AI痕迹检测(AI率, 概率+分层证据+指纹归因)
python scripts/ai_detector.py draft.txt --format json
# 句子级改写建议（v5.0.0: 哪几句、因为什么、怎么改）
python scripts/pp_fix_suggest.py draft.txt --top 10
# 学术写作规范自查（v5.2.0: 全半角/数字/缩写/单位）
python scripts/pp_style_norm.py draft.txt
# Word 文档直读（.docx 进任意入口）
python scripts/ai_detector.py thesis.docx --format json
# 投稿前自查包（v5.3.0: 一条命令产出带日期自查目录）
# 期刊口径预检（v5.4.0: 分学科语境；--discipline 覆盖）
python scripts/ai_detector.py draft.txt --profile journal --format json
# 指纹保鲜状态（v5.4.0: 基线漂移检查+到期提醒）
python scripts/pp.py freshness --status
python scripts/pp_report_bundle.py thesis.docx --outdir ~/selfcheck
# 改写效果回归验证（v5.1.0: 原稿 vs 改稿引擎同源对比）
python scripts/pp_rewrite_check.py draft_original.txt draft_revised.txt
# 批量 CSV → 单文件 HTML 汇总报告（v5.1.0）
python scripts/pp_batch_report.py scores.csv -o report.html
# 单文档可视化仪表盘（v5.8.0: workflow/detect/fix/norm JSON → 一份 HTML）
python scripts/pp.py html-report draft.workflow.json -o report.html
# 多轮趋势仪表盘（v6.0.0: 多份 workflow JSON → 改稿轨迹）
python scripts/pp.py trend 轮次目录/ -o trend.html
# 自然语言命令路由（v5.8.0: 描述需求 → 推荐命令）
python scripts/pp.py recommend "把这段的AI率降一降"
# 期刊口径预检(疑似AIGC比例, 对标20-25%参考线, 附不可互换声明)
python scripts/ai_detector.py draft.txt --profile journal
# 段落级归因(人机协作定位)
python scripts/paragraph_report.py draft.txt --output report.html
# AIGC合规标识检查(docx/pdf/png/txt)
python scripts/aigc_label_check.py manuscript.docx figures/*.png
# 术语 / 翻译腔 / 四层门禁
python scripts/term_check.py draft.txt --auto-fix
python scripts/translation_smell_check.py draft.txt
python scripts/deai_gate.py draft.txt
# 环境自检
python scripts/pp_doctor.py
# 结构化零网络自证 + 随包单元测试（v5.0.0）
python scripts/pp_verify.py
python -m unittest discover -s tests -t .          # 或: python scripts/pp.py test
# 留出集回归(改引擎后必跑)
python eval/run_eval.py --split test --tag mytag
```

### 可选监督层启用（推荐，v3.2+）

```bash
pip install onnxruntime regex          # 两个可选依赖
# 放置作者发布的两个模型文件(原样, 勿替换):
#   ~/.cache/paper-polisher/qwen3-detector/model.int8.onnx
#   ~/.cache/paper-polisher/qwen3-detector/tokenizer.json
python scripts/layers_lm.py            # 自检: supervised_available: true
# 之后 ai_detector.py 自动融合(0.9*监督+0.1*规则); PP_NO_SUP=1 可临时关回纯规则
# ⚠️ 勿替换为其他导出/量化版本——实测概率漂移, 只用作者发布的原样文件
```

### Python API（编程接口）

```python
import sys; sys.path.insert(0, "<skill>/scripts")
from pp_api import detect_text, gate_text, doctor_summary
r = detect_text("中文学术文本，建议 300 字以上。" * 10, lang="zh")
print(r["overall_ai_score"], r["overall_risk"], r["degraded_mode"])
```

`detect_text` 进程内运行（不发子进程），返回结构与 CLI JSON 一致。所有函数返回 JSON 兼容 dict，非法输入抛异常。零网络、纯标准库。

### 一键装模

```bash
# 不清楚模型怎么拿？python3 scripts/pp_setup.py --guide（获取指南：渠道/放置路径/验证/降级语义）
python3 scripts/pp_setup.py --model <作者签发 model.onnx>   # 校验 md5 → 安装 → 推理金丝雀
python3 scripts/pp_setup.py --check                          # 查看当前安装状态
```

只接受作者签发指纹（`references/supervised_models.json`）；未知权重在动任何东西之前就被拒绝。绝不联网下载——模型永远以本地文件形式来自作者渠道。模型获取：作者签发文件暂不公开下载——在 GitHub 仓库（docsor1212/paper-polisher-pro）提 issue 联系作者获取现行签发版；在此期间包内以如实披露的降级档运行（功能完整，仅少精度增益）。

### 端到端工作流（一条命令）

```bash
python3 scripts/pp_workflow.py draft.txt      # 产出 draft.workflow.md + draft.workflow.json
```

一次跑完全部自查：AI 率检测（融合引擎）、段落级归因（hi/med/lo 分级）、四层门禁、术语保护、
翻译腔、文体、质量报告、AIGC 标识自查——产出单一可读 Markdown 报告+机器可读 JSON。
编程接口：`from pp_api import workflow`。

## 常见问题（FAQ，分组：判定→模式→输出→安全→工具）

### 判定与边界

**Q：为什么不足 100 字的文本不给风险判定？**
短文本误报在学界公认失控（几句话撑不起文风分布）。工具按铁律输出 `risk=unknown`，分数仅供参考；请提交 100 字以上（建议 300 字以上）。

**Q：为什么我的医学文本分数偏高？**
大概率在跑降级模式（未装可选监督层）。纯规则引擎对医学语域系统性高估（留出集实测 @medium 档误报：医学约 59%、普通约 2%）。医学文本请只采信 @high 档结论，或安装监督层（下一条）。

### 模式与安装

**Q：监督层模型怎么装？怎么确认生效？**
一条命令：`python3 scripts/pp_setup.py --model <作者签发的模型文件>`——校验签发指纹、安装、推理金丝雀自检（GREEN 即生效；报告 `degraded_mode=false` 同样可确认）。手动把两个文件放到 `~/.cache/paper-polisher/qwen3-detector/` 仍然有效，`python scripts/pp_doctor.py` 仍是全量自检。

**Q：报告里的 degraded_mode / degraded_notice 是什么？**
引擎档位披露：true=纯规则+词频谱降级档，原因写在 notice 里（模型未装 / PP_NO_SUP=1 / 英文语言门控）。档位对照见「能力边界矩阵」。
**Q：`degraded_notice` 应该怎么读？**
它说明完整档的哪个成分被跳过及原因：监督模型缺失、`PP_NO_SUP=1`、或英文语言门控。后果不同——降级纯规则档对医学语域系统性高估（见能力边界矩阵），而英文门控只意味着中文训练的监督层不适用。提示里写了原因，据此决定装模型、去掉开关、或把分数当参考。


**Q：这个 AI 率和知网/万方的结果能互换吗？**
不能。阈值基于自有留出集校准，与任何机构官方检测不可互换，仅供投稿前自查（journal 预检输出内含此声明）。

### 输出与解读

**Q：deai_gate 某层显示"解析失败"怎么办？**
该层自动走中性 50 分兜底，不影响其他层与总判定。通常为子进程超时或输入编码异常；重跑一次，复现则用 `pp_doctor.py` 自检。

**Q：编辑程度估计（edit_extent）是什么？**
监督层附加回归头，估计文本被 AI 改写的程度（0-1）。判别力有限（ρ=0.54），仅作报告元数据，不参与判级。

**Q：支持英文吗？**
部分支持：监督层仅中文语料训练，英文按设计跳过监督融合、走纯规则骨架评分，结论仅供参考（报告会明示）。

**Q：一段人写、一段 AI 写的混合文档怎么办？**
注意报告中的"混写预警"（`mixed_signal=true`）：文档级分数会被人类段落稀释或被 AI 段落顶起，均不可单独采信；请运行 `paragraph_report.py` 逐段归因，按段落处理。

**Q：真实期刊论文（人写的）为什么也可能判 medium/high？**
两个实测原因：分布差异（自有留出集与真实期刊 PDF→文本存在排版噪声与分布偏移）+ 语域校准。**段落归因才是可用信号**——用它定位可疑段供人工复核；文档级分数只是 triage 提示，不构成定罪。期刊口径预检（分布口径）提供第二视角，与主评分方向不一致属设计内。

**Q：指纹归因说是 GPT-4o，但我的文本来自别的模型？**
归因是启发式参考（top-n 候选，只归因不进分），存在误归因——已知案例：GLM 生成的文本可能被归为其他家族。家族提示请当弱证据；检测分数与段落归因才是实质输出。

**Q：AIGC 合规标识检查怎么用？**
`python scripts/aigc_label_check.py manuscript.docx figures/*.png`——检查元数据/C2PA 水印/显式声明三类（对标《标识办法》2025-09）。rc=0 有标识、rc=1 无标识，均属正常执行。

### 安全与验证

**Q：「100% 本地 / 零上传」我自己怎么验证？**
跑 `python3 scripts/pp_verify.py`——AST 级结构化扫描全部脚本：网络 import/调用与 curl/wget 式子进程命令一律命中，报告页脚的 URL 字符串被正确视为数据（旧 grep 建议区分不了这两者）。exit 0=零网络调用。行为级验证可跑随包测试套件（`python -m unittest discover -s tests -t .`），铁律与报告契约在你自己的机器上逐条过。

### 工具与工作流

**Q：规范自查会出分数或判定吗？**
不会。`pp_style_norm.py` 是机械体例核对（全半角、数字写法、缩写定义、单位格式），只列 findings 与具体改法；不产生任何分数，也不进 AI 率引擎。短文本判定铁律不适用（因为根本没有判定）——但极短样本上的统计类检查（数字/缩写）天然不可靠，输出中会注明。

**Q：多个批处理任务写同一个 CSV 安全吗？**
安全——v4.9.0 起 batch CSV 为原子写（先写临时文件再改名落位）。两个并发批任务指向同一 CSV 不会互相穿插或覆盖；文件内容始终是某一次完整跑批的结果。

**Q：改写建议会改我的文件吗？**
不会。`pp_fix_suggest.py`（`pp.py fix`）只定位带有可改进特征的句子，并按特征类型解释改进策略（例如：AI 套话换成具体判断、模板句拆分改主动）。它从不编辑你的文件；改写与否、怎么改由作者本人决定。`--demo` 可看内置双样例演示。

### 各脚本速查

| 脚本 | 作用 | 关键参数 | 输出 |
|---|---|---|---|
| ai_detector.py | AI 痕迹检测主引擎 | `--lang auto\|zh\|en` `--format json\|text\|summary` `--profile journal` | 综合分+段落明细+指纹归因（JSON 含 degraded_mode/integrity_notice） |
| pp_fix_suggest.py | 句子级改写建议（v5.0.0） | `--top N` `--json` `--demo` | 逐句特征+改写策略（只指位与策略，不代改） |
| pp_doctor.py | 环境自检 | `--json` | 数据/依赖/模型/功能探针，exit 0=绿 |
| docx_text.py | .docx → 文本抽取（v5.3.0） | `file` `--output` | 按段落保留文本；解压炸弹防护 |
| freshness_refresh.py | 月度保鲜流水线/状态自检（v5.4.0） | `--status` `--json` | 最近执行/最新评测/基线漂移/到期旗标 |
| pp_report_bundle.py | 投稿前自查包（v5.3.0） | `file` `--outdir` | 带日期目录：workflow+段落 HTML+建议+规范+清单 |
| pp_style_norm.py | 学术写作规范自查（v5.2.0） | `--json` `--checks a,b` | findings 带改法（全半角/数字/缩写/单位）；不评分 |
| pp_rewrite_check.py | 改写效果回归验证（v5.1.0） | `原稿 改稿` `--json` `--demo` | 分数/风险带迁移+段落 delta+特征清除/残留 |
| pp_batch_report.py | 批量 CSV → HTML 汇总（v5.1.0） | `csv_file` `-o out.html` | 总数/均分/分档卡片+直方图+逐文件表 |
| pp_report_html.py | 单文档可视化仪表盘（v5.8.0） | `json...` `-o out.html` `--title` | 自包含 HTML：仪表盘+直方图+段落/建议/规范/台账表；零外部资源 |
| pp_trend.py | 多轮趋势仪表盘（v6.0.0） | `workflow.json.../目录` `-o` | 分数轨迹 SVG+逐轮 delta 表（↓改善/↑回升标注）；降级轮标记 |
| pp_verify.py | 结构化零网络自证（v5.0.0） | `--json` | AST 级扫描判定，exit 0=零网络调用 |
| quality_report.py | 综合质量报告 | `--json` | 可读性/质量多维度指标 |
| deai_gate.py | 四层融合门禁 | `--json` | composite 分+判定带（<35 通过 / 35-55 复核 / ≥55 疑似） |
| paragraph_report.py | 段落级人机归因 | `--output report.html` | HTML 报告 |
| term_check.py | 术语标准化（加载 2,344 条） | `--auto-fix` `--output` | 标准率+修复文件 |
| translation_smell_check.py | 翻译腔筛查 | `--json` | 命中清单+盲区新词 |
| style_distance.py | 文体特征（人类相似分） | `--json` | style_score+verdict（学术域外仅供参考） |
| aigc_label_check.py | AIGC 合规标识 | 文件可为 docx/pdf/png/txt | 逐文件标识判定 |

## 架构与指纹保鲜（参考）

日常使用无需阅读本节内容。完整架构图、模块地图与指纹保鲜流水线说明
（校准切分策略、月度保鲜流程、模型代际覆盖）已迁移至
[`references/architecture.md`](references/architecture.md)——按需阅读。
场景级怎么用建议见 [`references/best-practices.md`](references/best-practices.md)。

## 触发词

`润色论文`降AI检测` `查AI率` `论文AI率` `降低AI率` `AIGC检测` `AIGC率` `GPT检测` `查AI写作` `论文润色` `改写论文` `去AI味` `AI论文检测` `学术写作助手` `AI写作检测` `去除AI痕迹` `人化AI文本` `毕业论文润色` `学位论文降重` `SCI论文编辑` `手稿润色` `AI写作评分` `去AI化` `AI改写检测` `文风对标顶刊` `这篇文章像不像AI`

## 相关工具

- **cn-med-oa** — 中文医学文献 OA 免费下载与引文元数据
- **pubmed-verifier** — 投稿前 PMID/DOI 参考文献核验
- **cite-holmes** — 深度调研 × AI 幻觉引用检测
- **academic-figures** — 一条命令出出版级科研图表
- **doc-holmes** — 保持原文排版的 PDF 精准翻译
- **paper-rewriter** — 同源降AI改写姊妹版（完整改写管线）

官网与在线文档：**docsor.cn**

如需批量核验参考文献的真实性，可用 pubmed-verifier；整理引文信息可用 cn-med-oa；深度调研并核对每条引用，可用 cite-holmes；需要改写执行可用 paper-rewriter。另外提醒：arXiv 自 2026-05 起对含幻觉引用的投稿有一年禁投处理，投稿前自查引用是必要的。

## 版本历史（摘要）

- **v6.2.0（2026-10-21 发布）**— 改写对照双栏 HTML（--html：逐段并排摘录+分数迁移着色）；workflow 仪表盘新增信号细节节。
- **v6.1.0（2026-10-20 发布）**— 报告解读器（pp.py explain）；错误词典扩展（AST/漂移/签发/门禁层）；quickstart 超时+稳定性契约入册；架构深水区外迁 references/architecture.md；新增 references/best-practices.md；样例按场景标注。
- **v6.0.0（2026-10-19 发布）**— 报告中枢与体验大版本：多轮趋势仪表盘（pp.py trend）；统一人话错误呈现（pp_errors.py 接入四入口）；pp.py 分组帮助+新手三步+英文入口面（PP_LANG=en）；批处理混沌压测套件。
- **v5.9.0（2026-10-18 发布）**— 上手闭环与批处理稳健版：监督模型获取指南（pp_setup --guide，doctor/check 接线）；批处理熔断器（--circuit 默认 5）+ 修复单个坏 docx 炸整批；词典外新造词探测（term_check --neologism，opt-in 未校准）；版本头卫生+发布闸；FAQ 分组导航。
- **v5.8.1（2026-10-17 发布）**— 术语库扩充实战对照别名；term_check 匹配改单遍最长优先（短标准词不再压制长别名）；计数声明更新至 2,335。
- **v5.8.0（2026-10-16 发布）**— 可视化报告版：pp_report_html.py 单文档 HTML 仪表盘（workflow/detect/fix/norm JSON → 一份自包含 HTML）；`pp.py recommend` 自然语言命令路由；退出码契约入档并锁定；三条关键限制前置到 TL;DR 旁；中文版本历史瘦身对齐英文（唯一完整历史=CHANGELOG.md）。
- **v5.7.1（2026-10-16 发布）**— 样例脱敏版：随包样例文档文本中一处内网链接（examples/outputs/detect_sample.json）经卫生闸检出后脱敏；代码与引擎零变更（打分与 5.7.0 逐位一致）。
- **v5.7.0（2026-10-16 发布）**— 发布完整性机制化改造版：版本化守卫/打包后断言/输出样例随包/命中句定位/文档去冗。
- **v5.6.0（2026-10-14 发布）**— LLM 腔自查版：三层词表+判例库对照（跨线移植注明来源）；引擎计分尝试并诚实回退（负结果入档）。
- 更早版本（v5.5.0 及以前）：见 `CHANGELOG.md`（唯一历史来源）。
