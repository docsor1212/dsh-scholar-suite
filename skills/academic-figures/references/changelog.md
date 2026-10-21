# Changelog / 版本历史

> **何时读我**：查某版本改了什么。**版本索引一表总览；最近三版展开详情；完整历史见 `changelog-full.md`**（v5.6.0 拆分：降低单文件篇幅，内容零删减）。

> **回 INDEX**：SKILL.md「版本历史」。


## 版本索引 Version Index


| 版本 | 日期 | 首条要点 |
|---|---|---|
| v5.6.1 | 2026-10-20 | 修复 galbraith 深分支崩溃（>12 研究+离群标注相邻）+研究名避让算法升级（纵向 8 档+横向镜像，密集区零叠印） |
| v5.6.0 | 2026-10-20 | 新图型#36：`galbraith`Galbraith 径向图（Meta 异质性可视化）+composite `share_y` 共享尺度自动统一+提示词卡片文档 |
| v5.5.0 | 2026-10-19 | 新图型#35：`subgroup`亚组分析森林图 |
| v5.4.0 | 2026-10-18 | 新图型#34：`rcs`限制性立方样条/非线性剂量反应曲线 |
| v5.3.0 | 2026-10-17 | 新图型#33：`nomogram`列线图（临床预测模型第四件） |
| v5.2.0 | 2026-10-16 | 新图型#31：`calibration`校准曲线（临床预测模型三件套补齐） |
| v5.1.0 | 2026-10-15 | 新图型#30：`dumbbell`哑铃图（差距优先） |
| v5.0.0 | 2026-10-14 | 新图型#29：`ridgeline`山脊图（joyplot形态） |
| v4.10.0 | 2026-10-13 | 新图型#28：`swimmer`游泳图（临床试验逐例时长） |
| v4.9.0 | 2026-10-11 | 新图型#27：`raincloud`雨云图（分布三合一：半小提琴+箱线+雨点抖动） |
| v4.8.0 | 2026-10-10 | 新图型#26：`waterfall`肿瘤缓解瀑布图（RECIST 着色+阈值线） |
| v4.7.0 | 2026-10-09 | 新图型#25：`upset`集合交集图（≥5 集合，韦恩图后继）+场景指南 |
| v4.6.0 | 2026-10-08 | ROC默认语义轴标题 |
| v4.5.0 | 2026-10-07 | 两轮独立第三方严格测试（约180用例、24/24图型、教科书数据集）的12项修复 |
| v4.4.0 | 2026-10-06 | 新图型：`volcano`火山图（第24种） |
| v4.0.0 | 2026-10-02 | 引擎模块化第四刀 |
| v3.10.0 | 2026-10-01 | `dual_axis`重构为经典"左柱右线"形态 |
| v3.9.1 | 2026-09-30 | 文档准确性热修 |
| v3.9.0 | 2026-09-30 | `--order` |

## 最近版本详情 Recent Details


### English

## Version History

## 5.6.1 — 2026-10-20

  - **Fix: galbraith deep-branch crash** — with >12 studies and adjacent
    outlier labels, the label-declutter keep-outlier path hit a variable-name
    typo (NameError). Added a regression lock with duplicate outlier studies.
  - **Label avoidance upgrade**: the declutter now walks a vertical ladder
    (8 depths) plus mirrored horizontal candidates before giving up, driven
    by acceptance testing on a real 83-study meta-analysis dataset — dense
    outlier clusters now resolve with zero glyph overlap.

## 5.6.0 — 2026-10-20

  - **New chart type #36: `galbraith` — Galbraith radial plot (meta-analysis
    heterogeneity)**: precision (1/SE) on x vs standardized effect (effect/SE)
    on y; regression through origin = pooled fixed effect; ±1.96 parallel band
    covers homogeneous studies; out-of-band studies are highlighted with red
    circles and reported per-study on stderr (heterogeneity/outlier suspects).
    Same schema as `funnel` (`studies` name/effect/se, effects on the log
    scale); effect-size arcs (OR=0.125~16 readings) drawn by default for
    ratio labels (OR/HR/RR) and auto-disabled for difference scales
    (MD/SMD); stderr also reports DL random-effects pooling with I² and
    P_het. Right-edge study labels flip inward (canvas-fit guarantee).
  - **composite `share_y` auto-unification**: set `"share_y": true` and
    panels sharing the same ylabel are unified to one y scale (log scales
    sync too; unified range reported on stderr). The `--doctor` cross-panel
    shared-scale precheck now also reads panel-level ylabel (schema-accurate)
    and points to `share_y` as the fix.
  - **Prompt cards doc** (`references/prompt-cards.md`): 12 paste-ready
    agent prompts — "对智能体说 → expected command → acceptance checks" for
    the main scenarios (baseline/KM/ROC/prediction四件套/Meta trio/omics/
    composite/journal themes/CJK/pub-ready/batch/suggest).
  - **Changelog split**: this file becomes a version index + last-3 details;
    the full history moved verbatim to `references/changelog-full.md`
    (zero content loss).
  - **CLI help scenario quick-reference** (epilog) and wizard Meta row now
    routes forest/funnel/galbraith.
  - Test-suite hygiene mechanism: verbatim `_command` tests now redirect
    `-o` to temp dirs (no more render artifacts in the repo trunk).

## 5.5.0 — 2026-10-19

  - **New chart type #35: `subgroup` — subgroup analysis forest**: per-level
    estimate squares + 95%CI whiskers, P-interaction per variable on the
    subgroup header row, Overall diamond at the bottom, right-side est (95% CI)
    and P columns (significant values accented). JSON: `subgroups=[{name,
    p_interaction?, levels=[{name, est, ci_low, ci_high, n?, p?}]}]` (1-12
    variables × 2-8 levels) + optional `overall`; `est_label` picks the
    no-effect line (HR/OR/RR=1, MD/SMD=0); `log_x` defaults to ratio scale
    with plain log ticks. Visualizes your fitted subgroup model — the engine
    does not fit.
  - **FAQ discoverability**: top-of-SKILL pointer and section-nav entry for
    `references/faq.md`.
  - **Boundaries-first ordering**: Capabilities & Boundaries now sits right
    after the section nav (before Quick Start) in both SKILL docs.
  - **Domestic install channels documented first** in README: SkillHub /
    ModelScope mirror / setup_env mirror fallback; GitHub demoted to the
    international option.

## 5.4.0 — 2026-10-18

  - **New chart type #34: `rcs` — restricted cubic spline / nonlinear
    dose-response curve**: estimate line + 95%CI band (log-ratio axis by
    default), no-effect horizontal rule + `ref` vertical reference, exposure
    rug along the bottom. JSON: `points=[{value, est, ci_lo, ci_hi}]` (≥5 grid
    points from your fitted spline model — the engine visualizes, it does not
    fit); `log_y=false` switches to a linear scale with the reference level at
    y=0 (`hline_at` overrides).
  - **DCA benefit-region shading**: thresholds where a model's net benefit
    beats both reference strategies are shaded in the model's color
    (`benefit_shade=false` to disable); the shaded ranges are reported on
    stderr for figure-vs-text cross-checking.
  - **Tick-collision false positive fixed at the mechanism level** (found via
    the DCA shading work): the anti-overlap pass counted out-of-view ticks
    (e.g. x=0.0 when xlim starts at 0.016 — never rendered) as visible boxes;
    a false intersection with the corner y-label then triggered the
    degradation ladder and silently hid real tick labels. Collision detection
    now filters ticks to the view interval.
  - **Scenario cards** (`references/scenario-cards.md`): 12 complete
    workflows, one card each = scenario + full runnable command + per-flag
    explanation + variants — the single entry covering the whole parameter
    system (answers "why do I need several docs for one scenario").
  - **SKILL.md density slimming**: journal preset table sunk to
    `references/limits.md` §六, stats/legend mini-sections merged, rare flags
    delegated to the cheatsheet — 33 chart types stay, prose shrinks.
  - **--doctor cross-panel shared-scale precheck**: composite panels sharing a
    y-label (same variable semantics) with >5× range mismatch are flagged
    before rendering.
  - Log-axis plain ticks (LogLocator 1/1.5/2/3/5/7 + scalar formatter) for all
    log-scale renders — no more 10⁰-style offsets.

## 5.3.0 — 2026-10-17

  - **New chart type #33: `nomogram` — clinical nomogram**: the prediction-model
    lookup chart (points ruler → per-variable scales → Total Points → outcome
    scales). JSON: `variables=[{name, ticks[2-12], labels?, points_at?}]`
    (points_at defaults to linear 0-100) + `outcome_scales=[{label, ticks,
    points_at}]` (1-3, in total-points units) + optional `total_points_max`.
    Visualizes your **fitted** model — the engine does not fit; total-axis
    ticks adaptively choose the nicest split (350→five-way 0/70/140/210/280/350),
    and figure height scales with row count so dense nomograms never compress.
  - **Version-consistency lock** (doc-accuracy mechanism): packaged
    `evals/evals.json` `skill_version` now pinned to the SKILL version and
    asserted by a regression test — ends the stale-metadata drift class.
  - **Consolidated flag-conflict table** in `references/limits.md` §〇
    (journal×width, stats scope, composite nesting, verify×format — all in one
    place) and the cluster_heatmap two-tier wording (1500 warn / 3000 hard cap)
    made explicit in both summary rows.
  - **Per-chart pitfalls FAQ** in `references/faq.md` (Cox PH prerequisites,
    upset top_n truncation accounting, venn --area fit deviation, dca endpoint
    rule, calibration binning practice, nomogram provenance, swimmer arrows,
    raincloud zero-variance) and remaining English-only diagnostics
    (`VERIFY OK/FAIL`, `--verify` warnings) made bilingual.


## 中文

## 版本历史

### v5.6.1（2026-10-20）

- **修复 galbraith 深分支崩溃**：研究数>12 且多个离群标注相邻时，避让的
  「离群保留」分支引用了笔误变量名（NameError）；新增同点重复离群回归锁。
- **研究名避让算法升级**：纵向 8 档阶梯+横向镜像候选位全部试净后才落位；
  由真实 83 项研究元分析数据的验收 fail 驱动——密集离群区零字形叠印。

### v5.6.0（2026-10-20）

- **新图型 #36：`galbraith` Galbraith 径向图（Meta 异质性可视化，漏斗图姊妹图）**：
  横轴精度 1/SE、纵轴标准化效应 effect/SE；过原点回归线=固定效应合并（斜率 b），
  ±1.96 平行带覆盖同质研究；带外研究红圈高亮并在 stderr 逐个报名（异质性/离群嫌疑）。
  数据 schema 与 `funnel` 完全一致（studies name/effect/se，效应取 log 值）；
  比率标签（OR/HR/RR）默认画效应量弧线（OR=0.125~16 读数），差值尺度（MD/SMD）
  自动关；stderr 同报 DL 随机效应合并+I²+P_het。右缘研究名标注自动向画布内翻转（不裁切）。
- **composite `share_y` 共享尺度自动统一**：数据加 `"share_y": true`，同 ylabel
  （同变量语义）的面板 y 轴自动统一到全体范围（log 尺度同步），stderr 报统一区间；
  `--doctor` 跨面板共享尺度预检同步修复为面板级 ylabel 读取（与 composite schema 一致）
  并把 `share_y` 作为机制出口写进提示。
- **提示词卡片文档**（`references/prompt-cards.md`）：12 张对智能体说的可粘贴完整指令
  ——「对智能体说 → 应产出命令 → 验收点」，覆盖基线/KM/ROC/预测模型四件套/Meta 三件套/
  组学/组合图/期刊主题/中文/投稿包/批量重渲/选型建议十二场景。
- **changelog 拆分**：本文件改为版本索引+最近三版详情；完整历史原样移入
  `references/changelog-full.md`（内容零删减）。
- **CLI 帮助场景速查**（epilog）+向导 Meta 行路由 forest/funnel/galbraith 三件套。
- 测试卫生机制化：逐字执行 `_command` 的测试统一把 `-o` 重定向到临时目录
  （渲染产物不再落 trunk，哨兵泄漏教训进机制）。

### v5.5.0（2026-10-19）

- **新图型 #35：`subgroup` 亚组分析森林图**：逐层效应方块+95%CI、亚组标题
  行报 P 交互、底部 Overall 菱形、右侧 est(95%CI)/P 双列（显著值红色）。
  `subgroups=[{name, p_interaction?, levels=[...]}]`（1~12×2~8）+`overall`
  可选；`est_label` 定无效线；`log_x` 默认比率对数轴+平实刻度。只可视化
  已拟合亚组模型（引擎不拟合）。
- **FAQ 可发现性**：SKILL 顶部指针+章节导航条目。
- **边界前置**：能力与边界章节移至章节导航之后（双语）。
- **国内安装通路前置**：README 安装节 SkillHub/魔搭/setup_env 镜像优先。

### v5.4.0（2026-10-18）

- **新图型 #34：`rcs` 限制性立方样条/非线性剂量反应曲线**：估计线+95%CI 带
  （默认对数比值轴）、无效应水平参照线+`ref` 竖直参照线、底部暴露 rug。
  JSON：`points=[{value,est,ci_lo,ci_hi}]`（≥5 个网格点，来自你拟合的样条模型
  ——引擎只可视化不拟合）；`log_y=false` 切线性轴（参照水平默认 y=0，
  `hline_at` 可覆盖）。
- **DCA 获益区间着色**：模型净收益同时压过两条参照策略的阈值区段按模型色
  淡色填充（`benefit_shade=false` 关闭）；着色区段写入 stderr 供图文对账。
- **刻度碰撞假阳性机制级修复**（随 DCA 着色工作发现）：防重叠检查曾把视图
  区间外的刻度（如 xlim 从 0.016 起、渲染不显示的 x=0.0）当可见框，与轴角
  y 标签假相交后触发降级阶梯，静默藏掉真实刻度标签。碰撞检测现按视图区间
  过滤。
- **场景卡片**（`references/scenario-cards.md`）：12 个完整工作流，每卡=
  场景+完整可跑命令+参数逐项说明+常见变体——参数体系的单一入口。
- **SKILL.md 减密**：期刊预设表下沉 `references/limits.md` §六，统计/图例
  小节合并，低频参数移交 cheatsheet——33 种图型信息不减，密度下降。
- **--doctor 跨面板共享尺度预检**：组合图同 y 轴标签（同变量语义）面板数值
  范围差 >5 倍时渲染前提示。
- 全部对数轴平实刻度（LogLocator 1/1.5/2/3/5/7 + 标量格式化），不再出现
  10⁰ 式科学计数法。

### v5.3.0（2026-10-17）

- **新图型 #33：`nomogram` 列线图（临床预测模型第四件）**：Points 计分尺→
  逐变量刻度→Total Points→结局概率尺。JSON：`variables=[{name, ticks[2~12],
  labels?, points_at?}]`（points_at 缺省线性 0~100）+`outcome_scales=
  [{label, ticks, points_at}]`（1~3 个，总积分口径）+`total_points_max` 可选。
  **只可视化你已拟合的模型，引擎不拟合**（points 请来自 R rms::nomogram 等）；
  总轴刻度自适应选最好台阶（350→五等分 0/70/140/210/280/350）；图高随行数
  自适应（≥0.6 英寸/行），多变量列线图不再行距压缩。
- **版本一致性锁**（文档准确性机制化）：随包 `evals/evals.json` 的
  `skill_version` 钉住 SKILL 版本并由回归测试断言——终结陈旧元数据漂移类
  （此前 2.2.0 随包漂流三个大版本）。
- **参数冲突集中表**：`references/limits.md` §〇 新增一表收拢全部冲突组合
  （journal×width/stats 域/composite 嵌套/verify×格式）；cluster_heatmap
  两级口径（1500 警告线/3000 硬顶）在两处速查行写明。
- **图型专属易错点 FAQ**：faq.md 新增一节（Cox PH 前提/upset top_n 截断
  对账/venn --area 拟合偏差/dca 端点规则/calibration 分箱惯例/nomogram
  来源口径/swimmer 箭头/raincloud 零方差）；残留英文诊断输出
  （VERIFY OK/FAIL、--verify 警告）双语化。


---

**更早版本的完整详情**：见 `references/changelog-full.md`（本文件只展开最近三版）。
