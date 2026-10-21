# Verification details (v1.10)

> **30 秒入口**：何时读我——想弄懂某个判定为什么是 partial/invalid、或要配 --judge-url/--nli-url 等进阶旗标时。最短路径：先看「五态判定」表 + `--explain N`（CLI 直接人话解释单条，v3.12）再决定要不要深读本篇。回 [INDEX.md](INDEX.md)。


Full semantics of every check `verify_refs.py` performs. SKILL.md keeps the
short version; this file is the complete reference.

## Cross-check rules by identifier

- **DOI** (v1.4+): DOI.org content negotiation returns the registered CSL
  metadata. Title similarity < 0.50 → `invalid` ("real DOI, wrong paper" —
  fabricated or mis-cited); 0.50–0.82 → `partial` (human review); ≥ 0.82 →
  consistent. Year difference ≥ 2 adds a warning note. A DOI the registry has
  never heard of (404) → `invalid`, never `unreachable`.
- **PMID**: NCBI E-utilities esummary. PubMed's own web pages return 2xx even
  for nonexistent PMIDs, so only the API actually catches fabrications.
- **DOI ↔ PMID cross-check** (v1.6): when both keys are present, the PMID's
  registered DOI must match the claimed DOI — a mismatch is `invalid`
  ("stitched fake": each key real, pointing at different papers).
- **Journal name** (v1.6): claimed source vs DOI-registered container-title.
  NLM-style abbreviations are treated as equivalent (word-initial sequential
  match, stop-words skipped); cross-language names are not comparable and are
  skipped. A real mismatch downgrades to `partial` (journals do rename).
- **Author names** (v1.7): claimed surnames matched against the CSL author
  list; any hit counts (spelling variants tolerated); single-letter initials
  never substring-match (APA "Torvalds, L." would otherwise match any "G.").
  CJK-vs-Latin names are skipped (not comparable). A full miss downgrades to
  `partial`.
- **arXiv** (v1.5): official export.arxiv.org API (≥3 s/request politeness
  pause). Unknown ID or API error element → `invalid`. Same 0.50/0.82
  similarity thresholds as DOI.
- **Retraction** (v1.8): Crossref REST API `updated-by[]` (Retraction Watch
  data, updated daily). Any `type == "retraction"` → capped at `partial` +
  human-review flag. Check failures are silently skipped — never penalize a
  reference for the checker's network.
- **OpenAlex bibliographic check** (v1.8, v1.9 keys): for references without
  DOI/PMID/arXiv, title search against OpenAlex. Best of full/prefix title
  similarity ≥ 0.82 → "confirmed exists"; 0.60–0.82 → "near match, review";
  below → honest "no obvious match, not evidence of fabrication" (coverage
  lag). HTTP 403 → actionable hint to configure `--openalex-key` /
  `OPENALEX_API_KEY` (OpenAlex requires API keys for production use since
  2026-02; keyless calls still work within a free allowance).
- **Semantic Scholar third source** (v1.9): when a DOI reference's DOI.org
  metadata could not be fetched (network restricted / transient 5xx), the DOI
  is re-queried at the S2 Graph API. Confirmation (title similarity ≥ 0.82)
  adds a second-source note and enables the anti-bot rescue below. S2 record
  quality is uneven (real papers registered as journal ToC pages have been
  observed), so **S2 never speaks negatively**: mismatches and misses are
  silent. Optional `--s2-key` / `S2_API_KEY` (keyless shares a rate pool;
  client paces ≥1.5 s between S2 calls).
- **Semantic Scholar title search** (v1.10): references carrying neither
  DOI/PMID nor arXiv get one extra positive signal — the title is queried at
  the S2 `/paper/search` endpoint (best-of full/prefix similarity ≥ 0.82 →
  "confirmed exists"). Same discipline as above: confirmation only, misses
  and mismatches silent (titles < 18 chars are skipped — search noise).
  Per S2 API docs, hyphenated query terms return no results, so hyphens are
  normalized to spaces before encoding.

## Parallel verification & degraded-network mode (v1.10)

- `--workers N` (default 4): references are independent, so up to N of them
  are verified concurrently (offline mode and `--workers 1` stay serial).
  Progress lines print in completion order; the report/JSON keep strict
  index order. Shared state (host circuit breaker, arXiv/S2 rate pacing) is
  lock-protected, so politeness guarantees hold under parallelism. The
  per-reference `--interval` pacing applies to the serial path; the parallel
  path throttles through concurrency itself.
- **Degraded-network mode**: when ≥ 3 *different* hosts fail at the transport
  layer within one run (a restricted-egress signature), remaining lookups to
  not-yet-confirmed hosts are skipped immediately with an honest
  "global network degraded" note plus a one-line suggestion (configure a
  proxy / switch networks and rerun), and the run prints a summary advice
  line. Site-level HTTP responses (403/429 rate limits, anti-bot) never
  count toward degradation — the egress path itself is proven working when
  any server answers. Once degraded, transport retries stop (fast-fail).
  The per-host v1.6 circuit breaker still applies independently.
- **Intra-run cache**: a reference whose DOI/URL/PMID/arXiv matches an
  already-verified one reuses that verdict (note says so) instead of
  re-hitting the network. `mark_duplicates` still applies afterwards — the
  cache never promotes a duplicate.

## Rescue rules (anti-bot, anti-flaky-network)

- Landing page 403/429 but registry metadata confirmed (DOI.org, arXiv, or
  S2): existence is proven, so the reference is NOT `unreachable` — it is
  judged on tier/fields like any 200 page (trusted tier + complete fields →
  `verified`; any partial adjustment or missing field → `partial`). This
  prevents "metadata confirmed + 403 blog page" from slipping through.
- arXiv resolver 404 with unconfirmed metadata → `invalid` (official registry
  says no such ID).
- Wayback Machine (v1.5): every `unreachable` link is checked against
  archive.org; an archived copy adds a dated comparison link for human review.

## Rate limiting & resilience

- Host circuit breaker (v1.6): 2 consecutive *transport* failures
  (timeout/DNS/refused) → remaining calls to that host are skipped for the
  batch with an honest note. HTTP responses (403/404/429…) never trip it.
  Retries within one logical call count once.
- Transient failures retry once; error notes carry the cause (timeout / DNS /
  refused) and the fix (`--timeout 20` for slow links).
- 429 with `Retry-After` (v1.9): the DOI metadata check waits the requested
  duration (capped at 5 s) before its retry.
- `--mailto you@lab.edu` (v1.9): appended to Crossref requests — enters the
  Crossref polite pool with more generous rate limits. Recommended for CI and
  institutional batches. arXiv politeness (3 s/request) and S2 pacing (1.5 s
  keyless) are always on — both are global under parallel verification.
- OpenAlex hints (v1.10): 403 and 429 both explain the key situation —
  OpenAlex has required API keys for production use since 2026-02 (keyless:
  100 credits/day); configure `--openalex-key` / `OPENALEX_API_KEY`.

## Exports

- `--export bibtex`: verified-only bibliography, Zotero/EndNote-ready (PMID /
  arXiv eprint noted). Field values sanitized (brace/newline stripped).
- `--export csv`: full audit ledger (all refs, all fields, formula-injection
  neutralized, utf-8-sig for Excel).
- `--export auditjson` (v1.9): machine-readable working paper — per reference,
  which checks ran and what they found (`checks_catalog` documents every check
  type), plus a generation timestamp. Purpose: transparency and institutional
  audit. The July 2026 arXiv survey of citation checkers (arXiv 2607.22693)
  found none of five evaluated tools reliable enough to run unsupervised and
  calls for "transparent multi-source detection systems" — the audit trail is
  this skill's answer: a human can re-trace every mechanical verdict.

## Persistent disk cache (v1.12)

`--cache` is on by default. Stable verdicts (`verified` / `partial` /
`invalid`) are stored in a local SQLite database
(`~/.cache/cite-holmes/cache.sqlite3`, standard library) keyed by every
judgment-relevant input: identifier, claimed title/year/source/authors, tier,
verifier version, and profile — the same DOI with a different claimed title is
a different cache key, because title-similarity verdicts depend on the claim.
TTL is 168 h (`--cache-ttl`); `unreachable` is never cached (transient);
`--offline` results are never cached; `--strict` bypasses cache reads so CI
always runs live; `--refresh-cache` bypasses reads but still writes;
`--no-cache` disables the store entirely. Cache hits append an explicit
"磁盘缓存命中" note with the age, so an audited report always shows when a
verdict came from the network and when from the local store. What this buys:
re-running or extending a bibliography no longer re-travels the ocean —
the repeat-run pain flagged in every evaluation's Trust score.

## Proxy support (v1.12)

`--proxy http://host:port` (scheme optional) routes all verification traffic
through the given proxy; without the flag, urllib's standard
`HTTP_PROXY`/`HTTPS_PROXY` environment handling applies. Combined with the
v1.10 degraded-network mode, restricted-egress environments get one fast,
honest pass instead of minutes of stalls.

## BibTeX input (v1.9)

`--refs bibliography.bib` is auto-detected (extension `.bib`, or content
starting with `@` when JSON parsing fails). Minimal pure-stdlib parser:
`@article`/`@inproceedings`/`@book`/`@misc` and other entry types, nested
braces, quoted and bare values, `@comment`/`@preamble`/`@string` skipped.
Mapped fields: title, author (` and ` → `, `), year, journal/booktitle/
journaltitle/publisher → source, doi, url (including `\url{...}` macros in
howpublished/note), pmid, eprint+archivePrefix → arxiv. Unparseable entries
degrade to missing-field references and are judged honestly by the normal
pipeline; zero entries → actionable error.

## Verdict meanings (unchanged since v1.3)

| Verdict | Meaning | Score |
|---|---|---|
| `verified` | reachable + trusted tier + fields complete | +10 |
| `partial` | reachable but community tier / field or metadata concerns | +4 |
| `unreachable` | fetch failed — needs human check, ≠ nonexistent | 0 |
| `unverified` | skipped (`--offline`) | −2 |
| `invalid` | no identifier, registry says no, or stitched fake | −8 |

## arXiv 第二源 fallback（v1.11）

export.arxiv.org API 对批内多请求偶发 406/403（反机器人窗口；3 秒全局控频可降频
率、不能归零，实测单发全 200、批内可稳定 406）。v1.10 及之前 API 失败即静默跳过
内容核验，同一引用两次运行会漂移（一次 verified 一次 partial）。v1.11 起：

1. API 首败后指数退避（3s 时隙 + 5s 退避）重试一次；
2. 仍失败 → fallback 拉官方着陆页 `arxiv.org/abs/<id>`，剥掉 `[ID] ` 前缀后做
   标题相似度比对（0.50/0.82 阈值与 API 路径一致）；
3. 着陆页 404 → `invalid`（官方库查无）；着陆页也不可达 → 维持可达性路径判定，
   note 明示「元数据核验未完成」，不静默。

API 明确回答（Atom feed 正常返回）时行为不变：查无记录/格式错误 → `invalid`。
非 Atom 响应（反爬 HTML 页，常是合法 XML）**不作为查无依据**，走 fallback——
防止瞬态反爬把真论文误杀成编造。

## 批次耗时预期（2026-10 实测，20 条混合清单，DOI.org/Crossref/PubMed 全路径）

| 场景 | 实测 | 推算 100 条 |
|---|---|---|
| 冷缓存 · `--workers 4`（默认） | ~18s（≈0.9s/条） | ~1.5–3 分钟 |
| 热缓存重跑（同清单 7 天内） | ~7s | 秒级～1 分钟 |
| 冷缓存 · `--workers 1` | ~47s（≈2.3s/条） | ~4–8 分钟 |

影响因素：条目类型（DOI+URL 双核验最慢）、注册库当刻限流（429 退避）、
弱网（`--cn` 下限 25s 会让 unreachable 判定更慢但更稳）。大批量（>100 条）
建议先 `--preflight` 看注册库状态，再用 `--workers 4` 默认并行；CI 里加
`--strict` 时把任务超时按上表 ×2 预留。

## 多语言处理边界（中英之外）

判定守卫按**文字系统族**工作（v3.15）：Latin / Cyrillic / Greek / Han /
Kana（日文）/ Hangul（韩文）。声称题名与注册库登记题名**主导文字系统不同**
时——俄文引文对英文登记、希腊文对拉丁、日文对中文——相似度不作编造依据，
一律走跨语言守卫（partial 转人工或桥接核验升级）。

- 同族同语（德文声称 vs 德文登记、法语 vs 法语）：正常相似度比对 ✓
- 同族跨语（德文声称 vs **英文**登记）：相似度比对照常——西文互译题名差异大，
  低相似度会被判 invalid；此类引用请附原文题名，或把英文题名一并写入
  `title`（分号分隔均可识别）
- 桥接核验的三级通道（original-title / DOI 落地页 / OpenAlex）对各族语言
  同样生效；OpenAlex 对非英语文献的收录有滞后，「桥接未命中」不构成编造证据

## 无标识符医学引用（Vancouver 格式）核验（v4.0.0）

医学文档参考文献的主流形态是 Vancouver 纯文本（作者. 题名. 期刊. 年;卷(期):页.，
无 DOI/PMID/URL）。v4.0.0 起：

1. **直接核验**：`--refs` 接受 `.md` 文件——自动从「## 参考文献」节提取 Vancouver
   编号条目（`1. 作者. 题名. 期刊. 年;卷(期):页.`），无需手工转 JSON。
2. **PubMed 题名反查**：无标识符引用先走 PubMed 题名实词检索（区分词 [Title] AND，
   5→4→3 词递减放宽）——命中且题名相似度 ≥0.82（序列+词集 Jaccard 双通道取大）升
   `verified` 并回填 PMID 锚；0.50-0.82 近似命中转人工；未命中静默转 OpenAlex/S2。
   查无永不判死（收录面=生物医学，中文文献/非生物医学未命中属预期）。
3. **大批量限流边界**：反查走 E-utilities（无 key 3 req/s）——实测 30 条连续反查中后段
   可能触发 NCBI 限流静默未命中。大批量医学文档建议：配 `NCBI_API_KEY`（提至 10 req/s）
   或分批（每批 ≤20 条）重跑；报告 `checks.pubmed_reverse` 的限流注记可辨识受影响条目。
