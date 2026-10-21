#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pp.py — paper-polisher-pro 统一命令入口（v4.9.0 新增；v6.0.0 分组帮助+双语入口）

多脚本入口导航成本高：一个入口路由全部子命令，
参数原样透传给对应脚本（用法 = 各脚本自己的 --help）。

v6.0.0：帮助按场景分组（新手三步置顶）；PP_LANG=en 切英文入口面。

用法：
  python3 scripts/pp.py <子命令> [参数...]
  python3 scripts/pp.py            # 分组列出全部子命令
  PP_LANG=en python3 scripts/pp.py # 英文入口面
  python3 scripts/pp.py recommend "把这段的AI率降一降"   # 自然语言场景路由

示例：
  python3 scripts/pp.py detect draft.txt --format json
  python3 scripts/pp.py fix draft.txt --top 10   # 句子级改写建议
  python3 scripts/pp.py html-report draft.workflow.json -o report.html  # 可视化仪表盘
  python3 scripts/pp.py trend 轮次目录/           # 多轮改稿趋势仪表盘（v6.0.0）
  python3 scripts/pp.py quickstart               # 零模型零文件一键体验
  python3 scripts/pp.py test                     # 包内单元测试
  python3 scripts/pp.py workflow draft.txt
  python3 scripts/pp.py doctor

退出码契约（v5.8.0 起稳定）：0 成功 ｜ 1 运行完成但未通过 ｜ 2 用法/输入错误 ｜ 3 环境不满足。
详见 SKILL.md § Exit-code contract。
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
_LANG = os.environ.get("PP_LANG", "zh").lower()

# (脚本, 中文描述, 英文描述)
COMMANDS = {
    "detect": ("ai_detector.py", "AI 率检测（单文件或 --batch 目录 + --recursive/--csv）",
               "AI-rate detection (single file or --batch DIR + --recursive/--csv)"),
    "gate": ("deai_gate.py", "四层降AI门禁（词级/文体/翻译腔/术语 → 复合分）",
             "4-layer de-AI gate (lexical/style/translationese/terms → composite)"),
    "fix": ("pp_fix_suggest.py", "句子级改写建议（指位+策略，不代改）",
            "Sentence-level rewrite suggestions (locate + strategy, never auto-rewrites)"),
    "rewrite-check": ("pp_rewrite_check.py", "改写效果对比（原稿 vs 改稿，引擎同源）",
                      "Before/after rewrite comparison (same engine)"),
    "norm": ("pp_style_norm.py", "学术写作规范自查（全半角/数字/缩写/单位/LLM 腔，不评分）",
             "Academic style-norm self-check (fullwidth/numbers/abbrev/units/LLM jargon, no score)"),
    "term": ("term_check.py", "术语保护检查（--auto-fix 可自动修复；--neologism 新造词提示）",
             "Terminology standardization check (--auto-fix; --neologism out-of-bank probe)"),
    "smell": ("translation_smell_check.py", "翻译腔检查（--json）", "Translationese check (--json)"),
    "style": ("style_distance.py", "文体距离/人类相似度（--json）", "Stylometry / human-likeness (--json)"),
    "workflow": ("pp_workflow.py", "端到端自查工作流（Markdown + JSON 报告）",
                 "End-to-end self-check workflow (Markdown + JSON report)"),
    "quality": ("quality_report.py", "综合质量报告", "Overall quality report"),
    "bundle": ("pp_report_bundle.py", "投稿前自查包（一条命令产出全部自查产物）",
               "Submission self-check bundle (one command → all artifacts)"),
    "html-report": ("pp_report_html.py", "单文档可视化仪表盘（workflow 等 JSON → 单文件 HTML）",
                    "Single-document visual dashboard (workflow JSON → one self-contained HTML)"),
    "trend": ("pp_trend.py", "多轮趋势报告（多份 workflow JSON → 改稿轨迹仪表盘；v6.0.0）",
              "Multi-run trend report (several workflow JSONs → trajectory dashboard; v6.0.0)"),
    "explain": ("pp_explain.py", "报告解读器（workflow/detect JSON → 结论/证据/行动清单人话三段；v6.1.0）",
                "Report explainer (workflow JSON → plain-language verdict/evidence/actions; v6.1.0)"),
    "batch-report": ("pp_batch_report.py", "批量 CSV → HTML 汇总报告",
                     "Batch CSV → HTML summary report"),
    "aigc": ("aigc_label_check.py", "AIGC 合规标识检查（docx/pdf/图片/文本）",
             "AIGC label compliance check (docx/pdf/images/text)"),
    "verify": ("pp_verify.py", "结构化零网络自证（AST 级）",
               "AST-level structured zero-network self-verification"),
    "freshness": ("freshness_refresh.py", "指纹保鲜状态自检（--status）",
                  "Fingerprint freshness status (--status)"),
    "paragraph": ("paragraph_report.py", "段落级归因（HTML 报告）", "Paragraph-level attribution (HTML report)"),
    "setup": ("pp_setup.py", "监督层装模/状态/获取指南（--model / --check / --guide）",
              "Supervised-layer install/status/acquisition guide (--model / --check / --guide)"),
    "doctor": ("pp_doctor.py", "环境自检（能跑吗/跑哪档）", "Environment self-check (can it run / which mode)"),
}

# 场景分组（v6.0.0）：新手按需看一组，不再面对 21 行平铺清单
GROUPS = (
    ("检测", "Detection", ("detect", "gate", "paragraph")),
    ("改写建议", "Rewrite guidance", ("fix", "rewrite-check")),
    ("规范与术语", "Conventions & terms", ("norm", "term", "smell", "style")),
    ("报告与可视化", "Reports & visuals", ("workflow", "quality", "bundle", "html-report", "trend", "batch-report")),
    ("合规与自证", "Compliance & assurance", ("aigc", "verify", "freshness")),
    ("环境", "Environment", ("setup", "doctor")),
)

# 内建子命令（非透传，本文件内实现）
BUILTIN = ("quickstart", "test", "api", "recommend")

_QUICKSTART_SAMPLE = (
    "值得注意的是，随着人工智能技术的快速发展，其在医疗领域的应用日益受到关注。"
    "具体而言，AI 不仅能够提高诊断效率，而且可以优化治疗方案的制定。"
    "然而，与此同时，我们在享受技术红利的同时也面临着诸多挑战。"
    "在一定程度上，数据安全问题的存在对行业发展产生了一定的制约。"
    "综上所述，本研究为该领域的进一步探索提供了一定的参考价值。"
)

# 自然语言场景 → 子命令 路由规则（v5.8.0；v6.0.0 增趋势）
_RECOMMEND_RULES = (
    (("ai率", "ai 率", "检测", "查ai", "查 ai", "像不像", "多像ai", "gpt检测", "aigc率",
      "detect", "ai score", "ai写作", "ai生成"), "detect",
     "AI 率检测：概率 + 分层证据 + 风险带", "pp.py detect draft.txt --format json"),
    (("降ai", "降 ai", "去ai味", "去 ai 味", "改写", "降重", "润色", "改哪", "怎么改", "降一降",
      "rewrite", "humanize", "paraphrase"), "fix",
     "句子级改写建议：指位 + 策略，不代改", "pp.py fix draft.txt --top 10"),
    (("对比", "前后", "效果", "回归", "compare", "before"), "rewrite-check",
     "改写效果对比（原稿 vs 改稿，引擎同源）", "pp.py rewrite-check 原稿.txt 改稿.txt"),
    (("门禁", "四层", "复合分", "gate"), "gate",
     "四层降AI门禁（词级/文体/翻译腔/术语 → 复合分）", "pp.py gate draft.txt"),
    (("规范", "格式", "全半角", "数字用法", "缩写", "单位", "体例", "ai味", "腔", "norm"), "norm",
     "学术规范 + LLM 腔自查（不评分）", "pp.py norm draft.txt"),
    (("术语", "同概念", "一致性", "terminology"), "term",
     "术语标准化与同概念异写一致性", "pp.py term draft.txt"),
    (("翻译腔", "欧化", "translation"), "smell", "翻译腔检查", "pp.py smell draft.txt"),
    (("文体", "文风", "人类相似", "style"), "style", "文体距离 / 人类相似度", "pp.py style draft.txt"),
    (("投稿", "自查包", "一键全部", "bundle", "submission"), "bundle",
     "投稿前自查包：一条命令产出全部自查产物", "pp.py bundle thesis.docx --outdir ~/selfcheck"),
    (("批量", "整个目录", "多份", "batch"), "detect",
     "批量检测目录（配 --csv 与 batch-report 汇总）", "pp.py detect 目录/ --batch --csv s.csv"),
    (("word", "docx", "毕业论文", "学位论文"), "workflow",
     ".docx 直读端到端自查（各入口均可）", "pp.py workflow thesis.docx"),
    (("合规", "标识", "披露", "label", "办法"), "aigc",
     "AIGC 合规标识检查（元数据/C2PA/显式声明）", "pp.py aigc manuscript.docx"),
    (("段落", "归因", "哪一段", "paragraph"), "paragraph",
     "段落级人机归因（HTML）", "pp.py paragraph draft.txt"),
    (("环境", "报错", "跑不了", "装模型", "模型", "doctor", "setup", "install"), "doctor",
     "环境自检：能跑吗 / 跑哪档 / 缺什么", "pp.py doctor"),
    (("自证", "零网络", "审计", "verify"), "verify", "AST 级零网络结构自证", "pp.py verify"),
    (("保鲜", "过期", "漂移", "freshness"), "freshness", "指纹保鲜状态自检", "pp.py freshness --status"),
    (("仪表盘", "可视化", "汇总", "html", "dashboard", "report"), "html-report",
     "检测/建议/规范 JSON → 单文件 HTML 仪表盘", "pp.py html-report draft.workflow.json -o report.html"),
    (("趋势", "多次", "轨迹", "进步", "trend"), "trend",
     "多轮改稿趋势：多份 workflow JSON → 轨迹仪表盘", "pp.py trend 轮次目录/ -o trend.html"),
    (("解读", "解释", "什么意思", "怎么看", "explain", "下一步"), "explain",
     "报告解读器：把 workflow/detect JSON 翻成 结论/证据/行动清单", "pp.py explain draft.workflow.json"),
    (("质量", "可读性", "quality"), "quality", "综合质量报告", "pp.py quality draft.txt"),
    (("编程", "集成", "api", "sdk", "python"), "api",
     "Python SDK 提示（import pp_api，无 CLI）", "import pp_api  # 见 SKILL.md § Python API"),
    (("全流程", "一步到位", "工作流", "workflow", "综合", "整体"), "workflow",
     "端到端自查：一次产出全部结果（MD + JSON）", "pp.py workflow draft.txt"),
)


def _run_quickstart():
    """零模型零文件一键体验：内嵌样例跑一遍核心链路（detect → fix → doctor）。"""
    print("paper-polisher-pro 一键体验（内嵌样例，无需模型/文件）\n")
    print("【第 1 步/3】AI 率检测（ai_detector）")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as f:
        f.write(_QUICKSTART_SAMPLE)
        demo = f.name
    subprocess.run([sys.executable, str(HERE / "ai_detector.py"), demo], timeout=180)
    print("\n【第 2 步/3】句子级改写建议（pp_fix_suggest，只指位+给策略，不代改）")
    subprocess.run([sys.executable, str(HERE / "pp_fix_suggest.py"), demo, "--top", "3"], timeout=180)
    print("\n【第 3 步/3】环境自检（pp_doctor——你当前跑的是哪一档）")
    subprocess.run([sys.executable, str(HERE / "pp_doctor.py")], timeout=180)
    Path(demo).unlink(missing_ok=True)
    print("\n下一步：把你的文稿存成 txt，运行 python3 scripts/pp.py detect 你的文件.txt"
          "；想看逐句改写建议加 pp.py fix 你的文件.txt。")
    return 0


def _run_tests():
    """包内单元测试（stdlib unittest，秒级、零网络、零模型）。"""
    pkg_root = HERE.parent
    tests_dir = pkg_root / "tests"
    if not tests_dir.exists():
        print("未找到 tests/ 目录（包内测试随 v5.0.0 发布）", file=sys.stderr)
        return 2
    import unittest
    suite = unittest.defaultTestLoader.discover(str(tests_dir), top_level_dir=str(pkg_root))
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


def _run_recommend(query):
    """自然语言场景路由：命中数降序取前三，给出可直接复制的命令。"""
    en = _LANG.startswith("en")
    q = (query or "").lower()
    scored = []
    for kws, cmd, why, example in _RECOMMEND_RULES:
        hits = sum(1 for k in kws if k in q)
        if hits:
            scored.append((hits, cmd, why, example))
    scored.sort(key=lambda t: -t[0])
    if not scored:
        if en:
            print("No clear scenario matched. Two safe entries:")
            print("  · Full self-check   : python3 scripts/pp.py workflow draft.txt")
            print("  · Environment check : python3 scripts/pp.py doctor")
        else:
            print("没有命中明确的场景关键词。两个稳妥入口：")
            print("  · 全流程自查（一次产出全部结果）: python3 scripts/pp.py workflow draft.txt")
            print("  · 环境自检（能跑吗/跑哪档）    : python3 scripts/pp.py doctor")
            print("提示：换更具体的词再试，如「AI率」「降重」「翻译腔」「批量」「环境」；")
            print("      或直接列出全部子命令：python3 scripts/pp.py")
        return 0
    print("根据你的描述，推荐（按命中度排序）：\n" if not en
          else "Top matches (by keyword hits):\n")
    for i, (_, cmd, why, example) in enumerate(scored[:3], 1):
        print("【%d】%s" % (i, cmd))
        print("    %s" % why)
        print("    命令：%s" % example if not en else "    command: %s" % example)
        print()
    if not en:
        print("各子命令参数同原脚本（用法 = 对应脚本 --help）；退出码契约见 SKILL.md § Exit-code contract。")
    return 0


def _print_help():
    en = _LANG.startswith("en")
    if en:
        print("paper-polisher-pro unified entry\n")
        print("First 60 seconds: ① pp.py quickstart (zero-model demo)  "
              "② pp.py detect draft.txt  ③ pp.py workflow draft.txt (full report)\n")
        width = max(len(k) for k in COMMANDS)
        for cn, eng, keys in GROUPS:
            print(f"[{eng}]")
            for k in keys:
                script, _, desc_en = COMMANDS[k]
                print("  %-*s  %s" % (width, k, desc_en))
            print()
        print("[helpers]")
        print("  quickstart      Zero-model, zero-file demo (detect→fix→doctor)")
        print("  test            Bundled unit tests (unittest, seconds)")
        print("  recommend       Natural-language command router (describe the task)")
        print("\nPython SDK: import pp_api (no CLI; see SKILL.md § Python API)")
        print("Exit-code contract (stable since v5.8.0): 0 ok | 1 ran-but-not-passed | "
              "2 usage/input error | 3 environment not ready")
        return 0
    print("paper-polisher-pro 统一入口\n")
    print("新手三步：① pp.py quickstart（一键体验） ② pp.py detect 你的文稿.txt（测 AI 率）"
          " ③ pp.py workflow 你的文稿（完整报告）\n")
    width = max(len(k) for k in COMMANDS)
    for cn, eng, keys in GROUPS:
        print("【%s %s】" % (cn, eng))
        for k in keys:
            script, desc, _ = COMMANDS[k]
            print("  %-*s  %s" % (width, k, desc))
        print()
    print("【辅助】")
    print("  %-*s  %s" % (width, "quickstart", "零模型零文件一键体验（detect→fix→doctor）"))
    print("  %-*s  %s" % (width, "test", "包内单元测试（unittest，秒级）"))
    print("  %-*s  %s" % (width, "recommend", "自然语言场景路由（描述需求 → 推荐命令）"))
    print("\nPython SDK: import pp_api（无 CLI；编程接口见 SKILL.md § Python API）")
    print("提示：各子命令的参数同原脚本，例如 pp.py detect draft.txt --format json；"
          "英文入口面：PP_LANG=en pp.py")
    print("退出码契约（v5.8.0 起稳定）：0 成功 ｜ 1 运行完成但未通过 ｜ 2 用法/输入错误 ｜ 3 环境不满足")
    return 0


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        return _print_help()
    cmd = args[0]
    if cmd == "api":
        print("Python SDK 无 CLI：import pp_api（见 SKILL.md § Python API）")
        return 0
    if cmd == "quickstart":
        return _run_quickstart()
    if cmd == "test":
        return _run_tests()
    if cmd == "recommend":
        return _run_recommend(" ".join(args[1:]))
    if cmd not in COMMANDS:
        if _LANG.startswith("en"):
            print("Unknown subcommand: %s (available: %s quickstart test recommend)"
                  % (cmd, " ".join(COMMANDS)), file=sys.stderr)
        else:
            print("未知子命令: %s（可用：%s quickstart test recommend）"
                  % (cmd, " ".join(COMMANDS)), file=sys.stderr)
        return 2
    script, _, _ = COMMANDS[cmd]
    p = subprocess.run([sys.executable, str(HERE / script)] + args[1:])
    if p.returncode not in (0, 1) and not _LANG.startswith("en"):
        print(f"[{cmd} 退出码 {p.returncode}] 契约：0=成功 1=运行未通过 2=用法/输入错误 "
              "3=环境不满足；环境问题先跑 python3 scripts/pp.py doctor", file=sys.stderr)
    return p.returncode


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
