# dsh-scholar-suite

SkillHub 学术工具链 8 技能的 DeepSeek Harness 捆绑套件——一次安装，DeepSeek Harness 里直接用上我们在 SkillHub 上架的全部免费学术技能。

## 安装

```bash
dsh plugin --profile web add github:docsor1212/dsh-scholar-suite
```

无头模式把 `--profile web` 换成 `--profile headless`。

## 捆绑技能(8 个)

| 技能 | 版本 | 作用 | SkillHub |
|---|---|---|---|
| academic-figures | 5.6.1 | 学术图表:GLM 黄蓝双斜线风格,按真数据设计,VL 审核 | [链接](https://skillhub.cn/skills/academic-figures) |
| humanize-ai-text | 4.2.0 | 去 AI 味改写:文本层特征清洗,保留原意与密度 | [链接](https://skillhub.cn/skills/humanize-ai-text) |
| paper-polisher | 6.2.0 | 论文润色:语域/混写预警/对照可视化双栏报告 | [链接](https://skillhub.cn/skills/paper-polisher-pro) |
| pubmed-verifier | 5.4.0 | PubMed 引文核验:DOI/PMID 逐条对账 | [链接](https://skillhub.cn/skills/pubmed-verifier) |
| doc-holmes | 3.0.1 | 著作医生:中文医学著作引用形态核验 | [链接](https://skillhub.cn/skills/doc-holmes) |
| paper-rewriter | 4.2.0 | 论文改写:结构与表述重塑 | [链接](https://skillhub.cn/skills/paper-rewriter) |
| cite-holmes | 4.6.0 | 引文核验:中文著录完整版,[EB/OL] 类 URL 自动取证 | [链接](https://skillhub.cn/skills/cite-holmes) |
| cn-med-oa | 2.4.1 | 中文医学公众号:文章结构与发布流程 | [链接](https://skillhub.cn/skills/cn-med-oa) |

版本 = SkillHub 上架最新版(构建时逐技能对账,见 `skills/manifest.json`)。

## 用法

- **直接说需求**:技能已整包注册,模型按描述自动路由——"帮我把这段改得不像 AI 写的""核验这篇论文的引文";
- **斜杠命令**:每技能一条方法卡,如 `/cite-holmes 这篇的引文帮我过一遍`;`/suite-status` 看全部技能与版本。

## 安全声明(供安装前审查)

- **插件本体**:零联网、零遥测、无安装期脚本(package.json 无 lifecycle scripts)、不读凭据;
- **捆绑技能的联网行为(如实声明)**:
  - 纯本地运行:academic-figures、humanize-ai-text、paper-rewriter;
  - 按功能会访问外部服务:pubmed-verifier / cite-holmes / doc-holmes(NCBI E-utilities、期刊与 DOI 解析服务)、paper-polisher(对照报告生成,可选外部排版服务)、cn-med-oa(公众号平台接口)——是否联网由对应技能的功能触发,细则见各自 SKILL.md;
- **写盘范围**:仅当前工作目录(报告/核验产物);
- **子进程**:技能脚本按各自文档调用本机 Python 3.8+(标准库优先,个别可选依赖见技能文档)。

## 更新

技能更新后,本套件随版本发布重新打包(构建时逐技能与 SkillHub latestVersion 对账,不一致即构建失败)。重装即更新:

```bash
dsh plugin --profile web add github:docsor1212/dsh-scholar-suite
```

## 上游

- 各技能的独立上架页见上表(SkillHub);aesthete-agent(前端美学)另有独立插件 [dsh-aesthete-agent](https://github.com/docsor1212/dsh-aesthete-agent)。

## License

MIT(各捆绑技能许可见其目录内声明)
