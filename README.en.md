# dsh-scholar-suite

DeepSeek Harness native plugin bundling the 8 free academic skills we publish on SkillHub — one install, the whole toolkit.

## Install

```bash
dsh plugin --profile web add github:docsor1212/dsh-scholar-suite
```

Use `--profile headless` for headless mode.

## Bundled skills (8)

| Skill | Version | What it does |
|---|---|---|
| academic-figures | 5.6.1 | Academic figures, mechanically validated, designed from real data |
| humanize-ai-text | 4.2.0 | Strip AI-flavor from text while preserving meaning |
| paper-polisher | 6.2.0 | Paper polishing with side-by-side diff reports |
| pubmed-verifier | 5.4.0 | PubMed citation verification (DOI/PMID) |
| doc-holmes | 3.0.1 | Chinese medical book-citation verification |
| paper-rewriter | 4.2.0 | Paper rewriting (structure & expression) |
| cite-holmes | 4.6.0 | Reference verification incl. [EB/OL] URL evidence |
| cn-med-oa | 2.4.1 | Chinese medical WeChat-official-account writing |

Versions track the latest published on SkillHub (reconciled at build time, see `skills/manifest.json`).

## Usage

- **Just ask**: skills are registered wholesale — "make this paragraph sound human", "verify the citations in this paper";
- **Slash commands**: each skill has a method card (`/cite-holmes`, `/paper-polisher`, …); `/suite-status` lists all.

## Security declaration (for pre-install review)

- **Plugin itself**: zero telemetry, no lifecycle scripts, no credential access;
- **Bundled skills' network behavior**: academic-figures / humanize-ai-text / paper-rewriter run fully local; pubmed-verifier / cite-holmes / doc-holmes may query NCBI E-utilities and DOI resolution services; paper-polisher may use optional external layout services; cn-med-oa talks to the WeChat official-account platform — all triggered only by the corresponding skill's function, details in each SKILL.md;
- **Disk writes**: current working directory only (reports / verification artifacts).

## Update

Rebuilt and re-released whenever member skills update (build fails unless each member matches its SkillHub latestVersion). Reinstall to update.

## Upstream

Independent SkillHub listings linked above; the frontend-aesthetics engine ships separately as [dsh-aesthete-agent](https://github.com/docsor1212/dsh-aesthete-agent).

## License

MIT
