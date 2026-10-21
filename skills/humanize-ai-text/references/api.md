> **何时读我**：要在自己的 Python/脚本里调用。
> **最短路径**：查函数表对应行。
> **回 [INDEX](INDEX.md)**

# API 参考（程序化集成）

> 供想在 Python 内直接调用核心函数的用户/agent。所有函数纯标准库、零网络。
> CLI 优先场景请直接用命令行（见 SKILL.md）；本文档面向需要嵌入自己管线的人。

## hxt_core

```python
import sys
sys.path.insert(0, "<技能目录>/scripts")
import hxt_core
```

### hxt_core.scan(text, lang=None, profile="academic") → dict

风格特征扫描（≤1MB 文本）。

- `text`：str，待扫文本（必填）
- `lang`：`"zh"|"en"|"mix"|None`——None 时自动检测
- `profile`：`"academic"`（默认，论文口径）| `"general"`（八股/公文信号 ×0.4）
- 返回：`{"score": int 0-100, "level": "低|中|高|极高", "critical_hit": bool,
  "lang": str, "profile": str, "units": float, "sentences": int,
  "categories": {cat: {"label", "count", "weight", "samples", "auto_fixable"}},
  "guards_applied": [...], "stats": {"burstiness_cv", "connector_density", ...},
  "suggestions": [{"from", "to"}], "honest_note"}`

```python
r = hxt_core.scan("这个方案为业务赋能，打法清晰。")
print(r["score"], r["level"], r["categories"].get("zh_jargon", {}).get("count"))
```

### hxt_core.scan_chunked(text, lang=None, profile="academic") → dict

超大文本分块扫描（>1MB 自动启用；CLI 的 detect/pipeline 对 >1MB 输入自动走本函数）。
返回结构同 scan，额外带 `"chunked": 块数`；跨块边界的结构信号可能少量漏检（报告标注）。

### hxt_core.read_text(path, max_mb=50.0) → str

健壮文本读取：大小上限 / 二进制 NUL 检测 / BOM 剥离 / 乱码占比守卫 / .docx 直读。
失败抛 `ValueError`（消息含处置建议）或 `OSError`。

```python
try:
    text = hxt_core.read_text("稿件.docx")
except ValueError as e:
    print("输入不合规:", e)
```

### hxt_core.build_suggestions(orig, scan_result, guide) → str

把 scan 结果转为修订建议工作单（markdown 字符串：类别/样本/处理原则/指南锚点）。
`guide` 传指南相对路径（如 `references/style_guide_zh.md`）。

### hxt_core.verify_integrity 相关

完整性守卫的函数入口在 `verify.verify(orig, new, terms=None, max_len_change=25.0,
max_cjk_shift=0.12) -> {"ok": bool, "violations": [...], "warnings": [...], "stats": {...}}`
（`import verify as vf`）。退出码契约只属于 CLI 层。

## transform / extract_terms / verify（CLI 模块复用）

| 函数 | 说明 |
|---|---|
| `transform.load_fixes(lang=None, aggressive=False)` | 返回 (rx, repl, note, guards) 修复列表 |
| `transform.apply_auto_fixes(text, fixes)` | 应用机械修复（带术语守卫），返回 (text, applied) |
| `transform.drop_flagged_sentences(text)` | 客套句/截止声明整句删除（覆盖律+数字保护），返回 (text, removed) |
| `extract_terms.extract(orig, min_count=2, cap=40)` | 术语候选抽取，返回 [(term, count, kind)] |
| `verify.load_terms(path)` | 术语表加载（BOM/守卫内建） |

所有函数零网络、零环境变量、只读写调用方显式传入的路径。

## plan / learn_guards（v2.2.0 新增）

| 函数/入口 | 说明 |
|---|---|
| `hxt_core._chunk_spans(text, max_chars=800_000, overlap=2000)` | 分块切点（含重叠窗起点），scan_chunked 缝合的底层 |
| `hxt_core.scan_chunked(text, ..., max_chars, overlap)` | 分块扫描（重叠缝合口径）；小分块参数便于测试 |
| `hxt_core.clear_pattern_cache()` | 清词表缓存（learn_guards 写守卫后同进程生效用） |
| `hxt_core.verdict_exit_code(score, critical_hit, verify_ok=None)` | --exit-verdict 机器退出码（0/1/3/4），detect/compare/pipeline 共用 |
| `hxt_core.build_hints(text, r, profile)` | 处置建议引擎（v2.4.0）：critical/plan/learn_guards/--profile general 四类提示 |
| `transform.deep_polish(text)` | 确定性深改（v2.4.0）：句首八股删除+排除式连接合并，返回 (text, ops) |
| `hxt_core.scan(..., time_budget=120.0)` | 墙钟预算（v2.4.0）：超时抛 ValueError 带拆分建议；`SCAN_TIME_BUDGET` 为缺省常量 |
| `hxt_core.CliError(msg, hint)` / `fail()` / `cli_entry(main)` | 集中异常层（v2.5.0）：两行中文错误+处置建议，exit 2；SystemExit 穿透 |
| `pipeline.py --step-timeout SEC` / report `timings` | 单步墙钟预算与各步耗时（cleanup/scan/verify，v2.5.0） |
| `transform.normalize_fullwidth_alnum(text)` | 全角字母/数字→半角（v2.9.0）：E_NUM_WIDTH 的对症修复，返回 (text, 改写数) |
| `hxt_core.read_text_ex(path)` / `_pdf_confidence` | 带元数据读取（v2.8.0）：.pdf 返回 (text, {confidence 高/中/低, notes})；四启发指标校准见 tests/v280 |
| `detect --batch --json` / `pipeline --batch` 的 `retried` | 批量二遍重试标记（v2.5.0）：失败文件以双倍预算重扫一次 |
| `hxt_core.style_profile(text)` / `stylecheck.py` | 风格画像（v2.6.0）：段落级黑话定位+节奏/开场档位+指南锚点；--compare 验收差值（阈值=dev 四语料校准） |
| `hxt_core.audit_patterns()` / `STYLE_BANDS` | 模式审计兜底（v2.6.0）：未受限贪婪量词检测；档位阈值常量 |
| `reporter.render_style_profile/compare` / `stylecheck.py --html` | 风格画像 HTML（v2.7.0）：档位表+重点段落+对比差值 |
| `pipeline.py --terms auto` | 自动术语草稿（v2.7.0）：extract_terms 口径 min_count=1+警告；JSON terms_note 字段 |
| `hxt_core._load_user_guards()` | 读 `scripts/user_guards.json`（损坏降级为空并 stderr 提示） |
| `plan.py <file> --json / -o plan.md --top N` | 句级改写优先级计划：P0 队列+章节归属+线性预算投影 |
| `plan.py <file> --handoff`（v3.0.0） | 深改交接块：逐句「原句+操作指令」指令单（含守卫铁律+验收命令）；markdown 追加输出，`--json` 下为 `handoff` 键 |
| `check_terms.py <file> --pack <域> / --list-packs`（v3.0.0） | 术语守卫域包：八学科域 28 对按域选跑；结果带 `pack` 域标签；`hxt_core` 侧 `check_terms.validate_packs()` 嵌套安全校验（变体互斥断言） |
| `check_stats.py <file> --tolerance 0.3 / --json / --report`（v3.2.0） | 统计一致性守卫：percent_sum（仅划分用语句）/ group_n_conflict（前缀归一化）/ p_style_mix；退出码 0/1/2 同 check_terms |
| `check_stats.py --batch 目录`（v3.3.0） | 跨文件批量：逐文件三类检查+跨文件 group_n 聚合（只核 n= 记法；时点前缀加宽剥离，并组候选标 timepoint_merged 不计退出码）；--json 含 files/cross_file |
| `detect.py / pipeline.py --batch 目录 --resume`（v3.7.0） | 批量断点续传：进度每文件原子落 `<目录>/.pr_batch_state.json`；`hxt_core.batch_resume_prepare(root, resume, kind, row_len)` / `batch_state_store(state, root, fn, fp, status, row, kind)` 公共件（kind 分区制，detect/pipeline 各认各的分区；指纹=[size, mtime_ns]） |
| `check_terms.py --batch 目录`（v3.7.0） | 跨文件变体漂移：逐文件组内不一致 + 跨文件「主导变体」漂移检出（各文件各自一致、合起来不一致）；--json 结构 {files, load_errors, per_file, cross_file_drift, total} 恒 exit 0；全文件读取失败 exit 2、部分失败且零发现 exit 1（防假 clean） |
| `hxt_core.scan_chunked(..., degrade=True)`（v3.9.0） | 分块降级：单块超时→2× 重试→标记 degraded_chunks=[{start,end,chars,retried}] 继续；全块失败抛 ValueError；结果 stats.notes 带覆盖率注记。≤max_chars 单块文本直接 scan，degrade 不生效（CLI 不可达，仅 API 直调注意） |
| `hxt_core.read_text` 编码自适应（v4.0.0） | UTF-16 BOM / GB18030 自动转码+stderr 标注；`read_text_ex` meta 带 encoding 字段；`_transcode_sane` 卫生检查（控制字符率）|
| `hxt_core.batch_state_store` 并发锁（v4.0.0） | flock（.pr_batch_state.json.lock）内重读-合并-落盘；双进程同目录进度互不覆盖；Windows 无 fcntl 退化为无锁 |
| `verify.build_remedies(orig, r)`（v3.9.0） | 处方清单：每类违规→{check, remedy, context[原句锚点], warning}；verify JSON 报告带 remedies 字段 |
| `plan.build_queue(text, lang, profile, source_ext, top)`（v3.8.0） | 逐句风险排序核心（plan 主流程抽取版）：返回 (top_rows, sections, full)，供 pipeline --handoff 复用；超 MAX_PLAN_CHARS 抛 ValueError |
| `pipeline --handoff 文件`（v3.8.0） | 随管线产出深改交接块：build_queue(orig) + build_handoff 写盘；JSON 模式提示走 stderr 不污染 stdout |
| `hxt_core.PdfGateRejected` / `pdf_gate_error`（v3.7.0/v3.8.0） | PDF 置信度门闸统一报错（ValueError）：4 处 CLI 调用点共用一处人话化文案（原因+已拒收+三条出路；「低于门闸」短语为测试锚） |
| `hxt_core.strip_markdown(text)` / `scan_md(...)`（v3.6.0） | markdown 感知：结构剥离（代码块/表格行/标题/列表/粗体）+结构统计；detect/pipeline/stylecheck 对 .md/.markdown 自动启用，--raw-markdown 保留原样 |
| `pipeline.py --check-stats`（v3.3.0） | 管线统计一致性阶段：对原稿三查，JSON `stats_consistency` 字段；仅提示不改退出码 |
| `pipeline.py --bundle 目录`（v3.4.0） | 投稿自查包：带时间戳子目录汇集 01 检测报告(.html)/02 修订记录(.md+.json)/03 画像对比/04 统计一致性/05 术语一致性/06 完整性判定(.json)+README |
| `detect/pipeline/plan --pdf-min-confidence 高/中/低`（v3.3.0；v3.8.0 起缺省=中） | PDF 置信度硬门闸：低于阈值拒收并提示导出 UTF-8；「低」恢复仅标注旧行为 |
| `hxt_core.pdf_confidence_ok(conf, min)` | 门闸秩比较（低<中<高） |
| `learn_guards.py add/from-text/list/remove/test` | 误报→守卫固化；语义同内置 term_guards（±30 字符窗口豁免） |

plan 的逐句贡献与投影均为近似口径（同类同权线性近似）；learn_guards 只写
`scripts/user_guards.json` 一个文件，原子替换（tmp+rename）。
