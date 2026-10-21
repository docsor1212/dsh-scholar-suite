# cite-holmes-mcp

**Mechanical citation verification as an MCP server** — feed it the references an
agent is about to cite, get back per-reference verdicts (`verified / partial /
unreachable / invalid`) against official registries (DOI.org, PubMed
E-utilities, arXiv API, Crossref/Retraction Watch, Wayback). Zero API keys
required, zero telemetry, local-first.

Three MCP primitives:

| Primitive | Name | What it does |
|---|---|---|
| tool | `verify_references` | Verify a batch of references (≤50); returns CiteScore 0–100 + per-item verdicts with evidence chain |
| tool | `check_document` | Context-level check: parse in-text markers ([12]/[1-4]/(Author, Year)/doi.org links), bind to the reference list, flag low anchor-word overlap as possible mis-citations |
| tool | `explain_verdict` | Plain-language explanation of one verdict (evidence steps + suggested action); zero network |
| resource | `cite-holmes://capability-matrix` | What the mechanical layer catches vs. what stays with the semantic layer |
| resource | `cite-holmes://changelog` | Version history |
| prompt | `fact_check_workflow` | Three-step research-then-verify workflow for agents |

## Install (three channels)

```bash
# 1) uvx from GitHub (recommended — always current)
uvx --from "git+https://github.com/docsor1212/cite-holmes#subdirectory=mcp" cite-holmes-mcp

# 2) uvx from a local checkout
git clone https://github.com/docsor1212/cite-holmes
uvx --from ./cite-holmes/mcp cite-holmes-mcp --help

# 3) pip install (module + console script)
pip install "git+https://github.com/docsor1212/cite-holmes#subdirectory=mcp"
cite-holmes-mcp --help
```

> This is a Python package (uv/pip ecosystem). There is no npm package — the
> uvx/git channel above is the canonical install for all MCP clients.

## Client configuration

**Claude Code**

```json
{
  "mcpServers": {
    "cite-holmes": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/docsor1212/cite-holmes#subdirectory=mcp",
               "cite-holmes-mcp"]
    }
  }
}
```

**Codex / any stdio MCP client**

```json
{
  "mcpServers": {
    "cite-holmes": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/docsor1212/cite-holmes#subdirectory=mcp",
               "cite-holmes-mcp", "--transport", "stdio"]
    }
  }
}
```

**Cursor** (`~/.cursor/mcp.json`, same shape)

```json
{
  "mcpServers": {
    "cite-holmes": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/docsor1212/cite-holmes#subdirectory=mcp",
               "cite-holmes-mcp"]
    }
  }
}
```

HTTP mode (local): `cite-holmes-mcp --transport http --port 8760`.

## Bounds & behavior

- Batch ≤ 50 references per `verify_references` call (larger batches get a
  clear error — split them).
- Long output fields are clipped (800 chars + truncation marker) so MCP
  messages stay bounded; structure is preserved.
- Per-reference network timeout defaults to 15 s (configurable per call).
- Optional API keys via env: `OPENALEX_API_KEY` / `S2_API_KEY` /
  `NCBI_API_KEY` (only attach to the caller's own requests).

## Layout

```
mcp/
├── server.py          # FastMCP three-primitive server (engine-agnostic impl)
├── verify_refs.py     # embedded engine copy — synced from ../scripts/ by
│                      #   sync_engine.sh (sha-gated; never hand-edit here)
├── sync_engine.sh     # trunk↔mcp engine consistency gate (run before publish)
├── pyproject.toml
├── README.md
└── tests/
    ├── test_bounds.py        # batch/clip/bad-input unit tests
    └── e2e_transcript.md     # full MCP client session evidence
```

License: MIT. Author: SorSor. Repo: https://github.com/docsor1212/cite-holmes
