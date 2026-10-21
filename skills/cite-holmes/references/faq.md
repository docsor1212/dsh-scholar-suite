# FAQ (moved out of SKILL.md in v1.9 to keep the main guide short)

**Q: Is a `verified` citation guaranteed real?**
No. The mechanical layer catches machine-checkable fakes: nonexistent DOIs,
fabricated PMIDs (via E-utilities), fabricated arXiv IDs (via the official
arXiv API), dead links, duplicates, stitched DOI↔PMID pairs, wrong-paper
DOIs (title similarity), and retracted papers. A fabricated citation pointing
to a real, plausible page still relies on the semantic layer — never a
guarantee.

**Q: How are arXiv references checked?**
Same treatment as DOIs since v1.5: the official export.arxiv.org API returns
the registered title/year; similarity below 0.50 → `invalid` (fabricated or
wrong ID), 0.50–0.82 → `partial` (human review), above → consistent. An ID the
API has never heard of is `invalid`, not `unreachable`.

**Q: What do I do with `unreachable` references?**
Open them manually once — the report automatically attaches a Wayback Machine
archive link when one exists. If it matters and keeps failing, switch sources.

**Q: Did the PMID check fail because of my network?**
No. "不存在/编造" verdicts come from the official E-utilities API — that means the
PMID genuinely isn't in PubMed. Only "校验失败" wording means a network/API issue
(the reference is then treated as reachable and flagged).

**Q: Do I always need `--profile medical`?**
Use `--easy`: one flag auto-detects medical references, enables the medical
profile, and exports BibTeX + CSV automatically. For real clinical
conclusions, still prefer explicit `--profile medical`.

**Q: Can verified references go straight into my paper?**
Yes: `--export bibtex` exports only `verified` entries (with PMID / arXiv
eprint notes) and imports into Zotero/EndNote; `--export csv` is the full
audit ledger for advisors and editors; `--export auditjson` (v1.9) is the
machine-readable per-check working paper for institutional audit.

**Q: Which services does verification touch, and what if my network is slow or blocked?**
DOI.org (DOI metadata), NCBI E-utilities (PMID), export.arxiv.org (arXiv
metadata), archive.org (archived copies), api.crossref.org (retractions),
api.openalex.org (bibliographic confirmation), api.semanticscholar.org (third
source + title search, v1.9/v1.10). CN networks occasionally throttle several
of them. The verifier never stalls: transient failures retry once (429 honors
`Retry-After`), error notes tell you the cause with a fix (`--timeout 20` for
slow links), and a host-level circuit breaker skips a host after 2 consecutive
transport failures — with an honest note — instead of hanging the batch.
Since v1.10, references are verified in parallel (`--workers 4` by default —
roughly a quarter of the serial wall time), and when 3+ different hosts fail
at the transport layer in one run (restricted-egress signature) remaining
lookups are fast-skipped with a "全局网络降级" note and a proxy/retry
suggestion. Degraded checks are always labeled, never silently dropped.

**Q: Do I need API keys?**
No — everything runs keyless within public rate limits. OpenAlex has required
keys for *production* use since 2026-02 (free daily allowance; this skill
survives keyless but benefits from `--openalex-key` / `OPENALEX_API_KEY`).
Semantic Scholar keyless shares a rate pool; `--s2-key` / `S2_API_KEY` gets a
dedicated lane. Crossref asks heavy users to identify themselves — pass
`--mailto you@lab.edu` to join the polite pool.

**Q: MCP 模式是什么？agent 不装 skill 怎么用？**
v2.0.0 起仓库内置 `mcp/server.py`（FastMCP）：tools `verify_references`（机械验证）/
`explain_verdict`（判定解释）、resources（能力矩阵/版本史）、prompts（fact-check 工作流）。
推荐直跑：`uvx --from "git+https://github.com/docsor1212/cite-holmes#subdirectory=mcp" cite-holmes-mcp`；
或自行准备 FastMCP 环境后运行 `python mcp/server.py`。零密钥可用；可选 API key 经环境变量注入。

**Q: arXiv 论文有多个修订版怎么办？**
v2.0.0 自动备注：引用未指定版本而论文存在多个修订版 → 提示"引用未指定版本"；
引用指向旧版而存在更新版 → 提示最新版号（旧版可能含未修正内容）。同响应内取数，零额外请求。

**Q: 验证要访问哪些外部服务？国内网络慢怎么办？**
见上方服务清单——全部是官方学术注册库、全部 HTTPS。v1.12 起两件事让它在国内更可用：
① **持久磁盘缓存**默认开（7 天 TTL）：同一批引用复跑直接复用稳定判定、零外呼，
`--refresh-cache` 强制重验；② **`--proxy http://host:port`** 显式走代理（或设
`HTTPS_PROXY` 环境变量），配合网络降级模式，受限出口下也能一次跑完拿到诚实结论。

**Q: 判定结果会被缓存吗？撤稿状态更新了怎么办？**
缓存只存 verified/partial/invalid 三种稳定判定（TTL 默认 168 小时），
unreachable 永不入缓存（瞬态）；`--strict` 模式强制绕过缓存读（CI 诚实）。
撤稿状态这类可变信息以 TTL 为界——对时效敏感的批次用 `--refresh-cache` 强制重验。

**Q: Can I verify references straight from my reference manager?**
Yes, since v1.9: `--refs bibliography.bib` reads Zotero/EndNote/JabRef BibTeX
exports directly (entry types, nested braces, `\url{}` macros; DOI/PMID/arXiv
fields are picked up automatically).

## arXiv 条目 note 里出现「元数据 API 不稳，经官方着陆页标题比对确认」正常吗？

正常。arXiv 的 API 对批内多请求有反机器人窗口（偶发 406/403），与你的网络无关；
验证器已自动回退官方着陆页完成同等强度的标题比对，判定可信度不受影响。

## semantic 字段写什么？

模型逐条判定"来源是否真的支撑所引论断"后，写成结构化对象
`{"claim", "support", "quote", "note"}`（五值：supported / partial /
not_in_source / contradicted / unclear）。`not_in_source` 与 `contradicted`
会被机械验证器封顶为 `partial` 并转入人工复核区——来源存在不等于来源认同。
旧的字符串写法仍接受（仅注记）。

## Q: fast-judge 预筛会改我的判定吗？（v3.5.0）
不会。`--fast-judge-url` 外挂的小型分类器（任何 OpenAI 兼容 /v1 端点均可）只对"语义待定且无官方文本可升级"
的引用追加「倾向支持（供人工参考）」注记——永不产生/修改五态判定，永不标记人工
复核，默认关闭。校准曲线随仓库发布（阈值 0.95）。

## Q: GB/T 7714-2025 导出的数据来源是什么？（v3.6.0）
`--export gbt7714` 仅导出 verified 条目，且每条以**注册库登记的 CSL 元数据**
为准（作者按国标缩写惯例预格式化、期刊/年/卷期页来自 DOI.org/Crossref 登记），
不是你手填的字段。无注册元数据的电子资源按 [EB/OL] + 引用日期输出。

## Q: 国内网络直连核验总超时怎么办？（v3.6.0）
加 `--cn`：超时下限抬到 25 秒，且 DOI.org 三试全败时自动回源
api.crossref.org（独立主机，同构 CSL 元数据，报告注记会写明「经 Crossref
回源」）。仍不通时 `--proxy` / `HTTPS_PROXY` 继续兜底；`unreachable` 不等于
假引用，换网重跑后再下结论。

## Q: 能核验"正文里的引用"而不只是参考文献清单吗？（v3.7.0）
能。`--check-document paper.md --refs refs.json`：解析正文 in-text 标记
（[12]/[1-4]/(Author, Year)/doi.org 链接），把每处引用绑定到清单条目并计算
"引文句 ↔ 被引标题"锚词率——低于 0.34 标记为疑似错配引文（引 A 文却引了 B 句）。
锚词率低≠错引，是语义层人工复核候选；语义判断仍由 agent 负责。

## Q: 触发词误触发了怎么办？
触发词按语义匹配，可能被"查证一下"这类短句误触发。直接说明真实意图即可
（例如"我只要翻译这段"），误触发不产生任何副作用。想让某类请求**不**触发
引用核验：避免同时出现"研究/查证/引用"词与文献清单。

## Q: 中英混合引用（如中文声称+英文登记）会误判吗？
不会判 invalid。v3.0.0 起内置跨语言守卫：声称标题与登记标题跨语言（CJK vs
拉丁）时相似度不作编造依据，降 `partial` 转人工复核（与期刊名核查同款守卫）。
已知边界：跨语言混合引用的锚词率（上下文核验，v3.7.0）同样会偏低——属预期，
按"疑似错配候选"人工复核即可。

## Q: 报告里出现「克隆引用对」是什么意思？要删掉这两条吗？（v3.10.0）
不用急着删。克隆对 = 同一标题挂了多个不同 DOI（或同一 DOI 挂不同标题）——至少一个
标识有误，但也可能是预印本 DOI 与期刊版 DOI 并存的合法场景。看两条各自的判定：
verified 的是真的、invalid 的是假的；克隆注记只负责让这一对进入你的视野，判定以
元数据核验为准。

## Q: 清单画像的「标识符近邻簇」说我批量生成——我是正常引用怎么办？（v3.11.0）
画像旗标是人工抽查建议，不是判定。同一论文集/连续编号的合法引用确实会命中近邻簇。
按旗标把该簇几条逐条过一遍核验结果即可：全部 verified 就放心用；画像永远不改变
任何单条判定。

## Q: 「该预印本已登记正式发表」提示怎么处理？（v3.11.0）
你的 arXiv 引用有了期刊正式版。把引用条目的标识换成注记里的期刊版 DOI 后重跑，
确认新版 verified——投稿场景引用预印本常被审稿人挑，这个提示帮你在提交前完成
版本升级。

## Q: 跨语言桥接命中后我还需要做什么？（v3.10.0）
基本不用。桥接命中 = 中文原题与英文登记名经三级核验对上了，判定 verified 可信。
note 里附带了登记英文原题，扫一眼与你认知的论文一致即可（出版商字段理论上可被
刻意布置，一秒钟的人工确认是零成本的保险）。

## Q: 「投稿前终检」一键怎么跑？（v3.12.0）
`python scripts/verify_refs.py --refs research_refs.json --out report.md --preset submission`
——一键组合严格退出码（CI 可拦截）与 GB·T 7714/BibTeX/CSV 三导出。判定语义与
默认模式完全一致，只是把投稿场景的常用旗标打包。

## Q: 想看某一条引用为什么被判成这个结果？（v3.12.0）
跑批时加 `--explain 3`（换成条目号）——输出该条的判定语义、依据步骤、错误码翻译、
注记要点、导出完整度与建议动作，人话全文。
