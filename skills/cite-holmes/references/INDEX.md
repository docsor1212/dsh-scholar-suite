# references/ 索引（v3.8.0 新增）

| 文件 | 用途 | 何时读 |
|---|---|---|
| faq.md | 高频问题解答（网络/PMID/导出/API key/fast-judge/GB·T 导出/--cn/上下文核验） | 遇到具体疑问时 |
| anti-patterns.md | 反模式统一清单（误用方式集中收录，v3.8.0 从 README/SKILL 收拢） | 上手前通读一遍 |
| medical-mode.md | 医学证据模式详解（信源金字塔/CEBM 分级/监管信源） | 使用 --profile medical 前 |
| verification-details.md | 五态判定完整阈值规则与检查明细 | 需要理解判定依据时 |
| search-strategies.md | 中英双语检索策略矩阵 | 定制检索流程时 |
| skillhub-mcp.md（如存在） | MCP 集成参考 | 配置 MCP 前 |

> 主文档：SKILL.md（技能定义）/ README.md（用户文档）。本目录文件按需加载，
> 不进入主执行流。

## 按任务 30 秒路由（v3.12）

| 你要做什么 | 直接去 | 一行起步 |
|---|---|---|
| 快速核验一份引用清单 | 本页即可 | `python scripts/verify_refs.py --refs refs.json --out r.md` |
| 投稿前最终把关 | faq.md「投稿前终检」 | `--preset submission` |
| 看懂某条为什么这个判定 | verification-details.md + faq.md「--explain」 | `--explain 3` |
| 医学/临床问题 | medical-mode.md | `--profile medical --easy` |
| 写检索式/选信源 | search-strategies.md | 抄信源金字塔前三行 |
| 正文引用与清单对不上 | faq.md「check-document」 | `--check-document paper.md` |
| 出 GB·T 7714 / BibTeX 表 | faq.md「导出」 | `--export gbt7714,bibtex` |
| 弱网/国内网络 | faq.md「国内网络」 | `--cn` 或 `--proxy` |
| 遇到疑似误用 | anti-patterns.md | 通读一遍（每条带替代方案） |
| 统一用词/报告语言对齐 | GLOSSARY.md | 正词表（五态/信号/错误码），带 Avoid 列表 |
| 安全与行为承诺 | security.md | 单次运行/域名清单/零遥测/密钥边界 |
| 这事为什么不 做 | out-of-scope.md | 非目标档案，每条带理由 |
