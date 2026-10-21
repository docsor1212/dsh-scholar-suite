> **何时读我**：要调词表、固化误报守卫、或改评分标定之前。
> **最短路径**：误报固化用 learn_guards.py（不要手改 patterns_*.json）；词表与标定文件位置在下表。
> **回 [INDEX](INDEX.md)**

## 自定义

- `scripts/patterns_zh.json` / `patterns_en.json`：词表（含改写建议）、正则信号、
  术语保护（正当学术用法不误报，如 mutational landscape、pivotal trial、
  序列对齐、沉淀反应）、自动修复清单。
- **用户自学守卫**存放在 `scripts/user_guards.json`（由 `learn_guards.py`
  管理，不要手改；`list` 查看、`remove` 删除）。误报词固化请写这里而不是改
  `patterns_*.json`——词表文件升级会被覆盖，守卫文件不会。
- 评分标定系数在 `scripts/hxt_core.py`（`_LANG_K`）；开发仓库 `tests/` 四语料
  （发布包不含）记录了预期分离度。
