---
name: pubmed-verifier
license: MIT-0
version: 5.4.0
metadata:
  displayName: PMID引用验证·参考文献核查｜AI幻觉检测
description: "参考文献验真与AI幻觉引用检测：批量核验PMID/DOI/arXiv引用、验证文献真伪与论文引用错配——AI幻觉引用最常见的形态就是「真PMID指向别的论文」。五态判定系统，自动解析引用上下文并交叉比对，不匹配时推荐正确PMID。撤稿检测全覆盖（注册库撤稿标注直标，封顶为部分匹配并提示人工复核）、arXiv 预印本核验、纯文本参考文献表直读（论文草稿的文献列表粘贴即逐条核验：行内PMID/DOI/arXiv精确路由；中文文献条目经 OpenAlex 标题检索判定，无编号ID也能核验；无编号的英文条目按 PubMed 标题检索并如实标注）、参考文献生成与格式化导出（GB/T 7714、Vancouver、APA、AMA 四种格式，先验证后排版，只排已验真的条目）、OpenAlex DOI兜底（DataCite/Zenodo 等非Crossref注册的DOI可判定）。四数据源（NCBI + Europe PMC自动兜底 + Crossref + OpenAlex）、NCBI API key提速、429退避、断路器；网络故障诚实标注「未判定」，绝不误报「不存在」。零依赖，纯本地运行。触发词：验证PMID、核查文献、引用验证、文献验证、验证DOI、撤稿检查、PMID检查、参考文献格式化、文献排版、中文文献验证、文献核对、引用核查、verify PMIDs、check citations、validate references、citation audit、batch verify references、AI幻觉检测、参考文献核查、BibTeX审计。\n\n仅验证不生成：需要润色改写、翻译降重、或凭空生成参考文献时不要用本工具（它只核验真伪，拒绝编造任何引用）。\n\nTrigger on：PMID验证/引用验证/参考文献核查/DOI验证/arXiv核验/AI幻觉检测/参考文献格式/引用格式/文献排版/中文文献核查/论文引用核查；citation verification/bibliography audit/citation formatting/reference formatting/Chinese reference check。"
---

# PubMed 文献引用批量验证工具 v5.4.0

检测 AI 编造的虚假文献引用。不只检查 PMID 是否存在——还能判断 PMID 是否指向正确的论文。零依赖，纯本地运行。

## 触发词

用户请求中出现以下任一意图即触发本技能：**验证PMID / 检查引用 / 核查文献 /
引用验证 / 文献验证 / 验证DOI / DOI核查 / 撤稿检查 / 参考文献格式化 /
文献排版 / 中文文献验证 / 批量核验参考文献**；以及英文 verify PMIDs、
check citations、validate references、citation audit、AI hallucination
detection、citation formatting。粘贴的参考文献列表、`.bib`/`.ris` 文件、
Word `.docx` 文档、PowerPoint `.pptx` 课件、导出的 `.html` 页面、claims
CSV 都是直接输入。

三个速查映射：「帮我验证这几个 PMID 31018962、22213727」→ `--pmids`；
「检查我论文的参考文献」+粘贴列表 → `--parse-text`（或直接管道 `--stdin`——
**粘贴列表本身就是输入，无需明确说出「验证」二字**）；「这篇撤稿了该引什么」→
撤稿条目加 `--suggest`。

**按模式触发（不只按关键词）**：①请求中出现引用标识符（PMID/DOI/arXiv ID）
+「查/核/验」类语义即触发——即使没说「验证」（"这几个 PMID 是真的吗？"）；
②粘贴或附上参考文献表即触发，无论措辞（"帮我看下参考文献"）——列表本身就是
输入（`--parse-text`/`--stdin`）；③**不应单独触发**：「帮我写论文/综述」（先调
研走 cite-holmes，成稿后文献表交本技能终审）；④无验证意图的纯排版不单独触发
（`--format-references` 先验证后排版是设计内行为）。

**组合场景**（参数可叠加，各司一职）：投稿终验 `--source 草稿 --quick`；
粘贴即验 `pbpaste | ... --stdin --suggest`；知识库审计+证据包 `--source 库
--report-bundle 目录`；文献库往返 `--bibliography refs.bib --export-bibtex
out.bib`；跨月差分 `--source 库 --diff 旧audit.json`；纯中文文献表
`--parse-text refs-cn.txt`。

**何时必须用 `--claims-file`**：普通扫描验证的是存在性+上下文可解析的元数据；
凡判定结果要用于决策（投稿前的 mismatch/partial），必须提供预期标题+作者
走 `--claims-file` 才有决定性五态判定。**工具分工**：cite-holmes 面向带机器
验证引用的深度调研，本技能是核验/格式化环节——需求混合时先调研、文献最终
审计交给本技能。

## 从 Python 调用

整个工具就是一个纯标准库模块，无需安装即可导入（完整参考：
`references/python_api.md`）：

```python
import sys
sys.path.insert(0, "/path/to/pubmed-verifier/scripts")
import verify_pmids as vp

info = vp.fetch_summaries(["31018962"], batch_size=1)["31018962"]
cross = vp.cross_check_citation(
    {"claimed_title": "Classification criteria for autoinflammatory recurrent fevers",
     "claimed_year": "2019"},
    {"title": info["title"], "authors": info["authors"],
     "journal": info["journal"], "pubdate": info["pubdate"]})
print(cross["verdict"], round(cross["confidence"], 2))
```

凡是引用真实性重要的场景都可以调起：

- 「验证/核对这些 PMID / 这份参考文献表」（投稿或发布前）
- 审核 AI 生成内容中的引用（编造或错配的参考文献）
- 抽查系统综述的文献目录
- 「PMID 12345678 真的是这篇论文吗？」——存疑即验
- 知识库中 PMID/DOI 引用的批量质检
- 自动调用时机：用户提出"验证/核对/审计"引用、PMID、DOI、参考文献时即触发本技能——首轮无需任何参数；用户提供预期标题时加 `--claims-file`。

**触发优先级与工具选择**——用户明确要求「验证/核对/审计引用、文献、PMID、DOI」时优先调用本技能。cite-holmes 面向带机器验证引用的深度调研；当需求混合调研与核验时，先做调研、再用本工具做最终文献审计。

## 运行前必知

四条限制覆盖绝大多数意外——每条都有单参数规避动作：

| 限制 | 规避 |
|---|---|
| 引用上下文解析是启发式（奇特排版可能切错） | 需要精确元数据用 `--claims-file` |
| 无 PMID/DOI 标记的中文参考文献解析弱 | `--parse-text`（OpenAlex 中文检索腿）或提供 ID |
| 网络故障如实报「未判定」，绝不静默报「不存在」 | 先 `--check-net`，网络可达后重试 |
| 撤稿/DOI 状态以缓存时刻为准（30 天） | 投稿终验加 `--no-cache` |

以下章节都是这四条的展开。

**文档地图**——要找的内容在哪个文件，无需翻找：

| 想看什么 | 去哪 |
|---|---|
| 完整版本历史 | `references/CHANGELOG.md`（主文档只留近期要点） |
| 全量 FAQ、场景实操与调优参数 | `references/usage_guide.md` |
| 「场景 → 一条命令」旗标速查（38 个旗标按任务域分组） | `references/flags.md` |
| Python API 参考 / 可运行示例 | `references/python_api.md` / `references/api_examples.md` |
| 按任务找该读哪个文件 | `references/INDEX.md` |

## 五态判定系统

| 判定 | 含义 |
|------|------|
| ✅ 正确 | PMID 存在，且与引用的论文匹配（标题+作者/期刊） |
| ⚠️ 不匹配 | PMID 存在，但指向**不同的**论文（AI 幻觉最常见的情况！） |
| 🔶 部分匹配 | 部分元数据匹配（如作者+期刊匹配但标题不同） |
| ❌ 无效 | PubMed 中不存在此 PMID |
| ❓ 待确认 | 缺少足够的引用元数据无法交叉比对；或数据源不可达（网络故障诚实标注，绝不误报为「不存在」） |

**为什么「存在性检查」不够**：相当大一部分编造引用用的是**真实存在的 PMID**，只是指向同年份/同期刊/同领域的另一篇论文——我们自己的一次审计里，5 条「有效」PMID 就有 4 条属于此类。二元存在性检查对它们全部漏检。

## 快速开始

```bash
# 投稿终验一条命令（v5.0.0）：新鲜注册库（--no-cache）+ Crossref DOI 交叉
# 核验（--verify-doi）+ 正确 PMID 推荐（--suggest），无需记参数组合
python3 scripts/verify_pmids.py --source /path/to/draft --quick --output report.html

# 环境自检（v5.3.0）：版本/缓存/密钥/代理配置——加 --check-net 连通五库
python3 scripts/verify_pmids.py --doctor

# 粘贴即验证（v5.0.0）：复制来的参考文献表直接管道进来，无需落盘
pbpaste | python3 scripts/verify_pmids.py --stdin
git show HEAD:refs.txt | python3 scripts/verify_pmids.py --stdin

# 扫描项目目录中所有 PMID（自动解析引用上下文）
python3 scripts/verify_pmids.py --source /path/to/project --output report.html

# Word 文档与导出的 HTML 页面直接可读（v4.8.0）：.docx 段落/表格与 .html
# 正文内存中提取——script/style 内容忽略，链接指向（href）保留
python3 scripts/verify_pmids.py --source 指南审阅.docx --output report.html

# PowerPoint 课件同样直接可读（v4.9.0）：全部幻灯片按序+演讲者备注
# （患教会课件直接审计）
python3 scripts/verify_pmids.py --source 患教课件.pptx --output report.html

# 验证指定 PMID
python3 scripts/verify_pmids.py --pmids 31018962,22213727

# 不匹配演示：PMID 34078778 实际是一篇牙科材料论文，下面这条 JIA 引用
# 不会与它匹配——预期输出 ⚠️ 不匹配
python3 scripts/verify_pmids.py --claims '[{"pmid":"34078778","title":"JIA pathogenesis","authors":["Zaripova"],"journal":"Pediatr Rheumatol Online J","year":"2021"}]' --output report.html

# CSV 引用清单 + 不匹配时自动推荐正确 PMID
python3 scripts/verify_pmids.py --claims-file claims.csv --suggest --output report.html

# DOI 交叉验证 + 审计工作底稿 + BibTeX + 完整流程
python3 scripts/verify_pmids.py --source /path/to/files --verify-doi --suggest --output report.html --export-audit audit.json --export-bibtex refs.bib

# 验证 arXiv ID（预印本）——支持混合审计
python3 scripts/verify_pmids.py --arxivs "2401.12345,cs/0211004" --no-cache

# 预检：五个数据源当前是否可达？
python3 scripts/verify_pmids.py --check-net

# 直接审计 BibTeX / RIS 参考文献文件（PMID > DOI > arXiv 路由）
python3 scripts/verify_pmids.py --bibliography refs.bib --no-cache
python3 scripts/verify_pmids.py --bibliography refs.ris --no-cache --export-ris verified.ris

# 直接验证 DOI（无需 PMID）+ 差分审计 + 并行解析
python3 scripts/verify_pmids.py --dois "10.1038/nature12968,10.4012/dmj.2020-408" --workers 4 --export-audit audit.json --export-csv table.csv
python3 scripts/verify_pmids.py --source /path/to/project --diff audit.json --output report.html

# 核验从论文草稿复制的纯文本参考文献表（行内 PMID/DOI/arXiv 精确路由，
# 无编号条目按标题检索并如实标注 resolved_by=title_search）
python3 scripts/verify_pmids.py --parse-text references.txt --no-cache

# 流式输出给 agent 管道（v5.3.0）：每行一条引用
python3 scripts/verify_pmids.py --parse-text refs.txt --jsonl results.jsonl

# 将验证通过的条目渲染为可直接粘贴的参考文献表
# （--citation-style: gbt | gbty | vancouver | apa | ama，默认 gbt = GB/T 7714-2015）
python3 scripts/verify_pmids.py --parse-text references.txt --format-references refs_gbt.txt --citation-style gbt

# 机构用户推荐：NCBI API key + 联系邮箱（限速更宽松）
python3 scripts/verify_pmids.py --source . --verify-doi --ncbi-api-key $NCBI_API_KEY --mailto you@lab.org
```

## FAQ 与常见错误

**十件不该做的事**（每条在下方或「反模式」节有详解）：

| # | 不要 | 应该 |
|---|------|------|
| 1 | 把 `--pmids` 的存在性输出当「已验证」 | 配 `--claims-file` 提供标题做真核验 |
| 2 | claims 不填 `title` | 务必带标题——没有它判定封顶 partial |
| 3 | 发表当天就信缓存结果 | 投稿终验加 `--no-cache` |
| 4 | 把自动抽取 DOI 的「查无」读成「伪造」 | OpenAlex 二查后双库查无才升级；先经 doi.org / arxiv.org 人工复核 |
| 5 | 把 CSV 单元格开头的 `'` 当数据损坏 | 那是公式注入防护符——导入后再去除 |
| 6 | 把 READY 行当质量评分 | 它只表示「已运行的检查都没发现问题」 |
| 7 | `--source` 和 `--pmids` 同时传 | 传了 `--pmids` 时 `--source` 整个被忽略 |
| 8 | 千条清单直接上 `--verify-doi`/`--suggest` | 先跑批量，再只对标记子集深验 |
| 9 | 期待 CJK↔拉丁作者名比对 | 跨语言名诚实跳过（`author_check: skipped`） |
| 10 | 合规场景不出审计底稿 | `--export-audit` 生成可复算工作底稿 |

**几百条 PMID 批量验证很慢，怎么提速？**
纯元数据验证按 50 条/批、批间 0.4 秒（带 `--ncbi-api-key` 为 0.12 秒）查询；缓存后重跑约 5 秒。`--verify-doi` 每条引用多一次 Crossref 调用、`--suggest` 每条不匹配多一次搜索——大批量粗筛时先关掉，只对标记出的子集开。

**什么时候必须用 `--claims-file` 而不是扫描？**
上下文解析是启发式的（v3.3.0 已防护常见缩写，极端格式仍可能切错）。需要精确核验、或要在 claims 里提供 DOI（拼接检出需要 `doi` 字段）时，请用结构化 JSON/CSV。

**引用正文是中文——scan 几乎解析不出？**
GB/T 7714 格式（……标题[J]. 刊名， 年… PMID: xxx）自 v3.9.0 起可解析——标题/刊名与拉丁注册库的比对跨语言跳过，判定基于年份/DOI 证据。无 PMID 标记的自由中文散文仍解析受限——请用 `--claims-file` 拿与语言无关的完整判定。

**国内网络慢或不稳定？**
先跑 `python3 scripts/verify_pmids.py --check-net` 看五个数据源当前是否可达（各 5 秒），再按建议配置代理或切换数据源。
原生支持标准 `HTTPS_PROXY`/`HTTP_PROXY` 环境变量；可加大 `--timeout`；NCBI 不可达时 `--meta-source europepmc` 走 Europe PMC 兜底（每条 `meta_source` 标注实际来源）；缓存 30 天内复用。

**❓ 待确认 vs ❌ 无效 有什么区别？**
`待确认`（退出码 2）=「源不可达，没验成」——稍后重试；`无效`（退出码 1）=「已核实不存在」。网络故障绝不会被报成「不存在」，也不写缓存。

**报告里 RETRACTED 是什么意思？**
注册库自身把该论文的出版物类型标为 "Retracted Publication"（v2.7.0 起每条引用都查，无需 DOI、无需参数），和/或 Crossref 登记了撤稿记录。判定封顶为部分匹配并附人工复核提示——引用它会传播已被撤回的结论。撤稿**声明本身**不会被误标；处于 **Expression of Concern**（编辑关注声明，非撤稿）的论文也不标记。撤稿状态以缓存时刻为准——投稿前终验请加 `--no-cache`。

**报了不匹配，但标题看起来挺像？**
看 `details` 里哪个字段不符；阈值从严是有意的。用 `--claims-file` 提供完整引用信息可获得精确判定。

**能直接审计 .bib / .ris 文件吗？**
能——`--bibliography refs.bib`（BibTeX）与 `--bibliography refs.ris`（RIS/Zotero/EndNote/Mendeley）都按 PMID > DOI > arXiv 路由并交叉比对声称元数据；`--lint-claims` 可先离线体检。双向闭环：`--export-bibtex` 与 `--export-ris` 的输出修改后可直接喂回。

**claims 文件好像丢了行 / 判定偏弱？**
先离线体检：`python3 scripts/verify_pmids.py --lint-claims claims.csv` 会报出不可用行、ID 形状错误、未知列名（如把 title 拼成 titel）、缺标题与 DOI 前缀问题——零网络，有错误退出码 1。

**DOI 能带声称元数据做完整判定吗？**
能——v3.4.0 起只有 `doi` 的 claims 行（带 `title`，可选 `authors`/`journal`/`year`）与 PMID claims 走同一交叉比对：对登记元数据给出 correct / mismatch / partial。不带 claims 的 DOI 行保持「待确认」（仅存在性）。

**arXiv 引用为什么从 correct 掉到了 partial？**
你的 claims 行同时给了 `arxiv_id` 和 `doi`，而这个 DOI 与该 arXiv 条目登记的版本记录 DOI 不一致——要么笔误，要么是另一篇论文的 DOI。注册 DOI 就在 `details` 里；改正 claim 或去掉 `doi` 格即可。

## 输出长什么样

终端文本报告（判定汇总行，然后逐条证据）：

```
Readiness: NOT SUBMISSION-READY — 1 invalid, 1 mismatched
Results: 1/3 correct, 1 mismatch, 1 invalid, 0 partial, 0 unknown
============================================================

✅ PMID 31018962 (claims) [correct]
   Actual: Classification criteria for autoinflammatory recurrent fevers
   Claimed: Classification criteria for autoinflammatory recurrent fevers
   Evidence: title ✓ · author ✓ · journal ✓ · year ✓

⚠️ PMID 34078778 (claims) [mismatch]
   Actual: Effect of CAD/CAM materials on the marginal fit of crowds
   Claimed: JIA pathogenesis and treatment
   → Suggest: PMID 34425842 - Juvenile idiopathic arthritis: from aetio...
   Evidence: title ✗ · author ✗ · journal ✗ · year —

❌ PMID 99999999 (cli) [invalid]
   Error: PMID not found in API response
```

`--output report.json` 携带同样的判定外加每条引用的完整证据链
（`evidence.title_match / author_match / journal_match / year_match`、
`fields` 三态、`meta_source` 标注应答的注册库、标题检索/OpenAlex 腿命中
时标注 `resolved_by`）与含投稿就绪判定的 `stats` 块。
`--format-references` 输出即用型文献表（形态见 references/CHANGELOG.md 的 v4.0.0 条目）。

### 实操场景

- **「审稿人问我的引用是怎么核验的。」** —— 带 `--export-audit audit.json
  --verify-doi` 跑一次审计：JSON 工作底稿含工具身份、版本、脱敏后的完整
  调用命令与逐条证据链，审稿人或编辑可复放。随稿件一并提交即可。
- **「查学位论文的参考文献。」** —— 把文献表复制进纯文本文件（每行一
  条，或保留 `[1]` 编号），跑 `--parse-text refs.txt`：行内 PMID/DOI 精确
  路由；英文条目走 PubMed 标题检索；中文条目走 OpenAlex 中文检索腿。
  最后 `--format-references refs_clean.txt --citation-style gbt` 得到修正
  且格式统一的文献表。
- **「系统综述（PRISMA）文献库筛查。」** —— 全表核验一次并导出审计底
  稿作基线；每次重投前跑 `--diff audit.json`：新撤稿、降级、新增以增量
  报告呈现，只需复查变化的部分。

## 反模式——这些用法是错的

每条：错误用法 → 为什么错 → 正确做法。

1. **把 `--pmids` 的输出当成"已验证"**——那只确认了存在性。
   → 错："这 5 个 PMID 都存在，所以引用没问题。"
   → 对：存在性核对只是第一步；要核内容请配 `--claims-file` 提供标题（READY 行会显式标注）。
2. **claims 不填 `title`**——只有作者/期刊/年份永远到不了 `correct`，最高只能 `partial`。→ 请务必提供标题。
3. **发表当天就信缓存结果**——新上线论文可能被更早的运行缓存成"查无"，撤稿状态也以缓存时刻为准。→ 投稿终验加 `--no-cache`。
4. **以为"查无"就一定是编造**——Crossref 查无会先经 OpenAlex 二次核查（DataCite/Zenodo/中文注册库 DOI 在那里），「两个注册库都查无」才是新门槛；自动抽取的 DOI 双库查无仍只是*疑似*。被 arXiv 官方移除的论文同样查无。→ 先到 doi.org / arxiv.org 人工复核再下结论。
5. **把 CSV 单元格开头的 `'` 当数据错误**——那是公式注入防护符，不是数据损坏。→ 导入后再去除。
6. **把 READY 行当质量评分**——它只表示"已运行的检查都没发现问题"，不表示"这篇论文水平高"。

## 边界与声明（集中列出）

本工具**不能**做的事，集中在一处：

- **拼接/失配信号只报告不一致，不裁判谁对**——声称与登记库不符时，由人阅读证据行下结论。
- **跨语言作者名跳过而非判负**——CJK↔拉丁作者名不做比对（`author_check: skipped`），判定只依赖标题/期刊/年份。
- **上下文解析是启发式的**——v3.3.0 已防止常见缩写（U.S.、e.g.、vs.、St.、Vol.、No.）截断标题，但极端格式仍可能切错；需要精确元数据请用 `--claims-file`。
- **DataCite/仓储 DOI 不在 Crossref——OpenAlex 兜底覆盖**（v4.1.0）：
  Crossref 报 404 会先经 OpenAlex 二次核查；仅当两个注册库都查无才适用
  404 语义（`--dois`/claims=无效，自动提取=疑似）。经 OpenAlex 解析的条
  目带 `meta_source: openalex`。
- **arXiv 官方移除的论文同样"查无"**——invalid 判定的 details 里带此说明。
- **撤稿状态以缓存时刻为准**——投稿终验请加 `--no-cache`。
- **单字母首字母缩写永不匹配**——"Smith J" 对 "Smith John" 不计为不符。
- **unknown ≠ invalid**——数据源不可达 = 退出码 2 + 待确认；网络故障绝不报"查无"、绝不写缓存。
- **arXiv 限速是刻意的**——官方 API 要求调用间隔 ≥3 秒；大批量 arXiv 校验天然较慢（stderr 有进度与剩余时间估计）。登记了正式版 DOI 的条目会为挂接 PMID 额外发一次 Europe PMC 查询。
- **DOI claims 的比对基准**——DOI 解析到 PubMed 记录用 PubMed 记录比对，否则用 Crossref 登记信息（Crossref 的作者字段较稀疏，作者层更常判「—」）；DOI 行不带 title 停在「待确认」而非部分匹配；用户显式提供（--dois 或 claims）的 DOI 在 Crossref 查无计为无效。
- **标题复核腿只确认、不指控**（v4.8.0）——启发式单字段声称被降级为待确认后，会用 PubMed 标题检索复核：同一 PMID 得到印证则升级为「正确」（标注 `inline_title_search`，弱于用户直供 ID 的证据）；命中**不同** PMID 的同名记录则给出「疑似错挂 PMID」信号，判定仍保持待确认；中文标题跳过此腿（走 OpenAlex 中文检索腿）。该腿绝不制造不匹配指控。
- **Word/HTML/PowerPoint 直接可读，PDF 不行**（v4.8.0/v4.9.0）——`.docx` 段落/表格、`.pptx` 幻灯片+演讲者备注、`.html` 正文在内存中提取（script/style 忽略、链接 href 保留）；损坏的 office 文件回落为原始字节读取（扫不到引用，不报错）。扫描版 PDF/图片不是文本，请先导出为文本或 HTML。
- **输入规模与并发**（v5.1.0/v5.2.0）——`--max-entries` 护栏（默认 2000）统计去重后实际工作量并告警+给出分批建议；DOI 验证默认 4 并发；PMID 每批 50 条（有 API key 间隔更短）；arXiv 官方限速 3 秒/次（1000 个 arXiv ID 至少 50 分钟）；引用计数（`cited_by_count`）仅 Europe PMC/OpenAlex 路径提供，NCBI 路如实缺省。`--max-entries N` 调阈值、`0` 关闭告警。
- **参数优先级显式化**（v5.1.0）——`--pmids` 与 `--source` 同传时 `--pmids` 生效，被忽略的一方会在 stderr 明确告示，绝不静默丢弃。
- **撤稿原因**（v5.3.0）——被撤条目带 `retraction_reason`（注册库有摘要取摘要，否则取声明标题）与 `retraction_reason_doi`（声明出处）。多数声明仅为「Retraction Note: 原题」形态——**原题绝不冒充原因**，此时如实引用声明本身供查证。
- **判定阶梯单调性**（v4.9.0）——扫描来源中「唯一缺口=作者未声称」的条目（标题匹配、期刊/年份未声称）判定为「正确」并标注 `route: existence_title_match`——比纯存在性确认更强的证据不会判出更低的结果。凡作者/期刊/年份**声称了但不同**仍保持「部分匹配」（真疑点）；`--claims-file`/CLI 显式输入永远走完整判定不升级。

## claims.csv 参考格式

```csv
pmid,title,authors,journal,year,doi,arxiv_id
31018962,Candidate criteria for diagnosis of familial...,Gattorno,Ann Rheum Dis,2019,10.1136/annrheumdis-2019-215048,
,Attention Is All You Need,Vaswani,NeurIPS,2017,,1706.03762
```

- 有 `pmid` 走 PubMed 管线；纯 arXiv 引用只填 `arxiv_id`（+title 可核验真伪）；纯 DOI 引用只填 `doi`（v3.4.0 起走完整判定阶梯）。
- PMID 行的 `doi` 列用于拼接检出；`arxiv_id` 列走 arXiv 官方 API。

## 国内使用指北（集中一页）

所有网络相关事项集中于此（各项同时在使用处就地说明）：

- **预检**：`--check-net` 逐一探测四个注册库+arXiv（各 5 秒），给出每主机可达性与下一步建议。
- **注册库选择**：默认 `--meta-source auto` 已对 NCBI 失败批次自动重试 Europe PMC（免 key、一般可达）；`--meta-source europepmc` 可强制。
- **代理**：标准 `HTTPS_PROXY`/`HTTP_PROXY` 环境变量对所有请求生效；自动化直连场景应 `unset`（残留死代理会把注册库伪装成不可达）。
- **包体镜像**：魔搭提供技能包下载（modelscope.cn/skills/Docsor/pubmed-verifier）——但验证运行时仍需访问学术注册库，镜像只消除安装摩擦。
- **诚实失败**：无论网络如何，失败一律判「待确认」（退出码 2），绝不误报「不存在」，且不写缓存。

## 最佳实践与调优

- **大批量提速**——申请 NCBI API key（https://ncbiinsights.ncbi.nlm.nih.gov/api-keys/ ）：每批 50 条、间隔 0.12 秒（无 key 为 0.4 秒）；缓存命中重跑只要几秒。
- **DOI 并行**——`--workers`（默认 4，上限 8）作用于 Crossref 解析与 Europe PMC 挂接；arXiv 按官方礼仪保持串行（间隔 ≥3 秒）。
- **两段式工作流**——先跑仅元数据的批量核查（不带 `--verify-doi` 与 `--suggest`），再只对标记子集深验；每个深验标志每条引用多一次 API 调用。
- **文献库闭环**——`--export-bibtex` / `--export-ris` 输出已验证条目；修改后用 `--bibliography refs.bib` / `refs.ris` 直接复验（PMID 会重新挂接完整记录）。
- **claims 优先于上下文解析**——只要知道期望标题就用 `--claims-file`：它启用完整判定阶梯与 DOI/arXiv 配对检查。先用离线体检：`python3 scripts/verify_pmids.py --lint-claims claims.csv` 无网络即可报出 ID 形状错误、缺标题、未知列与重复键。
- **网络不稳**——调大 `--timeout`；原生支持 HTTPS_PROXY/HTTP_PROXY；NCBI 不可达自动切 Europe PMC 兜底（`meta_source` 显示实际应答方）。
- **缓存策略**——结果缓存 30 天、负条目 3 天；`--cache-days` 可调；投稿终验用 `--no-cache`。
- **规模预期**——仅元数据吞吐受 API 限制（带 key 约每 1000 条 1~2 分钟）；DOI 解析每条多一次 Crossref 调用。一个刻意取舍：验证器是单文件纯标准库——把 `scripts/verify_pmids.py` 拷到任何有 Python 3.9+ 的机器即可运行，无需 pip/venv（这是不做模块拆分的原因）。

## 近期版本（完整历史见 references/CHANGELOG.md）

- **v5.4.0** —— `--help` 按任务域分组（38 个旗标五组）；`references/flags.md` 场景速查；`--sort cited` 引用数排序。
- **v5.3.0** —— 撤稿原因蒸馏（摘要优先、原题绝不冒充）；`--doctor` 环境自检；`--jsonl` 流式输出；HTML 证据内联展开。
- **v5.2.0** —— `--max-entries` 量化输入护栏；`cited_by_count` 引用计数；触发节按模式重写+组合场景表。
- **v5.1.0** —— PowerPoint `.pptx` 课件直接可读；判定阶梯单调性（仅缺作者声称的「部分匹配」升级「正确」并如实标注）。
- **v5.0.0** —— `--stdin` 粘贴即验证 + `--quick` 投稿终验一键（--no-cache+--verify-doi+--suggest 组合）+ FAQ 高频失败处理扩充。
- **v4.9.0** —— PowerPoint `.pptx` 课件直接可读（幻灯片按序+演讲者备注）；判定阶梯单调性：仅缺作者声称的「部分匹配」升级「正确」并如实标注证据路线。
- **v4.8.0** —— Word `.docx` 与 `.html` 直接可读；标题复核腿（PubMed [Title] 短语检索：同 PMID 印证升级「正确」、异记录给错挂信号、绝不制造不匹配）。
- **v4.7.0 及更早** —— 全部条目见 [references/CHANGELOG.md](references/CHANGELOG.md)（逐字保留）。

## 安全与行为声明

- 单次运行 CLI：扫描→验证→写报告→退出。无守护进程、无后台任务、运行时零下载零安装（纯标准库，零依赖）。
- 网络访问仅限以下官方学术注册表，且全部 HTTPS：`eutils.ncbi.nlm.nih.gov`、`www.ebi.ac.uk`（Europe PMC）、`api.crossref.org`、`api.openalex.org`、`export.arxiv.org`——不访问任何其他主机；无遥测、无统计、无数据收集——出站载荷仅限你要求验证的 PMID/DOI/标题。
- 你的文件与报告留在本机。写入仅限你指定的报告路径与 `~/.cache/pubmed-verifier/` 下的 SQLite 缓存（`--no-cache` 可禁用）。
- 可选环境变量 `NCBI_API_KEY` / `PUBMED_VERIFIER_MAILTO` 仅用于你自己的 API 请求认证/署名，绝不发往其他任何地方。
- 无操作系统集成：无子进程、无系统服务、无权限变更、无计划任务。

## 工作原理

### 1. 提取 PMID + 解析引用上下文

扫描文件中的 PMID 模式（`PMID: 12345678`、PubMed URL 等），自动解析周围引用文本提取声称的元数据：作者、标题、期刊、年份。支持 `.html`、`.md`、`.txt`、`.json`、`.htm`。注意：上下文解析是启发式的（v3.3.0 已防止 "U.S." 之类常见缩写截断标题，极端格式仍可能切错）；需要精确核验时请用 `--claims-file` 显式提供结构化引用信息。

### 2. 获取 PubMed 元数据（带缓存）

PubMed esummary 批量查询（每次 50 条），SQLite 缓存 30 天（`--cache-days` 可调），3 次重试。NCBI 不可达时同批次自动切 Europe PMC 兜底。

### 3. 交叉比对：声称 vs 实际

双重模糊匹配：词级 Jaccard 重叠 ≥ 50%（容忍词序变化、缩写展开）或 SequenceMatcher ≥ 90%；作者姓氏命中；期刊包含匹配或 NLM 缩写等价；年份精确匹配。

### 4. DOI↔PMID 交叉（claims 含 doi 时自动启用）

声称的 DOI 与该 PMID 登记 DOI 不符 = 拼接伪造信号（封顶为部分匹配）。

### 5. Crossref DOI 验证（可选，`--verify-doi`）

对有 DOI 的文章，经 Crossref API 解析登记记录，并把登记标题与 PubMed 记录比对（JSON 中 `doi_title_match`），同时检测**撤稿论文**（判定封顶为部分匹配）。`doi_verified: false` 且备注 "crossref unreachable" 表示 Crossref 不可达（网络事实），**不构成判定**。

### 6. 自动推荐（可选，`--suggest`）

对不匹配的引用，用声称元数据搜索 PubMed，推荐正确 PMID（前 3 个候选）。推荐搜索始终走 NCBI（`--meta-source europepmc` 只影响元数据获取）。

| 格式 | 参数 | 用途 |
|------|------|------|
| HTML | `--output report.html` | 可视化审查，声称 vs 实际对比 |
| JSON | `--output report.json` | 程序化处理（含每条 `meta_source` 来源标注） |
| 文本 | 默认 | 终端快速查看 |

## 性能

以一次 225 条 PMID 审计（5 个 esummary 批次）实测：纯元数据验证在数秒级完成，缓存后重跑约 5 秒。批间等待 0.4 秒（带 `--ncbi-api-key` 为 0.12 秒）。可选项按条计次：`--verify-doi` 每条引用多一次 Crossref 调用（约 0.5–1 秒），`--suggest` 每条不匹配多一次 PubMed 搜索。

## 与 cite-holmes 怎么选

- **pubmed-verifier（本工具）**——轻量快速批量验证：手里有一批 PMID/DOI，要确认真实且引用正确。
- **cite-holmes**——深度调研：对整篇文档的全部引用做多数据库交叉核查，输出置信度分级报告。

两者共享同一套五态判定哲学，可搭配使用。

## 适用场景

- 系统性综述/荟萃分析文献验证
- AI 生成内容的文献真实性审核
- 论文投稿前引用自检
- 医学知识库/教材引用质量控制
- 药物警戒文献核查

## 相关工具

每个工具解决文献工作中的一个环节，按需取用。

- **cn-med-oa** — 中文医学文献 OA 免费下载与引用元数据
- **cite-holmes** — 深度调研，每条引用机器验证
- **paper-polisher-pro** — 学术润色、术语核查与期刊预检
- **academic-figures** — 一条命令出出版级科研配图
- **doc-holmes** — 保持排版的 PDF 精准翻译（内测中）

常见顺序：找文献（cn-med-oa）→ 验引用（本工具或 cite-holmes）→ 学术润色（paper-polisher-pro）→ 配图（academic-figures）→ 翻译 PDF（doc-holmes）——按手头环节取用。

## 文件说明

| 文件 | 用途 |
|------|------|
| `scripts/verify_pmids.py` | 主验证脚本（v5.4.0，纯标准库） |
| `references/api_examples.md` | PubMed / Europe PMC / Crossref / arXiv API 说明 |
| `references/usage_guide.md` | 完整 FAQ、场景演练、调优手册 |
| `references/flags.md` | 旗标速查——场景到一条命令，38 个旗标按域分组 |
| `references/INDEX.md` | 任务→文档 30 秒路由表 |
| `references/CHANGELOG.md` | 完整版本历史（主文档仅保留近期要点） |
| `references/python_api.md` | Python 编程集成（稳定接口+示例） |
| `examples/refs.sample.ris` | RIS 示例文献库（Zotero/EndNote/Mendeley） |
| `examples/refs_list.sample.txt` | `--parse-text` 样例输入（编号参考文献表） |
| `examples/claims.sample.csv` | `--claims-file` 参考格式（含 DOI-only 行） |
| `examples/refs.sample.bib` | `--bibliography` 示例文献库（DOI/PMID/arXiv 路由） |
| `tests/` | 离线测试矩阵 + 真网验收脚本（仅仓库，不随包分发） |

## 许可证

MIT-0 — 自由使用、修改和分发，无需署名。
