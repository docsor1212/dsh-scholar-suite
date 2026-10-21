---
name: cite-holmes
license: MIT
metadata:
  displayName: 引用核查·参考文献验真｜文献管理×AI幻觉检测
  clawdbot:
    emoji: "🔍"
    category: research
description: >-
  引用核查与参考文献验真工具：查文献真伪、核验论文引用、检测 AI 幻觉引用——
  编造 DOI、假 PMID、假 arXiv ID、撤稿论文、拼接伪造均为一级抓捕目标，
  未验证的引用绝不进入结论，投稿前参考文献一键终检（--preset submission）。
  文献发现模式：给主题、还你一份每条都经注册库核验的文献清单（--discover，GB/T/BibTeX 一键导出）。深度调研模式：像福尔摩斯一样调查自己的信源——先反问式校准范围（3-5 个关键问题）→
  制定研究计划 → 迭代多源检索（中英文、信源金字塔）→
  每条引用机器核实（DOI 经 DOI.org 解析、PMID 经 PubMed E-utilities 官方接口交叉验证、
  arXiv ID 经官方 API 核对标题与年份；五态判定：verified 可靠 / partial 部分 /
  unverified 未验 / unreachable 未达 / invalid 无效）。不可达条目自动查 Wayback
  存档供人工复核。报告头部自动输出 CiteScore 置信度评分（0-100，A–D 级）；正文结论
  按 🟢🟡🔴 三级置信度标注。未验证的引用绝不作为正文结论引用，仅列入人工复核区；
  专治 AI 幻觉引用，编造 DOI、假 arXiv ID、假 PMID 与死链均为一级抓捕目标。
  内置医学证据模式（Cochrane/BMJ/ClinicalTrials/ChiCTR/NMPA/CDC/NICE/万方 期刊层预设 + PMID 核实）
  与已验证文献导出（BibTeX + 审计 CSV）。触发词：深度研究、深度调研、深入调研、
  AI幻觉检测、AI 幻觉引用、引用核查、参考文献验真、PMID验证、信源验证、查证、
  这个说法是真的吗、综述一下、做个调研、查文献、文献综述、综述、文献检索、找文献、文献发现、参考文献格式、投稿前终检、
  fact check、verify citations、deep research。GB-T 7714 参考文献表一键导出。
  Skip when: 翻译、润色、改写、降重等不涉及引用真伪的请求（触发无副作用，说明真实意图即可）。

  Trigger on: 引用核查/参考文献验真/幻觉引用检测/事实核查/文献管理/查文献；Skip on 翻译/润色/改写；citation audit/reference verification/fact-checking
---

# cite-holmes：深度调研 × 引用核验（引用先核实，再落笔）

一句话：**一个问题进去，一份核实过的报告出来。**

与"搜索+总结"式工具的三点不同：

1. **先校准再干活**——先问准问题；最贵的浪费是研究了一个错的问题。
2. **结论带证据分级**——🟢 两个独立来源一致 / 🟡 单一权威 / 🔴 来源冲突。
3. **每条引用都被核验**——机械层（可达性/域名权威/字段完整/去重）+ 语义层
   （来源是否真支撑论断）。未核实的引用绝不冒充真实。

## ⛔ 铁律（零例外）

1. **绝不编造**：引用必须来自本会话真实抓取过的页面；宁可重新搜索，不凭记忆写 URL。
2. **绝不假装**：未核验的标 `unverified`；抓取失败标 `unreachable`（≠ 不存在，转人工）。
3. **不隐藏分歧**：来源冲突时摆出双方证据，标 🔴。
4. **预算内搜索**：QUICK ≤6 次、FULL ≤15 次；超预算就诚实说明缺口，不硬凑结论。
5. **先校准后检索**（FULL）：范围/时间跨度/受众/输出格式必须先锁定。

## Step 0：模式选择

| 模式 | 适合 | 校准 | 预算 | 产出 |
|---|---|---|---|---|
| **QUICK** | 单点事实核查（"这是真的吗"/"X 是什么时候发布的"） | 跳过 | ≤6 | 简报 |
| **FULL** | 开放研究（"X 的现状"/"A vs B"/综述） | 必须 | ≤15 | 全报告 |

一个可验证事实能回答 → QUICK；需要综合权衡 → FULL；"快速看看"→ QUICK，
"要彻底"→ FULL；拿不准 → FULL。投稿前参考文献终检无需选档：`--preset submission`
一键（严格退出码+GB·T/BibTeX/CSV 三导出）。

## 五阶段工作流

### 1. CALIBRATE 校准（仅 FULL）

一次性提出 3–5 个高杠杆问题：范围、时间跨度、受众与深度、输出格式、决策背景。
用户已给过的不重复问；用户说"你看着办"→ 按合理默认走并声明假设。三条规则：
问题按依赖排序；**每问自带推荐答案且措辞让"是"即接受推荐**；能自己查证的事实
绝不变成问题——决策永远留给用户。

### 2. PLAN 规划

给出简短计划：3–7 个子问题、信源优先级（官方一手 > 权威媒体 > 社区/博客仅作线索）、预算。

### 3. SEARCH 检索（迭代，非一次过）

先读 `references/search-strategies.md`。每轮只打一个子问题；用发现的术语进化
检索式；跨中英文主题两边都搜；抓取最有价值的 2–5 个来源全文（绝不靠搜索摘要
下结论）；关键数字回到原页核对后再引用。

### 4. VERIFY 验证（本 skill 的灵魂）

每条引用登记进 `research_refs.json`（schema 见 `references/report-template.md`），然后跑：

```bash
python scripts/verify_refs.py --refs research_refs.json --out verify_report.md
# 手里有 Zotero/EndNote 导出的 .bib？直接喂进来：
python scripts/verify_refs.py --refs bibliography.bib --out report.md
# 大批量前先环境自检（默认零外呼，加 --net 探测各注册库）：
python scripts/verify_refs.py --doctor --net
```

五态判定：`verified` / `partial` / `unreachable`（需人工复核）/ `invalid` /
`unverified`。每个标识符（`url`/`doi`/`pmid`/`arxiv`）都与官方登记库交叉核对，
编造的 ID 直接判 `invalid`，绝不会被可达性检查漏成 `unreachable`。每份报告
头部输出 **BLUF 双读者报头** + **CiteScore**（0-100 + A-D 级）+ **投稿前结论**。

#### 机械层（脚本负责）

| 能力 | 边界 |
|---|---|
| 注册库一致性（标题/年份/期刊/作者） | 12 类机器可读错误码；阈值 0.50/0.82 |
| 克隆引用对检测 | 同题不同 DOI / 同 DOI 不同题——成对线索，绝不改判定 |
| 跨语言标题桥接 | 六文字系统族（拉丁/西里尔/希腊/汉字/假名/谚文）；命中升 `verified`，未命中维持 `partial`；语言差异绝不作为编造依据；六族之外（阿拉伯/希伯来/泰文等）暂不触发守卫——请附英文或罗马化题名 |
| 清单画像 | 整批伪造统计指纹——人工抽查建议，绝不改判定 |
| 预印本升级提示 | arXiv 已正式发表者自动注记期刊版 DOI |
| 撤稿检测 | Crossref 在线，或 `--retraction-cache` 离线秒查；通告分档：撤稿/部分撤稿/撤回→转人工，编辑关注通告（EoC）→`verified` 封顶 `partial`，更正/勘误→仅提示；检查失败显式标记，绝不冒充「干净」 |
| 无标识符引用（Vancouver） | PubMed 题名反查→`verified` 并回填 PMID 锚；2 实词起查；传输失败标记 `network_error`，绝不计入「查无」 |
| GB/T 7714 中文医学引用 | `[1]` 方括号编号与题名先行变体可解析；著录内联 `PMID:`/`DOI:` 自动提取送官方核验；无标识符时「期刊+年+卷(期):页」在 PubMed 唯一定位即升 `verified`（官方引文定位器语义，语言无关——中文声称题名对英文登记题名绝不作为编造依据） |
| 中文医学注册库 | 万方/CNKI/中华期刊平台按期刊层识别 |
| 非 MEDLINE 期刊（无标识符） | OpenAlex 找锚→DOI 解析验锚：聚合库只当索引，判定证据全部来自 DOI 注册库（锚定 DOI 照走撤稿检测） |
| 撤稿检测规模化 | `tools/build_retraction_cache.py` 从官方日更 dump 一键构建本地 Retraction Watch 索引——`--retraction-cache` 离线秒查且带通告分档 |
| 文献发现 | `--discover "主题"` 检索 PubMed + OpenAlex 并逐条出生即核验——还你一份验过的文献清单，GB/T 7714 / BibTeX 一键导出；`--discover-since 2020` 按年份过滤；`--demo` 用内置 8 条样例（3 处预埋伪造）零门槛体验判定全流程 |
| EB/OL 类引用（指南/说明书） | [EB/OL] 著录中的 URL 自动提取（无更强标识符时）并走可达性+来源层级判据——药品说明书、指南、共识不再裸 unverified |
| 文献清单完整性 | `--check-document` 审计孤儿文献（列了没引——写作规范提示，绝不改判定）与引用覆盖率；单文件模式：只传文档路径，参考文献节自动提取 |
| Wayback 存档对照 | 死链自动附存档链 |
| 导出完整度评分 | 注册库 CSL 可回填多少导出字段 |
| 速度 | 20 条混合清单 `--workers 4`（默认）约 18s、热缓存约 7s、串行约 47s——实测表见 `references/verification-details.md` |
| 弱网 | `--proxy` / `--cn` / `--preflight`；3+ 注册库传输失败自动降级模式 |

完整语义：`references/verification-details.md`。

#### 语义层（模型负责）

把每条带引文的论断分解为原子三元组（主语-关系-宾语）
逐条对照来源；判定结构化登记（`"semantic": {"claim", "support", "quote",
"note"}`）成为可审计工作底稿；`not_in_source` / `contradicted` 把机械判定封顶
为 `partial`——来源存在 ≠ 来源认同。

#### 任务 → 开关

| 任务 | 开关 |
|---|---|
| 医学主题 | `--easy` · `--profile medical` |
| 分享/存档 | `--format html` |
| 导出 | `--export bibtex,gbt7714,ris,csv,auditjson` |
| CI | `--strict` · `--offline` |
| 礼貌限速 | `--mailto you@lab.edu` |
| API key | `--openalex-key` / `--s2-key` / `--ncbi-key` |
| 弱网/代理 | `--proxy` · `--cn` · `--preflight` · `--timeout` |
| 磁盘缓存 | `--no-cache` / `--refresh-cache` / `--cache-ttl` |
| 环境自检 | `--doctor`（加 `--net`） |
| 投稿前终检 | `--preset submission` |
| 解释单条判定 | `--explain N` |
| 投稿前对抗自查 | `--grill report.json`（审稿人预演问题单） |
| 外置判定 | `--judge-url` / `--nli-url` / `--fast-judge-url`（只记注记绝不翻案） |
| MCP 工具形态 | `mcp/server.py`——`verify_references` / `explain_verdict` / `check_document` |

### 5. SYNTHESIZE 综合

按 `references/report-template.md` 骨架输出：执行摘要先行；关键结论带置信度
分级 + 引用编号；引用表带五态列；`unverified/unreachable` 只进"人工复核"区；
以**收尾台账**收束：回到计划的问题清单逐条标记 answered / partially /
unresolved（附预算台账：已用轮次/剩余），再列研究缺口、来源分歧、后续追问。

## Files

| 文件 | 何时 |
|---|---|
| `scripts/verify_refs.py` | VERIFY 机械核验（纯标准库，跨平台） |
| `references/GLOSSARY.md` | 正词表（五态/信号/错误码统一用词，带 Avoid 列表） |
| `references/out-of-scope.md` | 非目标档案 + 诚实边界，每条带理由 |
| `references/security.md` | 安全与行为声明全文 |
| `docs/adr/` | 架构决策记录（公开层） |
| `mcp/server.py` | 可选 MCP 服务（同一引擎） |
| `references/search-strategies.md` | SEARCH 前读 |
| `references/report-template.md` | SYNTHESIZE 骨架；refs schema |
| `references/verification-details.md` | 全部开关语义与阈值 |
| `references/anti-patterns.md` | 误用清单（14 条，每条带正确做法） |
| `references/faq.md` | 常见问题 |
| `references/medical-mode.md` | 医学/临床前读 |
| `examples/demo_refs.json` | 8 条引用，3 处预埋伪造 |

## ⚠️ 常见误用

见 `references/anti-patterns.md`（每条带替代做法）。最重要的两条：别把
`verified` 当"内容正确"（那是语义层的事）；别把 `unreachable` 当"假引用"
（先 `--cn`/`--proxy` 重跑再说）。

## 安全、诚实边界与 FAQ

- 安全与行为声明：单次运行；仅 HTTPS 官方学术注册库（doi.org / api.crossref.org /
  eutils.ncbi.nlm.nih.gov / export.arxiv.org / api.openalex.org /
  api.semanticscholar.org / archive.org / pubmed.ncbi.nlm.nih.gov）；零遥测。
  全文：`references/security.md`
- 诚实边界与明确非目标：`references/out-of-scope.md`
- 常见问题：`references/faq.md`

## 30 秒上手

```bash
# 1. 引用清单 JSON（title/url/source/year）——或 Zotero 的 .bib
# 2. 核验：
python scripts/verify_refs.py --refs refs.json --out report.md
# 3. 打开 report.md——头部就是 CiteScore + 投稿前结论。
# 论文投稿？加 --export bibtex。医学？加 --profile medical。
# 已核验过一轮？加 --grill report.json 出审稿人预演问题单。
```

## 无网络环境兜底

没有联网工具时：诚实说明只能做"用户供给材料+机械核验"模式，绝不假装检索过。
