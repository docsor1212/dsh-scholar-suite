# paper-rewriter

[![GitHub Stars](https://img.shields.io/github/stars/docsor1212/paper-rewriter?style=social&label=Star)](https://github.com/docsor1212/paper-rewriter)

Bilingual (CN/EN) style naturalization for academic & medical writing: find stiff,
templated or machine-flavored patterns, clean mechanical debris, revise for clarity
and natural register — with integrity guardrails on every step.

Deterministic cleanup (model artifacts, punctuation, filler), style-pattern
self-check reports (local heuristic, detection only), sentence-level rewrite
planning, a deterministic deep-polish mode, and a whole-document integrity guard
(numbers, DOIs, PMIDs, terminology must survive untouched). 100% local, zero
upload, Python standard library only.

## Install / Quick Start

Install via your skill manager (skills CLI / ClawHub / SkillHub), or clone this
repository and run the scripts directly with Python 3 (no dependencies):

```bash
# one command: self-check -> cleanup -> revision brief -> integrity guard
python scripts/pipeline.py draft.txt -o out.txt --terms terms.txt

# or step by step
python scripts/detect.py draft.txt            # style-pattern self-check
python scripts/transform.py draft.txt -o step1.txt
python scripts/verify.py draft.txt step1.txt  # integrity guard (exit 0/1/2)

# full guide, boundaries and agent invocation protocol
cat SKILL.md
```

**China mirror (ModelScope 魔搭)**: <https://modelscope.cn/skills/Docsor/paper-rewriter> — if you find this skill useful, a like there helps others find it.

## Integrity guardrails

Permitted: polishing your own drafts; aligning AI-assisted text with your voice
where disclosure is allowed or required. Not permitted: misrepresenting
authorship, concealing required AI disclosure, or defeating integrity review —
the toolkit refuses that framing. See `references/compliance.md`.
