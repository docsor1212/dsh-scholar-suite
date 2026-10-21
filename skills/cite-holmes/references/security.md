# Security & Behavior Declaration

> SKILL.md 保留三行摘要，完整声明在此。承诺可验证：全部行为可在单次运行中
> 用 `strace`/抓包复核。

## 运行形态

- 单次 CLI：启动 → 核验 → 写报告 → 退出。无守护进程、无后台任务、运行时不
  下载或安装任何东西（纯标准库）。
- 无 OS 集成：无子进程、无系统服务、无权限变更；文件访问仅限你传入的输入/
  输出路径、本地缓存（`~/.cache/cite-holmes/`）与报告输出。

## 网络边界（始终 HTTPS，仅限官方学术注册库）

`doi.org` · `api.crossref.org` · `eutils.ncbi.nlm.nih.gov` ·
`export.arxiv.org` / `arxiv.org` · `archive.org` · `api.openalex.org` ·
`api.semanticscholar.org` · `pubmed.ncbi.nlm.nih.gov`

不访问任何其他主机；零遥测、零分析、零数据收集。唯一外呼 payload 是你要求
核验的标识符与标题。

## 密钥与数据

- 可选环境变量 `OPENALEX_API_KEY` / `S2_API_KEY` / `NCBI_API_KEY` 只用于向
  对应官方 API 认证你自己的请求，绝不发往其他任何地方，绝不回显（`--doctor`
  只报「已设置/未设置」）。
- 引用清单与报告全部留在本机；持久缓存只存判定与注册库元数据摘要
  （`--no-cache` 可关闭，`--cache-path` 可改位置）。
