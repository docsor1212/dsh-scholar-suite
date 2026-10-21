#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_refs.py — cite-holmes skill 的引用机械验证器。

对研究引用清单做机器可判定的检查（可达性 / 域名权威度 / 字段完整性 / 去重），
输出五态判定报告（Markdown + JSON）。语义验证（来源是否真的支持论断）由模型
在研究流程中完成，本脚本不做语义判断。

五态：
  verified     可达 + 权威层(official/journal/preprint/media) + 字段完整
  partial      可达，但社区/博客层来源，或必填字段缺失
  unreachable  404/超时/反爬（needs_human_check，≠ 不存在）
  invalid      无 URL/DOI 或格式错误
  unverified   --offline 或跳过检查

纯标准库，跨平台（win32/linux/darwin），控频访问。
用法：
  python verify_refs.py --refs research_refs.json --out verify_report.md
  python verify_refs.py --claims '[{"title":"...","url":"https://...","source":"X","year":2026}]'
  python verify_refs.py --refs refs.json --offline        # 不联网，仅结构检查
  python verify_refs.py --refs refs.json --strict         # unreachable/invalid 视为失败(CI 用)
  python verify_refs.py --refs refs.json --profile medical # 医学信源预设(期刊层域名扩展+社区层降级警示)
  python verify_refs.py --refs refs.json --export bibtex,csv # 导出verified-only参考文献(bibtex)+全量台账(csv)

引用字段支持 url / doi / pmid / arxiv 四选一（pmid 自动解析为 PubMed 页面，arxiv 自动解析为
arXiv abs 页面），去重覆盖 URL+DOI+PMID 及 arXiv 解析后的 URL。
v1.5：arXiv ID 元数据校验（export.arxiv.org 官方 API，不存在的 ID 直接判 invalid，
不被可达性检查误判 unreachable——沿用 DOI 元数据先行的判定顺序）；unreachable 条目
自动查 Wayback Machine 存档（有存档附对照链接，人工复核有抓手）。
v1.6：主机断路器（同一主机连续 2 次传输层失败 → 本批次跳过该主机外呼并诚实备注，
断网环境不再整批卡死）；可操作报错（超时给 --timeout 20 建议、DNS/拒连分类措辞、
待人工复核区加建议动作）；DOI↔PMID 交叉一致性（双键引用互证，抓「真 ID 拼接」伪造）；
期刊名一致性核查（复用 DOI 登记元数据，不符降 partial——抓「真 DOI 真论文假期刊」）。
v1.7：作者名一致性核查（复用 CSL author，任一姓氏命中即一致，全部不命中降 partial）；
能力边界矩阵（报告尾部结构化呈现已抓/未抓伪造类型）；--format html 自包含单文件报告
（零外链、移动端可读，给导师/编辑的分享件）。
v1.8：撤稿检测（Crossref/Retraction Watch API——真实存在的论文也可能已撤稿，
撤稿引用封顶 partial 并转入人工复核）；OpenAlex 书目级存在性核查（无 DOI/PMID/arXiv
的引用多一路正面确认信号，只确认不降级——收录有滞后，查无 ≠ 编造）；元数据端点
UA 轮换重试（403/406 韧性）；--easy 医学误触发修复。
v1.9：Semantic Scholar 第三源交叉确认（DOI 元数据获取失败时的第二路正面信号——
只确认不降级，S2 记录质量参差实测有误记，绝不以其不一致作负面判据）；
BibTeX 导入（--refs refs.bib 自动识别，Zotero/EndNote 导出文件零改造直查）；
OpenAlex API key 支持（2026-02 起生产调用需 key：--openalex-key 或环境变量）；
--mailto 进入 Crossref polite pool（机构用户限速更宽松）+ 429 Retry-After 遵从；
投稿前结论（arXiv 2026-05 起对含幻觉/未核引用投稿实施处罚——报告头部直接给出
可否提交的结论行）；--export auditjson 透明工作底稿（每条引用的逐项检查明细，
机器可读，回应"检测系统需要透明多源"的行业呼吁）。
v1.11：判定确定性保卫——arXiv API 偶发 406/403（批内多请求撞其反机器人窗口）
时不再静默跳过内容核验，指数退避重试后 fallback 官方着陆页 arxiv.org/abs/<id>
做标题比对（复用 0.50/0.82 阈值；着陆页 404 判 invalid），同一引用两次运行判定
不再漂移，并补齐与 DOI 路径（S2 第二源）的对称性；语义层工作底稿结构化
（semantic 字段支持 {claim, support, quote, note} 对象，auditjson/报告透出
semantic_audit 区；not_in_source/contradicted 封顶 partial+人工复核——把
「disclosing uncertainty」落成机器可读）；投稿前结论修正为 arXiv 2026-05 起
处罚并补会议（ICML 2026 桌拒）话术。
v1.10：引用级并行验证（--workers，默认 4——条与条相互独立，整批耗时约 ÷workers，
直攻「跨国数据库验证慢」）；全局网络降级模式（批内 ≥3 个不同主机传输层失败 →
其余外呼快速诚实跳过并给可操作建议，把「等很久」变成「快速结论」）；
Semantic Scholar 标题检索确认（无 DOI/PMID/arXiv 引用的第三路正面信号，只确认
不降级；query 连字符空格化——S2 官方文档确认连字符查询无结果）；批内结果缓存
（同 DOI/URL 二次出现复用判定，不重复外呼）；降级态快速失败（传输失败不再重试）。
v1.12：持久磁盘缓存（--cache 默认开，sqlite3 标准库存 ~/.cache/cite-holmes/，TTL 默认
168h——复跑不再出国、判定口径一致；--strict 强制绕过保 CI 诚实；--refresh-cache
强制重验）；--proxy 显式代理；能力矩阵新增「不支持输入」行；包内私有工具清除。
"""

import argparse
import csv
import difflib
import hashlib
import ipaddress
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import escape as html_escape
from urllib.parse import urlparse, urlunparse, quote

VERSION = "4.6.0"

# ---------------- 可选配置（v1.9，main() 按命令行/环境覆写） ----------------
# OpenAlex 2026-02 起生产调用需 API key（每日免费额度）；Semantic Scholar 免钥
# 走共享限速池，带 key 独享 1 req/s。mailto 用于 Crossref polite pool（限速更宽松）。
_OPTS = {"openalex_key": "", "s2_key": "", "mailto": "", "ncbi_key": ""}


def _ncbi_qs(extra: str = "") -> str:
    """E-utilities 查询串:可选 NCBI API key(环境 NCBI_API_KEY/--ncbi-key,
    3rps→10rps 提速并行批验证)。key 不落日志只进请求参数。"""
    qs = extra
    k = _OPTS.get("ncbi_key") or ""
    if k:
        qs += f"&api_key={quote(k, safe='')}"
    return qs


# ---------------- 主机断路器（v1.6，国内适配主攻）+ 全局网络降级（v1.10） ----------------
# 同一主机连续 _CB_THRESHOLD 次传输层失败（超时/连接重置/DNS 解析失败）→ 本批次内
# 跳过该主机的后续外呼并诚实备注，避免断网环境整批卡死（弱网痛点：等待网络响应的时间不可控）。
# HTTP 层失败（404/403/429 等站点有响应的情况）不触发熔断。main() 每次运行重置。
# v1.10 并行验证引入 _CB_LOCK：_cb_record 的「累计→熔断」是读改写序列，多 worker
# 并发下必须串行化（CPython dict 单操作原子不覆盖 check-then-act）。
# v1.10 全局网络降级：批内 ≥_NET_DEGRADE_THRESHOLD 个「不同主机」传输层失败 →
# 判定出海受限，未确认过成功的主机全部快速跳过（诚实备注+建议），不再逐主机烧超时
# ——受限网络下「等很久」的机制层缓解：一次快速诚实的通过胜过几分钟干等。
_CB_THRESHOLD = 2
_CB = {}
_CB_LOCK = threading.Lock()
_NET_DEGRADE_THRESHOLD = 3
_NET_STATE = {"fail_hosts": set(), "ok_hosts": set(), "degraded": False}


def _net_reset() -> None:
    with _CB_LOCK:
        _CB.clear()
        _NET_STATE["fail_hosts"] = set()
        _NET_STATE["ok_hosts"] = set()
        _NET_STATE["degraded"] = False


def _cb_host(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{(p.hostname or '').lower()}" if p.hostname else ""


def _cb_open(url: str) -> bool:
    """该主机是否应跳过外呼：单主机熔断，或（v1.10）全局降级下从未成功过的主机。"""
    h = _cb_host(url)
    with _CB_LOCK:
        st = _CB.get(h)
        if st and st["open"]:
            return True
        return _NET_STATE["degraded"] and h not in _NET_STATE["ok_hosts"]


def _cb_skip_note(url: str) -> str:
    h = _cb_host(url)
    with _CB_LOCK:
        degraded = _NET_STATE["degraded"] and h not in _NET_STATE["ok_hosts"]
    if degraded:
        return ("全局网络降级：本批次已有多个外部主机连续传输失败（出海受限特征），"
                "跳过本次外呼（建议配置代理/更换网络后重跑），本条仅按结构/其他信息判定")
    return (f"网络断路器：{h} 本批次已连续 {_CB_THRESHOLD} 次传输失败，"
            "跳过本次外呼（避免整批卡死），本条仅按结构/其他信息判定")


def _cb_record(url: str, transport_fail: bool, degrade: bool = None) -> None:
    """transport_fail=True 记一次传输层失败（累计到阈值即熔断）；
    False（拿到任意 HTTP 响应或成功）清零。v1.10：同时维护全局降级状态。
    degrade 显式传 False 表示「计入单主机熔断但不计入全局降级」——用于站点有
    HTTP 响应却被个别函数按传输失败记账的路径（如 OpenAlex 403/429、Crossref
    限流）：出海链路本身是通的，不能因为站点级反爬/限流就判定全局网络受限。"""
    h = _cb_host(url)
    if not h:
        return
    if degrade is None:
        degrade = transport_fail
    with _CB_LOCK:
        st = _CB.setdefault(h, {"fails": 0, "open": False})
        if transport_fail:
            st["fails"] += 1
            if st["fails"] >= _CB_THRESHOLD:
                st["open"] = True
            if degrade and not _NET_STATE["degraded"] and h not in _NET_STATE["ok_hosts"]:
                _NET_STATE["fail_hosts"].add(h)
                if len(_NET_STATE["fail_hosts"]) >= _NET_DEGRADE_THRESHOLD:
                    _NET_STATE["degraded"] = True
        else:
            st["fails"] = 0
            _NET_STATE["ok_hosts"].add(h)
            _NET_STATE["fail_hosts"].discard(h)

# ---------------- 公共安全/转义帮手（v1.4 评审加固） ----------------

def ssrf_blocked(url: str) -> bool:
    """SSRF 字面量防护：URL 主机部分写明回环/内网/链路本地/保留 IP 或 localhost
    时拒绝请求。**刻意不做 DNS 解析判定**——污染网络环境下解析结果不可信，
    会把正常域名误判成内网地址（实测 pubmed/doi.org 均被解析污染误伤）。
    域名类 URL 的 DNS 层防护不在本工具承诺内。"""
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    if not host:
        return False
    if host == "localhost" or host.endswith(".localhost") or \
            host.endswith(".local") or host.endswith(".internal"):
        return True
    try:
        addr = ipaddress.ip_address(host)  # 仅当主机部分本身就是 IP 字面量
    except ValueError:
        return False
    return (addr.is_private or addr.is_loopback or addr.is_link_local
            or addr.is_reserved or addr.is_multicast)


def md_cell(text, limit=90):
    """Markdown 表格单元格转义：竖线转义、换行剥除、截断。"""
    t = str(text if text is not None else "")
    t = t.replace("\r", " ").replace("\n", " ").replace("|", "\\|")
    return t[:limit]


def csv_safe(cell: str) -> str:
    """CSV 公式注入中和（OWASP 做法）：= + - @ 制表符 回车 开头的单元格前置单引号。"""
    c = str(cell)
    if c[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + c
    return c


def bib_safe(value: str) -> str:
    """BibTeX 字段值加固：剥除花括号与换行/控制字符，防 @entry 逃逸。"""
    v = str(value if value is not None else "")
    return v.replace("{", "").replace("}", "").replace("\r", " ").replace("\n", " ")

# ---------------- CiteScore 置信度评分（v1.3.0） ----------------
# 五态加权：verified +10 / partial +4 / unreachable 0 / unverified -2 / invalid -8
# 归一化到 0-100，等级 A(>=85) B(70-84) C(50-69) D(<50)
SCORE_WEIGHTS = {"verified": 10, "partial": 4, "unreachable": 0,
                 "unverified": -2, "invalid": -8}


def render_bluf_dict(results: list, scorecard: dict) -> dict:
    """v3.2.0 BLUF 结构化块(BLUF Report Specification v1.0 L1):
    五键字典 + typed 附加(score/counts)——JSON 报告 bluf 字段直接用它。
    worst-actionable 规则(规范第 4 节):invalid>未验>partial 分支措辞。"""
    c = scorecard["counts"]
    n = scorecard["total"]
    if c["invalid"]:
        verdict = f"不建议直接使用：{c['invalid']} 条编造/无效引用必须先清除"
        blocker = f"{c['invalid']} 条 invalid"
        action = "删除或更换 invalid 信源后重跑"
    elif c["unreachable"] or c["unverified"]:
        verdict = f"基本可用但有保留：{c['unreachable']} 条不可达/{c['unverified']} 条未验需人工复核"
        blocker = f"{c['unreachable'] + c['unverified']} 条待复核"
        action = "打开 Wayback 链核对不可达项,或联网重跑"
    elif c["partial"]:
        verdict = f"可用：{c['verified']}/{n} 条 verified,{c['partial']} 条 partial 需降级使用"
        blocker = f"{c['partial']} 条 partial"
        action = "partial 项在正文引用时注明保留意见"
    else:
        verdict = f"全部 verified（{n} 条）——可进入投稿/正文流程"
        blocker = "无"
        action = "可直接 --export bibtex 导出参考文献"
    _retr = sum(1 for r in results
                if ((r.get("checks") or {}).get("retraction") or {}).get("retracted"))
    _rev = sum(1 for r in results if r.get("needs_human_check"))
    kn = (f"CiteScore {scorecard['score']}/100 ({scorecard['grade']}), "
          f"verified {c['verified']}/{n}, invalid {c['invalid']}, "
          f"复核 {_rev} 条（其中撤稿 {_retr} 条）")
    return {"verdict": verdict, "key_numbers": kn, "blocker": blocker,
            "next_action": action, "cite_holmes_version": VERSION,
            "score": scorecard["score"], "grade": scorecard["grade"],
            "counts": dict(c)}


def render_bluf(results: list, scorecard: dict) -> str:
    """v3.0.0 YAML 前置块(md/html 用);v3.2.0 起从 render_bluf_dict 单一真源渲染。"""
    d = render_bluf_dict(results, scorecard)
    return ("---\n"
            f"verdict: {d['verdict']}\n"
            f"key_numbers: {d['key_numbers']}\n"
            f"blocker: {d['blocker']}\n"
            f"next_action: {d['next_action']}\n"
            f"cite_holmes_version: {d['cite_holmes_version']}\n"
            "---")


def compute_scorecard(results: list) -> dict:
    counts = {v: sum(1 for r in results if r["verdict"] == v)
              for v in SCORE_WEIGHTS}
    n = len(results)
    raw = sum(SCORE_WEIGHTS[v] * c for v, c in counts.items())
    score = round(100 * max(raw, 0) / (10 * n)) if n else 0
    grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "D"
    return {"score": score, "grade": grade, "total": n,
            "counts": counts, "weights": SCORE_WEIGHTS}


def _norm_name(s) -> str:
    """人名/期刊名规范化：小写、只留字母数字与 CJK。"""
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(s or "").lower())


def _claimed_surnames(authors: str) -> list:
    """从 "Smith J, Zhang W, 王五" 形式的作者串提取姓氏 token（每段第一个词）。"""
    out = []
    for part in re.split(r"[,，;；、]", str(authors or "")):
        toks = part.strip().split()
        if toks:
            out.append(toks[0])
    return out


def _author_consistent(claimed: list, csl_authors) -> bool:
    """声称姓氏与 CSL 登记作者列表比对：任一命中即一致（拼写/变体从宽）。
    v1.7 二轮评审修正：①跨语言不可比（中文译名 vs 拼音登记）跳过判定——
    与期刊核查同款守卫；②单字母 initial 不参与子串匹配（防 "L."/"G." 命中
    无关长名，使检查对 APA 格式与长作者列表失效）；③规范化后为空的声称
    token 跳过。登记列表缺失或无声称作者 → 跳过判定。"""
    reg = []
    for a in csl_authors or []:
        if not isinstance(a, dict):
            continue
        for k in ("family", "given", "name"):
            v = _norm_name(a.get(k))
            if v:
                reg.append(v)
    claimed_n = [c for c in (_norm_name(x) for x in claimed) if c]
    if not reg or not claimed_n:
        return True

    # v3.15 跨族守卫：声称与登记主导文字系统不同（任意族组合）→ 跳过判定
    sf_c = _script_family(claimed_n[0])
    if sf_c != "none" and all(_script_family(r) != sf_c for r in reg):
        return True
    for c in claimed_n:
        for r in reg:
            if c == r:
                return True
            if len(c) >= 2 and len(r) >= 2 and (c in r or r in c):
                return True
    return False


def capability_matrix() -> dict:
    """能力边界矩阵（v1.7）：机械层已抓伪造类型 vs 仍需语义层把关的类型。
    结构化呈现边界——「不能做什么」与「能做什么」同样值得写清楚。"""
    return {
        "caught": [
            "假 DOI（DOI.org 查无）", "真 DOI 配假论文（错引/张冠李戴）",
            "假 PMID（E-utilities 查无）", "假 arXiv ID（官方 API 查无）",
            "DOI↔PMID 拼接（两键各真但指向不同论文）", "期刊名不符", "作者名不符",
            "真实但已撤稿（Crossref/Retraction Watch 撤稿库）",
            "死链/不可达（自动附 Wayback 存档对照）", "重复引用（URL/DOI/PMID 三键去重）",
            "中文原题 vs 登记英文题名（v3.10 跨语言三级桥接核验）",
            "克隆引用对（v3.10 同题不同 DOI / 同 DOI 不同题，成对警示）",
            "整批伪装指纹（v3.11 清单画像：标识符近邻簇/年份集中/信源集中，人工抽查建议）",
            "预印本已正式发表未引用（v3.11 arXiv→期刊版 DOI 升级提示，注记级）",
        ],
        "semantic": [
            "指向真实、可信页面的精心伪造——内容是否真支撑论断由模型的语义层判断"
            "（research_refs.json 的 semantic 字段），机械层不承诺捕获",
        ],
        "unsupported": [
            "PDF/Word 文档直读（请先手工提取引用条目再投喂）",
            "万方号/维普号等中文库专属编号（可经 URL 或标题间接核验）",
            "网页所述事实本身的对错（机械层只验来源存在与一致性，语义层归模型/人工）",
        ],
    }

# ---------------- 输出编码（Windows GBK 控制台兜底） ----------------
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# ---------------- 域名权威度分层 ----------------
# 自上而下首个命中者生效；未命中默认 blog。
TIER_RULES = [
    ("official", [
        r"\.gov(\.[a-z]{2})?$", r"\.edu(\.[a-z]{2})?$", r"\.gov\.cn$", r"\.edu\.cn$",
        r"^docs\.", r"^developer\.", r"^documentation\.", r"^support\.",
        r"^www\.anthropic\.com$", r"^openai\.com$", r"^www\.nature\.com$",
        r"^www\.nejm\.org$", r"^www\.who\.int$", r"^www\.fda\.gov$",
        r"^www\.ema\.europa\.eu$", r"^arxiv\.org$", r"^export\.arxiv\.org$",
        r"^www\.thelancet\.com$",
        r"^jamanetwork\.com$", r"^pubmed\.ncbi\.nlm\.nih\.gov$", r"^doi\.org$",
        r"^www\.sciencedirect\.com$", r"^link\.springer\.com$", r"^ieeexplore\.ieee\.org$",
        r"^www\.stats\.gov\.cn$", r"^www\.nhc\.gov\.cn$",
    ]),
    ("journal", [
        r"^pubmed\.ncbi\.nlm\.nih\.gov$", r"^doi\.org$", r"^journals?\.",
        r"^academic\.", r"^scholar\.", r"^kns\.", r"^oa\.cqvip\.com$", r"(^|\.)yiigle\.com$",
        # v4.2.0 中文医学注册库（dogfood 实测：万方题录 URL 被误层为 blog）
        r"(^|\.)wanfangdata\.com\.cn$", r"(^|\.)cnki\.(?:net|com\.cn)$",
    ]),
    ("preprint", [r"^arxiv\.org$", r"^biorxiv\.org$", r"^medrxiv\.org$", r"^ssrn\.com$", r"^chemrxiv\.org$"]),
    ("media", [
        r"^www\.reuters\.com$", r"^apnews\.com$", r"^www\.bbc\.", r"^www\.nytimes\.com$",
        r"^www\.bloomberg\.com$", r"^www\.ft\.com$", r"^www\.economist\.com$",
        r"^news\.yahoo\.com$", r"^www\.thepaper\.cn$", r"^www\.caixin\.com$",
        r"^www\.jiemian\.com$", r"^36kr\.com$", r"^www\.infoq\.cn$", r"^techcrunch\.com$",
        r"^www\.theverge\.com$", r"^arstechnica\.com$", r"^www\.wired\.com$",
    ]),
    ("community", [
        r"^github\.com$", r"^stackoverflow\.com$", r"^en\.wikipedia\.org$",
        r"^zh\.wikipedia\.org$", r"^www\.zhihu\.com$", r"^zhuanlan\.zhihu\.com$",
        r"^stackexchange\.com$", r"^www\.reddit\.com$", r"^news\.ycombinator\.com$",
        r"^www\.v2ex\.com$", r"^segmentfault\.com$", r"^juejin\.cn$",
    ]),
    ("social", [
        r"(^|\.)x\.com$", r"(^|\.)twitter\.com$", r"(^|\.)weibo\.com$", r"(^|\.)t\.me$",
        r"(^|\.)facebook\.com$", r"(^|\.)youtube\.com$", r"(^|\.)bilibili\.com$",
        r"(^|\.)douyin\.com$", r"(^|\.)xiaohongshu\.com$", r"(^|\.)medium\.com$",
    ]),
]
TRUSTED_TIERS = {"official", "journal", "preprint", "media"}

# ---------------- 医学信源预设（--profile medical 时并入 journal 层） ----------------
MEDICAL_JOURNAL_PATTERNS = [
    r"\.cochranelibrary\.com$", r"^bestpractice\.bmj\.com$", r"^www\.bmj\.com$",
    r"^www\.embase\.com$", r"^clinicaltrials\.gov$", r"^www\.chinacdc\.cn$",
    r"^www\.cdc\.gov$", r"^www\.nmpa\.gov\.cn$", r"^www\.nice\.org\.uk$",
    r"\.wanfangdata\.com\.cn$", r"^guide\.medlive\.cn$", r"^rs\.yiigle\.com$",
    r"^(www\.)?chictr\.org\.cn$",
]

DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
PMID_RE = re.compile(r"^\d{6,9}$")
# arXiv ID：新式 YYMM.NNNNN——MM 限 01-12（月份段非法的伪 ID 会让官方 API 挂起，
# 必须在客户端拒掉）——可带 v2 版本号；旧式 类目/编号（hep-th/9901001、math.GT/0309136）
ARXIV_NEW_RE = re.compile(r"^\d{2}(?:0[1-9]|1[0-2])\.\d{4,5}(v\d+)?$", re.IGNORECASE)
ARXIV_OLD_RE = re.compile(r"^[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(v\d+)?$", re.IGNORECASE)
ARXIV_URL_RE = re.compile(
    r"^https?://(?:www\.|export\.)?arxiv\.org/(?:abs|pdf|format)/"
    r"([a-z\-]+(?:\.[A-Z]{2})?/\d{7}|\d{2}(?:0[1-9]|1[0-2])\.\d{4,5})(v\d+)?", re.IGNORECASE)
REQUIRED_FIELDS = ("title", "url", "source", "year")


def extract_arxiv_id(ref: dict) -> str:
    """从引用中提取 arXiv ID（v1.5）：显式 arxiv 字段优先（支持 "arXiv:" 前缀），
    其次识别 url 中的 arxiv.org/abs|pdf/<id>。格式校验通过才返回，否则 ""。"""
    raw = str(ref.get("arxiv") or "").strip()
    if not raw:
        m = ARXIV_URL_RE.match(str(ref.get("url") or "").strip())
        if m:
            raw = m.group(1) + (m.group(2) or "")
    raw = re.sub(r"(?i)^arxiv\s*:\s*", "", raw).strip()
    if ARXIV_NEW_RE.match(raw) or ARXIV_OLD_RE.match(raw):
        return raw
    return ""


def classify_tier(url: str, medical: bool = False) -> str:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return "unknown"
    for tier, patterns in TIER_RULES:
        for pat in patterns:
            if re.search(pat, host):
                return tier
    if medical:
        for pat in MEDICAL_JOURNAL_PATTERNS:
            if re.search(pat, host):
                return "journal"
    return "blog"


def normalize_url(url: str) -> str:
    p = urlparse(url.strip())
    return urlunparse((p.scheme.lower(), (p.netloc or "").lower(), p.path.rstrip("/"),
                       "", "", ""))


PUBMED_URL_RE = re.compile(r"^https?://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?$")


def _cjk_norm(s: str) -> str:
    """v3.10 中英混排标题归一化：全角→半角、去空白与标点、小写，仅保留
    字母数字与 CJK 表意文字。跨语言桥接比对与克隆引用检测共用——中文文献
    引用中全角标点/空格变体极常见，不归一会把同一题名误判成两个。"""
    out = []
    for ch in str(s or "").lower():
        o = ord(ch)
        if 0xFF01 <= o <= 0xFF5E:      # 全角 ASCII 区 → 半角
            ch = chr(o - 0xFEE0)
        elif ch == "\u3000":           # 全角空格
            continue
        if ch.isalnum() or "\u4e00" <= ch <= "\u9fff":
            out.append(ch)
    return "".join(out)


def _script_family(s: str) -> str:
    """v3.15 文字系统族判定（跨语言守卫用）：返回文本的主导文字系统。
    latin / cyrillic / greek / han / kana / hangul / none。假名在场即判 kana
    （假名仅用于日文——中日汉字题名借此可分）。跨族题名的字符相似度天然
    不可信，这正是守卫要扩到「中英之外」的依据：俄文/希腊文/日文声称题名
    对英文登记名，旧守卫（只认 CJK）会漏判导致 sim 低被误判 invalid。"""
    from collections import Counter
    cnt = Counter()
    for ch in str(s or ""):
        o = ord(ch)
        if 0x0400 <= o <= 0x04FF:
            cnt["cyrillic"] += 1
        elif 0x0370 <= o <= 0x03FF or 0x1F00 <= o <= 0x1FFF:
            cnt["greek"] += 1
        elif 0x3040 <= o <= 0x30FF:
            cnt["kana"] += 1
        elif 0xAC00 <= o <= 0xD7AF or 0x1100 <= o <= 0x11FF:
            cnt["hangul"] += 1
        elif 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF:
            cnt["han"] += 1
        elif ch.isalpha():
            cnt["latin"] += 1
    if not cnt:
        return "none"
    if cnt.get("kana"):
        return "kana"
    return cnt.most_common(1)[0][0]


def _cross_lingual_bridge(doi: str, claimed: str, meta: dict,
                          timeout: float) -> str:
    """v3.10 跨语言标题桥接核验（只补证据、只升不降）：中文期刊常在 Crossref
    登记英文题名而用户引用中文原题，跨语言相似度天然低——v3.0 守卫此时一律
    转 partial 人工核对。本函数依次尝试三级桥接，任一命中即返回一致注记
    （调用方升级 verified），全部未命中返回空串（维持 partial 转人工）。
      T1 零网络：Crossref 双语记录的 original-title 字段（常存原语言题名）
      T2 落地页：DOI 资源页的 citation_title/og:title，或页面全文命中中文原题
      T3 OpenAlex：display_name 常为原语言题名（无 key 403 静默跳过）
    设计铁律：网络失败一律静默——「桥接不通」绝不能变成「编造依据」；
    阈值 0.75 为归一化后中文题名比对的保守下限（全半角/标点已归一）。"""
    cn = _cjk_norm(claimed)
    if len(cn) < 6:
        return ""
    ot = meta.get("original-title")
    ot = (ot[0] if isinstance(ot, list) and ot else ot) or ""
    if ot:
        r = difflib.SequenceMatcher(None, cn, _cjk_norm(ot)).ratio()
        if r >= 0.75:
            return f"双语记录 original-title 核验一致（相似度 {r:.2f}）"
    res_url = (((meta.get("resource") or {}).get("primary") or {})
               .get("URL")) or f"https://doi.org/{doi}"
    # 安全门（审计 A1/A2 修复）：注册库/出版商自控 URL——
    # ① scheme 白名单（file: 等 hostname 为空的方案在 ssrf_blocked 放行，须显式拦）；
    # ② 禁自动重定向，手动逐跳跟随并对每一跳重查 SSRF 字面量——
    #    否则落地页 302 到内网地址会被默认 opener 照常跟随（盲 SSRF）。
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    def _fetch_landing(url):
        """手动逐跳抓取落地页（≤3 跳），每跳过 scheme+SSRF 双门，返回 HTML 或 None。
        断路器接线（审计 A3）：主机连续传输失败时本批跳过，与全局外呼同规。"""
        for _hop in range(4):
            if not str(url).lower().startswith(("http://", "https://")):
                return None
            if ssrf_blocked(url) or _cb_open(url):
                return None
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": f"Mozilla/5.0 (compatible; cite-holmes/{VERSION})"})
                opener = urllib.request.build_opener(_NoRedirect)
                with opener.open(req, timeout=timeout) as resp:
                    html = resp.read(262144).decode("utf-8", "ignore")
                _cb_record(url, False)
                return html
            except urllib.error.HTTPError as e:
                _cb_record(url, False)  # 站点有响应：不计传输失败
                loc = e.headers.get("Location") if e.headers else None
                if e.code in (301, 302, 303, 307, 308) and loc:
                    url = urllib.request.urljoin(url, loc)
                    continue
                return None
            except Exception:
                _cb_record(url, True)
                return None
        return None

    html = _fetch_landing(res_url)
    if html:
        m = (re.search(r'<meta[^>]+name="citation_title"[^>]+content="([^"]+)"',
                       html, re.I)
             or re.search(r'<meta[^>]+content="([^"]+)"[^>]+name="citation_title"',
                          html, re.I)
             or re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"',
                          html, re.I))
        if m:
            r = difflib.SequenceMatcher(None, cn, _cjk_norm(m.group(1))).ratio()
            if r >= 0.75:
                return f"DOI 落地页题名核验一致（相似度 {r:.2f}）"
        # 审计 A6 收紧：整页子串命中只认 <head> 区（<title>+meta）——正文区
        # （如攻击者自己论文的参考文献表）出现该题名不构成「同载」证据。
        head_m = re.search(r"<head[^>]*>(.*?)</head>", html, re.I | re.S)
        ttl_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        head_zone = _cjk_norm((head_m.group(1) if head_m else "")
                              + (ttl_m.group(1) if ttl_m else ""))
        if cn in head_zone:
            return "DOI 落地页同载声称中文原题（双语页命中）"
    if len(cn) >= 12 and (_OPTS.get("openalex_key") or ""):
        try:
            q = quote(claimed.strip(), safe="")
            url = (f"https://api.openalex.org/works?search={q}&per-page=1"
                   f"&select=display_name&api_key={quote(_OPTS['openalex_key'], safe='')}")
            if _cb_open(url):
                return ""
            req = urllib.request.Request(url, headers={
                "User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                _cb_record(url, False)
                hits = (json.loads(resp.read().decode("utf-8", "ignore"))
                        or {}).get("results") or []
            if hits:
                r = difflib.SequenceMatcher(
                    None, cn, _cjk_norm(hits[0].get("display_name"))).ratio()
                if r >= 0.75:
                    return f"OpenAlex 原语言题名核验一致（相似度 {r:.2f}）"
        except Exception:
            pass
    return ""


def doi_metadata_match(doi: str, title: str, year, timeout: float,
                       source: str = "", authors: str = "") -> tuple:
    """DOI 元数据交叉验证（v1.4）：doi.org 内容协商取官方登记的 CSL 元数据，
    与引用声称的标题/年份比对——专抓「真 DOI 假论文」这类最像真引用的伪造。
    v1.6 新增：期刊名一致性核查（复用已取回的 container-title，零网络成本；
    不符降 partial——期刊改名常见，不判 invalid），抓「真 DOI 真论文假期刊」。
    v1.7 新增：作者名一致性核查（复用 CSL author 列表；声称姓氏至少一个命中
    登记列表即视为一致——拼写/变体从宽；全部不命中才降 partial）。
    瞬态网络错误自动重试一次。主机断路器生效。
    返回 (adjust, note, matched, csl)：adjust ∈ {"", "partial", "invalid"}；
    matched=True 表示元数据成功取得且与声称标题一致。csl=注册库权威元数据摘要
    (v3.6 新增，供 GB/T 7714 导出使用；获取失败为 None)。
    v3.6 --cn 模式：doi.org 三试全败时回源 api.crossref.org/works/{doi}
    （独立主机，CN 出口常与 doi.org 不同命运），同 CSL 格式无缝续用。"""
    import difflib
    cb_url = f"https://doi.org/{doi}"
    if _cb_open(cb_url):
        return "", _cb_skip_note(cb_url) + "，未做 DOI 元数据核验", False, None
    mailto = _OPTS.get("mailto") or ""
    # doi.org 走 UA 联系方式（不加 query 参数——避免干扰个别 DOI 的解析行为）；
    # api.crossref.org 才用 ?mailto= polite pool 约定
    ua_contact = (f"cite-holmes/{VERSION}; +verified-deep-research "
                  "(https://skillhub.cn/skills/cite-holmes)")
    if mailto:
        ua_contact += f" mailto:{mailto}"
    req_url = cb_url
    ua_rot = [ua_contact,
              f"Mozilla/5.0 (compatible; cite-holmes/{VERSION}; +verified-deep-research)"]
    meta, fetch_err = None, ""
    retry_after = 0.0
    for attempt in range(3):
        req = urllib.request.Request(
            req_url, headers={
                "Accept": "application/vnd.citationstyles.csl+json",
                "User-Agent": ua_rot[min(attempt, 1)]})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                meta = json.loads(resp.read().decode("utf-8", "ignore"))
            fetch_err = ""
            _cb_record(cb_url, False)
            break
        except urllib.error.HTTPError as e:
            _cb_record(cb_url, False)
            if e.code == 404:
                return "invalid", "DOI 在 DOI.org 不存在（404）→ 疑似编造引用", False, None
            fetch_err = f"HTTP {e.code}"
            if e.code == 429:
                # v1.9：限速分层后的礼貌退避——尊重 Retry-After（封顶 5 秒）
                retry_after = 2.0
                try:
                    if e.headers and e.headers.get("Retry-After"):
                        retry_after = min(5.0, max(1.0, float(e.headers["Retry-After"])))
                except (TypeError, ValueError):
                    pass
        except Exception as e:
            fetch_err = type(e).__name__
        if attempt < 2:
            # T3a 家族第 5 变体修复(09-30 ④b 实证):慢窗下 2 连发全灭→3 连发递增退避
            time.sleep(retry_after if retry_after else (1.2 if attempt == 0 else 3.5))
    if meta is None and _OPTS.get("cn_mode"):
        # v3.6 --cn 回源：api.crossref.org/works/{doi} 返回同构 CSL(message 字段)。
        # 独立主机不计入 doi.org 断路器；失败静默回原路径。
        try:
            cr_url = f"https://api.crossref.org/works/{quote(doi, safe='()/')}"
            cr_req = urllib.request.Request(cr_url, headers={
                "User-Agent": ua_contact, "Accept": "application/json"})
            with urllib.request.urlopen(cr_req, timeout=timeout) as resp:
                meta = json.loads(resp.read().decode("utf-8", "ignore")).get("message") or {}
            fetch_err = f"doi.org 失败({fetch_err})→Crossref 回源成功"
        except Exception as e2:
            fetch_err += f";Crossref 回源失败({type(e2).__name__})"
    if meta is None:
        _cb_record(cb_url, True)  # 整次调用只记 1 次传输失败（重试是同一逻辑失败）
        return "", f"DOI 元数据获取失败（{fetch_err}），跳过内容核验", False, None
    mt = meta.get("title")
    meta_title = (mt[0] if isinstance(mt, list) else mt) or ""
    sim = difflib.SequenceMatcher(None, (title or "").lower(),
                                  str(meta_title).lower()).ratio()
    meta_year = None
    parts = (meta.get("issued") or {}).get("date-parts") or []
    if parts and parts[0]:
        meta_year = parts[0][0]
    # v3.6:注册库权威元数据摘要(GB/T 7714 导出原料)——作者按 GB/T 缩写惯例
    # 预格式化(拉丁:姓全大写+名首字母;CJK:全名),container/year/vol/issue/page 原样
    prov = ("；DOI 元数据经 Crossref 回源（CN 模式）"
            if "Crossref 回源成功" in fetch_err else "")

    def _gbt_author(a):
        fam = (a.get("family") or "").strip()
        giv = (a.get("given") or "").strip()
        whole = fam + giv
        if any("\u4e00" <= c <= "\u9fff" for c in whole):
            return whole
        ini = " ".join(t[0].upper() for t in re.split(r"[\s\-]+", giv) if t)
        return (fam.upper() + (" " + ini if ini else "")).strip()

    _ct = meta.get("container-title")
    _container = (_ct[0] if isinstance(_ct, list) and _ct else _ct) or ""
    csl = {"title": str(meta_title)[:300],
           "authors": [x for x in (_gbt_author(a) for a in (meta.get("author") or [])
                                   if isinstance(a, dict)) if x],
           "container": str(_container)[:200], "year": meta_year,
           "volume": str(meta.get("volume") or "")[:32],
           "issue": str(meta.get("issue") or "")[:32],
           "page": str(meta.get("page") or "")[:64]}
    # v1.6 期刊名一致性核查（零网络成本）：规范化后互不包含视为不符，
    # 降 partial（期刊改名常见，不判 invalid）。
    # 二轮评审 P1 修正：NLM 式缩写（N Engl J Med vs New England Journal of
    # Medicine）不算不符——短名各词按序匹配长名词首（可跳过虚词）即视为同一
    # 期刊；跨语言（拉丁 vs CJK）不具可比性，跳过判定。
    ct = meta.get("container-title")
    reg_journal = (ct[0] if isinstance(ct, list) and ct else ct) or ""
    jadj, jnote = "", ""
    src = (source or "").strip()
    if reg_journal and src:
        def _nj(s):
            return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(s).lower())

        def _tokens(s):
            return re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", str(s).lower())

        def _is_abbrev(short_toks, long_toks):
            j = 0
            for st in short_toks:
                while j < len(long_toks) and not (
                        long_toks[j].startswith(st) or st[0] == long_toks[j][0]):
                    j += 1
                if j >= len(long_toks):
                    return False
                j += 1
            return True

        def _journal_same(x, y):
            a, b = _nj(x), _nj(y)
            if not a or not b:
                return True
            # v3.15 跨族守卫（原 CJK-only）：主导文字系统不同（如俄文刊名 vs
            # 英文登记名、混合文字刊名）→ 不判不符
            if _script_family(a) not in ("none", _script_family(b)):
                return True
            if a in b or b in a:
                return True
            ta, tb = _tokens(x), _tokens(y)
            return _is_abbrev(ta, tb) or _is_abbrev(tb, ta)

        if not _journal_same(src, reg_journal):
            jadj = "partial"
            jnote = (f"；期刊名不符（声称 {str(src)[:40]} / DOI 登记 "
                     f"{str(reg_journal)[:40]}）→ 建议核对是否引错论文")
    # v1.7 作者名一致性核查（复用 CSL author，零网络成本）：任一声称姓氏命中
    # 登记列表即视为一致（拼写/变体从宽）；全部不命中才降 partial。
    aadj, anote = "", ""
    claimed = _claimed_surnames(authors)
    if claimed and not _author_consistent(claimed, meta.get("author")):
        aadj = "partial"
        more = " 等" if len([c for c in (_norm_name(x) for x in claimed) if c]) > 1 else ""
        anote = (f"；作者不符（声称 {claimed[0]}{more} 未见于 DOI 登记作者列表）"
                 f"→ 建议核对是否引错论文")
    if not title:
        return (jadj or aadj), (f"DOI 元数据核验完成（引用未提供标题，无法比对；"
                                f"登记年份 {meta_year or '未知'}）{jnote}{anote}"), True, csl
    # v3.15 文字系统守卫（原 v3.0 仅 CJK）：声称与登记的主导文字系统不同
    # （中俄/希/日/韩 vs 拉丁等任意跨族组合）即视为跨语言——不判 invalid。
    # v3.10 三级桥接核验对各族同样适用（original-title/落地页/OpenAlex）。
    _sf_claim, _sf_reg = _script_family(title), _script_family(meta_title)
    if title and sim < 0.50 and _sf_claim != "none" and _sf_reg != "none" \
            and _sf_claim != _sf_reg:
        bridge = _cross_lingual_bridge(doi, title, meta, timeout)
        if bridge:
            # 审计 B1 修复：桥接只解决「标题跨语言不可比」，期刊/作者不符信号
            # 必须原样透出——桥接命中≠整条引用干净，jadj/aadj 参与最终 adjust，
            # jnote/anote 拼回 note（与下方常规路径同款拼接）。
            # 契约:adjust ∈ {"", "partial", "invalid"}——一致=空串(verify_one 视为无调整)
            return (jadj or aadj), (f"DOI 元数据核验一致（跨语言桥接：{bridge}；"
                                    f"登记题名《{str(meta_title)[:60]}》）{jnote}{anote}"
                                    ), True, csl
        return "partial", (f"跨语言标题无法机器比对（声称 {_sf_claim} 文 vs 登记 "
                           f"{_sf_reg} 文,相似度 {sim:.2f}；桥接核验未命中）{jnote}{anote}"
                           f"→ 建议人工核对"), True, csl
    if title and sim < 0.50:
        return "invalid", (f"DOI 元数据标题相似度仅 {sim:.2f} → DOI 指向的不是这篇论文，"
                           f"疑似编造或错引（DOI 实际为《{str(meta_title)[:60]}》）"), True, csl
    year_note = ""
    if meta_year and year:
        try:
            if abs(int(year) - int(meta_year)) >= 2:
                year_note = f"；年份不符（声称 {year} vs DOI 登记 {meta_year}）"
        except (TypeError, ValueError):
            pass
    if title and sim < 0.82:
        return "partial", f"DOI 元数据标题相似度 {sim:.2f}，建议人工复核{year_note}{jnote}{anote}{prov}", True, csl
    return (jadj or aadj), f"DOI 元数据核验一致（相似度 {sim:.2f}）{year_note}{jnote}{anote}{prov}", True, csl


_NCBI_LAST = [0.0]
_NCBI_LOCK = threading.Lock()


def _ncbi_rate_wait():
    """E-utilities 免钥上限 3 req/秒（超限封 IP）。v1.10 并行验证下必须全局
    串行化：锁内等足 0.4 秒间隔（2.5 req/s，留安全余量），与 arXiv/S2 同模式。"""
    with _NCBI_LOCK:
        wait = 0.4 - (time.time() - _NCBI_LAST[0])
        if wait > 0:
            time.sleep(wait)
        _NCBI_LAST[0] = time.time()


def _urlopen_retry(req, timeout: float, attempts: int = 3, backoff: float = 1.5):
    """v4.1.0 传输层重试（与 pmid_doi_crosscheck v3.3.0 同标准，收拢为公共助手）。

    只重试传输类异常（URLError/超时/SSL 握手失败——代理抖动/TUN 环境实测高频）；
    HTTPError 是服务器已应答（429/404/403），绝不重试，由调用方走各自可观测路径。
    全部 attempts 耗尽后抛出最后一次异常——调用方负责把「传输失败」与「查无」
    区分开（2026-10-16 实测事故：传输失败曾被当成查无 → 12+ 条真文献被报 unverified）。
    """
    last_exc = None
    for attempt in range(attempts):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError:
            raise
        except Exception as e:
            last_exc = e
            if attempt + 1 < attempts:
                time.sleep(backoff * (attempt + 1))
    raise last_exc


def _title_sim(a: str, b: str) -> float:
    """题名比对双通道取 max：序列相似度（SequenceMatcher）+ 词集 Jaccard。
    后者对「登记版题名词序重排」鲁棒——ACR/EULAR 分类标准登记题名把年份
    提前（"2013 classification criteria...: an American College..."），
    声称题名（参考文献写法）与登记题名词序不同，纯序列比对给 <0.5 误判
    （实测 2026-10-14，PMID 24122180）。v4.3.0 起为模块级（OpenAlex 找锚
    通道复用同一比对口径，避免两套相似度漂移）。"""
    a_n, b_n = _cjk_norm(a).lower(), _cjk_norm(b).lower()
    seq = difflib.SequenceMatcher(None, a_n, b_n).ratio()
    # 词集用原始题名（保留空格）切词——_cjk_norm 输出是无空格连续串，
    # 在其上 findall 只会得到一个超长 token，Jaccard 退化为包含度（实测踩坑）
    ta = set(re.findall(r"[a-z0-9\u4e00-\u9fff]+", str(a).lower()))
    tb = set(re.findall(r"[a-z0-9\u4e00-\u9fff]+", str(b).lower()))
    jac = (len(ta & tb) / len(ta | tb)) if (ta or tb) else 0.0
    return max(seq, jac)


def pubmed_title_reverse_lookup(title: str, source: str, year,
                                timeout: float) -> tuple:
    """v4.0.0 Vancouver 医学引用的 PubMed 题名反查（无标识符引用的官方核验通道）。

    医学文档参考文献的主流形态是 Vancouver 纯文本（作者. 题名. 期刊. 年;卷(期):页.），
    无 DOI/PMID/URL——此前只能走 OpenAlex/S2 标题确认（只确认不升级，unverified 转人工）。
    本通道用 E-utilities esearch 题名实词组合 → 候选 PMID → esummary 官方元数据 →
    标题相似度+年份+期刊三重比对，命中即给「官方注册库核验一致」判定并回填 PMID 锚。

    v4.1.0：
      - 短题名支持：实词 ≥2 即检索（原 <3 静默跳过——"Scleroderma in children"
        类规范短题名漏检；[Title] 限定+相似度阈值守精度）；
      - 传输失败可观测：esearch/esummary 传输异常走 _urlopen_retry（3 次退避），
        仍失败返回 net_err=True——「网络没搜成」绝不伪装成「搜了没有」（2026-10-16
        实测事故：代理抖动致 12+ 条真文献被报 unverified 且无任何痕迹）。

    返回 (adjust, note, matched, pmid, net_err)：
      adjust=""  且 matched=True      → 反查一致（调用方可升 verified）
      adjust="partial"                → 近似命中（转人工）
      adjust=""   且 matched=False    → 未命中（静默：查无≠编造，调用方继续现有
                                        通道——PubMed 收录面为生物医学/生命科学，
                                        中文文献/非生物医学引用未命中属预期）
      net_err=True                    → 传输失败（检索未完成），note 已带说明；
                                        查无与失败必须可区分
    判定语义遵循家族铁律：查无永不判死；只升不降。"""
    q = (title or "").strip()
    if len(q) < 20:  # 题名过短，检索噪声过大
        return "", "", False, "", False
    # 检索构造（实测定标 2026-10-14）：整题名短语 [Title] 对含标点长题名零命中
    # （PubMed phrase 索引 tokenize 问题）——改用区分性实词 AND 组合：
    # 题名实词按长度降序取 5 个，逐词 [Title] AND（真身命中验证：
    # ACR/EULAR SSc 分类标准 → PMID 24122180 ✓）
    stop = {"the", "and", "for", "with", "from", "of", "in", "on", "a", "an", "to",
            "by", "at", "is", "are", "via", "after", "before", "during", "into",
            "over", "under", "between", "among", "against", "without", "within",
            "upon", "than", "that", "this", "these", "those", "its", "their"}
    words = [w for w in re.findall(r"[A-Za-z\u4e00-\u9fff0-9]{2,}", q)
             if w.lower() not in stop]
    words.sort(key=len, reverse=True)
    if len(words) < 2:  # v4.1.0：<3 → ≥2（短题名规范文献反查，如 "Scleroderma in children"）
        return "", "", False, "", False
    # 词数递减收集全轮候选（5→4→3→2）：不因某轮有命中而停——4 词轮可能只命中
    # 高频词杂讯而真身在 3 词轮（实测 #5 短题名场景）；esummary 统一比对
    ids_all = []
    net_err = False
    for nwords in (5, 4, 3, 2):
        if len(words) < nwords:
            continue
        term = " AND ".join(f"{w}[Title]" for w in words[:nwords])
        u = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
             + _ncbi_qs(f"?db=pubmed&retmode=json&retmax=8&sort=relevance&term={quote(term)}"))
        if _cb_open(u):
            return "", "", False, "", False
        _ncbi_rate_wait()
        try:
            req = urllib.request.Request(
                u, headers={"User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research"})
            with _urlopen_retry(req, timeout) as resp:
                j = json.loads(resp.read().decode("utf-8", "ignore"))
            _cb_record(u, False)
            got = [str(x) for x in ((j.get("esearchresult") or {}).get("idlist") or [])]
        except urllib.error.HTTPError as e:
            _cb_record(u, False)
            # 限流可观测：429/403 让调用方知道「没搜成」而非「搜了没命中」
            return "", (f"PubMed 反查限流（HTTP {e.code}）——建议 NCBI_API_KEY 或分批"
                        if e.code in (429, 403) else ""), False, "", False
        except Exception:
            _cb_record(u, True)
            # v4.1.0：传输失败（重试后仍不通）可观测——绝不与「查无」混淆
            net_err = True
            break
        ids_all.extend(got)
        if len(got) >= 8:  # 满额命中：该轮已是最优粒度，停
            break
    ids = list(dict.fromkeys(ids_all))
    if not ids:
        if net_err:
            return "", ("PubMed 反查未完成（网络传输失败，已重试）——非查无；"
                        "网络恢复后复跑可完成核验"), False, "", True
        return "", "", False, "", False
    ids = ids[:24]
    u2 = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
          + _ncbi_qs(f"?db=pubmed&retmode=json&id={','.join(ids)}"))
    if _cb_open(u2):
        return "", "", False, "", False
    _ncbi_rate_wait()
    try:
        req = urllib.request.Request(
            u2, headers={"User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research"})
        with _urlopen_retry(req, timeout) as resp:
            _cb_record(u2, False)
            j2 = json.loads(resp.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as e:
        _cb_record(u2, False)
        # 审计 P3:esummary 限流与 esearch 同款可观测
        return "", (f"PubMed 反查限流（HTTP {e.code}）" if e.code in (429, 403)
                    else ""), False, "", False
    except Exception:
        _cb_record(u2, True)
        return "", ("PubMed 反查未完成（网络传输失败，已重试）——非查无；"
                    "网络恢复后复跑可完成核验"), False, "", True
    best = None  # (sim, pmid, meta_title, meta_source, meta_year)
    for pid in ids:
        doc = (j2.get("result") or {}).get(pid) or {}
        mt = str(doc.get("title") or "").strip()
        if not mt:
            continue
        sim = _title_sim(title, mt)
        my = None
        m = re.search(r"(19|20)\d{2}", str(doc.get("pubdate") or ""))
        if m:
            my = int(m.group(0))
        ms = str(doc.get("source") or "").strip()
        try:
            year_i = int(year) if year else None
        except (TypeError, ValueError):
            year_i = None  # 审计 P2:坏 year 字符串（如 "2020 (Epub)"）不过滤，
            #               绝不因元数据解析异常走判死路径
        year_ok = (not year_i) or (not my) or abs(year_i - int(my)) <= 1
        # 收集全部 year_ok 候选取 sim 最大——阈值分档放在收集之后
        # （原实现在收集处就筛 0.82，导致 0.50-0.82 近似命中分支永不触发）
        if year_ok and (best is None or sim > best[0]):
            best = (sim, pid, mt, ms, my)
    if best and best[0] >= 0.82:
        sim, pid, mt, ms, my = best
        note = (f"PubMed 题名反查核验一致（PMID:{pid}；登记题名《{mt[:60]}》"
                f"{'·' + ms if ms else ''}{'·' + str(my) if my else ''}）")
        return "", note, True, pid, False
    if best and best[0] >= 0.50:
        sim, pid, mt, ms, my = best
        return ("partial",
                f"PubMed 题名反查近似命中（PMID:{pid}，相似度 {sim:.2f}，"
                f"登记题名《{mt[:60]}》）→ 人工核对是否同一篇",
                True, pid, False)
    return "", "", False, "", False


# v4.2.0 中文医学期刊 → NLM TA（题名缩写）映射。数据源=NLM 目录静态快照（中华医学会
# 系列命名规律 "Zhonghua X Za Zhi"）。收录错误的代价=锚定零命中静默放行（绝不误判）。
# v4.3.0 数据治理：2026-10-18 PubMed 在线抽验——21 条候选映射属「目录登记但 MEDLINE
# 零收录」（定位器永哑火）已剔除，现存 17 条全部实测有收录（中华儿科杂志 6254 条等；2026-10-18 复验
# 中华创伤杂志亦零收录同剔——「18 条全部实测」初版声明经二次抽验纠正为 17）；
# 抽验工具=tools/check_ta_table.py。未收录期刊由 OpenAlex 通道（v4.3.0）覆盖。
_CN_JOURNAL_TA = {
    "中华儿科杂志": "Zhonghua Er Ke Za Zhi",
    "中华医学杂志": "Zhonghua Yi Xue Za Zhi",
    "中华结核和呼吸杂志": "Zhonghua Jie He He Hu Xi Za Zhi",
    "中华心血管病杂志": "Zhonghua Xin Xue Guan Bing Za Zhi",
    "中华内科杂志": "Zhonghua Nei Ke Za Zhi",
    "中华外科杂志": "Zhonghua Wai Ke Za Zhi",
    "中华妇产科杂志": "Zhonghua Fu Chan Ke Za Zhi",
    "中华放射学杂志": "Zhonghua Fang She Xue Za Zhi",
    "中华血液学杂志": "Zhonghua Xue Ye Xue Za Zhi",
    "中华护理杂志": "Zhonghua Hu Li Za Zhi",
    "中华预防医学杂志": "Zhonghua Yu Fang Yi Xue Za Zhi",
    "中华流行病学杂志": "Zhonghua Liu Xing Bing Xue Za Zhi",
    "中华肿瘤杂志": "Zhonghua Zhong Liu Za Zhi",
    "中华耳鼻咽喉头颈外科杂志": "Zhonghua Er Bi Yan Hou Tou Jing Wai Ke Za Zhi",
    "中华眼科杂志": "Zhonghua Yan Ke Za Zhi",
    "中华口腔医学杂志": "Zhonghua Kou Qiang Yi Xue Za Zhi",
    "中华病理学杂志": "Zhonghua Bing Li Xue Za Zhi",
}


def _ta_for_journal(source: str) -> str:
    """中文刊名 → NLM TA；否则原样返回（英文引用的著录缩写通常即 TA）。"""
    s = re.sub(r"[\s《》*]+", "", str(source or ""))
    return _CN_JOURNAL_TA.get(s) or str(source or "").strip()


def discover_refs(topic: str, limit: int = 10, timeout: float = 15.0,
                  since: int = None) -> tuple:
    """v4.5.0 文献发现：主题 → PubMed + OpenAlex 双源检索 → 候选清单。

    把 skill 从「验已有的文献」扩展为「找文献且出生即核验」——检索结果天然
    带官方标识符（PMID/DOI），交回主管道后走全部既有核验栈（含撤稿检测），
    输出一份每条都验过的文献清单（GB/T/BibTeX 一键导出）。
    返回 (refs, notes)：单源失败静默跳过（绝不因单源失败崩批）；
    跨源按 doi/pmid/题名规一化去重；since 过滤出版年（近 N 年检索）。
    v4.6.0：跨源题名合并——同一论文一侧带 DOI 一侧仅题名时合并字段不再重复
    （原三级互斥键只认同键，跨源残余重复）。"""
    refs, notes = [], []
    seen = set()

    def _key(doi, pmid, title):
        return (f"doi:{doi.lower()}" if doi else
                f"pmid:{pmid}" if pmid else
                "t:" + re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", (title or "").lower())[:60])

    def _add(doi, pmid, title, source, year):
        doi = (doi or "").replace("https://doi.org/", "").strip()
        pmid = str(pmid or "").strip()
        title = re.sub(r"\s+", " ", str(title or "")).strip()
        if not title or len(title) < 15:
            return
        k = _key(doi, pmid, title)
        if k in seen or k == "t:":
            return
        seen.add(k)
        ref = {"title": title, "source": str(source or ""), "year": year}
        if doi and DOI_RE.match(doi):
            ref["doi"] = doi
        if pmid and PMID_RE.match(pmid):
            ref["pmid"] = pmid
        refs.append(ref)

    limit = max(1, min(int(limit or 10), 25))
    # 源一：PubMed 主题检索（官方题录，PMID 天然在握）
    try:
        u = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
             + _ncbi_qs(f"?db=pubmed&retmode=json&retmax={limit}&sort=relevance"
                        f"&term={quote(topic)}"))
        if not _cb_open(u):
            _ncbi_rate_wait()
            req = urllib.request.Request(
                u, headers={"User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research"})
            with _urlopen_retry(req, timeout) as resp:
                j = json.loads(resp.read().decode("utf-8", "ignore"))
            _cb_record(u, False)
            ids = [str(x) for x in ((j.get("esearchresult") or {}).get("idlist") or [])]
            if ids:
                u2 = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                      + _ncbi_qs(f"?db=pubmed&retmode=json&id={','.join(ids)}"))
                _ncbi_rate_wait()
                req2 = urllib.request.Request(
                    u2, headers={"User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research"})
                try:
                    with _urlopen_retry(req2, timeout) as resp2:
                        j2 = json.loads(resp2.read().decode("utf-8", "ignore"))
                    _cb_record(u2, False)
                except Exception:
                    _cb_record(u2, True)  # 审计 P2：题录拉取失败也要进断路器记账
                    j2 = {}
                res = j2.get("result") or {}
                for pid in ids:
                    doc = res.get(pid) or {}
                    my = re.search(r"(19|20)\d{2}", str(doc.get("pubdate") or ""))
                    _add(_pmid_reg_doi(doc), pid, doc.get("title"),
                         doc.get("source") or "",
                         int(my.group(0)) if my else None)
            else:
                notes.append("PubMed 该主题零命中")
        else:
            notes.append("PubMed 断路器跳过")
    except urllib.error.HTTPError as e:
        _cb_record(u, False, degrade=False)  # 审计 P2：服务器应答不熔断，但必须记账
        notes.append(f"PubMed HTTP {e.code}——本源跳过"
                     + ("（限流，建议 NCBI_API_KEY）" if e.code in (429, 403) else ""))
    except Exception:
        _cb_record(u, True)  # 审计 P2：传输失败必须进断路器/全局降级
        notes.append("PubMed 检索失败——本源跳过")
    # 源二：OpenAlex 主题检索（覆盖面更广，DOI 候选交回核验）
    ou = None
    try:
        q = quote(topic, safe="")
        ou = (f"https://api.openalex.org/works?search={q}&per-page={limit}"
              "&select=display_name,publication_year,doi,primary_location")
        okey = _OPTS.get("openalex_key") or ""
        if okey:
            ou += f"&api_key={quote(okey, safe='')}"
        if not _cb_open(ou):
            oreq = urllib.request.Request(
                ou, headers={"User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research"})
            with _urlopen_retry(oreq, timeout) as oresp:
                oj = json.loads(oresp.read().decode("utf-8", "ignore"))
            _cb_record(ou, False)
            for w in (oj.get("results") or []):
                _add(w.get("doi"), None, w.get("display_name"),
                     ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
                     if isinstance(w.get("primary_location"), dict) else "",
                     w.get("publication_year"))
        else:
            notes.append("OpenAlex 断路器跳过")
    except urllib.error.HTTPError as e:
        if ou:
            _cb_record(ou, False, degrade=False)  # 服务器应答不熔断（自家惯例）
        notes.append(f"OpenAlex HTTP {e.code}——本源跳过"
                     + ("（2026 年起生产调用需 --openalex-key）" if e.code == 403
                        else "（限流）" if e.code == 429 else ""))
    except Exception:
        if ou:
            _cb_record(ou, True)
        notes.append("OpenAlex 检索失败——本源跳过")
    # v4.6.0：since 出版年过滤（无年份条目保留——宁多勿错杀）
    if since and int(since) >= 1900:  # 审计 P3：0/负数静默无效→下限门
        refs = [r for r in refs if not r.get("year") or int(r["year"]) >= int(since)]
    # 跨源题名合并：同题不同键（一侧 DOI 一侧仅题名）字段互补
    by_title, merged = {}, []
    for r in refs:
        tk = "t:" + re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", r["title"].lower())[:60]
        hit = by_title.get(tk)
        if hit is None:
            by_title[tk] = r
            merged.append(r)
        else:
            # 审计 P3：60 字符前缀碰撞可能是不同论文（如 part one vs part one
            # extended）——年份不相容不融合，防 crosscheck 假 invalid
            yr_ok = (not hit.get("year") or not r.get("year")
                     or abs(int(hit["year"]) - int(r["year"])) <= 1)
            if yr_ok:
                for k, v in r.items():
                    if v and not hit.get(k):
                        hit[k] = v
    return merged, notes


def pubmed_locator_lookup(source: str, year, volume, issue, pages,
                          timeout: float, claimed_title: str = "") -> tuple:
    """v4.2.0 卷期页锚定核验（PubMed Single Citation Matcher 的 E-utilities 形态）。

    GB/T 7714 中文医学引用的第二个无标识符通道：期刊+年+卷(期):页 是 PubMed
    官方引文定位器——语言无关（声称中文题名 vs 登记英文/罗马化题名不影响定位），
    恰好覆盖题名反查的盲区（非 MEDLINE 题名形态、翻译题名相似度不足）。
    期刊映射：中文刊名走 _CN_JOURNAL_TA → NLM TA；英文刊名直接作 TA。

    判定（保守）：TA+年+卷+期+页 **唯一命中**（count==1）→ matched，调用方升
    verified 并回填 PMID 锚；count>=2 → 歧义注记转人工；count==0 → 静默（查无≠编造）。
    年份必须精确（定位器语义，无 ±1 宽限）。返回 (adjust, note, matched, pmid, net_err)，
    契约与题名反查一致。"""
    ta = _ta_for_journal(source)
    vol = str(volume or "").strip()
    if not ta or not vol:
        return "", "", False, "", False
    try:
        y = int(str(year)) if year else None
    except (TypeError, ValueError):
        y = None
    if not y:
        return "", "", False, "", False
    parts = [f"{ta}[TA]", f"{y}[DP]", f"{vol}[VI]"]
    iss = str(issue or "").strip()
    pg = str(pages or "").strip()
    if iss:
        parts.append(f"{iss}[IP]")
    if pg:
        parts.append(f"{pg}[PG]")
    term = " AND ".join(parts)
    u = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
         + _ncbi_qs(f"?db=pubmed&retmode=json&retmax=4&sort=relevance&term={quote(term)}"))
    if _cb_open(u):
        return "", "", False, "", False
    _ncbi_rate_wait()
    try:
        req = urllib.request.Request(
            u, headers={"User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research"})
        with _urlopen_retry(req, timeout) as resp:
            j = json.loads(resp.read().decode("utf-8", "ignore"))
        _cb_record(u, False)
        er = j.get("esearchresult") or {}
        count = int(er.get("count") or 0)
        ids = [str(x) for x in (er.get("idlist") or [])]
    except urllib.error.HTTPError as e:
        _cb_record(u, False)
        return "", (f"PubMed 卷期页锚定限流（HTTP {e.code}）——建议 NCBI_API_KEY 或分批"
                    if e.code in (429, 403) else ""), False, "", False
    except Exception:
        _cb_record(u, True)
        return "", ("PubMed 卷期页锚定未完成（网络传输失败，已重试）——非查无"
                    ), False, "", True
    if count == 1 and ids:
        pid = ids[0]
        # 取登记题名进注记（透明底稿；中文声称 vs 登记题名语言差异如实展示）
        mt = ""
        u2 = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
              + _ncbi_qs(f"?db=pubmed&retmode=json&id={pid}"))
        if not _cb_open(u2):
            _ncbi_rate_wait()
            try:
                req2 = urllib.request.Request(
                    u2, headers={"User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research"})
                with _urlopen_retry(req2, timeout) as resp2:
                    j2 = json.loads(resp2.read().decode("utf-8", "ignore"))
                _cb_record(u2, False)
                doc = (j2.get("result") or {}).get(pid) or {}
                mt = str(doc.get("title") or "").strip()
            except Exception:
                _cb_record(u2, True)  # 注记增强失败不影响判定
        # 审计 A2 修复：定位器只证「卷期页↔PMID」，不证「题名↔PMID」——同文字
        # 系统时登记题名必须过 sim 0.50（编造同语言题名+真实卷期页不得机器
        # verified）；跨文字系统（中文声称 vs 登记英文）维持语言无关语义
        if claimed_title and mt:
            import difflib
            _sim = difflib.SequenceMatcher(None, str(claimed_title).strip().lower(),
                                           re.sub(r"\s+", " ", mt).strip().lower()).ratio()
            _sf_c, _sf_r = _script_family(str(claimed_title)), _script_family(mt)
            if _sf_c != "none" and _sf_r != "none" and _sf_c == _sf_r and _sim < 0.50:
                return "partial", (f"卷期页唯一定位到 PMID:{pid}，但同语言登记题名"
                                   f"《{mt[:60]}》与声称题名相似度仅 {_sim:.2f}"
                                   "——疑似错引或拼接，转人工"), False, "", False
        return "", (f"PubMed 卷期页锚定核验一致（PMID:{pid}；TA:{ta}"
                    + (f"；登记题名《{mt[:60]}》" if mt else "") + "）"), True, pid, False
    if count >= 2:
        return "", (f"卷期页定位到 {count} 条（歧义）——转人工判定"), False, "", False
    return "", "", False, "", False


def pubmed_pmid_exists(pmid: str, timeout: float) -> tuple:
    """经 NCBI E-utilities 核实 PMID 真实存在。

    PubMed 网页对不存在的 PMID 也返回 2xx/203（且带反爬壳页），HTTP 状态码
    无法区分真假——AI 编造的 PMID 必须靠 API 核实才能抓住。
    返回 (exists, note)。
    """
    u = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
         + _ncbi_qs(f"?db=pubmed&id={pmid}&retmode=json"))
    if _cb_open(u):
        return True, _cb_skip_note(u) + "，按可达处理"
    _ncbi_rate_wait()
    try:
        req = urllib.request.Request(
            u, headers={"User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            j = json.loads(resp.read().decode("utf-8", "ignore"))
        _cb_record(u, False)
        res = j.get("result") or {}
        item = res.get(str(pmid)) or {}
        if item.get("error") or str(pmid) not in (res.get("uids") or []):
            return False, "PMID 在 PubMed 不存在（E-utilities 核实）→ 疑似编造引用"
        return True, "PMID 经 E-utilities 核实存在"
    except urllib.error.HTTPError as e:
        _cb_record(u, False)
        return True, f"E-utilities 校验失败（HTTP {e.code}），按可达处理"
    except Exception as e:
        _cb_record(u, True)
        return True, f"E-utilities 校验失败（{type(e).__name__}），按可达处理"


def pmid_doi_crosscheck(pmid: str, doi: str, timeout: float) -> tuple:
    """v1.6 DOI↔PMID 交叉一致性：两键各自真实也可能「拼接造假」（PMID 是 A 论文的、
    DOI 是 B 论文的）。取 PMID 在 PubMed 登记的 DOI 与声称 DOI 比对：
    不一致 → invalid「拼接伪造特征」；一致 → 加一致备注；登记无 DOI → 跳过。
    返回 (adjust, note)，adjust ∈ {"", "invalid"}。断路器生效。"""
    u = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
         + _ncbi_qs(f"?db=pubmed&id={pmid}&retmode=json"))
    if _cb_open(u):
        return "", _cb_skip_note(u) + "，DOI↔PMID 交叉未做"
    _ncbi_rate_wait()
    # v3.3.0 评审修复(09-29 ④b 实证):URLError/超时无重试会被网络抖动一击必杀
    # → 3 次递增退避重试(与 T3a DOI 探测同标准);HTTPError 服务器已应答不重试
    j = None
    last_exc = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                u, headers={"User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                j = json.loads(resp.read().decode("utf-8", "ignore"))
            break
        except urllib.error.HTTPError as e:
            _cb_record(u, False)
            return "", f"E-utilities 交叉查询失败（HTTP {e.code}），跳过 DOI↔PMID 交叉"
        except Exception as e:
            _cb_record(u, True)
            last_exc = e
            time.sleep(1.5 * (attempt + 1))
    if j is None:
        return "", (f"E-utilities 交叉查询失败（{type(last_exc).__name__}×3 重试后仍失败），"
                    "跳过 DOI↔PMID 交叉")
    _cb_record(u, False)
    res = j.get("result") or {}
    item = res.get(str(pmid)) or {}
    reg = ""
    for a in item.get("articleids") or []:
        if a.get("idtype") == "doi":
            reg = (a.get("value") or "").strip()
            break
    if not reg:
        return "", "PMID 未登记 DOI，跳过 DOI↔PMID 交叉"
    if reg.lower().rstrip(".").rstrip("/") == doi.lower().strip().rstrip(".").rstrip("/"):
        return "", "DOI↔PMID 交叉一致（两键指向同一论文）"
    return "invalid", (f"DOI 与 PMID 指向不同论文（PMID {pmid} 登记为 {reg}，"
                       f"引用声称 {doi}）→ 拼接伪造特征，疑似编造引用")



_JOURNAL_ACRO = {
    # 不透明缩写(不可按词首拆分匹配的 NLM 缩写)→全称;小写无句点
    "jama": "journal of the american medical association",
    "pnas": "proceedings of the national academy of sciences",
    "bmj": "british medical journal",
    "jco": "journal of clinical oncology",
    "jnci": "journal of the national cancer institute",
    "ajr": "american journal of roentgenology",
    "jid": "journal of investigative dermatology",
    "jacc": "journal of the american college of cardiology",
}


def _journal_tokens(s: str) -> list:
    return re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", str(s).lower())


def _journal_acro_expand(name: str) -> str:
    """不透明缩写展开(双向);其余原样返回。"""
    k = re.sub(r"[^a-z0-9 ]", "", str(name).lower()).strip()
    if k in _JOURNAL_ACRO:
        return _JOURNAL_ACRO[k]
    return str(name)


def _journal_consistent(claimed: str, registry: str) -> bool:
    """期刊名一致性(宽容口径,与 v1.6 DOI 路径同哲学):
    ①规范化后互含→一致 ②NLM 式缩写:短名各词按序匹配长名词首(可跳虚词)
    →一致 ③不透明缩写(JAMA/PNAS 等)经 _JOURNAL_ACRO 展开后再比 ④跨语言跳过。"""
    c = str(claimed or "").strip().lower()
    r = str(registry or "").strip().lower()
    if not c or not r:
        return True
    cn, rn = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", c), re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", r)
    if not cn or not rn:
        return True  # 跨语言不可比,跳过
    if bool(re.search(r"[\u4e00-\u9fff]", c)) != bool(re.search(r"[\u4e00-\u9fff]", r)):
        return True  # 拉丁 vs CJK:字系不同不可比,跳过(v1.6 同语义)
    if cn in rn or rn in cn:
        return True
    for a, b in ((c, r), (r, c)):
        ea, eb = _journal_acro_expand(a), _journal_acro_expand(b)
        if ea != a or eb != b:
            an, bn = re.sub(r"[^a-z0-9]+", "", ea), re.sub(r"[^a-z0-9]+", "", eb)
            if an in bn or bn in an:
                return True
            ta, tb = _journal_tokens(ea), _journal_tokens(eb)
            short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
            stop = {"of", "the", "and", "in", "for", "on"}
            long_content = [w for w in long_ if w not in stop]
            j, hit = 0, 0
            ok = True
            for st in short:
                if st in stop:
                    continue
                while j < len(long_content) and not long_content[j].startswith(st):
                    j += 1
                if j >= len(long_content):
                    ok = False
                    break
                hit += 1
                j += 1
            if ok and hit >= max(1, len([w for w in short if w not in stop])):
                return True
    ct, rt = _journal_tokens(c), _journal_tokens(r)
    short, long_ = (ct, rt) if len(ct) <= len(rt) else (rt, ct)
    stop = {"of", "the", "and", "in", "for", "on"}
    long_content = [w for w in long_ if w not in stop]
    j, hit, ok = 0, 0, True
    for st in short:
        if st in stop:
            continue
        while j < len(long_content) and not long_content[j].startswith(st):
            j += 1
        if j >= len(long_content):
            ok = False
            break
        hit += 1
        j += 1
    return bool(ok and hit >= max(1, len([w for w in short if w not in stop])))


def _pmid_reg_doi(item: dict) -> str:
    """v4.3.0 从 esummary item 提取登记 DOI（articleids），供桥接拯救复用。"""
    for a in item.get("articleids") or []:
        if (a.get("idtype") or "") == "doi":
            return a.get("value") or ""
    return ""


def pmid_metadata_match(pmid: str, title: str, source: str, year, timeout: float) -> tuple:
    """v3.4 池开发:PMID 元数据核验——堵「真 PMID+假标题/假期刊」拼接洞。
    此前 PMID-only 引用仅查存在性(pubmed_pmid_exists),esummary 拉回的
    标题/期刊/年份字段被丢弃:攻击者拿真 PMID 配编造标题即可过 verified。
    本函数复用同源数据(一次 esummary):标题相似度三档(与 DOI 路径同阈值)
    +期刊一致性(不透明缩写展开,不符降 partial——期刊改名常见不判 invalid)。
    返回 (adjust, note, matched),adjust ∈ {"", "partial", "invalid"}。"""
    import difflib
    u = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
         + _ncbi_qs(f"?db=pubmed&id={pmid}&retmode=json"))
    if _cb_open(u):
        return "", _cb_skip_note(u) + "，PMID 元数据核验未做", False
    _ncbi_rate_wait()
    j = None
    last_exc = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                u, headers={"User-Agent": f"cite-holmes/{'3.4'}; +verified-deep-research"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                j = json.loads(resp.read().decode("utf-8", "ignore"))
            break
        except urllib.error.HTTPError as e:
            _cb_record(u, False)
            return "", f"E-utilities 元数据获取失败（HTTP {e.code}），跳过 PMID 内容核验", False
        except Exception as e:
            _cb_record(u, True)
            last_exc = e
            time.sleep(1.5 * (attempt + 1))
    if j is None:
        return "", (f"E-utilities 元数据获取失败（{type(last_exc).__name__}×3），"
                    "跳过 PMID 内容核验"), False
    _cb_record(u, False)
    res = j.get("result") or {}
    item = res.get(str(pmid)) or {}
    if item.get("error") or str(pmid) not in (res.get("uids") or []):
        return "invalid", "PMID 在 PubMed 不存在（E-utilities 核实）→ 疑似编造引用", False
    mt = item.get("title") or ""
    matched = False
    if title:
        sim = difflib.SequenceMatcher(None, str(title).strip().lower(),
                                      re.sub(r"\s+", " ", mt).strip().lower()).ratio()
        if sim < 0.50:
            # v4.2.0 文字系统守卫（与 DOI 通路同语义；家族铁律：语言差异绝不作
            # 编造依据）——真网实锤：中文指南 39429074 声称中文题名 vs 登记英文
            # 题名 sim 0.10 被误判「拼接伪造」。跨族时低相似度不得判死；桥接原料
            # =登记 DOI（articleids），桥接命中给一致，否则 partial 转人工。
            _sf_c, _sf_r = _script_family(str(title)), _script_family(mt)
            if _sf_c != "none" and _sf_r != "none" and _sf_c != _sf_r:
                reg_doi = _pmid_reg_doi(item)
                bridge = (_cross_lingual_bridge(reg_doi, str(title),
                                                {"title": mt}, timeout)
                          if reg_doi and DOI_RE.match(reg_doi) else "")
                if bridge:
                    return "", (f"PMID 元数据核验一致（跨语言桥接：{bridge}；"
                                f"登记题名《{mt[:60]}》）"), True
                return "partial", (f"跨语言标题无法机器比对（声称 {_sf_c} 文 vs 登记 "
                                   f"{_sf_r} 文,相似度 {sim:.2f}）→ 建议人工核对"), False
            # v4.3.0 判死前桥接拯救（audit P2：罗马化/翻译题名形态——声称与登记
            # 同属拉丁族但一个是拼音/译名时 sim 天然低）；桥接原料=登记 DOI。
            # 桥接未命中仍判死——同语言假标题的拼接防护不弱化。
            reg_doi = _pmid_reg_doi(item)
            if reg_doi and DOI_RE.match(reg_doi):
                bridge = _cross_lingual_bridge(reg_doi, str(title),
                                               {"title": mt}, timeout)
                if bridge:
                    return "", (f"PMID 元数据核验一致（跨语言桥接：{bridge}；"
                                f"登记题名《{mt[:60]}》）"), True
            return "invalid", (f"PMID 登记标题相似度仅 {sim:.2f}（登记为《{mt[:60]}》）"
                               "→ 真 PMID 假标题，疑似拼接伪造"), False
        if sim < 0.82:
            return "partial", (f"PMID 登记标题相似度 {sim:.2f}：《{mt[:60]}》，建议人工复核"), False
        matched = True
    if source:
        reg_j = item.get("fulljournalname") or item.get("source") or ""
        if reg_j and not _journal_consistent(source, reg_j):
            return "partial", (f"期刊名与 PubMed 登记不符（登记为 {reg_j}，"
                               "引用声称 " + str(source).strip() + "）——真 PMID 假期刊或改名，"
                               "降 partial 人工复核"), matched
    return "", "PMID 元数据核验一致" + (f"：《{mt[:50]}》" if mt else ""), matched



_ARXIV_LAST = [0.0]
_ARXIV_LOCK = threading.Lock()


def _arxiv_rate_wait():
    """export.arxiv.org 官方礼貌上限：同一客户端 ≥3 秒/请求（仅 arXiv 查询互相控频）。
    v1.10：加锁——并行 worker 下也保持全局限速（先到者持锁等待，计时刻整体串行）。"""
    with _ARXIV_LOCK:
        wait = 3.0 - (time.time() - _ARXIV_LAST[0])
        if wait > 0:
            time.sleep(wait)
        _ARXIV_LAST[0] = time.time()


def _arxiv_landing_fallback(arxiv_id: str, title: str, timeout: float,
                            api_err: str) -> tuple:
    """v1.11 arXiv 第二源 fallback（判定确定性保卫）：export.arxiv.org API 偶发
    406/403——批内多条 arXiv 引用时即便有 3 秒全局控频仍可撞上其反机器人窗口
    （实测单发全 200、批内稳定 406）。此前 API 失败即静默跳过内容核验，导致同一
    引用两次运行判定漂移（verified↔partial，GESIS 立场论文 arXiv:2607.22693
    批评的「inconsistent results across repeated runs of the same tool」）。
    fallback 拉官方着陆页 arxiv.org/abs/<id>（权威层）做标题比对，恢复确定性，
    并补齐与 DOI 路径（S2 第二源）的对称性。着陆页也不可达（全网降级特征）→
    维持可达性路径判定，但 note 明示「元数据核验未完成」，不静默。
    返回 (adjust, note, matched)，语义同 arxiv_metadata_match。"""
    landing = "https://arxiv.org/abs/" + quote(arxiv_id, safe="")
    if ssrf_blocked(landing):  # 与 wayback 同款守卫（域名固定，防御性一致）
        return "", (f"arXiv 元数据获取失败（{api_err}），着陆页核验跳过（SSRF 防护），"
                    "元数据核验未完成"), False
    if _cb_open(landing):
        return "", (f"arXiv 元数据获取失败（{api_err}），着陆页核验跳过（断路器/降级），"
                    "元数据核验未完成"), False
    req = urllib.request.Request(
        landing,
        headers={"User-Agent": f"Mozilla/5.0 (compatible; cite-holmes/{VERSION};"
                               " +verified-deep-research)",
                 "Accept": "text/html"})
    html_text, err = None, ""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html_text = resp.read().decode("utf-8", "ignore")
        _cb_record(landing, False)
    except urllib.error.HTTPError as e:
        # 站点有响应（HTTP 层失败）——走熔断清零记账，不计全局传输失败（与
        # _cb_record 的 degrade 语义一致：arxiv.org 可达≠全网通，不能误判降级）
        _cb_record(landing, False)
        if e.code == 404:
            # 官方着陆页 404 = 官方库查无该 ID（与 verify_one 的 abs 域 404 判定一致）
            return "invalid", (f"arXiv 元数据 API 失败（{api_err}）后官方着陆页亦 404 → "
                               "官方库查无该 ID，疑似编造引用"), False
        err = f"HTTP {e.code}"
    except Exception as e:  # 传输层失败（超时/DNS/拒连）——如实记账
        _cb_record(landing, True)
        err = type(e).__name__
    if html_text is None:
        return "", (f"arXiv 元数据获取失败（{api_err}）且官方着陆页不可达（{err}），"
                    "元数据核验未完成——本条仅按可达性/结构判定"), False
    m = re.search(r"<title>(.*?)</title>", html_text, re.S | re.IGNORECASE)
    if not m:
        return "", (f"arXiv 元数据获取失败（{api_err}），着陆页无标题可比对，"
                    "元数据核验未完成"), False
    page_title = re.sub(r"\s+", " ", m.group(1)).strip()
    # arXiv abs 页 <title> 形如 "[2607.22693] 标题"——剥掉 ID 前缀再比对
    page_title = re.sub(r"^\[" + re.escape(arxiv_id) + r"\]\s*", "", page_title,
                        count=1)
    sim = difflib.SequenceMatcher(None, (title or "").lower(),
                                  page_title.lower()).ratio()
    if title and sim < 0.50:
        return "invalid", (f"arXiv 元数据 API 失败（{api_err}），官方着陆页标题相似度"
                           f"仅 {sim:.2f} → ID 指向的不是这篇论文，疑似错引"
                           f"（arXiv 实际为《{page_title[:60]}》）"), True
    if title and sim < 0.82:
        return "partial", (f"arXiv 元数据 API 失败（{api_err}），官方着陆页标题相似度 "
                           f"{sim:.2f}，建议人工复核"), True
    note = (f"arXiv 元数据 API 不稳（{api_err}），经官方着陆页标题比对确认"
            + (f"（相似度 {sim:.2f}）" if title else "（引用未提供标题，仅确认存在）"))
    return "", note, True


def arxiv_metadata_match(arxiv_id: str, title: str, year, timeout: float) -> tuple:
    """arXiv ID 元数据交叉验证（v1.5）：export.arxiv.org 官方 API 取登记的 Atom 元数据，
    与引用声称的标题/年份比对——复用 DOI 的 0.50/0.82 相似度阈值体系。
    查无记录/格式错误的 ID 直接判 invalid（疑似编造），调用方（verify_one）保证
    该判定先于可达性检查，假 ID 不会被误判为 unreachable。
    返回 (adjust, note, matched)：adjust ∈ {"", "partial", "invalid"}；
    matched=True 表示元数据成功取得且与声称标题一致。"""
    import xml.etree.ElementTree as ET
    ns = {"a": "http://www.w3.org/2005/Atom",
          "ax": "http://arxiv.org/schemas/atom"}
    api_url = ("https://export.arxiv.org/api/query?id_list="
               + quote(arxiv_id, safe="") + "&max_results=1")
    if _cb_open(api_url):
        return "", _cb_skip_note(api_url) + "，未做 arXiv 元数据核验", False
    _arxiv_rate_wait()
    ua_rot = [f"cite-holmes/{VERSION}; +verified-deep-research",
              f"Mozilla/5.0 (compatible; cite-holmes/{VERSION}; +verified-deep-research)"]
    xml_text, fetch_err = None, ""
    for attempt in range(2):
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": ua_rot[min(attempt, 1)]})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                xml_text = resp.read().decode("utf-8", "ignore")
            fetch_err = ""
            _cb_record(api_url, False)
            break
        except urllib.error.HTTPError as e:
            _cb_record(api_url, False)
            fetch_err = f"HTTP {e.code}"
        except Exception as e:
            fetch_err = type(e).__name__
        if attempt == 0:
            # v1.11 指数退避：406 反爬窗口对短间隔敏感（3s 仍撞），首败后多等 5s
            # 再守 3s 礼貌时隙；sleep 在锁外，不占其他 worker 的限速时隙
            time.sleep(5)
            _arxiv_rate_wait()  # 重试同样守 3 秒礼貌上限（v1.5 评审修正）
    if xml_text is None:
        _cb_record(api_url, True)  # 整次调用只记 1 次传输失败
        # v1.11：不再静默跳过——fallback 官方着陆页恢复判定确定性
        return _arxiv_landing_fallback(arxiv_id, title, timeout, fetch_err)
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        # API 返回了非 XML（典型=反爬 HTML 页）——同样走着陆页 fallback
        return _arxiv_landing_fallback(arxiv_id, title, timeout,
                                       f"返回非预期格式（{e}）")
    entries = root.findall("a:entry", ns)
    # v1.11 评审修正：反爬/错误页常是格式良好的 HTML（合法 XML、可解析成功），
    # 但它不是 Atom feed——绝不能据此判「查无记录 → invalid」误杀真论文。
    # feed 根元素校验失败 → 着陆页 fallback 恢复确定性。
    if not (root.tag == "feed" or root.tag.endswith("}feed")):
        return _arxiv_landing_fallback(arxiv_id, title, timeout,
                                       "返回非 Atom 格式")
    if not entries:
        return "invalid", "arXiv ID 在官方 API 查无记录 → 疑似编造引用", False
    entry = entries[0]
    t = entry.find("a:title", ns)
    meta_title = re.sub(r"\s+", " ", (t.text or "")).strip() if t is not None else ""
    # 错误判据以官方 ax:error 元素为准；标题恰为 "Error" 的真实论文不误杀，
    # 仅当 summary 明确含格式错误文案时才作辅助判据（v1.5 评审修正）
    err = entry.find("ax:error", ns)
    summ = entry.find("a:summary", ns)
    err_text = ""
    if err is not None and err.text:
        err_text = err.text.strip()
    elif summ is not None and summ.text and "incorrect id format" in summ.text:
        err_text = summ.text.strip()
    if err_text:
        return "invalid", f"arXiv 官方 API 拒绝该 ID（{err_text[:60]}）→ 疑似编造引用", False
    pub = entry.find("a:published", ns)
    meta_year = None
    if pub is not None and pub.text:
        m = re.match(r"(\d{4})", pub.text.strip())
        if m:
            meta_year = int(m.group(1))
    sim = difflib.SequenceMatcher(None, (title or "").lower(),
                                  meta_title.lower()).ratio()
    # v2.0.0 arXiv 版本二级核验(零额外请求):entry id 自带版本号,与声称版本比对。
    # 引用未指定版本且最新版>1 → 提示「该论文存在多个修订版,引用未指定」;
    # 引用指定了旧版且最新版更高 → 提示可能有修订(同一响应内取数,零网络成本)。
    ver_note = ""
    eid = entry.find("a:id", ns)
    latest_v = None
    if eid is not None and eid.text:
        vm = re.search(r"v(\d+)$", eid.text.strip())
        if vm:
            latest_v = int(vm.group(1))
    claimed_v = None
    cm = re.search(r"v(\d+)$", arxiv_id.strip())
    if cm:
        claimed_v = int(cm.group(1))
    if latest_v and latest_v > 1:
        if claimed_v is None:
            ver_note = f"；注意：该论文已有 {latest_v} 个修订版本，引用未指定版本（arXiv 默认解析最新版）"
        elif claimed_v < latest_v:
            ver_note = (f"；注意：引用指向 v{claimed_v}，最新版为 v{latest_v}"
                        "——请确认引用的是预期版本（旧版可能含未修正内容）")
    if not title:
        return "", (f"arXiv 元数据核验完成（引用未提供标题，无法比对；登记年份 "
                    f"{meta_year or '未知'}）{ver_note}"), True
    # v3.15 文字系统守卫（与 DOI 路径同规）
    if sim < 0.50 and _script_family(title) not in ("none", _script_family(meta_title)):
        return "partial", (f"跨语言标题无法机器比对（相似度 {sim:.2f} 不作编造依据）"
                           "→ 建议人工核对"), True
    if sim < 0.50:
        return "invalid", (f"arXiv 元数据标题相似度仅 {sim:.2f} → ID 指向的不是这篇论文，"
                           f"疑似编造或错引（arXiv 实际为《{meta_title[:60]}》）"), True
    year_note = ""
    if meta_year and year:
        try:
            if abs(int(year) - int(meta_year)) >= 2:
                year_note = f"；年份不符（声称 {year} vs arXiv 登记 {meta_year}）"
        except (TypeError, ValueError):
            pass
    if sim < 0.82:
        return "partial", f"arXiv 元数据标题相似度 {sim:.2f}，建议人工复核{year_note}{ver_note}", True
    return "", f"arXiv 元数据核验一致（相似度 {sim:.2f}）{year_note}{ver_note}", True


def wayback_available(url: str, timeout: float) -> str:
    """v1.5 unreachable 存档兜底：查 Wayback Machine 是否有历史存档。
    有 → 返回「Wayback 存档可用（YYYY-MM-DD）：<存档URL>（人工复核可对照）」；
    无存档/查询失败 → 返回 ""（静默跳过，不加额外文案）。SSRF 字面量防护同样
    适用——内网/保留地址不外发到 archive.org。"""
    if ssrf_blocked(url):
        return ""
    # 实测教训：archive.org 对全量百分号编码的 url 参数不匹配（原样 200+快照，
    # %3A%2F 编码形式 200 但快照集为空）——必须原文直传，仅编码破坏外层查询的字符
    q = quote(url, safe=":/?&=#%@+!$,;'~()*[]-._")
    wb_url = ("https://archive.org/wayback/available?url=" + q)
    # 断路器看真正的外呼对象 archive.org（v1.6 二轮评审 P1 修正）——
    # 目标主机熔断不影响存档查询（死站查存档正是本函数的主用例）
    if _cb_open(wb_url):
        return ""
    req = urllib.request.Request(
        wb_url,
        headers={"User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                j = json.loads(resp.read().decode("utf-8", "ignore"))
            _cb_record(wb_url, False)
            closest = (j.get("archived_snapshots") or {}).get("closest") or {}
            if closest.get("available") and closest.get("url"):
                ts = str(closest.get("timestamp") or "")
                nice = f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}" if len(ts) >= 8 else ts
                return f"Wayback 存档可用（{nice}）：{closest['url']}（人工复核可对照）"
            return ""  # 有明确响应但无存档：确定性结果，不重试
        except urllib.error.HTTPError as e:
            _cb_record(wb_url, False)
            if e.code == 429 and attempt == 0:
                time.sleep(3.0)  # archive.org 对公共 IP 常见限流：退避一次
                continue
            return ""
        except Exception:
            _cb_record(wb_url, True)
            return ""
    return ""


def check_url(url: str, timeout: float, retries: int = 1) -> tuple:
    """返回 (reachable, status, note)。reachable 以 2xx/3xx/429(反爬) 计。
    瞬态网络错误（超时/连接重置）自动重试一次——国内网络偶发抖动不误判。
    内网/环回地址直接拒绝（SSRF 防护），不发起请求。
    v1.6：主机断路器生效；传输失败按成因给可操作话术（超时给 --timeout 建议）。"""
    if ssrf_blocked(url):
        return False, None, "内网/保留地址，验证请求已拒绝（SSRF 防护）"
    if _cb_open(url):
        return False, None, _cb_skip_note(url)
    note = ""
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, method="HEAD", headers={
            "User-Agent": f"Mozilla/5.0 (compatible; cite-holmes/{VERSION}; +verified-deep-research)",
            "Accept": "*/*",
        })
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
        transient = False
        for method in ("HEAD", "GET"):
            try:
                req.method = method
                with opener.open(req, timeout=timeout) as resp:
                    _cb_record(url, False)
                    return True, resp.status, f"{method} {resp.status}"
            except urllib.error.HTTPError as e:
                _cb_record(url, False)  # 站点有响应：不算传输失败
                if method == "HEAD" and e.code in (403, 405, 501):
                    continue  # 站点拒绝 HEAD，降级 GET 重试
                if e.code == 429:
                    return True, 429, "HTTP 429（反爬限流，站点实际存在）"
                return False, e.code, f"HTTP {e.code}（站点拒绝或页面不存在）"
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                if method == "HEAD":
                    continue
                transient = True
                msg = str(e)
                if isinstance(e, TimeoutError) or "timed out" in msg or "timeout" in msg.lower():
                    note = "连接超时（站点慢或网络受限），建议 --timeout 20 重试"
                elif ("getaddrinfo" in msg or "name or service" in msg.lower()
                        or "no address" in msg.lower()):
                    note = "域名无法解析，连接失败（站点可能已下线或被网络拦截）"
                elif "refused" in msg or "reset" in msg.lower():
                    note = "连接被拒/重置（站点或网络问题）"
                else:
                    note = f"网络异常：{e}"[:120]
            except ValueError as e:
                return False, None, f"URL 格式无效：{e}"[:120]
        if transient and attempt < retries:
            time.sleep(1.5)  # 瞬态抖动稍候重试
    # 重试耗尽仍失败：每次 check_url 调用只记 1 次传输失败（重试是同一逻辑失败，
    # 逐次记录会导致一次调用即熔断）
    _cb_record(url, True)
    return False, None, note or "连接失败（站点不可达、域名不存在或网络受限）"


FIELD_ZH = {"title": "标题(title)", "url": "链接(url)", "source": "来源(source)", "year": "年份(year)"}


_RETRACTION_CACHE = [None]  # 惰性加载:--retraction-cache 指向 JSON 索引
# {doi_lower: {"date","type","reason"}}(Crossref GitLab 官方 dump 构建,63k+ 条)


def _retraction_local(doi: str):
    """v3.2.0 本地撤稿缓存命中查询(零网络)。未配置/未命中返回 None。"""
    path = _OPTS.get("retraction_cache") or ""
    if not path:
        return None
    if _RETRACTION_CACHE[0] is None:
        try:
            with open(os.path.expanduser(path), encoding="utf-8") as f:
                _RETRACTION_CACHE[0] = json.load(f) or {}
        except Exception:
            _RETRACTION_CACHE[0] = {}  # 坏文件=视为空缓存,不炸主流程
    return _RETRACTION_CACHE[0].get(doi.strip().lower())


def _retraction_classify(raw_type: str) -> str:
    """v4.1.0 撤稿通告类型归一化（Crossref updated-by type 与 RWDB dump 字符串
    两种来源统一到六类）。返回 ∈ {"retraction", "partial_retraction", "withdrawal",
    "expression_of_concern", "correction", ""}（未识别返回小写原文，调用方按
    未分档处理——查无永不判死同样适用于「不认识的通告类型」）。"""
    t = (raw_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    if t in ("retraction", "retraction_notice", "retract_and_republish",
             "retraction_of_publication"):
        return "retraction"
    if t in ("partial_retraction", "partial_retraction_notice"):
        return "partial_retraction"
    if t in ("withdraw", "withdrawal", "remove", "removal"):
        return "withdrawal"
    if t in ("expression_of_concern", "expressions_of_concern"):
        return "expression_of_concern"
    if t in ("correction", "erratum", "corrigendum", "amendment"):
        return "correction"
    return t


def _retraction_nature_note(nature: str, when: str, notice: str,
                            source_label: str) -> str:
    """v4.1.0 按通告分档生成中文注记（降级语义由调用方统一接线）。"""
    when_note = f"（{when}）" if when else ""
    extra = f"，通告 {notice}" if notice else ""
    if nature == "retraction":
        return (f"论文已撤稿（{source_label}{when_note}{extra}）"
                "→ 不得作为有效证据引用")
    if nature == "partial_retraction":
        return (f"论文部分撤稿（{source_label}{when_note}{extra}）——撤稿部分"
                "不得作为证据，请人工核对结论边界")
    if nature == "withdrawal":
        return (f"论文已被出版方撤回（{source_label}{when_note}{extra}）"
                "→ 不得作为有效证据引用")
    if nature == "expression_of_concern":
        return (f"该文存在编辑关注通告 Expression of Concern"
                f"（{source_label}{when_note}{extra}）——证据效力存疑，转人工复核")
    if nature == "correction":
        return (f"该文存在更正/勘误通告（{source_label}{when_note}{extra}）"
                "——仅提示引用时留意勘误内容，不影响有效性判定")
    return f"存在出版方通告（{nature}，{source_label}{when_note}{extra}）"


def crossref_retraction_check(doi: str, timeout: float) -> dict:
    """v1.8 撤稿检测：Crossref REST API（Retraction Watch 数据，免费/每日更新）。
    v3.2.0：--retraction-cache 配置本地索引(GitLab 官方 dump 构建)时先查本地
    (零网络/离线可用),未命中再走网络拿最新状态。
    v4.1.0 通告分档：updated-by/type 细分（撤稿/部分撤稿/撤回/EoC/更正）——
    原二元判定对「编辑关注通告」完全漏抓（医学场景 EoC 论文不应继续当作
    干净证据引用；JMIR 2026 实证 AI 工具单靠自身抓不全撤稿文献）。
    查询失败一律静默跳过（绝不因检查失败惩罚引用）——但 v4.1.0 起
    check_failed=True 可观测（传输失败≠「干净」，报告层注明检查未完成）。

    返回 dict：{"retracted": bool,            # 撤稿族（retraction/partial/withdrawal）
                "nature": str,                # 六类分档（_retraction_classify）
                "notice_doi": str, "when": str,
                "source": "local"|"crossref"|"",
                "check_failed": bool}         # 传输失败（重试耗尽）——非「未撤稿」"""
    failed = {"retracted": False, "nature": "", "notice_doi": "", "when": "",
              "source": "", "check_failed": True}
    clean = {"retracted": False, "nature": "", "notice_doi": "", "when": "",
             "source": "", "check_failed": False}
    hit = _retraction_local(doi)
    if hit is not None:
        raw_date = (hit.get("date") or "").split(" 0:00")[0]  # CSV 时间残渣剥除
        nature = _retraction_classify(hit.get("type") or "Retraction")
        family = nature in ("retraction", "partial_retraction", "withdrawal")
        return {"retracted": family, "nature": nature,
                "notice_doi": "", "when": raw_date, "source": "local",
                "check_failed": False}
    mailto = _OPTS.get("mailto") or ""
    url = f"https://api.crossref.org/works/{quote(doi, safe='()/')}"
    if mailto:
        url += f"?mailto={quote(mailto, safe='@')}"
    if _cb_open(url):
        return dict(clean)
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research "
                                        "(https://skillhub.cn/skills/cite-holmes)"})
        with _urlopen_retry(req, timeout) as resp:
            m = (json.loads(resp.read().decode("utf-8", "ignore")) or {}).get("message") or {}
        _cb_record(url, False)
        for item in m.get("updated-by") or []:
            if not isinstance(item, dict):
                continue
            nature = _retraction_classify(item.get("type") or "")
            if not nature:
                continue
            notice = item.get("DOI") or ""
            when = ((item.get("updated") or {}).get("date-time") or "")[:10]
            if nature in ("retraction", "partial_retraction", "withdrawal"):
                return {"retracted": True, "nature": nature, "notice_doi": notice,
                        "when": when, "source": "crossref", "check_failed": False}
            # EoC/更正：不升级为 retracted，但分档记录（EoC 由调用方降级转人工）
            clean.update(nature=nature, notice_doi=notice, when=when,
                         source="crossref")
        return dict(clean)
    except urllib.error.HTTPError:
        _cb_record(url, False, degrade=False)  # 站点有响应（含 429 限流）：不计入全局降级
        return dict(clean)
    except Exception:
        _cb_record(url, True)
        return dict(failed)


def openalex_works_lookup(title: str, year, timeout: float) -> tuple:
    """v4.3.0 OpenAlex 书目检索升级版：确认存在性 + 候选 DOI 锚。

    背景（TA 表在线甄别实锤）：39 条候选中文医学期刊映射仅 18 条有 PubMed 收录——
    非 MEDLINE 期刊（中华神经科杂志等 21 条）与万方系期刊的引用此前无任何官方
    核验通路。本函数把 v1.8 的「只确认」升级为「找锚→验锚」链的前半程：
    OpenAlex 检索命中（_title_sim ≥0.82 且年份相容）即提取该记录的 DOI，
    交给 DOI.org 权威核验（verify_one 接线）——OpenAlex 只当索引用，
    判定证据全部来自注册库，聚合库质量参差不影响判定权威性。
    无 DOI 候选或相似度不足时维持 v1.8 语义（确认→partial；查无永不判死）。

    返回 (note, confirmed, doi_candidate)。"""
    if len((title or "").strip()) < 18:
        return "", False, ""
    q = quote(title.strip(), safe="")
    url = (f"https://api.openalex.org/works?search={q}&per-page=3"
           "&select=display_name,publication_year,doi")
    key = _OPTS.get("openalex_key") or ""
    if key:
        url += f"&api_key={quote(key, safe='')}"
    try:
        if _cb_open(url):
            return "", False, ""
        req = urllib.request.Request(
            url, headers={"User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            _cb_record(url, False)
            results = (json.loads(resp.read().decode("utf-8", "ignore"))
                       or {}).get("results") or []
        if not results:
            return "OpenAlex 未检索到明显匹配条目（可能未被收录，不作为编造依据）", False, ""
        try:
            year_i = int(str(year)) if year else None
        except (TypeError, ValueError):
            year_i = None
        best = None  # (sim, w)
        for w in results:
            mt = re.sub(r"\s+", " ", str(w.get("display_name") or "")).strip()
            if not mt:
                continue
            sim = _title_sim(title, mt)
            my = w.get("publication_year")
            year_ok = (not year_i) or (not my) or abs(year_i - int(my)) <= 1
            if year_ok and (best is None or sim > best[0]):
                best = (sim, w)
        if best is None:
            return ("OpenAlex 未检索到明显匹配条目（可能未被收录，不作为编造依据）",
                    False, "")
        sim, w = best
        mt = re.sub(r"\s+", " ", str(w.get("display_name") or "")).strip()
        my = w.get("publication_year")
        year_note = f"（{my}）" if my else ""
        doi_c = str(w.get("doi") or "").replace("https://doi.org/", "").strip()
        if sim >= 0.82:
            return (f"OpenAlex 书目确认存在：{mt[:60]}{year_note}", True, doi_c)
        if sim >= 0.60:
            return (f"OpenAlex 近似条目（标题相似度 {sim:.2f}）：{mt[:60]}{year_note}，"
                    "建议人工复核", False, "")
        return (f"OpenAlex 未检索到明显匹配（最高相似度 {sim:.2f}）；"
                "可能未被收录或较新，不作为编造依据", False, "")
    except urllib.error.HTTPError as e:
        _cb_record(url, True, degrade=False)  # 站点有响应：不计入全局网络降级
        if e.code == 403:
            return ("OpenAlex 拒绝访问（403）——2026 年起生产调用需 API key（无 key 每日仅 "
                    "100 credits 测试额度），可用 --openalex-key 或环境变量 OPENALEX_API_KEY 配置后重试",
                    False, "")
        if e.code == 429:
            return ("OpenAlex 限流（429）——生产调用建议 --openalex-key 或环境变量 "
                    "OPENALEX_API_KEY，稍后自动重试即可", False, "")
        return "", False, ""
    except Exception:
        _cb_record(url, True)
        return "", False, ""


def openalex_title_check(title: str, timeout: float) -> str:
    """v1.8 OpenAlex 书目级存在性核查（v4.3.0 起为 openalex_works_lookup 的
    兼容薄包装——丢弃 DOI 候选只返回注记，消除双实现漂移：同一题名两条路径
    必须给同一 confirmed 判定）。"""
    note, _confirmed, _doi = openalex_works_lookup(title, None, timeout)
    return note



def s2_citation_contexts(doi: str, timeout: float, max_samples: int = 3) -> dict:
    """v3.0.0 L3 引文语境层（Scite 平替的数据面）：对已 verified 的 DOI 引文拉取
    Semantic Scholar citations 端点(fields=contexts,intents,isInfluential)。
    产出「学界评价」素材：被引次数、引用语境摘录（后续文献如何提及本文）、
    intents 分类（background/methodology/result）、influential 标记。
    诚实边界：S2 contexts 覆盖率不均（实测部分空）——返回 coverage 字段如实标注，
    绝不装作全知。失败静默跳过（语境是增强信号,非判定依据）。CC BY 4.0 数据源。
    返回 {}（无数据）或 {"cited_by": int, "samples": [{"context","intents","influential","citing_title"}],
    "coverage": float}。"""
    url = ("https://api.semanticscholar.org/graph/v1/paper/DOI:"
           + quote(doi, safe="") + "/citations?fields=contexts,intents,isInfluential,title&limit=30")
    key = _OPTS.get("s2_key") or ""
    if key:
        url += "&api_key=" + quote(key, safe="")
    if _cb_open(url):
        return {}
    for attempt in range(2):
        _s2_rate_wait()
        try:
            headers = {"User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research"}
            if key:
                headers["x-api-key"] = key
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                _cb_record(url, False)
                data = (json.loads(resp.read().decode("utf-8", "ignore")) or {})
            break
        except urllib.error.HTTPError as e:
            _cb_record(url, False)
            if e.code == 429 and attempt == 0:
                time.sleep(6)  # S2 共享池限流常态：单次退避
                continue
            return {}
        except Exception:
            # 传输层错误（SSL EOF 等，弱网出口实测常见）：单次快速重试，仍败才记熔断
            if attempt == 0:
                time.sleep(2)
                continue
            _cb_record(url, True)
            return {}
    else:
        return {}
    items = data.get("data") or []
    if not items:
        return {"cited_by": 0, "samples": [], "coverage": 0.0}
    with_ctx = [it for it in items if (it.get("contexts") or [])]
    samples = []
    for it in with_ctx[:max_samples]:
        cp = it.get("citingPaper") or {}
        samples.append({"context": (it.get("contexts") or [""])[0][:220],
                        "intents": it.get("intents") or [],
                        "influential": bool(it.get("isInfluential")),
                        "citing_title": (cp.get("title") or "")[:80]})
    return {"cited_by": len(items), "samples": samples,
            "coverage": round(len(with_ctx) / len(items), 2)}


_S2_LAST = [0.0]
_S2_LOCK = threading.Lock()


def _s2_rate_wait():
    """免钥走 S2 共享限速池（约 100 请求/5 分钟），客户端串行化 ≥1.5 秒/请求。
    v1.10：加锁——并行 worker 下保持全局串行（否则并发线程同时读到旧时刻，
    一起通过等待，实际请求间隔被压缩）。"""
    with _S2_LOCK:
        wait = 1.5 - (time.time() - _S2_LAST[0])
        if wait > 0:
            time.sleep(wait)
        _S2_LAST[0] = time.time()


def s2_doi_confirm(doi: str, title: str, timeout: float) -> tuple:
    """v1.9 Semantic Scholar 第三源交叉确认——定位是「第二路正面信号」：
    仅在 DOI.org 元数据未能取得时（网络受限/瞬时 5xx）由 S2 再给一次存在性确认，
    着陆页反爬救回时与 DOI/arXiv 元数据同门槛（仍走层级/字段门控）。
    实测 S2 记录质量参差（存在把正式论文登记成期刊目录页的情况）——因此
    ①只确认不降级：标题不一致一律静默，绝不下调判定；
    ②查无/限流/失败一律静默跳过（S2 收录不全，查无 ≠ 编造）。
    返回 (matched, note)。key 只走 x-api-key 头（query 参数会进代理日志）。"""
    if not (title or "").strip():
        return False, ""  # 无标题无从比对，不浪费限速调用
    url = ("https://api.semanticscholar.org/graph/v1/paper/DOI:"
           + quote(doi, safe="") + "?fields=title,year")
    key = _OPTS.get("s2_key") or ""
    if _cb_open(url):
        return False, ""
    _s2_rate_wait()
    try:
        headers = {"User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research"}
        if key:
            headers["x-api-key"] = key
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            _cb_record(url, False)
            j = json.loads(resp.read().decode("utf-8", "ignore")) or {}
    except urllib.error.HTTPError:
        _cb_record(url, False)  # 站点有响应（404/429 等）：不算传输失败
        return False, ""
    except Exception:
        _cb_record(url, True)
        return False, ""
    mt = re.sub(r"\s+", " ", str(j.get("title") or "")).strip()
    my = j.get("year")
    if not mt or not (title or "").strip():
        return False, ""
    t = title.strip().lower()
    mt_l = mt.lower()
    sim = difflib.SequenceMatcher(None, t, mt_l).ratio()
    pfx = difflib.SequenceMatcher(None, t, mt_l[:len(t)]).ratio() if len(mt_l) >= len(t) else 0.0
    if max(sim, pfx) < 0.82:
        return False, ""  # 不一致静默：绝不以 S2 的不一致作负面判据
    year_note = f"（{my}）" if my else ""
    return True, f"Semantic Scholar 交叉确认存在：{mt[:60]}{year_note}（DOI.org 之外的第二路确认）"


def s2_title_confirm(title: str, timeout: float) -> tuple:
    """v1.10 Semantic Scholar 标题检索确认——无 DOI/PMID/arXiv 引用（.bib 导入常见）
    的第三路正面信号（与 OpenAlex 书目核查并列，互为备份：两库收录面不同）。
    与 s2_doi_confirm 同纪律：只确认不降级——查无/限流/失败一律静默跳过，
    绝不以下调判定（S2 收录不全 + 记录质量参差）。
    实现细节（S2 官方文档确认）：/paper/search 的 query 为纯文本，连字符词
    （如 state-of-the-art）查询无结果——先把连字符归一为空格再编码。
    返回 (matched, note)。key 只走 x-api-key 头。"""
    t = (title or "").strip()
    if len(t) < 18:
        return False, ""  # 过短标题检索噪声大，不浪费限速调用
    q = quote(re.sub(r"[-\u2010-\u2015]+", " ", t), safe="")
    url = (f"https://api.semanticscholar.org/graph/v1/paper/search"
           f"?query={q}&fields=title,year&limit=1")
    key = _OPTS.get("s2_key") or ""
    if _cb_open(url):
        return False, ""
    _s2_rate_wait()
    try:
        headers = {"User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research"}
        if key:
            headers["x-api-key"] = key
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            _cb_record(url, False)
            j = json.loads(resp.read().decode("utf-8", "ignore")) or {}
    except urllib.error.HTTPError:
        _cb_record(url, False)  # 站点有响应（404/429 等）：不算传输失败
        return False, ""
    except Exception:
        _cb_record(url, True)
        return False, ""
    data = j.get("data")
    if not isinstance(data, list) or not data:
        return False, ""  # 查无 ≠ 编造（收录滞后），静默
    w = data[0] or {}
    mt = re.sub(r"\s+", " ", str(w.get("title") or "")).strip()
    my = w.get("year")
    if not mt:
        return False, ""
    t_l = t.lower()
    mt_l = mt.lower()
    sim = difflib.SequenceMatcher(None, t_l, mt_l).ratio()
    pfx = difflib.SequenceMatcher(None, t_l, mt_l[:len(t_l)]).ratio() if len(mt_l) >= len(t_l) else 0.0
    if max(sim, pfx) < 0.82:
        return False, ""  # 不一致静默：绝不以 S2 的不一致作负面判据
    year_note = f"（{my}）" if my else ""
    return True, f"Semantic Scholar 标题检索确认存在：{mt[:60]}{year_note}"


def missing_fields(ref: dict) -> list:
    miss = [f for f in REQUIRED_FIELDS if not ref.get(f)]
    if "url" in miss and (
            (ref.get("doi") and DOI_RE.match(str(ref["doi"]).strip())) or
            (ref.get("pmid") and PMID_RE.match(str(ref["pmid"]).strip())) or
            extract_arxiv_id(ref)):
        miss.remove("url")
    return [FIELD_ZH.get(f, f) for f in miss]


def ref_to_url(ref: dict) -> str:
    """url → doi → arxiv → pmid 四级解析，返回最终可检查的 URL。字段统一强转为字符串。"""
    url = str(ref.get("url") or "").strip()
    if url:
        return url
    doi = str(ref.get("doi") or "").strip()
    if doi and DOI_RE.match(doi):
        return f"https://doi.org/{doi}"
    arxiv = extract_arxiv_id(ref)
    if arxiv:
        return f"https://arxiv.org/abs/{arxiv}"
    pmid = str(ref.get("pmid") or "").strip()
    if pmid and PMID_RE.match(pmid):
        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    return ""


# ---------------- BibTeX 导入（v1.9，对标 Zotero/EndNote 工作流） ----------------

def _bib_unbrace(value: str) -> str:
    """BibTeX 字段值清理：还原常见 TeX 转义（\\& → & 等）、去花括号与转义残留、
    压缩空白。刻意不做重音展开（Schr\\"oder 类）——标题比对走模糊相似度，无需精确。"""
    v = re.sub(r"\\([{}&%$#_])", r"\1", str(value or ""))
    v = v.replace("{", "").replace("}", "").replace("\\", "")
    return re.sub(r"\s+", " ", v).strip()


def _bib_entry_to_ref(etype: str, f: dict) -> dict:
    """BibTeX 字段 → 引用 schema。source 依次取 journal/booktitle/journaltitle/
    publisher；howpublished 含 \\url 宏时只取链接不进 source（避免垃圾来源名）。"""
    def g(k):
        return _bib_unbrace(f.get(k, ""))

    url = g("url")
    if not url:
        for k in ("url", "howpublished", "note"):
            m = re.search(r"\\url\{([^}]+)\}", str(f.get(k) or ""))
            if m:
                url = m.group(1).strip()
                break
    src = (g("journal") or g("booktitle") or g("journaltitle") or g("publisher"))
    if not src:
        hp = str(f.get("howpublished") or "")
        if hp and "\\url" not in hp:
            src = _bib_unbrace(hp)
    ref = {"title": g("title"),
           # BibTeX 多作者分隔符 " and " 归一为逗号——姓氏提取按逗号分段
           "authors": g("author").replace(" and ", ", "), "source": src,
           "year": re.sub(r"[^0-9]", "", g("year"))[:4] or None,
           "doi": g("doi"), "url": url,
           "pmid": re.sub(r"[^0-9]", "", g("pmid"))}
    eprint = g("eprint")
    if eprint and g("archiveprefix").lower() in ("arxiv", ""):
        ref["arxiv"] = eprint
    return {k: v for k, v in ref.items() if v not in ("", None)} or {"title": ""}


def parse_bibtex(text: str) -> list:
    """v1.9 最小 BibTeX 解析器（纯 stdlib）：支持 @article/@inproceedings/@book/
    @misc 等常规条目、嵌套花括号值、引号值与多行字段。@comment/@preamble/@string
    跳过。解析不抛异常——坏条目降级为缺字段引用，由后续检查如实标注；
    完全无法解析时返回空列表（调用方给可操作报错）。"""
    refs = []
    i, n = 0, len(text)
    while i < n:
        if text[i] != "@":
            i += 1
            continue
        m = re.match(r"@([A-Za-z]+)\s*([{(])\s*([^,\s]*)\s*,", text[i:])
        if not m:
            i += 1
            continue
        etype = m.group(1).lower()
        close_ch = "}" if m.group(2) == "{" else ")"
        i += m.end()
        if etype in ("comment", "preamble", "string"):
            continue
        fields = {}
        depth = 1
        while i < n and depth > 0:
            ch = text[i]
            if ch == close_ch:
                depth -= 1
                i += 1
                if depth == 0:
                    break
                continue
            fm = re.match(r"\s*([A-Za-z][A-Za-z0-9_-]*)\s*=\s*", text[i:])
            if not fm:
                i += 1 if ch not in ", \t\r\n" else re.match(r"[, \t\r\n]+", text[i:]).end()
                continue
            i += fm.end()
            if i < n and text[i] == "{":  # 花括号值：计数嵌套
                k, d = i + 1, 1
                while k < n and d > 0:
                    if text[k] == "{":
                        d += 1
                    elif text[k] == "}":
                        d -= 1
                    k += 1
                raw = text[i + 1:k - 1]
                i = k
            elif i < n and text[i] == '"':  # 引号值（内部可含花括号）
                k = text.find('"', i + 1)
                k = n if k < 0 else k
                raw = text[i + 1:k]
                i = k + 1
            else:  # 裸值（数字/缩写）
                k = i
                while k < n and text[k] not in ",}\n)":
                    k += 1
                raw = text[i:k].strip()
                i = k
            fields[fm.group(1).lower()] = raw
            while i < n and text[i] in ", \t\r\n":
                i += 1
        if fields:
            refs.append(_bib_entry_to_ref(etype, fields))
    return refs


def load_refs_file(path: str) -> list:
    """--refs 加载：JSON 数组或 BibTeX（v1.9）。.bib 扩展名直接走 BibTeX 解析；
    JSON 解析失败且内容以 @ 开头时自动降级 BibTeX（用户存错扩展名也能跑）。"""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if path.lower().endswith(".bib"):
        refs = parse_bibtex(text)
        if not refs:
            raise ValueError("BibTeX 文件中没有解析到任何条目（应有 @article{...} 等）")
        return refs
    if path.lower().endswith((".md", ".markdown")):
        # v4.0.0 医学文档直接核验：markdown 参考文献节 Vancouver 条目提取
        refs = parse_markdown_refs(text)
        if not refs:
            raise ValueError("markdown 中未解析到编号参考文献条目（应有 '## 参考文献' 节与 '1. ' 编号行）")
        return refs
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if text.lstrip().startswith("@"):
            refs = parse_bibtex(text)
            if not refs:
                raise ValueError("内容以 @ 开头但 BibTeX 解析到 0 条，请检查文件格式")
            return refs
        raise


_REF_SECTION_RE = re.compile(
    r"(?:^|\n)#{0,6}\s*(?:\d+[.、]?\s*)?(?:参考文献|References)[^\n]*\n")


def parse_markdown_refs(text: str) -> list:
    """v4.0.0 从 markdown「参考文献」节提取 Vancouver 编号条目（医学文档主流形态：
    `1. **作者, et al.** 题名. *期刊*. 年;卷(期):页.`——无 DOI/PMID/URL）。
    提取的条目走 PubMed 题名反查通道（pubmed_title_reverse_lookup）获得官方核验。
    解析保守：无编号行/段数不足/题名过短的行跳过。

    v4.2.0（GB/T 7714 变体实测扩展）：16 条带内联 PMID 的 GB/T 著录全军覆没驱动——
    - 编号行支持 `[1] ` 方括号（与 `1. ` 并列，GB/T 最常见变体）；
    - 标题行支持裸「参考文献」行（无 # 前缀）；
    - 内联标识符提取：`PMID: 39429074` / `DOI: 10.xxx/yyy` 进 ref 字段——
      著录里带着官方锚，此前却被当无标识符引用盲查；
    - 卷(期):页提取 → volume/issue/pages（卷期页锚定通道原料）；
    - `[J]`/`[EB/OL]` 类型标记剥除；期刊段内「年, 卷(期): 页」残尾清理。"""
    refs = []
    m = _REF_SECTION_RE.search(text)
    body = text[m.end():] if m else text
    for raw in body.splitlines():
        line = re.sub(r"\*\*|\*|__|_", "", raw.strip())
        mm = re.match(r"^(?:\[(\d{1,3})\][.、]?|(\d{1,3})[.、)])\s+(.{10,})$", line)
        if not mm:
            continue
        rest = (mm.group(3) or "").strip()
        if not rest:
            continue
        # 缩写句点不劈（v4.6.0 dogfood 实锤：'U.S. Food and Drug Administration'
        # 被切分器劈开，机构名当了题名）——「单大写字母+.」紧跟的句点不切分；
        # 普通首字母缩略后的题名界（如 N H. Title）不受影响
        segs = [s.strip(" *") for s in re.split(r"(?<![A-Z]\.[A-Z])\.\s+", rest)
                if s.strip(" *")]
        if len(segs) < 2:
            continue
        year = None
        # 后随数字的年份排除（批准文号 H20093320 里的 2009 不是年份）
        ym = re.search(r"(19|20)\d{2}(?!\d)", rest)
        if ym:
            year = int(ym.group(0))
        # 无作者段变体判定：GB/T 允许题名先行著录（`题名[J]. 期刊, 年, 卷(期): 页.`，
        # 机构共识/指南常见）——segs[0] 以文献类型标记结尾即为题名段
        if re.search(r"\[[A-Z]{1,2}(?:/OL)?\]\s*$", segs[0] or ""):
            title, source = segs[0], (segs[1] if len(segs) >= 2 else "")
        elif len(segs) >= 3:
            title, source = segs[1], segs[2]
        else:
            title, source = segs[0], ""
        if source and re.fullmatch(r"(19|20)\d{2}.*", source):
            source = ""
        # 访问日期残段（"(2023)[2026-10-05]" 形态）不作期刊名
        if source and re.match(r"^\((?:19|20)\d{2}\)\[[\d-]+\]$", source):
            source = ""
        if len(title) < 15:
            continue
        # 文献类型标记剥除（[J]/[EB/OL]/[M]/[C] 等 GB/T 类型码）
        title = re.sub(r"\[[A-Z]{1,2}(?:/OL)?\]\s*$", "", title).strip()
        source = re.sub(r"\[[A-Z]{1,2}(?:/OL)?\]\s*$", "", source).strip()
        # 期刊段残尾清理（"中华儿科杂志, 2024, 62(11): 1030-1042" → 期刊名）
        source = re.sub(r"[,，]\s*(?:19|20)\d{2}\s*[,，]?.*$", "", source).strip(" .,，")
        entry = {"title": title, "source": source, "year": year}
        # 内联标识符提取（authoritative anchor 前置——ref_to_url 已支持 PMID→官方 URL）
        pm = re.search(r"PMID\s*[:：]?\s*(\d{6,9})", rest, re.I)
        if pm:
            entry["pmid"] = pm.group(1)
        dm = re.search(r"\b(10\.\d{4,9}/[^\s，,;；)]+)", rest)
        if dm:
            entry["doi"] = dm.group(1).rstrip(".,;)")
        # v4.6.0：EB/OL 著录的 URL 提取（说明书/指南/共识的中文医学文档高频形态）
        # ——仅当无 doi/pmid（强锚优先不遮蔽）；[EB/OL] 引用从裸 unverified 升
        # 「可达性+官方层级」判据
        if "doi" not in entry and "pmid" not in entry:
            um = re.search(r"https?://[^\s，,;；)\]。，＞>”（“]+", rest)
            if um:
                entry["url"] = um.group(0).rstrip(".>）")
        # 卷(期):页 锚定在年份之后提取（避免误抓随机数字）。
        # 实测形态：`2024, 62(11): 1030-1042` / `2014, 134(5): e1474-502` /
        #           `2020, 8: 218`（无期）/ `2020, 35(12)`（无页）
        lm = re.search(
            r"(?:19|20)\d{2}\s*[,，]\s*(\d{1,4})\s*(?:\((\d{1,4})\))?"
            r"(?:\s*[:：]\s*([A-Za-z]{0,2}\d+[A-Za-z0-9]*))?", rest)
        if lm:
            entry["volume"] = lm.group(1)
            entry["issue"] = lm.group(2) or ""
            entry["pages"] = lm.group(3) or ""
        refs.append(entry)
    return refs


def verify_one(ref: dict, idx: int, offline: bool, timeout: float, medical: bool = False) -> dict:
    def _s(v):
        return str(v) if v is not None else ""

    title_in = _s(ref.get("title"))
    out = {"index": idx, "title": title_in or "(无标题)",
           "url": _s(ref.get("url")).strip(),
           "doi": _s(ref.get("doi")).strip(), "pmid": _s(ref.get("pmid")).strip(),
           "arxiv": extract_arxiv_id(ref),
           "source": _s(ref.get("source")).strip(), "year": ref.get("year"),
           "tier": ref.get("tier") or "", "semantic": ref.get("semantic", ""),
           "verdict": "unverified", "http_status": None, "note": "", "needs_human_check": False,
           "checks": {},  # v1.9 透明工作底稿：逐项检查的结构化明细（随 JSON 报告/auditjson 导出）
           "semantic_audit": build_semantic_audit(ref)}  # v1.11 语义层底稿（dict 输入才非空）

    pmid = out["pmid"]
    doi_adj, doi_matched = "", False
    arxiv_adj, arxiv_matched = "", False
    retracted = False
    url = ref_to_url(ref)
    if not url:
        raw_arxiv = str(ref.get("arxiv") or "").strip()
        if raw_arxiv and not out["arxiv"]:
            out.update(verdict="invalid",
                       note="arxiv 字段格式无法识别（应为 YYMM.NNNNN 或 category/NNNNNNN）")
        else:
            # v3.4 外部独测合并(#2):无标识符引用先走标题检索(与 SKILL.md「查无≠编造」
            # 声明对齐)——确认存在→partial 保留;查无→unverified 转人工(诚实未知),
            # 不得以「缺标识符」判编造。离线模式维持原 invalid。
            t_claim = clean_title(str(ref.get("title") or "")).strip()
            if offline or not t_claim:
                out.update(verdict="invalid",
                           note="缺少 url 且无可解析的 doi/pmid/arxiv" +
                                ("（pmid 须为 6-9 位数字）" if pmid else ""))
                return out
            # v4.0.0 Vancouver 医学引用的官方核验通道（PubMed 题名反查）——
            # 置于 OpenAlex/S2 之前：它是唯一能给出「官方一致→verified」的无
            # 标识符通道；未命中静默，继续现有确认路径（只确认不降级不变）
            pm_adj, pm_note, pm_matched, rev_pmid, pm_net_err = pubmed_title_reverse_lookup(
                t_claim, str(ref.get("source") or ""), ref.get("year"),
                max(timeout, 20.0))  # 反查=esearch+esummary 两跳，单跳超时给足
            _eutils_open = any(d.get("open") for hk, d in _CB.items()
                               if "eutils" in hk)
            out["checks"]["pubmed_reverse"] = {
                "ran": True, "matched": pm_matched,
                "pmid": rev_pmid or None,
                "skipped_by_circuit": (not pm_matched and not pm_note
                                       and _eutils_open),
                # v4.1.0：传输失败与查无必须可区分（报告层按此注明「核验未完成」）
                "network_error": pm_net_err}
            if pm_note:
                out["note"] = (out["note"] + "；" if out["note"] else "") + pm_note
            if pm_matched and pm_adj == "":
                # 审计 P3 修复:PMID 锚结构化回填——bibtex/CSV 导出与批内去重可获取
                if not out.get("pmid"):
                    out["pmid"] = rev_pmid
                out.update(verdict="verified",
                           needs_human_check=False,
                           note=(out["note"] + "；" if out["note"] else "") +
                                "无标识符引用经 PubMed 官方题名反查核验一致，已回填 PMID 锚")
                return out
            if pm_adj == "partial":
                out.update(verdict="partial", needs_human_check=True)
                return out
            # v4.2.0 卷期页锚定（题名反查未命中后的第二无标识符通道）：
            # 期刊+年+卷(期):页 是 PubMed 官方引文定位器，语言无关——
            # 中文声称题名 vs 登记题名翻译差异不再阻断核验
            loc_adj, loc_note, loc_matched, loc_pmid, loc_err = pubmed_locator_lookup(
                out["source"], ref.get("year"), ref.get("volume"),
                ref.get("issue"), ref.get("pages"), max(timeout, 15.0),
                claimed_title=t_claim)
            out["checks"]["pubmed_locator"] = {
                "ran": bool(out["source"] and ref.get("volume") and ref.get("year")),
                "matched": loc_matched, "pmid": loc_pmid or None,
                "network_error": loc_err}
            if loc_note:
                out["note"] = (out["note"] + "；" if out["note"] else "") + loc_note
            if loc_matched and loc_adj == "":
                if not out.get("pmid"):
                    out["pmid"] = loc_pmid
                out.update(verdict="verified", needs_human_check=False,
                           note=(out["note"] + "；" if out["note"] else "") +
                                "无标识符引用经 PubMed 卷期页锚定核验一致，已回填 PMID 锚")
                return out
            oa_note, oa_confirmed, oa_doi = openalex_works_lookup(t_claim, ref.get("year"), timeout)
            out["checks"]["openalex"] = {"ran": True, "confirmed": oa_confirmed,
                                         "doi_candidate": oa_doi or None}
            s2_matched, s2_note = s2_title_confirm(t_claim, timeout)
            out["checks"]["s2_title"] = {"matched": s2_matched}
            if oa_note:
                out["note"] = (out["note"] + "；" if out["note"] else "") + oa_note
            if s2_note:
                out["note"] = (out["note"] + "；" if out["note"] else "") + s2_note
            # v4.3.0 找锚→验锚链：OpenAlex 确认且带候选 DOI → DOI.org 权威核验。
            # OpenAlex 只当索引（聚合库记录质量参差，v1.8 既有结论），判定证据
            # 全部来自注册库；标题不符按 DOI 通路语义判（错引不因「存在相似条目」
            # 放行）；撤稿检测照走，锚定通路不绕开安全检查。
            if oa_confirmed and oa_doi and not offline and DOI_RE.match(oa_doi):
                doi_adj2, note2, doi_m2, csl2 = doi_metadata_match(
                    oa_doi, clean_title(str(ref.get("title") or "")),
                    ref.get("year"), timeout,
                    str(ref.get("source") or ""),
                    str(ref.get("authors") or ""))
                out["checks"]["doi_metadata"] = {
                    "matched": doi_m2, "adjust": doi_adj2, "via": "openalex-anchor"}
                if csl2:
                    out["checks"]["doi_metadata"]["csl"] = csl2
                if note2:
                    out["note"] = (out["note"] + "；" if out["note"] else "") + note2
                ret2 = crossref_retraction_check(oa_doi, timeout)
                retracted = bool(ret2.get("retracted"))
                out["checks"]["retraction"] = ret2
                if ret2.get("nature"):
                    out["note"] = (out["note"] + "；" if out["note"] else "") + \
                        _retraction_nature_note(
                            ret2["nature"], ret2["when"], ret2["notice_doi"],
                            "本地 Retraction Watch 索引" if ret2.get("source") == "local"
                            else "Crossref/Retraction Watch")
                elif ret2.get("check_failed"):
                    out["note"] = (out["note"] + "；" if out["note"] else "") + \
                        "撤稿检查未完成（网络传输失败，重试后仍不通）——非「未撤稿」"
                if doi_adj2 == "invalid":
                    out.update(verdict="invalid", needs_human_check=True)
                    return out
                if doi_adj2 == "":
                    if not doi_m2:
                        # 审计 P0 修复：元数据获取失败/断路器跳过的 adjust="" 不等于
                        # 「核验一致」——CN 网络 doi.org 常态不通，此场景旧逻辑会把
                        # 失败当一致升 verified。诚实封顶 partial 转人工
                        out.update(verdict="partial", needs_human_check=True)
                        return out
                    if retracted or ret2.get("nature") == "expression_of_concern":
                        out.update(verdict="partial", needs_human_check=True)
                    else:
                        if not out.get("doi"):
                            out["doi"] = oa_doi
                        out.update(verdict="verified", needs_human_check=False,
                                   note=(out["note"] + "；" if out["note"] else "") +
                                        "无标识符引用经 OpenAlex 找锚、DOI.org 权威核验一致，已回填 DOI 锚")
                    return out
                # doi_adj2 == "partial"（跨语言桥接未命中/相似度居中）→ 封顶 partial
                out.update(verdict="partial", needs_human_check=True)
                return out
            if oa_confirmed:
                out.update(verdict="partial", needs_human_check=True)
                return out
            out.update(verdict="unverified", needs_human_check=True,
                       note=(out["note"] + "；" if out["note"] else "") +
                            "无标识符且两库标题检索未确认——未知状态转人工，不作编造判定")
            return out
        return out
    if not re.match(r"^https?://", url, re.IGNORECASE):
        out.update(verdict="invalid", note=f"url 非 http(s) 格式: {url[:60]}")
        return out

    if not out["tier"]:
        out["tier"] = classify_tier(url, medical)
    out["url"] = url
    if medical and out["tier"] in ("community", "social", "blog"):
        out["note"] = "医学模式：社区/社交/博客层来源不得支撑医学结论（仅作线索）"
    elif medical and out["tier"] == "preprint":
        out["note"] = "医学模式：预印本未经同行评审，证据强度受限"

    if offline:
        out["note"] = (out["note"] + "；" if out["note"] else "") + "offline 模式未做可达性检查"
    else:
        # 带 DOI 的引用优先走元数据核验：能同时判定「存在性」与「内容匹配」，
        # 且假 DOI 的 404 在这里直接判 invalid（不会先被可达性检查误判为 unreachable）
        retracted = False
        s2_matched = False
        if out["doi"] and DOI_RE.match(out["doi"]):
            doi_adj, note, doi_matched, doi_csl = doi_metadata_match(
                out["doi"], clean_title(str(ref.get("title") or "")), ref.get("year"), timeout,
                str(ref.get("source") or ""),
                str(ref.get("authors") or ""))
            out["checks"]["doi_metadata"] = {"matched": doi_matched, "adjust": doi_adj}
            # v3.6:注册库权威元数据(GB/T 7714 导出原料)——仅 matched 时可信
            if doi_matched and doi_csl:
                out["checks"]["doi_metadata"]["csl"] = doi_csl
            if note:
                out["note"] = (out["note"] + "；" if out["note"] else "") + note
            if doi_adj == "invalid":
                out.update(verdict="invalid", needs_human_check=True)
                return out
            # v1.9 Semantic Scholar 第三源：DOI.org 元数据没拿到时（网络受限/瞬时故障）
            # 的第二路正面确认——只确认不降级（S2 记录质量参差，不一致静默）
            if not doi_matched:
                s2_matched, s2note = s2_doi_confirm(
                    out["doi"], clean_title(str(ref.get("title") or "")), timeout)
                out["checks"]["s2"] = {"matched": s2_matched}
                if s2note:
                    out["note"] = (out["note"] + "；" if out["note"] else "") + s2note
            # v1.8 撤稿检测：真实存在的论文也可能是撤稿状态，不得作为有效证据
            # v4.1.0 分档：撤稿族降级转人工；EoC 同闸转人工；更正仅提示；
            # check_failed=True 可观测（传输失败≠「未撤稿」，报告层注明）
            ret = crossref_retraction_check(out["doi"], timeout)
            retracted = bool(ret.get("retracted"))
            out["checks"]["retraction"] = ret
            if ret.get("nature"):
                retnote = _retraction_nature_note(
                    ret["nature"], ret["when"], ret["notice_doi"],
                    "本地 Retraction Watch 索引" if ret.get("source") == "local"
                    else "Crossref/Retraction Watch")
            elif ret.get("check_failed"):
                retnote = ("撤稿检查未完成（网络传输失败，重试后仍不通）——"
                           "本条结果不含撤稿核验，非「未撤稿」")
            else:
                retnote = ""
            if retnote:
                out["note"] = (out["note"] + "；" if out["note"] else "") + retnote
                if retracted:  # EoC 的转人工在统一降级闸处理；更正提示不强制转人工
                    out["needs_human_check"] = True
        # 带 arXiv ID 的引用同层核验（无 DOI 时）：官方 API 查无记录 → 直接 invalid，
        # 同样先于可达性检查，避免假 ID 被误判为 unreachable（v1.5）
        elif out["arxiv"]:
            arxiv_adj, note, arxiv_matched = arxiv_metadata_match(
                out["arxiv"], clean_title(str(ref.get("title") or "")), ref.get("year"), timeout)
            out["checks"]["arxiv_metadata"] = {"matched": arxiv_matched, "adjust": arxiv_adj}
            if note:
                out["note"] = (out["note"] + "；" if out["note"] else "") + note
            if arxiv_adj == "invalid":
                out.update(verdict="invalid", needs_human_check=True)
                return out
        # v1.6：双键引用（doi+pmid）做交叉一致性——两键各自真实也可能拼接造假，
        # 元数据层判定，先于可达性检查
        if (out["doi"] and DOI_RE.match(out["doi"])
                and out["pmid"] and PMID_RE.match(out["pmid"])):
            xadj, xnote = pmid_doi_crosscheck(out["pmid"], out["doi"], timeout)
            out["checks"]["doi_pmid_crosscheck"] = {"done": True}
            if xnote:
                out["note"] = (out["note"] + "；" if out["note"] else "") + xnote
            if xadj == "invalid":
                out.update(verdict="invalid", needs_human_check=True)
                return out
        reachable, status, note = check_url(url, timeout)
        out["http_status"] = status
        out["checks"]["url"] = {"reachable": reachable, "status": status}
        out["note"] = (out["note"] + "；" if out["note"] else "") + note
        if not reachable:
            # DOI/arXiv 注册元数据或 S2 交叉已确认存在 + 着陆页反爬（403/429）→
            # 引用存在性已被官方注册库证实，不能因反爬误判为 unreachable。评审修正：
            # 救回不再无条件盖 verified——层级/字段门控照走，防"真 ID + 403 博客链接"骗过权威层
            if (doi_matched or arxiv_matched or s2_matched) and status in (403, 429):
                label = ("DOI" if doi_matched else "arXiv" if arxiv_matched
                         else "Semantic Scholar")
                out["note"] = (out["note"] + "；" if out["note"] else "") + \
                    f"着陆页反爬（HTTP {status}），但 {label} 注册元数据核验一致——存在性已确认"
                # v1.5 二轮评审 P1：元数据本身判 partial（相似度 0.50-0.82）时，
                # 救回同样不得给 verified——与 200 路径末尾的降级不变量保持一致，
                # 防"疑似错引"借反爬救回混进 verified（进而流入 bibtex/strict CI）
                if (out["tier"] in TRUSTED_TIERS and not missing_fields(ref)
                        and doi_adj != "partial" and arxiv_adj != "partial"):
                    out["verdict"] = "verified"
                else:
                    out["verdict"] = "partial"
                # v4.1.0：撤稿族与 EoC 同闸——反爬救回不得把带通告的文献盖成 verified
                if (retracted or (out["checks"].get("retraction") or {}).get("nature")
                        == "expression_of_concern") and out["verdict"] == "verified":
                    out["verdict"] = "partial"
                    out["needs_human_check"] = True
                return out
            # v1.5：arXiv ID 以 arxiv.org/abs 为官方解析器——官方站可达却对该 ID
            # 返回 404 → 官方库查无此 ID，判 invalid（官方 API 被墙时兜底）。
            # 评审修正（P0）：仅当元数据核验未能确认存在时才允许此判定——
            # 官方 API 刚确认过存在时，脏 URL 的 404 不得反转成 invalid；
            # 此逻辑仅适用于解析器域名，普通网页 404 仍是 unreachable
            elif status == 404 and not (doi_matched or arxiv_matched) and re.match(
                    r"^https?://(?:www\.|export\.)?arxiv\.org/(?:abs|pdf)/", url, re.IGNORECASE):
                out.update(verdict="invalid", needs_human_check=True,
                           note=(out["note"] + "；" if out["note"] else "") +
                                "arXiv 官方站对该 ID 返回 404（官方库查无）→ 疑似编造引用")
                return out
            out.update(verdict="unreachable", needs_human_check=True,
                       note=(out["note"] + "；" if out["note"] else "") + "可能反爬/临时故障，不等于不存在")
            # v1.5 存档兜底：不可达 ≠ 不存在，附 Wayback 存档链给人工复核做对照
            wb = wayback_available(url, timeout)
            out["checks"]["wayback"] = {"archive_found": bool(wb)}
            if wb:
                out["note"] = (out["note"] + "；" if out["note"] else "") + wb
            return out
        m = PUBMED_URL_RE.match(url)
        if m:
            pmid_ok, pmid_note = pubmed_pmid_exists(m.group(1), timeout)
            if not pmid_ok:
                out.update(verdict="invalid", needs_human_check=True,
                           note=(out["note"] + "；" if out["note"] else "") + pmid_note)
                return out
            out["note"] = (out["note"] + "；" if out["note"] else "") + pmid_note
            # v3.4 池:PMID 元数据核验(标题+期刊一致性)——此前 PMID-only 引用
            # 仅查存在性,真 PMID+假标题/假期刊拼接可过 verified(评审缺口)
            if not offline and (str(ref.get("title") or "").strip() or
                                str(ref.get("source") or "").strip()):
                padj, pnote, pmatched = pmid_metadata_match(
                    m.group(1), clean_title(str(ref.get("title") or "")),
                    str(ref.get("source") or ""), ref.get("year"), timeout)
                out["checks"]["pmid_metadata"] = {"matched": pmatched, "adjust": padj}
                if pnote:
                    out["note"] = (out["note"] + "；" if out["note"] else "") + pnote
                if padj == "invalid":
                    out.update(verdict="invalid", needs_human_check=True)
                    return out
                if padj == "partial":
                    # v4.2.0 跨语言佐证升级：标题不可比（跨文字系统）partial 时，
                    # 卷期页锚定若唯一命中**同一 PMID**——注册库亲自确认了
                    # 「该组卷期页 ↔ 该 PMID」，声称引用恰好给出同组定位器，
                    # 标题差异纯属翻译——证据充分，解除终局 partial 封顶
                    if "跨语言标题无法机器比对" in pnote and out["source"] \
                            and ref.get("volume") and ref.get("year"):
                        la, ln, lm_, lp, le = pubmed_locator_lookup(
                            out["source"], ref.get("year"), ref.get("volume"),
                            ref.get("issue"), ref.get("pages"), max(timeout, 15.0),
                            claimed_title=str(ref.get("title") or ""))
                        out["checks"]["pubmed_locator"] = {
                            "ran": True, "matched": lm_, "pmid": lp or None,
                            "network_error": le}
                        if ln:
                            out["note"] = (out["note"] + "；" if out["note"] else "") + ln
                        if lm_ and str(lp) == str(out["pmid"]):
                            out["checks"]["pmid_metadata"]["cross_lang_corroborated"] = True
                            out["note"] = (out["note"] + "；" if out["note"] else "") + \
                                "跨语言标题经卷期页锚定佐证（同一 PMID 唯一命中）——语言差异不作为编造依据"
                        else:
                            out.update(verdict="partial", needs_human_check=True)
                    else:
                        out.update(verdict="partial", needs_human_check=True)
        # v1.8 OpenAlex 书目级核查：无 DOI/PMID/arXiv 的引用多一路正面确认信号；
        # v1.10 S2 标题检索为并列第二路（两库收录面不同，互为备份；同样只确认不降级）
        if not out["doi"] and not out["pmid"] and not out["arxiv"]:
            oa_note = openalex_title_check(str(ref.get("title") or ""), timeout)
            out["checks"]["openalex"] = {"ran": True, "confirmed": "确认存在" in oa_note}
            if oa_note:
                out["note"] = (out["note"] + "；" if out["note"] else "") + oa_note
            s2t_matched, s2t_note = s2_title_confirm(clean_title(str(ref.get("title") or "")), timeout)
            out["checks"]["s2_title"] = {"matched": s2t_matched}
            if s2t_note:
                out["note"] = (out["note"] + "；" if out["note"] else "") + s2t_note

    # v3.0.0 L3 引文语境层：verified 的 DOI 引文追加学界评价（默认开,--no-contexts 关）
    if (not offline and _OPTS.get("contexts", True) and out["doi"]
            and DOI_RE.match(out["doi"])):
        ctx = s2_citation_contexts(out["doi"], timeout)
        out["checks"]["citation_contexts"] = {
            "ran": True, "cited_by": ctx.get("cited_by", 0)}
        if ctx:
            out["citation_contexts"] = ctx
            n = ctx["cited_by"]
            cov = ctx.get("coverage", 0)
            note_ctx = (f"学界评价：被引 {'≥' if n >= 30 else ''}{n} 次"
                        f"（语境覆盖率 {cov:.0%}）")
            if ctx["samples"]:
                note_ctx += "；后续文献如是以引用：《" + ctx["samples"][0]["citing_title"] + "》"
            out["note"] = (out["note"] + "；" if out["note"] else "") + note_ctx

    miss = missing_fields(ref)
    if out["tier"] in TRUSTED_TIERS and not miss:
        out["verdict"] = "verified"
    else:
        why = []
        if out["tier"] not in TRUSTED_TIERS:
            why.append(f"来源层级为 {out['tier']}（非权威层）")
        if miss:
            why.append(f"缺字段 {','.join(miss)}")
        out["verdict"] = "partial"
        out["note"] = (out["note"] + "；" if out["note"] else "") + "；".join(why)

    # v1.4：元数据核验判为 partial 时，verified 降级为 partial
    if (doi_adj == "partial" or arxiv_adj == "partial") and out["verdict"] == "verified":
        out["verdict"] = "partial"
    # v3.4 外部独测合并:PMID 元数据 partial 与 DOI/arXiv 同闸——降级不得被终局覆盖
    if (out.get("checks", {}).get("pmid_metadata", {}) or {}).get("adjust") == "partial" \
            and not (out.get("checks", {}).get("pmid_metadata", {}) or {}).get(
                "cross_lang_corroborated") \
            and out["verdict"] == "verified":
        out["verdict"] = "partial"
    # v4.1.0：撤稿族与 EoC 同闸降级（EoC=编辑关注通告，证据效力存疑转人工；
    # 更正/勘误不降级——仅提示注记）
    _ret_chk = out.get("checks", {}).get("retraction") or {}
    if (retracted or _ret_chk.get("nature") == "expression_of_concern") \
            and out["verdict"] == "verified":
        out["verdict"] = "partial"
        out["needs_human_check"] = True
    elif _ret_chk.get("nature") == "expression_of_concern":
        # EoC 落在其他 partial 路径（层级/缺字段）也要挂人工旗——复核计数口径
        # 与撤稿族一致，注记说「转人工」旗标必须真挂（审计 P3-1）
        out["needs_human_check"] = True
    # offline 模式只做结构核验（格式/字段/层级/去重），可达性未验证——
    # 诚实起见 verified 封顶为 partial（避免离线盖章"已验证"）
    if offline and out["verdict"] == "verified":
        out["verdict"] = "partial"
        out["note"] = (out["note"] + "；" if out["note"] else "") + \
            "offline 模式最高判 partial（可达性未验证）"
    return out


# ---------------- 语义层工作底稿（v1.11，semantic_audit） ----------------
# 模型在研究流程中对每条引用做语义判定（该来源是否真的支撑所引论断），v1.11 起
# 支持把判定以结构化对象写进 research_refs.json 的 semantic 字段，机械层负责校验
# 结构、透传进 auditjson/报告，并对否定性判定封顶——落实 GESIS 立场论文
# （arXiv:2607.22693）「disclosing their own uncertainty」的行业呼吁：
# 检测系统的语义不确定性必须可披露、可审计，而不是藏在模型"感觉"里。
# support 取值：supported（支撑）/ partial（部分支撑）/ not_in_source（来源未
# 包含该论断）/ contradicted（来源与论断相矛盾）/ unclear（无法判定）。
SEMANTIC_SUPPORTS = ("supported", "partial", "not_in_source", "contradicted",
                     "unclear")
_SEMANTIC_CAP = ("not_in_source", "contradicted")


def build_semantic_audit(ref: dict):
    """解析 semantic 字段：dict（新）→ 结构化底稿对象；字符串/缺失（旧）→ None。
    非法 support 值按 unclear 处理并留注记——宁可降级也不让脏数据静默通过。"""
    s = ref.get("semantic")
    if not isinstance(s, dict):
        return None
    support = str(s.get("support") or "").strip().lower()
    note = ""
    if support not in SEMANTIC_SUPPORTS:
        if support:
            note = f"semantic.support 非法值「{support[:30]}」，按 unclear 处理"
        support = "unclear"
    own_note = str(s.get("note") or "").strip()
    if note and own_note:
        note = note + "；" + own_note
    else:
        note = note or own_note
    return {"claim": str(s.get("claim") or "").strip(),
            "support": support,
            "quote": str(s.get("quote") or "").strip(),
            "note": note}


def apply_semantic_cap(results: list) -> None:
    """v1.11 语义封顶：语义判定 not_in_source / contradicted 时，机械层 verified
    不得覆盖——封顶 partial 并转人工复核（能力边界矩阵明示语义层不归机械层承诺，
    但模型已做出的否定性判定机械层必须尊重）。在 mark_duplicates 之后统一执行：
    所有判定已收齐，verify_one 的任何 early-return 路径都被覆盖，且串行/并行/
    缓存复用三条路径行为一致。invalid 条目不动（不得反向"提升"为 partial）。"""
    for r in results:
        sa = r.get("semantic_audit") or {}
        if sa.get("support") not in _SEMANTIC_CAP:
            continue
        if r.get("verdict") == "invalid":
            continue
        if r.get("verdict") == "verified":
            r["verdict"] = "partial"
        r["needs_human_check"] = True
        why = ("来源未包含所引论断" if sa.get("support") == "not_in_source"
               else "来源内容与该论断相矛盾")
        r["note"] = ((r.get("note") + "；") if r.get("note") else "") + \
            f"语义层判定 {sa.get('support')}（{why}）→ 封顶 partial，需人工复核"


def apply_l4_cascade(results: list, timeout: float) -> None:
    """v3.1 L4 证据升级级联（主流程接入）：语义层 not_in_source/unclear 且配置了
    --judge-url 的条目，升级取官方摘要（PMID→PubMed efetch）或全文（arXiv→ar5iv/abs）
    做段落检索（bge-m3，TF-IDF 保底）后交外置裁判。
    判定策略保守：裁判结论只追加注记/needs_human_check，绝不翻案（不把 partial 提回
    verified，不动 invalid）；未配置 --judge-url 时零网络调用零行为变化（审核安全）。"""
    if not judge_endpoint_available():
        return
    # v3.9.0 位 B(fastjudge_design 落地):--fast-judge-url 时先对学生模型预筛
    # (小型分类器延迟极低),按「高置信 REFUTES 优先」排序后再做贵的官方文本升级——
    # 排序路由不跳过任何条目(诚实:总核验量不变,变的是处理次序与可观测性)。
    def _fj_prefilter(r):
        if not (_OPTS.get("fast_judge_url") or "").strip():
            return 0  # 无预筛:保持原顺序
        sa = r.get("semantic_audit") or {}
        claim = str(sa.get("claim") or "").strip()
        src = "\n".join(x for x in (str(r.get("title") or ""),
                                    str(r.get("journal") or "")) if x.strip())
        if not claim or len(src.strip()) < 20:
            return 0
        fj = fast_judge_vote(claim, src, timeout=timeout)
        r.setdefault("checks", {})["fast_judge_prescreen"] = {
            "label": fj.get("label"), "prob": fj.get("prob")}
        if fj.get("label") == "REFUTES" and float(fj.get("prob") or 0) >= 0.95:
            return 2  # 高置信反驳:疑似错引,升级复核优先级最高
        return 1

    cands = []
    for r in results:
        try:
            sa = r.get("semantic_audit") or {}
            if sa.get("support") not in ("not_in_source", "unclear"):
                continue
            claim = str(sa.get("claim") or "").strip()
            if not claim or r.get("verdict") == "invalid":
                continue
            pmid = str(r.get("pmid") or "").strip()
            m = re.search(r"(\d{4}\.\d{4,5})(?:v\d+)?", str(r.get("arxiv") or ""))
            if not ((pmid and PMID_RE.match(pmid)) or m):
                continue
            cands.append((_fj_prefilter(r), r))
        except Exception as e:
            try:
                r.setdefault("checks", {})["l4_evidence_cascade"] = {
                    "degraded": f"cascade-error:{type(e).__name__}"}
            except Exception:
                pass
    cands.sort(key=lambda t: -t[0])
    if any(p == 2 for p, _ in cands):
        n_hi = sum(1 for p, _ in cands if p == 2)
        print(f"[L4] fast-judge 预筛:{n_hi} 条疑似错引置前复核")
    for _prio, r in cands:
        try:
            sa = r.get("semantic_audit") or {}
            if sa.get("support") not in ("not_in_source", "unclear"):
                continue
            claim = str(sa.get("claim") or "").strip()
            if not claim or r.get("verdict") == "invalid":
                continue
            pmid = str(r.get("pmid") or "").strip()
            m = re.search(r"(\d{4}\.\d{4,5})(?:v\d+)?", str(r.get("arxiv") or ""))
            if pmid and PMID_RE.match(pmid):
                src_name = "pubmed-abstract"
                text = fetch_pubmed_abstract(pmid, timeout)
            elif m:
                src_name = "arxiv-fulltext"
                text = fetch_fulltext(m.group(0), timeout)
            else:
                continue
            chk = r.setdefault("checks", {})
            if not text:
                chk["l4_evidence_cascade"] = {"trigger": sa.get("support"),
                                              "evidence_source": src_name,
                                              "degraded": "no-text"}
                continue
            hits = retrieve_evidence(claim, text, k=2)
            if not hits:
                chk["l4_evidence_cascade"] = {"trigger": sa.get("support"),
                                              "evidence_source": src_name,
                                              "degraded": "no-chunks"}
                continue
            jd = judge_claim_via_endpoint(claim, "\n\n".join(hits), timeout=timeout)
            rec = {"trigger": sa.get("support"), "evidence_source": src_name,
                   "top_chunk_chars": len(hits[0]), "judge_verdict": jd.get("verdict")}
            if _OPTS.get("nli_url"):
                no = nli_vote("\n\n".join(hits), claim, timeout=timeout)
                agg = aggregate_l2(jd.get("verdict") or "NEI", no)
                rec["nli"] = agg["nli"]
                rec["l2_confidence"] = agg["confidence"]
            if jd.get("degraded"):
                rec["degraded"] = jd["degraded"]
            chk["l4_evidence_cascade"] = rec
            add = lambda s: r.update({"note": ((r.get("note") + "；") if r.get("note") else "") + s})
            if rec.get("l2_confidence") == "contested":
                r["needs_human_check"] = True
                add(f"L2 分歧：裁判判 {jd.get('verdict')} 而 NLI 第三票判 {rec.get('nli')}"
                    "→ 标记人工复核（不自动翻案）")
            if jd.get("verdict") == "SUPPORTS":
                add("L4 升级：官方文本段落级证据经外置裁判判定支持（语义封顶维持，供人工复核参考）")
            elif jd.get("verdict") == "CONTRADICTS":
                r["needs_human_check"] = True
                add("L4 升级：外置裁判在官方文本段落级判定反驳（与语义层否定一致）")
            else:
                add("L4 升级：段落检索后外置裁判仍判证据不足")
        except Exception as e:  # 单条失败不拖垮整跑
            try:
                r.setdefault("checks", {})["l4_evidence_cascade"] = {
                    "degraded": f"cascade-error:{type(e).__name__}"}
            except Exception:
                pass


def fast_judge_vote(claim: str, source: str, timeout: float = 30) -> dict:
    """v3.5.0 fast-judge 预筛(外挂小型分类器,OpenAI 兼容端点)。
    输入格式与训练一致(SENTENCE/SOURCE);失败/未配置返回 {"label": None}
    ——预筛层整体弃权,绝不影响主流程。"""
    url = _OPTS.get("fast_judge_url") or ""
    if not url or not (claim or "").strip():
        return {"label": None}
    try:
        inp = f"SENTENCE: {claim[:800]}\n\nSOURCE:\n{(source or '')[:6000]}"
        body = json.dumps({"input": inp}).encode()
        req = urllib.request.Request(url.rstrip("/") + "/api/fastjudge", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return {"label": None}


def apply_fast_judge(results: list, timeout: float) -> None:
    """v3.5.0 fast-judge 预筛(--fast-judge-url 时激活;零配置零变化):
    只服务「语义层待定(not_in_source/unclear)且 L4 级联没给出官方文本判定」的
    条目——外挂学生分类器对 claim×元数据底稿做预筛,高置信 SUPPORTS 仅追加供
    人工参考的 note。永不产生/修改 verdict、永不设 needs_human_check
    (设计红线 fastjudge_design.md;阈值校准 calibration_fastjudge.json:
    SCitance v2.2 claim 级分组 dev,泄漏 0)。"""
    if not (_OPTS.get("fast_judge_url") or "").strip():
        return
    thr = float(_OPTS.get("fast_judge_threshold") or 0.9)
    for r in results:
        try:
            sa = r.get("semantic_audit") or {}
            if sa.get("support") not in ("not_in_source", "unclear"):
                continue
            claim = str(sa.get("claim") or "").strip()
            if not claim or r.get("verdict") == "invalid":
                continue
            chk = (r.get("checks") or {}).get("l4_evidence_cascade") or {}
            if chk.get("judge_verdict"):
                continue  # L4 已有官方文本判定——预筛让位
            src = "\n".join(x for x in (str(r.get("title") or ""),
                                        str(r.get("journal") or "")) if x.strip())
            if len(src.strip()) < 20:
                continue  # 无元数据底稿——预筛弃权
            fj = fast_judge_vote(claim, src, timeout=timeout)
            rec = {"label": fj.get("label"), "prob": fj.get("prob")}
            if fj.get("label") == "SUPPORTS" and float(fj.get("prob") or 0) >= thr:
                r["note"] = ((r.get("note") + "；") if r.get("note") else "") + \
                    f"fast-judge 预筛倾向支持（p={float(fj['prob']):.2f}，供人工参考，非判定）"
                rec["action"] = "note-only"
            r.setdefault("checks", {})["fast_judge"] = rec
        except Exception:
            continue


def clean_title(line: str) -> str:
    """v3.3.1 标题清洗(demo 原型移植):剥序号前缀/ID 后缀/作者段——提升
    DOI/arXiv 元数据匹配的标题相似度(实测 demo 端 AlphaFold 整行 0.66→清洗后 0.9+)。"""
    t = re.sub(r"^(?:\[\d+\]|\d+[.)])\s*", "", line.strip())
    t = re.split(r"\s+(?:doi|pmid|arxiv)\s*[:：]", t, flags=re.I)[0]
    t = re.sub(r"(?:,|\.\s)\s*(?:et al\.?|and\s+[A-Z][a-z]+)[^0-9]{0,40}"
               r"(?:19|20)\d{2}", "", t, count=1)
    t = re.sub(r"[.。]\s*(?:19|20)\d{2}.*$", "", t)
    return t.strip()[:200] or line.strip()[:200]


def _cache_key(ref: dict) -> tuple:
    """v1.10 批内缓存键：doi → url → pmid → arxiv 取首个可用标识；全无则 ()（不缓存）。
    仅作缓存命中优化，不参与判定；判定顺序与 mark_duplicates 去重一致（url/doi/pmid）。"""
    doi = str(ref.get("doi") or "").strip()
    if doi:
        return ("doi", doi.lower())
    u = str(ref.get("url") or "").strip()
    if u:
        return ("url", normalize_url(u))
    pmid = str(ref.get("pmid") or "").strip()
    if pmid:
        return ("pmid", pmid)
    ax = extract_arxiv_id(ref)
    if ax:
        return ("arxiv", ax)
    return ()


# ---------------- 持久磁盘缓存（v1.12：复跑不出国，判定口径一致） ----------------
# ~/.cache/cite-holmes/cache.sqlite3（标准库 sqlite3）。键=影响判定的全部输入字段
# （同 DOI 不同声称标题/年份必须分开——标题相似度判定依赖声称值）+ 验证器版本 + 预设。
# 只缓存稳定判定 verified/partial/invalid；unreachable（瞬态）与 offline 结果不缓存。
# --strict 强制绕过读（CI 诚实）；--refresh-cache 绕过读但仍写；写失败静默（缓存绝不影响验证）。
_DC_CACHEABLE = {"verified", "partial", "invalid"}


def _dc_key(ref: dict, profile: str) -> str:
    basis = {k: ref.get(k) for k in ("doi", "url", "pmid", "arxiv", "title",
                                     "year", "source", "authors", "tier")}
    basis["_v"] = VERSION
    basis["_p"] = profile
    raw = json.dumps(basis, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


# ---------------- L4 证据升级级联（v3.0.0,DeepSciVerify 两级联开源化） ----------------

def fetch_pubmed_abstract(pmid: str, timeout: float) -> str:
    """L4 Phase1 证据源：E-utilities efetch 取摘要（夜间雷达管线同源）。失败返回 ""。"""
    u = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
         + _ncbi_qs(f"?db=pubmed&id={pmid}&rettype=abstract&retmode=text"))
    if _cb_open(u):
        return ""
    try:
        req = urllib.request.Request(u, headers={
            "User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            _cb_record(u, False)
            return r.read().decode("utf-8", "ignore")[:4000]
    except Exception:
        _cb_record(u, True)
        return ""


def fetch_fulltext(arxiv_id: str, timeout: float) -> str:
    """L4 Phase2 全文源：arXiv HTML（ar5iv 镜像,优先）/abs 页兜底。失败返回 ""。"""
    aid = re.sub(r"v\d+$", "", arxiv_id)
    for url in (f"https://ar5iv.labs.arxiv.org/html/{aid}",
                f"https://arxiv.org/abs/{aid}"):
        if _cb_open(url):
            continue
        for attempt in range(2):  # v3.1：传输错误单次重试（弱网出口 SSL 间歇断流实测）
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": f"Mozilla/5.0 (compatible; cite-holmes/{VERSION})"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    _cb_record(url, False)
                    text = r.read().decode("utf-8", "ignore")
                # 粗剥 HTML 标签
                return re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>",
                                                      " ", text, flags=re.S))[:120000]
            except Exception:
                if attempt == 0:
                    time.sleep(2)
                    continue
                _cb_record(url, True)
    return ""


def chunk_text(text: str, size: int = 900, overlap: int = 120) -> list:
    """段落分块（字符级,重叠防切断句界证据）。"""
    if not text:
        return []
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i:i + size])
        i += size - overlap
    return chunks


def _embed_ollama(texts: list) -> list:
    """bge-m3 嵌入（本机 ollama,HTTP 零依赖）。不可用返回 [] → 调用方降级 TF-IDF。
    v3.1：ollama+bge-m3 对部分短文本产 NaN（500 unsupported value: NaN，实测约 9%
    的短科学声明）——单条 500 时对该条用「文本加倍」变体重试（语义嵌入仍有效），
    再失败才整批降级。"""
    def _call(inp):
        payload = json.dumps({"model": "bge-m3", "input": inp}).encode()
        req = urllib.request.Request("http://127.0.0.1:11434/api/embed",
                                     data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode()).get("embeddings") or []
    try:
        try:
            return _call(texts)
        except urllib.error.HTTPError as e:
            if e.code != 500 or not texts:
                raise
        # NaN 疑似：单条加倍逐条重建（仅查询路径,量小）
        out = []
        for t in texts:
            try:
                out.append(_call([t])[0])
            except urllib.error.HTTPError:
                out.append(_call([(t or " ") * 2])[0])  # 加倍变体绕 NaN
        return out
    except Exception:
        return []


def _tfidf_top(query: str, chunks: list, k: int = 2) -> list:
    """TF-IDF 保底检索（无 ollama 时）。纯标准库实现,选 top-k 索引。"""
    import math
    def tokens(t):
        return re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]+", t.lower())
    q = tokens(query)
    if not q or not chunks:
        return list(range(min(k, len(chunks))))
    df = {}
    for ch in chunks:
        for w in set(tokens(ch)):
            df[w] = df.get(w, 0) + 1
    scores = []
    for ch in chunks:
        toks = tokens(ch)
        tf = {}
        for w in toks:
            tf[w] = tf.get(w, 0) + 1
        sc = sum(tf.get(w, 0) * math.log((len(chunks) + 1) / (df.get(w, 0) + 1))
                 for w in q)
        scores.append(sc)
    return sorted(range(len(chunks)), key=lambda i: -scores[i])[:k]


def retrieve_evidence(query: str, fulltext: str, k: int = 2) -> list:
    """L4 Phase2 段落检索：bge-m3 余弦 top-k；ollama 不可用降级 TF-IDF（保底）。"""
    chunks = chunk_text(fulltext)
    if not chunks:
        return []
    embs = _embed_ollama([query] + chunks)
    if len(embs) == len(chunks) + 1 and embs[0]:
        import math
        q = embs[0]
        norms = [math.sqrt(sum(x * x for x in e)) or 1.0 for e in embs]
        scores = [sum(a * b for a, b in zip(q, e)) / (norms[0] * n)
                  for e, n in zip(embs[1:], norms[1:])]
        top = sorted(range(len(chunks)), key=lambda i: -scores[i])[:k]
        return [chunks[i] for i in top]
    return [chunks[i] for i in _tfidf_top(query, chunks, k)]


def nli_vote(premise: str, hypothesis: str, timeout: float = 30) -> dict:
    """v3.3.0 L2 NLI 第三票(独立 HTTP 服务,nli_service.py 形态)。失败/未配置返回
    {"label": None}——聚合层按弃权处理,绝不影响主流程。"""
    url = _OPTS.get("nli_url") or ""
    if not url:
        return {"label": None}
    try:
        body = json.dumps({"premise": (premise or "")[:6000],
                           "hypothesis": (hypothesis or "")[:1000]}).encode()
        req = urllib.request.Request(url.rstrip("/") + "/api/nli", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return {"label": None}


_NLI_MAP = {"entailment": "SUPPORTS", "contradiction": "CONTRADICTS",
            "neutral": "NEI"}


def aggregate_l2(gen_verdict: str, nli_out: dict) -> dict:
    """生成式裁判 + NLI 第三票 → 聚合(实验验证:REFUTES F1 0→0.63)。
    产品哲学:聚合结论只用于注记/复核标记——contested 必须 needs_human_check,
    绝不自动翻转机械层判定(与 L4 保守策略一致)。"""
    nv = _NLI_MAP.get((nli_out or {}).get("label") or "")
    if nv is None or (nli_out or {}).get("abstain"):
        return {"confidence": "single", "nli": "abstained"}
    if nv == gen_verdict:
        return {"confidence": "high", "nli": nv}
    return {"confidence": "contested", "nli": nv}


def judge_endpoint_available() -> bool:
    """L2 外置裁判端点是否配置(--judge-url,OpenAI 兼容:ollama/llama-server/GLM 网关)。"""
    return bool(_OPTS.get("judge_url"))


def _scan_label(text: str, labels: tuple) -> str:
    """末位词边界标签提取（思考型模型的思维链里前面可能顺嘴提到其它标签）。"""
    best = None
    for m in re.finditer(r"\b(" + "|".join(labels) + r")\b", text or "", re.I):
        best = m.group(1).upper()
    return best or ""


def judge_claim_via_endpoint(claim: str, evidence: str, timeout: float = 60) -> dict:
    """L4 裁判调用：外部端点判 SUPPORTS/CONTRADICTS/NEI（v3.1 双端点加固）。
    - URL 以 /v1 结尾 → OpenAI 兼容（ollama /v1、llama-server、GLM 网关）；
      content 为空时回退 reasoning 字段（qwen3 等思考模型把结论留在 reasoning——
      实测 /no_think 软开关与 /v1 透传 think 均不可靠，故三者都做）。
    - 其他 URL → ollama 原生 /api/chat：think:false + format JSON schema 枚举强制直答
      （思考模型唯一可靠路径，harness 实测）。
    判不出 → NEI + degraded 注记；无端点 → NEI + no-judge-endpoint。零新依赖。"""
    if not judge_endpoint_available():
        return {"verdict": "NEI", "degraded": "no-judge-endpoint"}
    labels = ("SUPPORTS", "CONTRADICTS", "NEI")
    prompt = ("你是证据核查裁判。给定 CLAIM 与 EVIDENCE,只输出三选一标签：\n"
              "SUPPORTS（证据支持声明）/ CONTRADICTS（证据反驳声明）/ NEI（证据不足）。\n\n"
              f"CLAIM: {claim[:800]}\n\nEVIDENCE: {evidence[:3000]}\n\n标签:")
    api = _OPTS["judge_url"].rstrip("/")
    model = _OPTS.get("judge_model", "qwen3.8-27b")
    try:
        if api.endswith("/v1"):
            body = json.dumps({"model": model,
                               "messages": [{"role": "user", "content": prompt + " /no_think"}],
                               "temperature": 0, "max_tokens": 96}).encode()
            req = urllib.request.Request(api + "/chat/completions", data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                msg = (json.loads(r.read().decode("utf-8", "ignore"))
                       .get("choices", [{}])[0].get("message", {}))
            tag = _scan_label(msg.get("content") or "", labels)
            if tag:
                return {"verdict": tag}
            reas = msg.get("reasoning") or ""
            tag = _scan_label(reas, labels)
            if tag:
                return {"verdict": tag, "degraded": "parsed-from-reasoning"}
            return {"verdict": "NEI",
                    "degraded": "unparsed-reply:" + (msg.get("content") or reas)[:40]}
        schema = {"type": "object",
                  "properties": {"label": {"type": "string", "enum": list(labels)}},
                  "required": ["label"]}
        body = json.dumps({"model": model,
                           "messages": [{"role": "user", "content": prompt}],
                           "think": False, "stream": False, "format": schema,
                           "options": {"temperature": 0, "num_predict": 32}}).encode()
        req = urllib.request.Request(api + "/api/chat", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            msg = json.loads(r.read().decode("utf-8", "ignore")).get("message", {})
        out = (msg.get("content") or msg.get("thinking") or "").strip()
        try:
            out = json.loads(out).get("label", out)
        except Exception:
            pass
        tag = _scan_label(str(out), labels)
        if tag:
            return {"verdict": tag}
        return {"verdict": "NEI", "degraded": "unparsed-reply:" + str(out)[:40]}
    except Exception as e:
        return {"verdict": "NEI", "degraded": f"endpoint-error:{type(e).__name__}"}


def _dc_path(args) -> str:
    return os.path.abspath(os.path.expanduser(args.cache_path))


def _dc_get(path: str, key: str, ttl_h: float):
    """命中且未过期 → (result_dict, age_hours)；未命中/坏库/坏行 → None（静默）。"""
    if not key:
        return None
    try:
        import sqlite3
        os.makedirs(os.path.dirname(path), exist_ok=True)
        conn = sqlite3.connect(path)
        try:
            conn.execute("CREATE TABLE IF NOT EXISTS dc("
                         "k TEXT PRIMARY KEY, ts REAL, payload TEXT)")
            row = conn.execute("SELECT ts, payload FROM dc WHERE k=?", (key,)).fetchone()
        finally:
            conn.close()
    except Exception:
        return None
    if not row:
        return None
    ts, payload = row
    age_h = (time.time() - ts) / 3600.0
    if age_h > max(0.0, ttl_h):
        return None
    try:
        r = json.loads(payload)
    except Exception:
        return None
    if not isinstance(r, dict) or not r.get("verdict"):
        return None
    return r, age_h


def _dc_put(path: str, key: str, result: dict) -> None:
    if not key:
        return
    try:
        import sqlite3
        os.makedirs(os.path.dirname(path), exist_ok=True)
        slim = {k: v for k, v in result.items() if k != "index"}
        conn = sqlite3.connect(path)
        try:
            conn.execute("CREATE TABLE IF NOT EXISTS dc("
                         "k TEXT PRIMARY KEY, ts REAL, payload TEXT)")
            conn.execute("INSERT OR REPLACE INTO dc(k, ts, payload) VALUES (?,?,?)",
                         (key, time.time(), json.dumps(slim, ensure_ascii=False)))
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass  # 缓存写失败绝不影响验证本身


def _dup_title_sig(r: dict) -> str:
    """v3.4 去重指纹:引用行的归一化标题(小写去非字母数字)。
    同标识符+同标题=真重复;同标识符+不同标题=T2/T7 型拼接变体,须独立判定。
    审计 B3 修复:归一改走 _cjk_norm(保留 CJK)——旧 [^a-z0-9] 归一会把纯中文
    标题折成空串,导致「异题同 DOI」的两条中文引用被误并成真重复。"""
    return _cjk_norm(r.get("title") or r.get("claim") or "")[:120]


def mark_duplicates(results: list) -> None:
    seen = {}
    kind_zh = {"url": "URL", "doi": "DOI", "pmid": "PMID"}
    for r in results:
        sig = _dup_title_sig(r)
        keys = []
        if r.get("url"):
            keys.append(("url", normalize_url(r["url"]) + "|" + sig))
        if r.get("doi"):
            keys.append(("doi", r["doi"].lower() + "|" + sig))
        if r.get("pmid"):
            keys.append(("pmid", r["pmid"] + "|" + sig))
        hit = next(((k, seen[v]) for k, v in keys if v in seen), None)
        if hit:
            kind, first = hit
            r["note"] = (r["note"] + "；" if r["note"] else "") + f"与 #{first} 重复（同{kind_zh[kind]}）"
            if r["verdict"] == "verified":
                r["verdict"] = "partial"
        else:
            for _, v in keys:
                seen[v] = r["index"]


def _clone_pairs_scan(results: list) -> list:
    """v3.10 克隆引用对扫描（纯函数，零网络）：返回 [{a, b, kind}]。
      R1「同题不同 DOI」：同一真论文被写成多个 DOI 变体——克隆引用，
        至少一个标识为编造/错引（LLM 生成文本最常见的伪造形态之一）。
      R2「同 DOI 不同题」：拼接变体——两键各真但组合造假的前兆形态，
        mark_duplicates 已对其实行独立核验（v3.4 指纹），此处补成对警示。
    不改变五态判定：克隆对是高价值线索而非定罪证据，最终以元数据核验为准。
    归一比对走 _cjk_norm（中英同规）；长度差+quick_ratio 预筛控制 O(n²)
    常数（千条清单为秒级）——审计 B2 披露：预筛只作用于 R1；同 DOI 对
    豁免预筛（R2 无相似度下限，完全不同的标题也要走 R2 判定），预筛
    砍掉的 R2 粗端由 doi_metadata_match 的标题比对兜住。"""
    import difflib as _d
    pairs = []
    items = []
    for r in results:
        t = _cjk_norm(r.get("title") or r.get("claim") or "")
        items.append((r, t))
    n = len(items)
    for i in range(n):
        ra, ta = items[i]
        if len(ta) < 8:
            continue
        da = (ra.get("doi") or "").lower()
        for j in range(i + 1, n):
            rb, tb = items[j]
            db = (rb.get("doi") or "").lower()
            same_doi = bool(da) and da == db
            if len(tb) < 8 or abs(len(ta) - len(tb)) > max(len(ta), len(tb)) * 0.35:
                continue
            sm = _d.SequenceMatcher(None, ta, tb)
            # 审计 B2:预筛只作用于 R1;同 DOI 对豁免(R2 无相似度下限)
            if not same_doi and sm.quick_ratio() < 0.85:
                continue
            sim = sm.ratio()
            if sim >= 0.92 and da and db and da != db:
                pairs.append({"a": ra["index"], "b": rb["index"], "kind": "clone_doi",
                              "sim": round(sim, 2)})
            elif da and da == db and sim < 0.92:
                pairs.append({"a": ra["index"], "b": rb["index"], "kind": "clone_title",
                              "sim": round(sim, 2)})
    return pairs


def detect_clone_pairs(results: list) -> int:
    """v3.10 克隆引用搭档检测（主流程调用一次）：扫描克隆对并为双方追加
    警示注记。判定不改——注记明确「以元数据核验为准」。返回克隆对数。"""
    zh = {"clone_doi": "同题不同 DOI（克隆引用：至少一个标识为编造或错引）",
          "clone_title": "同 DOI 不同标题（拼接变体警示：判定已各自独立核验）"}
    seen_pairs = set()
    cnt = 0
    for p in _clone_pairs_scan(results):
        key = (p["a"], p["b"], p["kind"])
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        ra = next(r for r in results if r["index"] == p["a"])
        rb = next(r for r in results if r["index"] == p["b"])
        note = f"克隆引用对 #{p['a']}↔#{p['b']}：{zh[p['kind']]}（相似度 {p['sim']}）→ 以元数据核验为准"
        for r in (ra, rb):
            r["note"] = (r["note"] + "；" if r.get("note") else "") + note
        cnt += 1
    return cnt


def collect_clone_pairs(results: list) -> list:
    """v3.10 渲染层只读收集（不写 note——detect_clone_pairs 已写过，渲染
    时重算只为取结构化列表，纯函数幂等零成本）。"""
    return _clone_pairs_scan(results)


# ═══ v3.11.0 清单画像与版本提示：从单条伪造到整批伪装 ═══

def profile_bibliography(results: list) -> dict:
    """v3.11 清单级伪造画像（纯本地，零网络）：LLM 批量编造参考文献表时
    会留下统计指纹——标识符近号成簇、年份过度集中/超前、期刊过度集中。
    逐条核验抓「单条伪造」，本画像抓「整批伪装」。画像只描述分布并给出
    人工抽查建议，绝不改变任何单条判定（集中也可能是合法的专题综述）。
    返回 {"flags": [{kind, detail}], "stats": {...}}；flags 为空=画像干净。"""
    import datetime as _dt
    flags, stats = [], {}
    n = len(results)
    if n < 4:
        return {"flags": [], "stats": {"n": n, "skipped": "条目过少，画像不具统计意义"}}

    # ① 标识符近邻簇：同前缀 DOI 的尾部数字段数值近邻（差 ≤2）成簇 ≥3 条
    #    ——批量生成器的典型指纹；合法的连续页码/论文集编号同样会命中，
    #    因此只给「人工抽查」建议，不判伪造。
    clusters = {}
    for r in results:
        doi = str(r.get("doi") or "").lower()
        m = re.match(r"^(10\.\d{4,9}/\S*?)(\d{3,})$", doi)
        if not m:
            continue
        clusters.setdefault(m.group(1), []).append((int(m.group(2)), r["index"]))
    seen_cluster = set()
    for prefix, seqs in sorted(clusters.items()):
        if len(seqs) < 3:
            continue
        seqs = sorted(seqs)
        run = [seqs[0]]
        best = []
        for prev, cur in zip(seqs, seqs[1:]):
            if cur[0] - prev[0] <= 2:
                run.append(cur)
            else:
                best = max(best, run, key=len)
                run = [cur]
        best = max(best, run, key=len)
        if len(best) >= 3:
            key = (prefix, tuple(x[1] for x in best))
            if key not in seen_cluster:
                seen_cluster.add(key)
                flags.append({
                    "kind": "serial_cluster",
                    "detail": (f"标识符近邻簇：{prefix}* 尾号 "
                               f"{'、'.join(str(x[0]) for x in best[:6])}"
                               f"{'…' if len(best) > 6 else ''} 共 {len(best)} 条连续"
                               f"（条目 {'/'.join('#' + str(x[1]) for x in best[:6])}"
                               f"{'…' if len(best) > 6 else ''}）——批量生成常见指纹，"
                               "也可能是合法连续编号，建议逐条抽查该簇")})

    # ② 年份画像：未来年份逐项注记 + 清单级过度集中
    now_y = _dt.date.today().year
    years = []
    for r in results:
        y = r.get("year")
        try:
            y = int(y)
        except (TypeError, ValueError):
            continue
        years.append((y, r["index"]))
    future = [(y, i) for y, i in years if y > now_y + 1]
    if future:
        flags.append({"kind": "future_year",
                      "detail": f"声称年份超前当前时间（{'、'.join(f'{y}(#{i})' for y, i in future[:5])}"
                                f"{'…' if len(future) > 5 else ''}）——尚未发生的文献年份，重点核查"})
    if years:
        ys = [y for y, _ in years]
        from collections import Counter as _C
        top_y, top_n = _C(ys).most_common(1)[0]
        stats["year"] = {"min": min(ys), "max": max(ys),
                         "mode": top_y, "mode_share": round(top_n / len(ys), 2)}
        if len(ys) >= 8 and top_n / len(ys) >= 0.8:
            flags.append({"kind": "year_concentration",
                          "detail": f"{top_n}/{len(ys)} 条声称同年（{top_y}）——"
                                    "综述专辑可能合法，但整批同年的参考文献表更像一次性生成，建议抽查"})

    # ③ 期刊集中度：单一信源占比过高（合法专题综述 vs 编造窄源，两可→仅提示）
    srcs = [str(r.get("source") or "").strip() for r in results]
    srcs = [s for s in srcs if s]
    if len(srcs) >= 8:
        from collections import Counter as _C
        top_s, top_n = _C(srcs).most_common(1)[0]
        stats["source_top"] = {"name": top_s[:40], "share": round(top_n / len(srcs), 2)}
        if top_n / len(srcs) >= 0.6:
            flags.append({"kind": "source_concentration",
                          "detail": f"{top_n}/{len(srcs)} 条同信源「{top_s[:40]}」（占比 "
                                    f"{top_n/len(srcs):.0%}）——确认该刊是否真的承载这些论文"})

    # ④ 标识符构成比：完全无标识符（doi/pmid/arxiv/url 全空）的条目占比
    bare = [r["index"] for r in results
            if not any((r.get(k) or "").strip() for k in ("doi", "pmid", "arxiv", "url"))]
    stats["identifier_mix"] = {"bare": len(bare), "n": n,
                               "bare_share": round(len(bare) / n, 2)}
    if bare and len(bare) / n >= 0.5:
        flags.append({"kind": "bare_refs",
                      "detail": f"{len(bare)}/{n} 条无任何可机验标识符（DOI/PMID/arXiv/URL 均空）"
                                f"（如 #{'、#'.join(str(x) for x in bare[:5])}…）——无法机械核验，"
                                "建议补全标识符后重跑"})
    return {"flags": flags, "stats": stats}


def completeness_for_ref(ref: dict) -> dict:
    """v3.11 逐条完整度评分（纯本地）：verified 条目能从注册库 CSL 回填多少
    导出字段（作者/刊名/年份/卷/期/页）——GB/T 与 BibTeX 导出「宁缺毋错」的
    下一代：不仅告诉你能不能导，还告诉你差哪些字段。评分口径：authors 30 /
    container 20 / year 20 / volume·issue·page 各 10；csl 缺失（如非 DOI 源）
    返回 score=None（未知≠零分）。只读不写。"""
    csl = ((ref.get("checks") or {}).get("doi_metadata") or {}).get("csl") or {}
    if not csl:
        return {"score": None, "missing": [], "suggestion": ""}
    have = {"authors": bool(csl.get("authors")),
            "container": bool(csl.get("container")),
            "year": bool(csl.get("year")),
            "volume": bool(csl.get("volume")),
            "issue": bool(csl.get("issue")),
            "page": bool(csl.get("page"))}
    weights = {"authors": 30, "container": 20, "year": 20,
               "volume": 10, "issue": 10, "page": 10}
    score = sum(w for k, w in weights.items() if have[k])
    missing = [k for k, v in have.items() if not v]
    zh = {"authors": "作者", "container": "刊名", "year": "年份",
          "volume": "卷", "issue": "期", "page": "页码"}
    sug = ""
    if missing:
        sug = ("注册库未登记：" + "、".join(zh[m] for m in missing)
               + "——可对照原文补全后再导出（导出策略仍为宁缺毋错）")
    return {"score": score, "missing": missing, "suggestion": sug}


def annotate_completeness(results: list) -> int:
    """v3.11 批处理接线：给 verified 且 csl 在场的条目写 completeness 字段。
    返回有 completeness 的条数（JSON 报告逐条透出，md/html 不逐条展开）。"""
    n = 0
    for r in results:
        if r.get("verdict") != "verified":
            continue
        c = completeness_for_ref(r)
        if c["score"] is not None:
            r["completeness"] = c
            n += 1
    return n


def annotate_preprint_upgrades(results: list, timeout: float) -> int:
    """v3.11 预印本→正式版提示（注记级，只增线索不改判定）：arXiv 引用
    verified 且未带 DOI 时，经 Semantic Scholar 同记录 externalIds 查该
    预印本是否已登记正式发表（期刊版 DOI/venue）——投稿场景引用预印本
    常被审稿人挑，此提示帮作者在提交前完成版本升级。失败/限流一律静默
    （S2 共享池限速走 _s2_rate_wait，断路器生效）；引用已带 DOI 则跳过。"""
    n = 0
    for r in results:
        if r.get("verdict") != "verified":
            continue
        ax = str(r.get("arxiv") or "").strip()
        if not ax or (r.get("doi") or "").strip():
            continue
        try:
            url = (f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{quote(ax)}"
                   f"?fields=externalIds,venue,year")
            if _cb_open(url):
                continue
            _s2_rate_wait()
            _hdrs = {"User-Agent": f"cite-holmes/{VERSION}; +verified-deep-research"}
            if _OPTS.get("s2_key"):
                _hdrs["x-api-key"] = _OPTS["s2_key"]  # 与 s2_doi_confirm 同款头
            req = urllib.request.Request(url, headers=_hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                _cb_record(url, False)
                d = json.loads(resp.read().decode("utf-8", "ignore"))
            ext = d.get("externalIds") or {}
            jdoi = str(ext.get("DOI") or "").strip()
            venue = str(d.get("venue") or "").strip()
            if jdoi:
                venue = venue[:60]  # 截断外部数据:防超长与下游子串扫描误触发
                r["note"] = ((r.get("note") + "；") if r.get("note") else "") + (
                    f"该预印本已登记正式发表（{venue or '期刊版'}"
                    f"{' ' + str(d.get('year')) if d.get('year') else ''}，"
                    f"DOI:{jdoi}）——建议引用正式版（preprint→published 升级提示）")
                n += 1
        except urllib.error.HTTPError:
            # 审计修复:HTTP 层失败（404 未收录/429 限流）不触发熔断——否则连续
            # 2 条未收录 arXiv ID 会熔断 api.semanticscholar.org,殃及同主机的
            # s2_doi_confirm 第二源确认（断路器契约:仅传输层失败计数）
            _cb_record(url, False)
        except Exception:
            _cb_record(url, True)
    return n


VERDICT_ZH = {"verified": "✅ verified", "partial": "🟡 partial", "unreachable": "⚠️ unreachable",
              "invalid": "❌ invalid", "unverified": "⏸ unverified"}



# ═══ v3.7.0 文档级引用核查(--check-document):从清单核验到上下文核验 ═══

_CIT_NUM = re.compile(r"\[(\d{1,3}(?:\s*[,,]\s*\d{1,3})*)\]")
_CIT_RANGE = re.compile(r"\[(\d{1,3})\s*-\s*(\d{1,3})\]")
_CIT_AY = re.compile(
    r"\(([A-Z][A-Za-z\-]+)(?:\s+et\s+al\.)?[,;]\s*(\d{4})\)"      # (Smith, 2023)/(Smith et al., 2023)
    r"|([A-Z][A-Za-z\-]+\s+et\s+al\.)\s*\((\d{4})\)")               # Smith et al. (2023) 叙述式
_CIT_DOI = re.compile(r"https?://(?:dx\.)?doi\.org/(10\.[^\s)\]}]+)", re.I)
_SENT_SPLIT = re.compile(r"(?<=[。！？])\s*|(?<=[.!?])\s+(?=[A-Z0-9\u4e00-\u9fff])")
_STOP = set("a an the of in on at to for and or is are was were be been with as by from "
            "that this these those it its we our their his her study paper research "
            "的 与 和 在 是 了 等 对 将 被 从 而 及 其 该 项 项".split())


def _sentences(text: str):
    parts = _SENT_SPLIT.split(text)
    return [p.strip() for p in parts if p and len(p.strip()) > 2]


def extract_citations(text: str) -> list:
    """从正文抽取 in-text 引用标记,返回 [{marker, kind, sentence, index[]}]."""
    out = []
    for sent in _sentences(text):
        found = {}
        for m in _CIT_RANGE.finditer(sent):
            lo, hi = int(m.group(1)), int(m.group(2))
            if 1 <= lo <= hi <= 999 and hi - lo <= 20:
                found[m.group(0)] = list(range(lo, hi + 1))
        for m in _CIT_NUM.finditer(sent):
            if m.group(0) in found:
                continue
            idxs = [int(x) for x in re.split(r"\s*[,,]\s*", m.group(1))]
            if all(1 <= x <= 999 for x in idxs):
                found[m.group(0)] = idxs
        for m in _CIT_AY.finditer(sent):
            if m.group(1):
                found[m.group(0)] = ("author-year", m.group(1), m.group(2))
            else:
                found[m.group(0)] = ("author-year",
                                     m.group(3).replace(" et al.", ""), m.group(4))
        for m in _CIT_DOI.finditer(sent):
            found[m.group(0)] = ("doi", m.group(1))
        for marker, idxs in found.items():
            kind = ("numeric" if isinstance(idxs, list)
                    else idxs[0] if isinstance(idxs, tuple) else "numeric")
            out.append({"marker": marker, "kind": kind,
                        "sentence": sent[:400], "index": idxs})
    return out


def _norm_word(w: str) -> str:
    """轻词形归一:去复数/时态尾缀(≥5 字符才剥,防过削)。"""
    for suf in ("ing", "ies", "ed", "es", "s"):
        if len(w) > 4 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def _content_words(s: str) -> set:
    return {_norm_word(w) for w in
            re.findall(r"[a-z0-9\u4e00-\u9fff]{2,}", (s or "").lower())
            if w not in _STOP}


def anchor_rate(sentence: str, ref: dict) -> float:
    """引文句与被引条目标题的内容词重叠率(分母=标题词,0~1)。
    匹配容忍:完全相等或 ≥5 字符前缀互吞(thermometry~thermometer、cell~cells)。"""
    csl = (ref.get("checks", {}).get("doi_metadata", {}) or {}).get("csl", {}) or {}
    tw = _content_words(ref.get("title") or csl.get("title") or "")
    if not tw:
        return 0.0
    sw = _content_words(sentence)
    hit = 0
    for t in tw:
        if t in sw or any(t.startswith(s) or s.startswith(t)
                          for s in sw if min(len(s), len(t)) >= 5) \
           or any(s == t for s in sw):
            hit += 1
    # v3.8.0:作者姓氏出现在引文句=强绑定证据(注册库权威名),计 1 词命中
    surnames = {a.split()[0].lower() for a in (csl.get("authors") or []) if a.split()}
    if surnames & sw:
        hit += 1
    return min(hit, len(tw)) / len(tw)


def bind_citation(cit: dict, results: list) -> dict:
    """标记→条目绑定。numeric=results[index-1];author-year=姓氏+年匹配;doi=直配。"""
    idxs = cit["index"]
    if isinstance(idxs, list):
        bound, missing = [], []
        for n in idxs:
            r = next((x for x in results if x.get("index") == n), None)
            (bound if r else missing).append(r if r else n)
        return {"marker": cit["marker"], "kind": "numeric",
                "bound": bound, "unbound": missing}
    if idxs[0] == "doi":
        r = next((x for x in results
                  if (x.get("doi") or "").lower() == idxs[1].lower()), None)
        return {"marker": cit["marker"], "kind": "doi",
                "bound": [r] if r else [], "unbound": [] if r else [idxs[1]]}
    _, surname, year = idxs
    cands = [x for x in results
             if str(x.get("year") or "") == year
             and surname.lower() in _content_words(
                 json.dumps((x.get("checks", {}).get("doi_metadata", {})
                             .get("csl", {}) or {}).get("authors", []),
                            ensure_ascii=False).lower())
             or surname.lower() in (x.get("title") or "").lower()]
    return {"marker": cit["marker"], "kind": "author-year",
            "bound": cands[:1], "unbound": [] if cands else [f"{surname} {year}"]}


def check_document(text: str, results: list, anchor_threshold: float = 0.34) -> dict:
    """文档级上下文核验:抽取→绑定→锚词匹配。语义层(句子是否真被支撑)仍归 agent。
    v4.4.0：正文提取截断到「参考文献」节之前——节内 [N] 是清单编号不是引用标记，
    不截断会把每条文献「自引」成已引用，孤儿审计与引用数全部失真（真网实战
    首跑实锤：69 处"引用"含 16 个清单标签、覆盖度假 100%）。"""
    _m = _REF_SECTION_RE.search(text)
    if _m:
        text = text[:_m.start()]
    cits = extract_citations(text)
    out = []
    cited_all = set()  # 复合标记（[1-3]/[1,3]）的全部绑定条目——审计 P1：
    # 原实现每标记只记首绑，医学高频的 [2-5] 会让条目 2-4 被误报孤儿
    for c in cits:
        b = bind_citation(c, results)
        for r in (b["bound"] or []):
            if r is not None and r.get("index") is not None:
                cited_all.add(r["index"])
        for r in (b["bound"] or [None])[:1]:
            ar = anchor_rate(c["sentence"], r) if r else 0.0
            entry = {"marker": c["marker"], "sentence": c["sentence"][:300],
                     "ref_index": (r or {}).get("index"),
                     "ref_verdict": (r or {}).get("verdict"),
                     "anchor_rate": round(ar, 3),
                     "anchor": "ok" if ar >= anchor_threshold else "low",
                     "bound": bool(r)}
            if not r:
                entry["note"] = "未绑定:正文中引用了清单外的编号/条目"
                entry["anchor"] = "n/a"
            out.append(entry)
    unbound = [e for e in out if not e["bound"]]
    low = [e for e in out if e["bound"] and e["anchor"] == "low"]
    # v4.4.0 引用完整性审计：孤儿文献（清单里列了、正文从未引用）与覆盖率。
    # 实锤：毛细支气管炎报告 16 条中 5 条（31%）从未被正文引用——列了没引是学术
    # 写作规范问题（漏引或冗列），不是编造——advisory 级，绝不改判定。
    cited_idx = {e["ref_index"] for e in out if e.get("ref_index") is not None}
    cited_idx |= cited_all
    listed_idx = sorted({r.get("index") for r in results
                         if r.get("index") is not None})
    uncited = sorted(i for i in listed_idx if i not in cited_idx)
    coverage = (round(len([i for i in listed_idx if i in cited_idx])
                      / len(listed_idx), 2) if listed_idx else 0.0)
    return {"citations": out, "n_citations": len(out),
            "n_unbound": len(unbound), "n_low_anchor": len(low),
            "anchor_threshold": anchor_threshold,
            "n_listed": len(listed_idx), "n_uncited": len(uncited),
            "uncited_refs": uncited, "coverage": coverage,
            "note": ("锚词率=引文句与被引标题的内容词重叠(阈值 %.2f);low≠错引,"
                     "是语义层人工复核候选;未引用条目=写作规范建议(漏引或冗列),"
                     "非真伪问题" % anchor_threshold)}


# ═══ v3.9.0 结构化错误码(errorHandling):五态之上的机器可读细分 ═══

def derive_error_codes(r: dict) -> list:
    """从单条 result 的 checks/note 派生结构化错误码(纯函数,零网络)。
    码表(稳定契约,MCP/脚本可依赖):
      E_DOU_NOT_FOUND   DOI 在 DOI.org 不存在(404)——编造引用
      E_TITLE_MISMATCH  DOI 存在但登记标题与声称不符——错引/张冠李戴
      E_CROSS_LANG      跨语言标题不可比——降 partial 转人工
      E_ARXIV_NOT_FOUND arXiv ID 官方 API 查无
      E_PMID_NOT_FOUND  PMID E-utilities 查无
      E_STITCHED        DOI/PMID 拼接(两键各真但指向不同论文)
      E_RETRACTED       已撤稿(Crossref/Retraction Watch)
      E_EXPRESSION_OF_CONCERN  编辑关注通告(EoC)——降级转人工(v4.1.0)
      E_AUTHOR_MISMATCH 作者姓氏与登记不符
      E_JOURNAL_MISMATCH 期刊名与登记不符
      E_UNREACHABLE     来源抓取失败(超时/反爬/网络)——不等于不存在
      E_OFFLINE         离线模式未核验
    无问题返回 [](空=没有可断言的错误信号,不等于"证明正确")。"""
    codes = []
    v = r.get("verdict")
    c = r.get("checks") or {}
    note = r.get("note") or ""
    doi_m = c.get("doi_metadata") or {}
    if "DOI 在 DOI.org 不存在" in note or (doi_m.get("matched") is False
                                          and "404" in note and r.get("doi")):
        codes.append("E_DOU_NOT_FOUND")
    elif "疑似编造或错引" in note or doi_m.get("adjust") == "invalid":
        codes.append("E_TITLE_MISMATCH")
    if "跨语言" in note:
        codes.append("E_CROSS_LANG")
    if "拼接" in note:
        codes.append("E_STITCHED")
    ax = c.get("arxiv_metadata") or {}
    if ax.get("matched") is False and r.get("arxiv"):
        codes.append("E_ARXIV_NOT_FOUND")
    if "E-utilities 查无" in note or ("E-utilities" in note and r.get("pmid")
                                      and v == "invalid"):
        codes.append("E_PMID_NOT_FOUND")
    if (c.get("retraction") or {}).get("retracted"):
        codes.append("E_RETRACTED")
    if (c.get("retraction") or {}).get("nature") == "expression_of_concern":
        codes.append("E_EXPRESSION_OF_CONCERN")
    if "作者" in note and ("不符" in note or "不一致" in note):
        codes.append("E_AUTHOR_MISMATCH")
    if "期刊名不符" in note or "期刊" in note and "不符" in note:
        codes.append("E_JOURNAL_MISMATCH")
    if v == "unreachable":
        codes.append("E_UNREACHABLE")
    if r.get("note") and "offline" in str(r.get("note", "")).lower():
        codes.append("E_OFFLINE")
    return codes


def main_with_check_document(args, results, text_path):
    text = open(text_path, encoding="utf-8").read()
    cd = check_document(text, results,
                        float(getattr(args, "anchor_threshold", 0.34) or 0.34))
    return cd



def export_bibtex(results: list, path: str) -> int:
    """仅导出 verified 条目为 BibTeX（可直接导入论文参考文献管理器）。返回条数。
    字段值经 bib_safe 加固（剥除花括号/换行，防 @entry 逃逸），citation key 保证唯一。"""
    n = 0
    used_keys = set()
    with open(path, "w", encoding="utf-8") as f:
        for r in results:
            if r["verdict"] != "verified":
                continue
            n += 1
            title = bib_safe(r.get("title") or "untitled").strip() or "untitled"
            # 评审修正：year 未经消毒可携带换行/花括号逃逸 @entry，只留数字
            ys = re.sub(r"[^0-9]", "", str(r.get("year") or ""))[:4] if r.get("year") else ""
            year = ys or "n.d."
            words = re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", title)[:3]
            key = ("holmes" + ys + "".join(words))[:42] or f"ref{r['index']}"
            k2 = key
            sfx = 2
            while k2 in used_keys:
                k2 = f"{key}_{sfx}"
                sfx += 1
            used_keys.add(k2)
            fields = [f"  title = {{{bib_safe(title)}}}"]
            if r.get("source"):
                fields.append(f"  journal = {{{bib_safe(r.get('source'))}}}")
            if r.get("year"):
                fields.append(f"  year = {{{year}}}")
            if r.get("url"):
                fields.append(f"  url = {{{bib_safe(r.get('url'))}}}")
            if r.get("doi"):
                fields.append(f"  doi = {{{bib_safe(r.get('doi'))}}}")
            if r.get("arxiv"):
                fields.append(f"  eprint = {{{bib_safe(r.get('arxiv'))}}}")
                fields.append("  archivePrefix = {arXiv}")
            notes = ["cite-holmes verified"]
            if r.get("pmid"):
                notes.append(f"PMID: {r['pmid']}")
            fields.append("  note = {{{}}}".format(bib_safe("; ".join(notes))))
            f.write("@misc{" + k2 + ",\n" + ",\n".join(fields) + "}\n\n")
    return n


def _gbt_type_code(r: dict) -> tuple:
    """GB/T 7714 文献类型标识:期刊[J];预印本/网页[EB/OL];无卷期页的电子资源兜底[EB/OL]。
    返回 (类型码, 是否电子资源)。"""
    if r.get("arxiv"):
        return "EB/OL", True
    if (r.get("checks", {}).get("doi_metadata", {}) or {}).get("csl", {}).get("container"):
        return "J", False
    if r.get("url"):
        return "EB/OL", True
    return "EB/OL", True


def export_gbt7714(results: list, path: str) -> int:
    """v3.6 GB/T 7714-2025 参考文献表导出(verified + 元数据一致的 partial,返回条数)。
    每条以注册库权威 CSL 元数据为准(mcp:checks.doi_metadata.csl;输入声称值兜底):
      期刊: 作者1, 作者2, 作者3, 等. 题名[J]. 刊名, 年, 卷(期): 页码.
      电子: 题名[EB/OL]. (发布年)[引用日期]. URL. DOI: ...
    作者规则:≤3 全列;>3 取前 3 + ", 等"(中文条目)/", et al."(拉丁条目);
    拉丁作者姓全大写+名首字母(取自 CSL 预格式化)。正文中文条目判定=题名含 CJK。
    收录策略:verified 全收;partial 仅当 DOI 元数据**一致**(adjust=="" 且有 CSL,
    如仅缺可选输入字段)——标题/期刊存疑的 partial 不收(宁缺毋错)。"""
    n = 0
    cite_date = time.strftime("%Y-%m-%d")
    lines_out = []
    for r in results:
        dm = r.get("checks", {}).get("doi_metadata", {}) or {}
        if r["verdict"] == "verified":
            pass
        elif (r["verdict"] == "partial" and dm.get("adjust") == ""
              and dm.get("matched") and dm.get("csl")):
            pass  # 元数据一致、仅缺可选输入字段的 partial:注册库已确认存在与内容
        else:
            continue
        csl = (r.get("checks", {}).get("doi_metadata", {}) or {}).get("csl") or {}
        title = (csl.get("title") or r.get("title") or "").strip() or "untitled"
        year = str(csl.get("year") or r.get("year") or "").strip()
        authors = list(csl.get("authors") or [])
        if not authors:
            raw = re.split(r"[,，;；、]", str(r.get("authors") or ""))
            authors = [a.strip() for a in raw if a.strip()]
        cjk_title = any("\u4e00" <= c <= "\u9fff" for c in title)
        et_al = "等" if cjk_title else "et al"
        if len(authors) > 3:
            authors = authors[:3] + [et_al]
        author_str = ", ".join(authors)
        tcode, is_e = _gbt_type_code(r)
        seg = []
        if author_str:
            seg.append(author_str + ".")
        seg.append(f"{title}[{tcode}].")
        container = (csl.get("container") or r.get("source") or "").strip()
        vol = csl.get("volume") or ""
        iss = csl.get("issue") or ""
        page = csl.get("page") or ""
        if tcode == "J" and container:
            part = f"{container}, {year or 's.d.'}"
            if vol:
                part += f", {vol}"
                if iss:
                    part += f"({iss})"
            if page:
                part += f": {page}"
            seg.append(part + ".")
        else:
            if year:
                seg.append(f"({year}).")
            seg.append(f"[{cite_date}].")
        url = (r.get("url") or "").strip()
        doi = (r.get("doi") or "").strip()
        if doi and not url.lower().startswith("https://doi.org/"):
            seg.append(f"DOI: {doi}.")  # DOI 尾注(规范形);url 为 doi.org 链接时已承载
        if url:
            seg.append(f"{url}.")
        lines_out.append(" ".join(seg))
        n += 1
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out) + ("\n" if lines_out else ""))
    return n


def export_ris(results: list, path: str) -> int:
    """v3.7.0 RIS 导出(Zotero/EndNote 通用,与 v1.9 BibTeX 导入构成回环)。
    收录策略与 GB/T 相同:verified + 元数据一致 partial。AU 每作者一行。"""
    n = 0
    out = []
    for r in results:
        dm = r.get("checks", {}).get("doi_metadata", {}) or {}
        if r["verdict"] == "verified":
            pass
        elif (r["verdict"] == "partial" and dm.get("adjust") == ""
              and dm.get("matched") and dm.get("csl")):
            pass
        else:
            continue
        csl = dm.get("csl") or {}
        title = (csl.get("title") or r.get("title") or "").strip() or "untitled"
        out.append("TY  - " + ("JOUR" if csl.get("container") else "GEN"))
        out.append("TI  - " + title)
        for a in (csl.get("authors") or []):
            out.append("AU  - " + a)
        if not csl.get("authors") and r.get("authors"):
            for a in re.split(r"[,，;；、]", str(r["authors"])):
                if a.strip():
                    out.append("AU  - " + a.strip())
        if csl.get("container"):
            out.append("JO  - " + csl["container"])
        if r.get("source"):
            out.append("PB  - " + str(r["source"])[:200])
        if csl.get("year") or r.get("year"):
            out.append("PY  - " + str(csl.get("year") or r.get("year")))
        if csl.get("volume"):
            out.append("VL  - " + csl["volume"])
        if csl.get("issue"):
            out.append("IS  - " + csl["issue"])
        if csl.get("page"):
            pg = str(csl["page"])
            if "-" in pg:
                sp, ep = pg.split("-", 1)
                out.append("SP  - " + sp.strip())
                out.append("EP  - " + ep.strip())
            else:
                out.append("SP  - " + pg)
        if r.get("doi"):
            out.append("DO  - " + str(r["doi"]))
        if r.get("url"):
            out.append("UR  - " + str(r["url"]))
        out.append("N1  - cite-holmes verified (" + r["verdict"] + ")")
        out.append("ER  - ")
        out.append("")
        n += 1
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    return n


def export_csv(results: list, path: str) -> None:
    """全量审计台账 CSV（utf-8-sig，Excel 直接打开不乱码）。单元格做公式注入中和。"""
    cols = ["index", "title", "verdict", "tier", "http_status", "needs_human_check",
            "year", "source", "url", "doi", "pmid", "arxiv", "note"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in results:
            row = [csv_safe(str(r.get(c) if r.get(c) is not None else "")) for c in cols]
            w.writerow(row)


def export_audit(results: list, path: str, offline: bool, profile: str) -> None:
    """v1.9 透明工作底稿（auditjson）：每条引用的逐项检查明细，机器可读。
    供人工复核、机构审计与流程合规——回应"检测系统需要透明多源"的行业呼吁
    （arXiv 2607.22693：五家检测工具均不可无人监督运行，透明度是刚需）。"""
    doc = {
        "version": VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "offline": offline, "profile": profile,
        "checks_catalog": {
            "doi_metadata": "DOI.org CSL 元数据（标题/年份/期刊/作者交叉核验）",
            "retraction": "Crossref/Retraction Watch 撤稿库",
            "s2": "Semantic Scholar 第三源交叉确认（只确认不降级）",
            "s2_title": "Semantic Scholar 标题检索确认（无 DOI/PMID/arXiv 引用的正面信号，只确认不降级）",
            "arxiv_metadata": "arXiv 官方 API（标题/年份）",
            "arxiv_landing_fallback": "arXiv API 失败时官方着陆页标题比对（v1.11 确定性保卫）",
            "url": "可达性检查（HEAD→GET 降级）",
            "openalex": "OpenAlex 书目级存在性（只确认不降级）",
            "wayback": "Wayback Machine 存档对照（unreachable 时）",
            "doi_pmid_crosscheck": "DOI↔PMID 拼接伪造检测",
            "semantic_audit": "语义层工作底稿（v1.11，模型判定结构化透出；not_in_source/contradicted 封顶 partial）",
            "citation_contexts": "L3 引文语境层（v3.0.0，S2 citations contexts/intents——学界评价）",
            "l4_evidence_cascade": "L4 证据升级级联（v3.1.0 接入主流程：语义 not_in_source/unclear 且配置裁判端点时，升级官方摘要/全文段落检索+外置裁判；判定只加固不翻案）"},
        "results": [{"index": r.get("index"), "title": r.get("title"),
                     "verdict": r.get("verdict"), "tier": r.get("tier"),
                     "http_status": r.get("http_status"),
                     "needs_human_check": bool(r.get("needs_human_check")),
                     "checks": r.get("checks") or {},
                     "semantic_audit": r.get("semantic_audit"),
                     "citation_contexts": r.get("citation_contexts"),
                     "triples": (r.get("semantic_audit") or {}).get("triples", []),
                     "note": r.get("note", "")}
                    for r in results],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def precheck_conclusion(sc: dict) -> str:
    """v1.9 投稿前结论（一行）：arXiv 自 2026-05 起对含幻觉/未核引用的投稿实施
    处罚（最长禁投一年；v1.11 据 Nature 2026-05-19 报道修正起始月份），ICML 2026
    等会议亦将幻觉引用列为桌拒理由——报告头部直接给出可否提交的结论。"""
    c = sc["counts"]
    parts = [f"{c[k]} 条 {k}" for k in ("invalid", "unreachable", "unverified") if c[k]]
    if parts:
        return ("⚠️ 投稿前结论：不建议直接提交——存在 " + " / ".join(parts)
                + "，先完成人工复核（arXiv 自 2026-05 起、ICML 2026 等会议已对"
                "含幻觉/未核引用的投稿实施处罚）")
    if c["partial"]:
        return (f"🟡 投稿前结论：可提交，但建议先处理 {c['partial']} 条 partial"
                "（降级使用项，正文引用需注明保留意见）")
    return "✅ 投稿前结论：全部 verified——可进入投稿流程"


def render_md(results: list, offline: bool, profile: str = "general",
              context_check: dict = None) -> str:
    sc = compute_scorecard(results)
    c = sc["counts"]
    lines = [
        render_bluf(results, sc), "",
        "# 引用机械验证报告",
        f"- 验证器：verify_refs.py v{VERSION} · 模式：{'offline（未联网）' if offline else 'online'}"
        + (" · 医学信源预设" if profile == "medical" else ""),
    ]
    if profile == "medical":
        lines.append("- ⚠️ 免责声明：本报告仅为信源机械核验，不构成证据分级结论或医疗建议；"
                     "预印本/社区层来源不得支撑医学结论。")
    lines.append(f"- {precheck_conclusion(sc)}")

    lines += [
        "",
        "## CiteScore 置信度评分",
        f"### **{sc['score']} / 100 · {sc['grade']} 级**",
        "",
        f"- 总计 {sc['total']} 条：✅verified {c['verified']} · 🟡partial {c['partial']} · "
        f"⚠️unreachable {c['unreachable']} · ❌invalid {c['invalid']} · ⏸unverified {c['unverified']}",
        "- 计分：verified +10 / partial +4 / unreachable 0 / unverified −2 / invalid −8，"
        "满分 = 10 × 条数，归一化 0-100",
        "",
        "| # | 标题 | 层级 | HTTP | 判定 | 说明 |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        title = md_cell(r["title"], 48)
        # 含 Wayback 存档链的备注放宽截断（存档 URL 普遍 >90 字符，截断即废链）
        note = md_cell(r["note"], 200 if "web.archive.org" in (r.get("note") or "") else 90)
        lines.append(f"| {r['index']} | {title} | {r['tier']} | "
                     f"{r['http_status'] or '-'} | {VERDICT_ZH[r['verdict']]} | {note} |")
    flagged = [r for r in results if r["needs_human_check"] or r["verdict"] in ("invalid", "unverified")]
    if flagged:
        lines += ["", "## 待人工复核", ""]
        for r in flagged:
            lim = 200 if "web.archive.org" in (r.get("note") or "") else 110
            act = {"invalid": "建议：删除或更换信源",
                   "unreachable": "建议：人工打开原链复核",
                   "unverified": "建议：在线环境重跑验证"}.get(r["verdict"], "建议：按备注复核")
            lines.append(f"- #{r['index']} {md_cell(r['title'], 60)} → {r['verdict']}"
                         f"（{act}）：{md_cell(r['note'], lim)}")
    # v1.11 语义层判定区：仅当引用带结构化 semantic 字段时输出（无则与 v1.10
    # 输出逐字节一致，老消费者零感知）。机械层只做结构化透出与封顶，判定由模型做出。
    sem_rows = [r for r in results if r.get("semantic_audit")]
    if sem_rows:
        lines += ["", "## 语义层判定（模型在研究流程中做出，机械层结构化透出）", "",
                  "| # | support | 论断（claim） | 原文摘句 |",
                  "|---|---|---|---|"]
        for r in sem_rows:
            sa = r["semantic_audit"]
            lines.append(f"| {r['index']} | {md_cell(sa.get('support'), 16)} | "
                         f"{md_cell(sa.get('claim'), 60)} | "
                         f"{md_cell(sa.get('quote'), 60)} |")
        lines += ["", "support 取值：supported 支撑 / partial 部分支撑 / not_in_source "
                  "来源未包含 / contradicted 相矛盾 / unclear 无法判定；"
                  "not_in_source 与 contradicted 的条目已封顶 partial 并转人工复核。"]
    lines += ["", "## 能力边界矩阵", "",
              "- ✅ 机械层已抓伪造类型：" + "；".join(capability_matrix()["caught"]),
              "- 🧠 仍需语义层把关：" + "；".join(capability_matrix()["semantic"]),
              "- 🚫 不支持的输入：" + "；".join(capability_matrix()["unsupported"]),
              "", "## 判定说明", "",
              "- `verified`：可达 + 权威层(official/journal/preprint/media) + 字段完整 —— 可支撑正文结论",
              "- `partial`：可达但社区/博客层来源，或字段缺失 —— 降级使用，结论需注明",
              "- `unreachable`：抓取失败（404/超时/反爬）—— 不等于不存在，需人工打开复核",
              "- `invalid`：无 URL/DOI 或格式错误 —— 不得进入报告",
              "- 语义验证（来源是否支持论断）由模型完成，本报告只覆盖机械层", ""]
    # v3.8.0 上下文核验区(--check-document 时呈现)
    if context_check:
        lines += ["", "## 上下文核验（正文 in-text 引用）", "",
                  f"- 正文引用 {context_check['n_citations']} 处：未绑定 "
                  f"{context_check['n_unbound']}，锚词不足 {context_check['n_low_anchor']}"
                  f"（阈值 {context_check['anchor_threshold']}）"]
        if context_check.get("n_listed"):
            _u = context_check.get("uncited_refs") or []
            _us = (f"（条目 {'、'.join(str(i) for i in _u[:10])}"
                   f"{'…' if len(_u) > 10 else ''}）" if _u else "")
            lines.append(
                f"- 引用覆盖 {context_check['coverage']:.0%}：清单 "
                f"{context_check['n_listed']} 条中 {context_check['n_uncited']} 条"
                f"未在正文引用{_us}——漏引或冗列建议（写作规范提示，非真伪判定）")
        for c in context_check["citations"]:
            if not c["bound"]:
                lines.append(f"- ⚠️ {c['marker']} 未绑定——正文引用了清单外的编号/条目")
            elif c["anchor"] == "low":
                lines.append(f"- ⚠️ {c['marker']} 锚词率 {c['anchor_rate']}"
                             f"（疑似错配引文：引文句与被引标题内容词重叠过低）→ 人工复核")
        lines += ["", "- 锚词率低≠错引：是语义层人工复核候选（句子是否真被支撑由模型判定）"]
    _pairs = collect_clone_pairs(results)  # v3.10 克隆引用对区块（有对才出现）
    if _pairs:
        lines += ["", "## 克隆引用对（同题不同 DOI / 同 DOI 不同题）", ""]
        for p in _pairs:
            kind = ("同一标题挂多个不同 DOI——至少一个标识为编造或错引"
                    if p["kind"] == "clone_doi" else
                    "同一 DOI 挂不同标题——拼接变体，两条判定已各自独立核验")
            lines.append(f"- #{p['a']} ↔ #{p['b']}（相似度 {p['sim']}）：{kind}；以元数据核验为准")
        lines.append("")
    _prof = profile_bibliography(results)  # v3.11 清单画像区块（有旗标才出现）
    if _prof["flags"]:
        lines += ["", "## 清单画像（批量伪造指纹筛查）", "",
                  "> 逐条核验抓单条伪造，画像抓整批伪装——旗标是人工抽查建议，不是判定。"]
        for f in _prof["flags"]:
            lines.append(f"- **{f['kind']}**：{f['detail']}")
        lines.append("")
    # v3.7.0 求星合规铺设:交付物尾注(每报告一次,低调一行;家族任务 10-06)
    lines += ["", "> 本文档由 cite-holmes 生成（[GitHub](https://github.com/docsor1212/cite-holmes) · "
              "[SkillHub](https://skillhub.cn/skills/indiv-sorsor/cite-holmes)）· 觉得有用欢迎 Star / 收藏", ""]
    return "\n".join(lines)


def render_html(results: list, offline: bool, profile: str = "general",
                context_check: dict = None) -> str:
    """v1.7：自包含单文件 HTML 报告——零外链（无外部 CSS/JS/字体）、移动端可读，
    用作给导师/编辑的存档分享件（与 BibTeX/CSV 台账并列的第三种交付物）。
    动态内容全部经 html_escape；备注中的 URL 转为可点击链接。"""
    sc = compute_scorecard(results)
    c = sc["counts"]
    e = html_escape
    vcls = {"verified": "v-ok", "partial": "v-part", "unreachable": "v-unreach",
            "invalid": "v-bad", "unverified": "v-unk"}

    def linkify(note: str) -> str:
        s = e(str(note or ""))
        return re.sub(r"(https?://[^\s<\"]+)",
                      lambda m: f'<a href="{m.group(1)}">{m.group(1)}</a>', s)

    def _chain(r: dict) -> str:
        """v2.0.0 证据链微可视化:基于 checks 明细生成检查路径图标行。"""
        c = r.get("checks") or {}
        seg = []
        if c.get("doi_metadata"):
            seg.append(("DOI.org" + (" ✓" if c["doi_metadata"].get("matched") else " ?")))
        if c.get("arxiv_metadata"):
            seg.append("arXiv ✓" if c["arxiv_metadata"].get("matched") else "arXiv ?")
        if c.get("s2"):
            seg.append("S2 ✓" if c["s2"].get("matched") else "S2 ·")
        if c.get("retraction"):
            # v4.1.0 分档展示：撤稿族⚠/EoC⚠/更正ℹ/检查未完成✗（失败不冒充干净）
            r = c["retraction"]
            if r.get("retracted"):
                seg.append("撤稿⚠")
            elif r.get("nature") == "expression_of_concern":
                seg.append("EoC⚠")
            elif r.get("nature") == "correction":
                seg.append("更正ℹ")
            elif r.get("check_failed"):
                seg.append("撤稿检查✗")
            else:
                seg.append("撤稿库 ✓")
        if c.get("pubmed_reverse"):
            # v4.1.0：反查三态（命中✓/未命中·/传输失败✗）——失败不冒充查无
            pr = c["pubmed_reverse"]
            if pr.get("network_error"):
                seg.append("反查✗")
            elif pr.get("matched"):
                seg.append("反查✓")
            else:
                seg.append("反查·")
        if c.get("openalex"):
            seg.append("OpenAlex ✓" if c["openalex"].get("confirmed") else "OpenAlex ·")
        if c.get("url"):
            seg.append("可达 ✓" if c["url"].get("reachable") else "可达 ✗")
        if c.get("wayback"):
            seg.append("存档 ·")
        return " → ".join(seg)

    rows = []
    for r in results:
        chain = _chain(r)
        chain_html = (f"<br><span class='chain'>{e(chain)}</span>" if chain else "")
        rows.append(
            f"<tr><td>{r['index']}</td>"
            f"<td>{e(str(r.get('title') or ''))}</td>"
            f"<td>{e(str(r.get('tier') or ''))}</td>"
            f"<td>{r.get('http_status') if r.get('http_status') is not None else '-'}</td>"
            f"<td class='{vcls[r['verdict']]}'><b>{VERDICT_ZH[r['verdict']]}</b></td>"
            f"<td class='note'>{linkify(r.get('note'))}{chain_html}</td></tr>")

    actions = {"invalid": "建议：删除或更换信源", "unreachable": "建议：人工打开原链复核",
               "unverified": "建议：在线环境重跑验证"}
    review = []
    for r in results:
        if r.get("needs_human_check") or r["verdict"] in ("invalid", "unverified"):
            act = actions.get(r["verdict"], "建议：按备注复核")
            review.append(f"<li>#{r['index']} {e(str(r.get('title') or ''))} → "
                          f"<b>{r['verdict']}</b>（{act}）：{linkify(r.get('note'))}</li>")
    review_html = ("<h2>待人工复核</h2><ul>" + "".join(review) + "</ul>") if review else ""

    cap = capability_matrix()
    cap_html = (f"<h2>能力边界矩阵</h2>"
                f"<p>✅ <b>机械层已抓伪造类型</b>：{e('；'.join(cap['caught']))}</p>"
                f"<p>🧠 <b>仍需语义层把关</b>：{e('；'.join(cap['semantic']))}</p>"
                f"<p>🚫 <b>不支持的输入</b>：{e('；'.join(cap['unsupported']))}</p>")

    # v1.11 语义层判定区（仅当引用带结构化 semantic 字段时输出）
    sem_rows = [r for r in results if r.get("semantic_audit")]
    if sem_rows:
        sem_trs = "".join(
            f"<tr><td>{r['index']}</td>"
            f"<td>{e(str(r['semantic_audit'].get('support') or ''))}</td>"
            f"<td>{e(str(r['semantic_audit'].get('claim') or ''))}</td>"
            f"<td>{e(str(r['semantic_audit'].get('quote') or ''))}</td></tr>"
            for r in sem_rows)
        sem_html = (f"<h2>语义层判定</h2>"
                    f"<p class='meta'>模型在研究流程中做出，机械层结构化透出；"
                    f"not_in_source / contradicted 条目已封顶 partial 并转人工复核。</p>"
                    f"<table><tr><th>#</th><th>support</th><th>论断（claim）</th>"
                    f"<th>原文摘句</th></tr>{sem_trs}</table>")
    else:
        sem_html = ""

    med = ("<p class='disclaim'>⚠️ 免责声明：本报告仅为信源机械核验，不构成证据分级结论"
           "或医疗建议；预印本/社区层来源不得支撑医学结论。</p>") if profile == "medical" else ""
    pcls = "disclaim" if sc["counts"]["invalid"] or sc["counts"]["unreachable"] or sc["counts"]["unverified"] else "preok"
    pre = (f"<p class='{pcls}'>{e(precheck_conclusion(sc))}</p>")
    bluf = render_bluf(results, sc)
    bluf_v = html_escape("\n".join(l for l in bluf.splitlines()
                                if not l.startswith("---")))
    cc_html_block = ""
    if context_check:
        rows_cc = []
        for item_cc in context_check["citations"]:  # v3.8.0:变量名避开 f-string 后文的 c
            if not item_cc["bound"]:
                state = "⚠️ 未绑定（清单外条目）"
            elif item_cc["anchor"] == "low":
                state = f"⚠️ 锚词率 {item_cc['anchor_rate']}（疑似错配引文，人工复核）"
            else:
                state = f"锚词率 {item_cc['anchor_rate']}"
            rows_cc.append(f"<li>#{item_cc.get('ref_index') or '-'} {item_cc['marker']} — {state}<br>"
                           f"<span class='note'>{item_cc['sentence'][:160]}</span></li>")
        cc_html_block = ("<div style='margin-top:20px;padding:12px;border:1px solid #e5e5e5;border-radius:6px;'>"
                         "<h3 style='margin:0 0 8px 0;'>上下文核验（正文 in-text 引用）</h3>"
                         f"<p>共 {context_check['n_citations']} 处：未绑定 {context_check['n_unbound']}，"
                         f"锚词不足 {context_check['n_low_anchor']}（阈值 {context_check['anchor_threshold']}）。"
                         "锚词率低≠错引，是语义层人工复核候选。</p><ul>"
                         + "".join(rows_cc) + "</ul></div>")
    _pairs = collect_clone_pairs(results)  # v3.10 克隆引用对区块（有对才出现）
    clone_html_block = ""
    if _pairs:
        rows_cl = []
        for p in _pairs:
            kind = ("同一标题挂多个不同 DOI——至少一个标识为编造或错引"
                    if p["kind"] == "clone_doi" else
                    "同一 DOI 挂不同标题——拼接变体，两条判定已各自独立核验")
            rows_cl.append(f"<li>#{p['a']} ↔ #{p['b']}（相似度 {p['sim']}）：{kind}；以元数据核验为准</li>")
        clone_html_block = ("<div style='margin-top:20px;padding:12px;border:1px solid #f0d9d9;"
                            "border-radius:6px;background:#fffafa;'>"
                            "<h3 style='margin:0 0 8px 0;'>克隆引用对（同题不同 DOI / 同 DOI 不同题）</h3>"
                            "<ul>" + "".join(rows_cl) + "</ul></div>")
    _prof = profile_bibliography(results)  # v3.11 清单画像区块（有旗标才出现）
    prof_html_block = ""
    if _prof["flags"]:
        rows_pf = [f"<li><b>{f['kind']}</b>：{e(f['detail'])}</li>" for f in _prof["flags"]]
        prof_html_block = ("<div style='margin-top:20px;padding:12px;border:1px solid #e5e5e5;"
                           "border-radius:6px;'>"
                           "<h3 style='margin:0 0 8px 0;'>清单画像（批量伪造指纹筛查）</h3>"
                           "<p>逐条核验抓单条伪造，画像抓整批伪装——旗标是人工抽查建议，不是判定。</p>"
                           "<ul>" + "".join(rows_pf) + "</ul></div>")
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>引用机械验证报告 · CiteScore {sc['score']}/{sc['grade']}</title>
<style>
body{{font-family:system-ui,-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
margin:0 auto;padding:16px;max-width:960px;color:#1c2733;background:#fbfaf7;line-height:1.55}}
h1{{font-size:1.3em}} .score{{font-size:2.6em;font-weight:700}}
.v-ok{{color:#1a7f37}} .v-part{{color:#9a6700}} .v-unreach{{color:#b45309}}
.v-bad{{color:#c1341b}} .v-unk{{color:#57606a}}
.bluf{{background:#eef6ff;padding:10px 12px;border-radius:6px;font-size:.85em;white-space:pre-wrap;margin:8px 0}}
.chain{{color:#57606a;font-size:.78em;opacity:.85}}
.preok{{color:#1a7f37;background:#e9f7ee;padding:8px 12px;border-radius:6px}}
table{{border-collapse:collapse;width:100%;font-size:.88em;background:#fff}}
td,th{{border:1px solid #d8d2c4;padding:6px 8px;vertical-align:top;text-align:left}}
td.note{{word-break:break-all}} a{{color:#0b5394;word-break:break-all}}
.disclaim{{color:#9a6700;background:#fdf6dd;padding:8px 12px;border-radius:6px}}
.meta{{color:#57606a}} footer{{margin-top:24px;color:#57606a;font-size:.85em;
border-top:1px solid #d8d2c4;padding-top:8px}}
</style></head><body>
<h1>引用机械验证报告</h1>
<!-- cite-holmes BLUF machine-readable
{bluf}
-->
<pre class="bluf">{bluf_v}</pre>
<p class="score">{sc['score']}<span style="font-size:.45em;color:#57606a"> / 100 · {sc['grade']} 级</span></p>
<p class="meta">验证器 verify_refs.py v{VERSION} · 模式：{'offline（未联网）' if offline else 'online'}
{' · 医学信源预设' if profile == 'medical' else ''}<br>
总计 {sc['total']} 条：✅verified {c['verified']} · 🟡partial {c['partial']} ·
⚠️unreachable {c['unreachable']} · ❌invalid {c['invalid']} · ⏸unverified {c['unverified']}</p>
{med}
{pre}
<table><tr><th>#</th><th>标题</th><th>层级</th><th>HTTP</th><th>判定</th><th>说明</th></tr>
{''.join(rows)}</table>
{review_html}
{sem_html}
{cap_html}
<h2>判定说明</h2>
<ul>
<li><b>verified</b>：可达 + 权威层 + 字段完整——可支撑正文结论</li>
<li><b>partial</b>：可达但社区/博客层，或字段/期刊/作者存疑——降级使用</li>
<li><b>unreachable</b>：抓取失败——不等于不存在，需人工打开复核</li>
<li><b>invalid</b>：无 URL/DOI、编号不存在或格式错误——不得进入报告</li>
</ul>
<footer>语义验证（来源是否支持论断）由模型完成，本报告只覆盖机械层；
指向真实可信页面的精心伪造仍需人工判断。cite-holmes · Cite Holmes</footer>
{cc_html_block}
{clone_html_block}
{prof_html_block}
<footer style="margin-top:24px;padding-top:12px;border-top:1px solid #eee;color:#9aa0a6;font-size:12px;text-align:center;">
本文档由 cite-holmes 生成 · <a href="https://github.com/docsor1212/cite-holmes" style="color:#9aa0a6;">GitHub</a> · <a href="https://skillhub.cn/skills/indiv-sorsor/cite-holmes" style="color:#9aa0a6;">SkillHub</a> · 觉得有用欢迎 Star / 收藏
</footer>
</body></html>"""


_DOCTOR_PROBES = [
    ("DOI.org 解析", "https://doi.org/10.3866/PKU.WHXB201112303"),
    ("Crossref API", "https://api.crossref.org/works?rows=0&mailto=doctor%40cite-holmes"),
    ("PubMed E-utilities", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
                           "esearch.fcgi?db=pubmed&retmode=json&retmax=0&term=cite+holmes+doctor"),
    ("arXiv API", "https://export.arxiv.org/api/query?search_query=all:cite&max_results=1"),
    ("OpenAlex", "https://api.openalex.org/works?per-page=1&select=id"),
    ("Semantic Scholar", "https://api.semanticscholar.org/graph/v1/paper/"
                         "DOI:10.3866/PKU.WHXB201112303?fields=title"),
    ("Wayback 存档", "https://archive.org/wayback/available?url=example.com"),
]


# ═══ v3.14 --grill 对抗审查:对已核验报告做「审稿人预演」 ═══

_GRILL_BY_VERDICT = {
    "verified": [
        "该文献在你核验之后是否可能被撤稿/更正？——投稿前用撤稿库复查一次（--refresh-cache 重跑）",
        "引用句声称的结论强度是否超过了该文献实际支持的范围？（机械层只证明来源存在且一致，"
        "「这句话是否被支撑」请对照原文逐句确认——必要时用 --check-document 做锚词核验）",
        "你引用的是这一篇，还是同刊同年的相似题名？核对卷期页与 DOI 是否逐字一致",
    ],
    "partial": [
        "降级原因（见注记/错误码）是否直接影响你引用的那句话？若只影响其他部分，"
        "在正文中明确标注保留意见范围",
        "能否找到一个更强的替代来源替换它？（partial 来源长期留在关键结论上是风险敞口）",
    ],
    "unreachable": [
        "报告附带的 Wayback 存档链里，存档内容与你声称的内容一致吗？打开对照过吗？",
        "更换网络（--cn/--proxy）重跑后仍不可达吗？——不可达连续两轮就该换信源",
    ],
    "invalid": [
        "标识符是否为一位之差的抄写错误？按标题在注册库检索过正确的 ID 吗？",
        "若为编造：溯源到正文哪一句产生的它？——同一句附近的其他引用需要连坐复查",
    ],
    "unverified": [
        "联网重跑的阻塞是什么？离线 partial 不能作为投稿依据（ADR-0003）",
    ],
}

_GRILL_LIST_LEVEL = [
    "清单画像/克隆对旗标（若有）逐条作答了吗？——旗标是审稿人第一眼会问的问题单",
    "CiteScore 与投稿结论基于本次核验时刻——距投稿超过一周建议 --refresh-cache 重跑一次",
    "「待人工复核」区的条目是否每条都有了结论（处理/替换/删除）？——带着未决条目投稿是最大风险",
]


def grill_report(results: list) -> list:
    """v3.14 对抗审查问题单（审稿人预演，纯模板零网络）：对已核验的每条引用
    生成「最强挑战问题」——逐条作答后报告才具备投稿说服力。只出问题不出
    判定（与 ADR-0005 同向：这是自查工具，不是二次审判）。返回
    [{index, verdict, title, questions}]。"""
    out = []
    for r in results:
        qs = list(_GRILL_BY_VERDICT.get(r.get("verdict"), [
            "该条判定异常（非五态），请重跑确认",
        ]))
        note = str(r.get("note") or "")
        if "克隆引用对" in note:
            qs.append("该条处于克隆引用对中——与配对条目孰真孰假，元数据核验结论是什么？")
        if "正式发表" in note:
            qs.append("预印本升级提示处理了吗？引用是否已换成注记中的期刊版 DOI？")
        if "跨语言" in note:
            qs.append("跨语言桥接未命中/命中——登记原题与你的引文是同一篇吗？人工确认了吗？")
        out.append({"index": r.get("index"), "verdict": r.get("verdict"),
                    "title": str(r.get("title") or "")[:80], "questions": qs})
    return out


def render_grill_md(items: list, meta: dict) -> str:
    """v3.14 对抗审查问题单渲染（md）。meta 含 score/grade。"""
    n_q = sum(len(x["questions"]) for x in items)
    bluf = ("---\nverdict: 对抗审查问题单就绪——逐条作答后再投稿\n"
            f"key_numbers: {len(items)} 条引用 · {n_q} 个挑战问题 · 判定不变\n"
            "blocker: 无（问题单是自查工具）\n"
            "next_action: 按清单逐条作答，未决条目投稿前处理\n"
            f"cite_holmes_version: {VERSION}\n---")
    lines = [bluf, "",
             "# 对抗审查问题单（审稿人预演）",
             f"- 生成：verify_refs.py v{VERSION} · 来源报告 CiteScore "
             f"{meta.get('score', '?')}/100（{meta.get('grade', '?')} 级）",
             "- 用法：逐条作答。答不上来的条目就是你投稿前要处理的事——问题单"
             "不改变任何判定（自查工具，非二次审判）。", ""]
    cur = None
    for it in items:
        if it["verdict"] != cur:
            cur = it["verdict"]
            lines.append(f"## {VERDICT_ZH.get(cur, cur)}")
        lines.append(f"### #{it['index']} {it['title']}")
        for q in it["questions"]:
            lines.append(f"- [ ] {q}")
        lines.append("")
    lines += ["## 清单级追问", ""]
    for q in _GRILL_LIST_LEVEL:
        lines.append(f"- [ ] {q}")
    lines.append("")
    return "\n".join(lines)


# v3.12 --explain:错误码人话翻译表(与 derive_error_codes 码表一一对应)
_ERR_CODE_ZH = {
    "E_DOU_NOT_FOUND": "DOI 在 DOI.org 不存在（404）——疑似编造引用",
    "E_TITLE_MISMATCH": "DOI 存在但登记标题与声称不符——错引或张冠李戴",
    "E_CROSS_LANG": "跨语言标题无法机器比对——已保守处理，建议人工核对",
    "E_ARXIV_NOT_FOUND": "arXiv ID 官方 API 查无",
    "E_PMID_NOT_FOUND": "PMID 在 PubMed E-utilities 查无",
    "E_STITCHED": "标识符拼接嫌疑（两键各真但疑似指向不同论文）",
    "E_RETRACTED": "命中撤稿记录（Crossref/Retraction Watch）",
    "E_EXPRESSION_OF_CONCERN": "编辑关注通告（Expression of Concern）——证据效力存疑，转人工",
    "E_AUTHOR_MISMATCH": "作者姓氏与登记列表不符",
    "E_JOURNAL_MISMATCH": "期刊名与登记不符",
    "E_UNREACHABLE": "来源抓取失败（超时/反爬/网络）——不等于不存在",
    "E_OFFLINE": "离线模式未执行核验",
}


def explain_ref(r: dict) -> str:
    """v3.12 单条判定链人话解释（--explain N）：判定语义 → 依据步骤 →
    错误码翻译 → 注记要点 → 完整度 → 建议动作。纯静态，零网络；
    与 MCP explain_verdict 同源语义（本版为 CLI 超集：含错误码/克隆对/
    预印本/完整度等 v3.10+ 新信号）。"""
    v = r.get("verdict")
    base = {
        "verified": ("来源存在、处于权威层级、字段完整，且通过官方注册库交叉核验",
                     "可支撑正文结论；引用时保留原始链接与判定时间"),
        "partial": ("来源可达但存在降级因素（社区层级/字段缺失/元数据存疑/撤稿/语义否定）",
                    "降级使用：正文引用注明保留意见，或先人工复核再升级"),
        "unreachable": ("本次抓取失败（404/超时/反爬），不等于不存在",
                        "先开报告附带的 Wayback 存档链对照；关键来源反复失败则更换信源"),
        "invalid": ("标识符不存在、指向错误论文或拼接伪造——机械层确凿判死",
                    "不得引用；从清单删除或更换信源"),
        "unverified": ("未执行检查（离线模式或跳过）",
                       "联网环境重跑以获得真实判定"),
    }.get(v)
    if base is None:
        return f"无法解释：未知判定 {v!r}"
    why, action = base
    lines = [f"== 第 {r.get('index')} 条：{str(r.get('title') or '')[:60]}",
             f"判定：{v} —— {why}"]
    steps = []
    c = r.get("checks") or {}
    dm = c.get("doi_metadata") or {}
    if dm.get("matched"):
        steps.append("DOI.org 注册元数据比对一致（标题/年份）")
    elif r.get("doi") and dm:
        steps.append("DOI.org 注册元数据未确认（获取失败或比对未通过）")
    if (c.get("arxiv_metadata") or {}).get("matched"):
        steps.append("arXiv 官方 API 元数据比对一致")
    if (c.get("s2") or {}).get("matched"):
        steps.append("Semantic Scholar 第三源交叉确认")
    if (c.get("retraction") or {}).get("retracted"):
        steps.append("⚠️ 撤稿库命中——见错误码")
    if (c.get("openalex") or {}).get("confirmed"):
        steps.append("OpenAlex 书目级存在性确认")
    u = c.get("url") or {}
    if u.get("reachable") is True:
        steps.append(f"来源页可达（HTTP {u.get('status')}）")
    if (c.get("wayback") or {}).get("archive_found"):
        steps.append("Wayback 存档对照可用")
    lines.append("依据：" + ("；".join(steps) if steps else "无可用检查记录（离线/跳过）"))
    codes = r.get("error_codes") or derive_error_codes(r)
    if codes:
        zh = [_ERR_CODE_ZH.get(x, x) for x in codes]
        lines.append("错误码：" + "；".join(f"{x}（{z}）" for x, z in zip(codes, zh)))
    note = str(r.get("note") or "").strip()
    if note:
        lines.append("注记：" + (note[:300] + ("…" if len(note) > 300 else "")))
    comp = r.get("completeness")
    if isinstance(comp, dict) and comp.get("score") is not None:
        extra = f"（缺：{'、'.join(comp['missing'])}）" if comp.get("missing") else ""
        lines.append(f"导出完整度：{comp['score']}/100{extra}")
    lines.append(f"建议：{action}")
    return "\n".join(lines)


def run_doctor(net: bool = False, timeout: float = 6.0,
               cache_path: str = "") -> int:
    """v3.10 --doctor 环境自检：先做零外呼体检（版本/缓存目录/配置键/运行
    形态），--net 时加测各学术注册库连通性与延迟。三态 PASS/WARN/FAIL；
    FAIL 存在退出码 1（可入 CI 健康门）。doctor 只诊断不治疗——修复建议
    给到操作层，绝不静默改配置。"""
    checks = []  # (name, status, detail)
    checks.append(("引擎版本", "PASS",
                   f"verify_refs.py v{VERSION} · Python {sys.version.split()[0]}"))
    # 缓存目录可写（持久缓存 v1.12 的唯一落盘依赖；写失败会静默停用——doctor 把它显性化）
    cp = os.path.expanduser(cache_path or "~/.cache/cite-holmes/cache.sqlite3")
    try:
        os.makedirs(os.path.dirname(cp), exist_ok=True)
        probe = cp + ".doctor_probe"
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        checks.append(("缓存目录", "PASS", os.path.dirname(cp)))
    except Exception as e:
        checks.append(("缓存目录", "WARN",
                       f"不可写（{type(e).__name__}）——持久缓存将静默停用，复跑会全量外呼"))
    # 配置键状态（只报状态不改行为；键值绝不回显）
    env_keys = [("OPENALEX_API_KEY", "OpenAlex（2026 起生产调用需 key，无 key 每日 100 credits）"),
                ("NCBI_API_KEY", "PubMed E-utilities（无 key 3 req/s 限速）"),
                ("S2_API_KEY", "Semantic Scholar（无 key 共享池限流）"),
                ("CITE_HOLMES_PROXY", "代理"), ("ALL_PROXY", "系统代理")]
    for env, desc in env_keys:
        v = os.environ.get(env)
        if v:
            checks.append(("配置键", "INFO", f"{env} 已设置（{desc}）"))
        else:
            checks.append(("配置键", "INFO", f"{env} 未设置——{desc}"))
    # 输出编码形态（Windows GBK 控制台历史故障面）
    enc = getattr(sys.stdout, "encoding", "") or ""
    checks.append(("输出编码", "PASS" if enc.lower().replace("-", "") == "utf8" else "INFO",
                   f"stdout={enc or '未知'}（非 UTF-8 控制台下特殊字符按 replace 降级显示）"))
    if net:
        print("── 注册库连通性探针（--net）──")
        for name, url in _DOCTOR_PROBES:
            t0 = time.time()
            status, detail = "FAIL", ""
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": f"cite-holmes/{VERSION}; +doctor"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    code = resp.code
                ms = (time.time() - t0) * 1000
                if code == 200:
                    status = "PASS" if ms <= 2000 else "WARN"
                    detail = f"HTTP 200 · {ms:.0f}ms" + ("" if ms <= 2000 else "（慢>2s）")
                else:
                    status, detail = "WARN", f"HTTP {code} · {ms:.0f}ms"
            except urllib.error.HTTPError as e:
                ms = (time.time() - t0) * 1000
                if e.code in (403, 429):
                    status, detail = "WARN", f"HTTP {e.code}（可达但限流/需 key）· {ms:.0f}ms"
                else:
                    status, detail = "WARN", f"HTTP {e.code} · {ms:.0f}ms"
            except Exception as e:
                detail = f"{type(e).__name__}（不可达/超时 {timeout}s）——该源核验将走降级路径"
            checks.append((f"探针·{name}", status, detail))
    n_fail = sum(1 for _, s, _ in checks if s == "FAIL")
    n_warn = sum(1 for _, s, _ in checks if s == "WARN")
    print("== cite-holmes doctor ==")
    for name, s, detail in checks:
        mark = {"PASS": "✅", "WARN": "⚠️ ", "INFO": "ℹ️ ", "FAIL": "❌"}[s]
        print(f"  {mark} [{s:4s}] {name}: {detail}")
    if n_fail:
        print(f"verdict: FAIL（{n_fail} 项 FAIL / {n_warn} 项 WARN）——先修复 FAIL 再跑批")
    elif n_warn:
        print(f"verdict: usable with caveats（{n_warn} 项 WARN）——可跑批，注意降级提示")
    else:
        print("verdict: all clear——环境就绪，可直接跑批")
    return 1 if n_fail else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="deep-research 引用机械验证器（五态判定）")
    ap.add_argument("--refs", help="引用清单路径：JSON 数组（research_refs.json）或 BibTeX（refs.bib，v1.9）")
    ap.add_argument("--discover", help='v4.5.0 文献发现：主题检索双源（PubMed+OpenAlex）找文献，'
                                       '结果带官方标识符交全栈核验——出生即核验（如 --discover "bronchiolitis diagnosis"）')
    ap.add_argument("--discover-limit", type=int, default=10,
                    help="文献发现每源条数上限（默认 10，封顶 25）")
    ap.add_argument("--discover-since", type=int, default=None,
                    help="文献发现出版年下限（如 --discover-since 2020 只收 2020 及以后）")
    ap.add_argument("--demo", action="store_true",
                    help="v4.5.0 零门槛体验：用内置样例清单（8 条含 3 处预埋伪造）跑完整判定流程")
    ap.add_argument("--claims", help="内联 JSON 引用数组（同 --refs 的 schema）")
    ap.add_argument("--out", default="verify_report.md", help="Markdown 报告输出路径")
    ap.add_argument("--json-out", help="JSON 报告输出路径（默认 <out>.json）")
    ap.add_argument("--offline", action="store_true", help="不联网，仅结构/字段检查")
    ap.add_argument("--strict", action="store_true", help="unreachable/invalid 计为失败（exit 1）")
    ap.add_argument("--timeout", type=float, default=10.0, help="单 URL 超时秒数（默认 10）")
    ap.add_argument("--interval", type=float, default=1.0, help="请求间隔秒数（默认 1.0）")
    ap.add_argument("--check-document", default="",
                    help="v4.4.0 单文件模式:仅给文档路径(含参考文献节)即一体化核验;"
                         "或配合 --refs 做文档级上下文核验:解析 in-text "
                         "引用标记([12]/[1-4]/(Author, Year)/doi.org 链接),绑定 --refs "
                         "核验结果并做锚词匹配(需与 --refs 同用)")
    ap.add_argument("--anchor-threshold", type=float, default=0.34,
                    help="上下文核验锚词率阈值(默认 0.34;低于=疑似错配引文,人工复核)")
    ap.add_argument("--preflight", action="store_true",
                    help="v3.7.0 注册库预检面板:核验前探测各官方源可达性(3s 超时),"
                         "弱网环境先看状态再跑批")
    ap.add_argument("--preset", choices=["submission"], default="",
                    help="v3.12 场景预设：submission=投稿前参考文献终检"
                         "（--strict 严格退出码 + --export gbt7714,bibtex,csv 组合，"
                         "判定语义不变，只打包常用旗标）")
    ap.add_argument("--grill", metavar="REPORT_JSON", default="",
                    help="v3.14 对抗审查：对已生成的 JSON 报告出「审稿人预演」问题单"
                         "（逐条最强挑战+清单级追问，纯模板零网络，不改变任何判定）")
    ap.add_argument("--explain", type=int, metavar="N", default=None,
                    help="v3.12 跑批后对第 N 条输出判定链人话解释"
                         "（判定语义/依据步骤/错误码/注记/完整度/建议动作）")
    ap.add_argument("--doctor", action="store_true",
                    help="v3.10 环境自检：零外呼体检（版本/缓存/配置/文件形态），"
                         "配合 --net 加测各学术注册库连通性与延迟；FAIL 存在时退出码 1")
    ap.add_argument("--net", action="store_true",
                    help="--doctor 配套：加测注册库连通性探针（单独使用无效果）")
    ap.add_argument("--cn", action="store_true",
                    help="CN 韧性预设(v3.6)：超时下限 25s；DOI.org 三试全败时回源 "
                         "api.crossref.org 同构 CSL(独立主机)；其余逻辑不变")
    ap.add_argument("--profile", choices=["general", "medical"], default="general",
                    help="信源预设：medical=医学期刊层域名扩展(Cochrane/CTS/NMPA/CDC/万方等)+社区层降级警示")
    ap.add_argument("--export", help="附加导出，逗号分隔：bibtex（仅verified，可直接进论文）/ "
                    "gbt7714（v3.6 GB/T 7714-2025 参考文献表,注册库元数据为准）/ "
                    "ris（v3.7 RIS,Zotero/EndNote 通用）/ "
                    "csv（全量审计台账）/ auditjson（v1.9 透明工作底稿：逐项检查明细）")
    ap.add_argument("--format", choices=["md", "html"], default="md",
                    help="报告格式：md（默认）或 html（自包含单文件，零外链，可直接分享/存档）")
    ap.add_argument("--easy", action="store_true",
                    help="傻瓜模式：自动识别医学引用启用医学预设，验证后自动导出 bibtex+csv，无需其他参数")
    ap.add_argument("--openalex-key", default="",
                    help="OpenAlex API key（2026-02 起生产调用需要；也可用环境变量 OPENALEX_API_KEY）")
    ap.add_argument("--judge-url", default="",
                    help="L4 外置裁判端点（OpenAI 兼容 /chat/completions,如 ollama/llama-server;"
                         "自备模型,cite-holmes 只出框架——零依赖不破）")
    ap.add_argument("--judge-model", default="qwen3.8-27b",
                    help="L4 裁判模型名（配合 --judge-url；URL 带 /v1=OpenAI 兼容,否则=ollama 原生 think:false+结构化输出）")
    ap.add_argument("--no-contexts", action="store_true",
                    help="关闭 L3 引文语境层（v3.0.0 默认开：verified 引文拉取 S2 引用语境/学界评价）")
    ap.add_argument("--ncbi-key", default="",
                    help="NCBI E-utilities API key（3→10 req/s 提速并行批验证；"
                         "也可用环境变量 NCBI_API_KEY）")
    ap.add_argument("--s2-key", default="",
                    help="Semantic Scholar API key（免钥为共享限速池；也可用环境变量 S2_API_KEY）")
    ap.add_argument("--nli-url", default="",
                    help="L2 NLI 第三票服务(nli_service.py;弃权式,分歧标人工复核不翻案)")
    ap.add_argument("--fast-judge-url", default="",
                    help="fast-judge 预筛服务(任何 OpenAI 兼容端点;小型分类器即可——仅对语义"
                         "待定且无官方文本可升级的条目做预筛,高置信 SUPPORTS 只加参考"
                         "note 永不判定;默认关闭)")
    ap.add_argument("--fast-judge-threshold", type=float, default=0.95,
                    help="fast-judge 预筛 note 触发阈值(默认 0.95=校准曲线选定:"
                         "SUPPORTS 精度 0.82/覆盖 0.32;模型过度自信,top 桶 0.97 置信"
                         "实际 acc 0.77——故产品姿态=note-only 永不判定;精度优先可调 0.99)")
    ap.add_argument("--retraction-cache", default="",
                    help="撤稿本地缓存 JSON 索引（Crossref GitLab dump 构建,63k+ DOI;"
                         "命中零网络,离线可用;未配置走 Crossref 在线查询）")
    ap.add_argument("--mailto", default="",
                    help="联系邮箱：进入 Crossref polite pool（限速更宽松），机构/CI 用户建议配置")
    ap.add_argument("--workers", type=int, default=4,
                    help="引用并行验证线程数（默认 4；1=串行；offline 模式自动串行）。"
                         "条与条独立，整批耗时约 ÷N；v1.10 新增")
    ap.add_argument("--no-cache", action="store_true",
                    help="关闭持久磁盘缓存（v1.12 默认开：TTL 内复跑直接复用稳定判定，零外呼）")
    ap.add_argument("--cache-ttl", type=float, default=168.0,
                    help="磁盘缓存有效期小时数（默认 168=7 天；撤稿状态等可变信息以 TTL 为界）")
    ap.add_argument("--cache-path", default="~/.cache/cite-holmes/cache.sqlite3",
                    help="磁盘缓存文件路径（默认 ~/.cache/cite-holmes/cache.sqlite3）")
    ap.add_argument("--refresh-cache", action="store_true",
                    help="绕过缓存读取强制重验（结果仍回写缓存）")
    ap.add_argument("--proxy", default="",
                    help="显式 HTTP(S) 代理地址（如 http://127.0.0.1:7890）；"
                          "不指定时自动遵循 HTTP_PROXY/HTTPS_PROXY 环境变量")
    args = ap.parse_args()
    if getattr(args, "preset", "") == "submission":  # v3.12 投稿终检预设:组合旗标不改判定语义
        args.strict = True
        args.export = args.export or "gbt7714,bibtex,csv"
        print(f"[preset] submission：--strict + --export {args.export} 已组合"
              "（投稿前一键终检；判定语义与默认模式完全一致。"
              "注意 --strict 语义含绕过磁盘缓存读——复跑为全量外呼）")
    if getattr(args, "grill", ""):
        gpath = os.path.expanduser(args.grill)
        if not os.path.isfile(gpath):
            print(f"❌ 报告文件不存在：{gpath}（--grill 需要一次真实核验产出的 JSON 报告）")
            return 2
        try:
            with open(gpath, encoding="utf-8") as f:
                doc = json.load(f)
        except (ValueError, UnicodeDecodeError) as e:
            print(f"❌ 不是有效的 JSON 报告：{gpath}（{type(e).__name__}）——"
                  "请先跑一次 --refs 核验生成报告")
            return 2
        if not (doc.get("results") or []):
            print(f"❌ {gpath} 内无 results 字段——请提供本工具生成的完整 JSON 报告")
            return 2
        items = grill_report(doc.get("results") or [])
        sc = doc.get("scorecard") or {}
        out = args.out if args.out != "verify_report.md" else gpath.rsplit(".", 1)[0] + "_grill.md"
        with open(out, "w", encoding="utf-8") as f:
            f.write(render_grill_md(items, sc))
        n_q = sum(len(x["questions"]) for x in items)
        print(f"[grill] 对抗审查问题单：{len(items)} 条引用 · {n_q} 个挑战问题 → {out}")
        print("[grill] 判定不变（自查工具）；逐条作答后再投稿。")
        return 0
    if getattr(args, "doctor", False):
        return run_doctor(net=getattr(args, "net", False),
                          timeout=min(args.timeout, 8.0),
                          cache_path=args.cache_path)
    medical = args.profile == "medical"
    _net_reset()  # 断路器+全局网络降级状态按批次重置（v1.6/v1.10）
    if args.proxy.strip():
        proxy = args.proxy.strip()
        if "://" not in proxy:
            proxy = "http://" + proxy
        urllib.request.install_opener(urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})))
        print(f"[proxy] 显式代理已启用：{proxy}")
    if getattr(args, "cn", False) and args.timeout < 25:
        args.timeout = 25.0  # --cn 超时下限(v3.6):跨国 RTT 抖动下不误判 unreachable
    if getattr(args, "preflight", False):
        # v3.7.0 注册库预检面板:3s 探测,弱网先看状态再跑批(CN 韧性可观测化)
        import socket as _sk
        print("== 注册库预检(3s 超时) ==")
        for name, host, port in (("DOI.org", "doi.org", 443),
                                 ("PubMed E-utilities", "eutils.ncbi.nlm.nih.gov", 443),
                                 ("arXiv", "export.arxiv.org", 443),
                                 ("Crossref", "api.crossref.org", 443),
                                 ("Semantic Scholar", "api.semanticscholar.org", 443),
                                 ("Wayback", "web.archive.org", 443)):
            t0 = time.time()
            try:
                _sk.create_connection((host, port), timeout=3)
                st = f"✓ 可达 ({(time.time()-t0)*1000:.0f}ms)"
            except Exception as e:
                st = f"✗ 不可达({type(e).__name__})"
            print(f"  {name:20s} {st}")
    args.cache = not args.no_cache
    args.cache_path = os.path.expanduser(args.cache_path)
    _OPTS.update({
        "openalex_key": args.openalex_key or os.environ.get("OPENALEX_API_KEY", ""),
        "s2_key": args.s2_key or os.environ.get("S2_API_KEY", ""),
        "ncbi_key": args.ncbi_key or os.environ.get("NCBI_API_KEY", ""),
        "retraction_cache": args.retraction_cache.strip(),
        "nli_url": args.nli_url.strip(),
        "fast_judge_url": args.fast_judge_url.strip(),
        "fast_judge_threshold": args.fast_judge_threshold,
        "mailto": args.mailto.strip(),
        "contexts": not args.no_contexts,
        "cn_mode": bool(getattr(args, "cn", False)),
        "judge_url": args.judge_url.strip(),
        "judge_model": args.judge_model.strip(),
    })

    refs = None
    if getattr(args, "demo", False) and not args.refs and not args.claims:
        _demo = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "..", "examples", "demo_refs.json")
        with open(_demo, encoding="utf-8") as f:
            refs = json.load(f)
        print(f"[demo] 内置样例清单 {len(refs)} 条（含 3 处预埋伪造）——体验五态判定全流程")
    if (getattr(args, "discover", "") and not args.refs
            and not args.claims and not refs):
        if args.offline:
            print("❌ 文献发现需要联网检索——--offline 模式不适用", file=sys.stderr)
            return 2
        _drefs, _dnotes = discover_refs(args.discover, args.discover_limit,
                                        args.timeout,
                                        since=getattr(args, "discover_since", None))
        for _n in _dnotes:
            print(f"[discover] {_n}")
        if _drefs:
            refs = _drefs
            print(f"[discover] 双源命中 {len(refs)} 条（去重后）——进入核验栈，出生即核验")
        else:
            print("❌ 文献发现双源零命中——请换检索词或检查网络", file=sys.stderr)
            return 2
    if (getattr(args, "check_document", "") and not refs and not args.refs
            and not args.claims):
        # v4.4.0 单文件一体化：--check-document 独用=从文档自身「参考文献」
        # 节提取清单再全量核验——dogfood 实录同一文件传两遍是最大使用摩擦
        # （审计 P2：not refs 守卫——否则无条件覆盖 demo/discover 已装载清单）
        try:
            _doctext = open(args.check_document, encoding="utf-8",
                            errors="replace").read()
        except (OSError, ValueError) as e:
            print(f"❌ 读取文档失败：{e}", file=sys.stderr)
            return 2
        refs = parse_markdown_refs(_doctext)
        if refs:
            print(f"[one-file] 自文档参考文献节提取 {len(refs)} 条（GB/T/Vancouver）")
    if not args.refs and not args.claims and not refs:
        print("❌ 需要 --refs 或 --claims 之一；--check-document 指向含「参考文献」节"
              "的文档（v4.4.0 单文件模式）；--discover 主题检索（v4.5.0 文献发现）；"
              "或 --demo 零门槛体验", file=sys.stderr)
        return 2
    try:
        if args.claims:
            refs = json.loads(args.claims)
        elif args.refs:
            refs = load_refs_file(args.refs)  # v1.9：JSON 或 BibTeX 自动识别
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"❌ 读取引用清单失败：{e}", file=sys.stderr)
        print("   支持 JSON 数组（research_refs.json）或 BibTeX 文件（v1.9 起 --refs refs.bib）",
              file=sys.stderr)
        return 2
    if not isinstance(refs, list) or not refs:
        print("❌ 引用清单须为非空数组（JSON 或 BibTeX）", file=sys.stderr)
        return 2

    if args.easy:
        # 傻瓜模式：有 PMID/PubMed 信号 → 直接启用医学预设；仅医学期刊域命中
        # （如万方）需 ≥2 条才触发——v1.8 修复：单条万方来源的技术类清单被误判成医学清单
        hints = False
        med_hits = 0
        for r in refs:
            if not isinstance(r, dict):
                continue
            u = str(r.get("url") or "")
            if str(r.get("pmid") or "").strip() or "pubmed" in u.lower():
                hints = True
                break
            # v4.2.0：中文医学注册库升为无条件 journal 层后，「medical 才升层」
            # 信号对它们失效——改用显式注册库清单计数
            if re.search(r"(wanfangdata|cnki|yiigle|cqvip)\.", u.lower()):
                med_hits += 1
                continue
            try:
                if classify_tier(u, True) == "journal" and classify_tier(u, False) == "blog":
                    med_hits += 1
            except Exception:
                pass
        if not hints and med_hits >= 2:
            hints = True
        if hints:
            args.profile = "medical"
        if not args.export:
            args.export = "bibtex,csv"
        medical = args.profile == "medical"
        print(f"[easy] 傻瓜模式：医学预设={'开' if medical else '关'}；自动导出 {args.export}")

    def _safe_verify_one(i, ref):
        # 单条坏数据（非对象/标量/处理异常）降级为该条 invalid，绝不拖垮整批
        if not isinstance(ref, dict):
            return {"index": i, "title": str(ref)[:48], "url": "", "doi": "", "pmid": "",
                    "arxiv": "", "source": "", "year": None, "tier": "-", "semantic": "",
                    "verdict": "invalid",
                    "http_status": None, "note": "条目不是对象", "needs_human_check": False,
                    "checks": {}}
        # v1.12 持久磁盘缓存：TTL 内复用稳定判定（复跑零外呼）；--strict 绕过读保 CI
        # 诚实；--refresh-cache 绕过读但仍写；offline 不读不写（offline 判定不可入库）。
        # 仅带标识符(doi/url/pmid/arxiv)的引用入缓存——与批内缓存同口径；
        # 纯标题引用不走磁盘缓存（其判定多为结构性 invalid，无外呼可省）
        dc_key = (_dc_key(ref, args.profile)
                  if (args.cache and not args.offline and _cache_key(ref)) else "")
        if dc_key and not args.strict and not args.refresh_cache:
            hit = _dc_get(_dc_path(args), dc_key, args.cache_ttl)
            if hit is not None:
                r, age_h = hit
                r = dict(r)
                r["index"] = i
                r["note"] = ((r.get("note") + "；") if r.get("note") else "") +                     f"磁盘缓存命中（{age_h:.0f}h 前验证；--refresh-cache 强制重验）"
                return r
        try:
            r = verify_one(ref, i, args.offline, args.timeout, medical)
        except Exception as e:
            return {"index": i, "title": str(ref.get("title") or "")[:48] or "(无标题)",
                    "url": "", "doi": "", "pmid": "", "arxiv": "", "source": "", "year": None,
                    "tier": "-", "semantic": "", "verdict": "invalid",
                    "http_status": None, "note": f"条目处理异常（{type(e).__name__}）",
                    "needs_human_check": True, "checks": {}}
        if dc_key and r.get("verdict") in _DC_CACHEABLE:
            _dc_put(_dc_path(args), dc_key, r)
        return r

    results = [None] * len(refs)
    workers = max(1, int(args.workers or 1))
    if args.offline or workers <= 1 or len(refs) <= 1:
        # 串行路径（offline 模式 / --workers 1 / 单条）：保留逐条 interval 控频
        for i, ref in enumerate(refs, 1):
            r = _safe_verify_one(i, ref)
            results[i - 1] = r
            print(f"[{i}/{len(refs)}] {VERDICT_ZH[r['verdict']]} {r['title'][:40]}")
            if not args.offline and i < len(refs) and args.interval > 0:
                time.sleep(args.interval)
    else:
        # v1.10 引用级并行验证：条与条相互独立（共享状态仅断路器/限速器，均已加锁），
        # 整批耗时约 ÷workers——跨国数据库验证慢的机制层缓解。进度行按完成顺序
        # 打印（带真实序号），最终结果按 index 有序回填，报告/JSON 顺序与串行一致。
        # 并行下不做逐条 interval（并发本身就是节流；单主机礼貌由断路器+限速锁保证）。

        def _task(i, ref):
            # 双保险：任何意外异常都降级为该条 invalid，绝不拖垮整批
            try:
                return _safe_verify_one(i, ref)
            except Exception as e:
                return {"index": i,
                        "title": (str(ref.get("title") if isinstance(ref, dict) else ref)[:48]
                                  or "(无标题)"),
                        "url": "", "doi": "", "pmid": "", "arxiv": "", "source": "",
                        "year": None, "tier": "-", "semantic": "", "verdict": "invalid",
                        "http_status": None, "note": f"条目处理异常（{type(e).__name__}）",
                        "needs_human_check": True, "checks": {}}

        with ThreadPoolExecutor(max_workers=min(workers, len(refs))) as ex:
            # v1.10 批内缓存（领导者-跟随者）：同 DOI/URL/PMID/arXiv 只验证一次。
            # 并行下两条同键引用会同时起飞，「先查缓存后存储」永远轮空——④c 真网
            # 验收抓到，改为派发前去重：首个入键者为领导者，其余为跟随者，待领导者
            # 完成后复制判定（跟随者零网络调用）。
            futs = {}
            leader_of, followers = {}, {}
            for i, ref in enumerate(refs, 1):
                key = _cache_key(ref) if isinstance(ref, dict) else ()
                if key and key in leader_of:
                    followers.setdefault(leader_of[key], []).append(i)
                    continue
                if key:
                    leader_of[key] = i
                futs[i] = ex.submit(_task, i, ref)
            for fut in as_completed(futs.values()):
                r = fut.result()
                results[r["index"] - 1] = r
                print(f"[{r['index']}/{len(refs)}] {VERDICT_ZH[r['verdict']]} {r['title'][:40]}")
            for lead_idx in sorted(followers):
                lead = results[lead_idx - 1]
                for j in followers[lead_idx]:
                    r = dict(lead)
                    r["checks"] = dict(lead.get("checks") or {})
                    r["index"] = j
                    # v1.11 语义底稿按各自引用重建（缓存只复用机械判定——同
                    # DOI/URL 的两条引用可以引向不同论断，语义判定不得共享）
                    r["semantic_audit"] = build_semantic_audit(refs[j - 1])
                    r["note"] = ((lead.get("note") + "；") if lead.get("note") else "") + \
                        "同 DOI/URL 本批已验证，复用缓存判定"
                    results[j - 1] = r
                    print(f"[{j}/{len(refs)}] {VERDICT_ZH[r['verdict']]} {r['title'][:40]}")
        if _NET_STATE["degraded"]:
            print("⚠️ 全局网络降级：本批次多个外部主机连续传输失败（出海受限特征），"
                  "部分外呼已快速跳过——建议配置代理/更换网络后重跑以获得更完整结果")

    mark_duplicates(results)
    _n_clone = detect_clone_pairs(results)  # v3.10 克隆引用搭档检测（只注记不改判定）
    if _n_clone:
        print(f"[clone] 克隆引用对 {_n_clone} 组（同题不同 DOI / 同 DOI 不同题）——详见报告克隆引用对区块")
    # v3.11 预印本→正式版提示（注记级;offline 显式零网络,不依赖跨函数不变量）
    _n_preprint = 0 if args.offline else annotate_preprint_upgrades(results, args.timeout)
    if _n_preprint:
        print(f"[preprint] {_n_preprint} 条预印本已登记正式发表——建议引用正式版（详见各条注记）")
    annotate_completeness(results)  # v3.11 逐条完整度（JSON 字段）
    apply_semantic_cap(results)  # v1.11：语义否定判定封顶（在去重后统一执行）
    for _r in results:  # v3.9.0 结构化错误码(errorHandling):五态之上的机器可读细分
        try:
            _r["error_codes"] = derive_error_codes(_r)
        except Exception:
            _r["error_codes"] = []
    apply_l4_cascade(results, args.timeout)  # v3.1：L4 证据升级级联（--judge-url 时激活；零配置零变化）
    apply_fast_judge(results, args.timeout)  # v3.5.0：fast-judge 预筛（--fast-judge-url 时激活；零配置零变化）
    scorecard = compute_scorecard(results)
    cd = None
    if getattr(args, "check_document", ""):
        cd = check_document(open(args.check_document, encoding="utf-8",
                                 errors="replace").read(),
                            results, float(args.anchor_threshold))
    content = (render_html(results, args.offline, args.profile, context_check=cd)
               if args.format == "html"
               else render_md(results, args.offline, args.profile,
                              context_check=cd))
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(content)
    json_path = args.json_out or (args.out.rsplit(".", 1)[0] + ".json")
    _json_doc = {"version": VERSION, "profile": args.profile, "offline": args.offline,
                 "bluf": render_bluf_dict(results, scorecard),  # v3.2.0 规范 L1:对象
                 "bluf_yaml": render_bluf(results, scorecard),  # 兼容:YAML 文本
                 "scorecard": scorecard, "results": results,
                 "bibliography_profile": profile_bibliography(results)}  # v3.11 清单画像
    if cd is not None:
        _json_doc["context_check"] = cd
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(_json_doc, f, ensure_ascii=False, indent=2)
    if cd is not None:
        print(f"\n== 上下文核验({args.check_document}) ==")
        print(f"  in-text 引用 {cd['n_citations']} 处:未绑定 {cd['n_unbound']},"
              f"锚词不足 {cd['n_low_anchor']}(阈值 {cd['anchor_threshold']})")
        if cd.get("n_listed"):
            print(f"  引用覆盖 {cd['coverage']:.0%}:清单 {cd['n_listed']} 条中 "
                  f"{cd['n_uncited']} 条未在正文引用"
                  f"{(':' + '、'.join(str(i) for i in (cd.get('uncited_refs') or [])[:10]) + ('…' if len(cd.get('uncited_refs') or []) > 10 else '')) if cd.get('uncited_refs') else ''}"
                  "（漏引或冗列建议，非真伪判定）")
        for c in cd["citations"][:12]:
            flag = ("未绑定" if not c["bound"] else
                    f"锚词率 {c['anchor_rate']}{'⚠' if c['anchor'] == 'low' else ''}")
            print(f"  {c['marker']:22s} → 条目{c['ref_index'] or '-'} {flag}")
        if cd["n_citations"] > 12:
            print(f"  …其余 {cd['n_citations'] - 12} 处见 JSON")
    print(f"CiteScore: {scorecard['score']}/100 ({scorecard['grade']} 级，{scorecard['total']} 条)")

    if getattr(args, "explain", None) is not None:  # v3.12 单条判定链人话解释
        target = next((r for r in results if r.get("index") == args.explain), None)
        print()
        print(explain_ref(target) if target else
              f"第 {args.explain} 条不存在——有效范围 1-{len(results)}")

    if args.export:
        base = args.out.rsplit(".", 1)[0] if "." in args.out else args.out
        for fmt in [x.strip().lower() for x in args.export.split(",") if x.strip()]:
            if fmt == "bibtex":
                p = base + ".bib"
                n = export_bibtex(results, p)
                print(f"导出：{p}（{n} 条 verified，可直接进论文）")
            elif fmt == "ris":
                p = base + ".ris"
                n = export_ris(results, p)
                print(f"导出：{p}（{n} 条，RIS/Zotero/EndNote 通用）")
            elif fmt in ("gbt7714", "gb"):
                p = base + "_GB-T7714.txt"
                n = export_gbt7714(results, p)
                print(f"导出：{p}（{n} 条 verified/元数据一致，GB/T 7714-2025 参考文献表，"
                      "元数据以注册库登记为准）")
            elif fmt == "csv":
                p = base + ".csv"
                export_csv(results, p)
                print(f"导出：{p}（{len(results)} 条全量审计台账）")
            elif fmt == "auditjson":
                p = base + ".audit.json"
                export_audit(results, p, args.offline, args.profile)
                print(f"导出：{p}（透明工作底稿：逐项检查明细）")
            else:
                print(f"⚠️ 未知导出格式 {fmt}（支持 bibtex,gbt7714,ris,csv,auditjson）", file=sys.stderr)

    bad = [r for r in results if r["verdict"] in ("unreachable", "invalid")]
    print(f"\n报告：{args.out}\nJSON：{json_path}")
    if bad:
        print(f"⚠️ {len(bad)} 条 unreachable/invalid" + ("（strict 模式 → exit 1）" if args.strict else ""))
    return 1 if (args.strict and bad) else 0


def main_with_args(argv: list) -> int:
    """程序化调用入口（测试/其他脚本用）。argv 不含脚本名。"""
    old = sys.argv
    sys.argv = [sys.argv[0]] + list(argv)
    try:
        return main()
    finally:
        sys.argv = old


if __name__ == "__main__":
    sys.exit(main())
