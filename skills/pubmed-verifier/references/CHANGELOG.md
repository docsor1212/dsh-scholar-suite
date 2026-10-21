> **何时读我**：想知道某版本改了什么、或对照旧版行为时。
> **最短路径**：SKILL.md 只保留最近三版摘要；完整 20 版历史在本文件逐字保留。
> **回 INDEX**：[INDEX.md](INDEX.md)

# pubmed-verifier — full release history

Complete version history. The SKILL.md "Recent releases" section keeps the
last three; everything older lives here verbatim.

## v2.2.0 — network hardening

| Feature | Flag | Effect |
|---------|------|--------|
| NCBI API key | `--ncbi-api-key` / env `NCBI_API_KEY` | Rate ceiling 3→10 req/s, batch interval 0.4s→0.12s (~3x faster) |
| Europe PMC fallback | `--meta-source auto\|ncbi\|europepmc` | NCBI batch failure automatically retries via Europe PMC (free, no key); per-entry origin in JSON (`meta_source`) |
| Crossref polite pool | `--mailto` / env `PUBMED_VERIFIER_MAILTO` | `?mailto=` on Crossref + tool/email params on NCBI — more generous limits |
| Retry-After backoff | automatic | 429 responses honored (clamped 1–5 s) instead of failing |
| UA rotation | automatic | 403/406 retried with a browser User-Agent |
| Host circuit breaker | automatic | After 2 call-level transport failures a host is skipped with an actionable message; success resets; HTTP errors never trip it |
| Honest unknown | automatic | Network failures report as ❓ unknown + exit code 2, never as "PMID not found", and are never cached |

**Exit codes:** `0` clean · `1` problems found (invalid / mismatch / retracted /
DOI-splice, incl. arXiv claimed-DOI pairing mismatches) · `2` could not verify
(data sources unreachable) — automation can tell "all good" from "no answer".

## v2.3.0 — retraction detection

With `--verify-doi`, each cited DOI is also checked against Crossref's
withdrawal records (`updated-by`). A paper Crossref lists as RETRACTED is:

- flagged in JSON (`retracted: true` + `retraction_note`) and in reports,
- **capped at 🔶 partial** even when every metadata field matches — citing a
  retracted paper is never "correct"; the report says *human review required*.

Corrections and other update types do not trigger the cap. Crossref outages
never flag anything (a missing check is not a retraction).

## v2.4.0 — DOI↔PMID cross-check & journal abbreviations

- **DOI splice detection**: add a `doi` field to your claims (JSON or CSV).
  The claimed DOI is compared with the DOI registered for that PMID — a
  mismatch is a splice/fabrication signal (a real DOI attached to the wrong
  paper): flagged in JSON (`doi_splice_suspect`), verdict capped at 🔶
  partial, counted in exit 1. Uses the PubMed record only — no extra API call.
- **Journal abbreviation equivalence**: journal matching now understands
  NLM-style abbreviations in both directions — "N Engl J Med" matches "New
  England Journal of Medicine", "Pediatr Rheumatol" matches "Pediatric
  Rheumatology" (in-order word prefixes, function words skipped). No more
  false "journal differs" for abbreviated citations.

Known limits: highly ambiguous abbreviations can over-match at the
journal-only level ("J Immunol" ~ "Journal of Immunology Research") — the
title remains the decisive field. A DOI-splice flag can also appear on an
otherwise-unverifiable citation (the DOI mismatch is an independent fact).

## v2.5.0 — author-name verification

- **Initials never match**: single-letter tokens ("A.", "L.") on either side
  are excluded from surname matching — an initial is not evidence, and
  substring-matching one produced false author hits.
- **Cross-language honesty**: CJK author names claimed against Latin
  registry records (or the reverse) are skipped, not counted as a mismatch —
  the report marks them `author_check: skipped` and the verdict falls back
  to what was actually comparable (title/journal/year), or to ❓ unknown
  when nothing else is checkable.

## Security & behavior declaration

- Single-run CLI: scan, verify, write the report, exit. No daemons, no
  background jobs, nothing downloaded or installed at runtime (pure standard
  library, zero dependencies).
- Network access is limited to these official academic registries, always
  over HTTPS: `eutils.ncbi.nlm.nih.gov`, `www.ebi.ac.uk` (Europe PMC),
  `api.crossref.org`, `api.openalex.org`, `export.arxiv.org` — no other
  hosts are contacted; no telemetry, no
  analytics, no data collection — the only outbound payloads are the PMIDs,
  DOIs and titles you asked to verify.
- Your files and reports stay on your machine. Writes are limited to the
  report paths you pass and the SQLite cache under
  `~/.cache/pubmed-verifier/` (`--no-cache` to disable).
- Optional environment variables `NCBI_API_KEY` / `PUBMED_VERIFIER_MAILTO`
  authenticate or attribute your own API requests and are never sent
  anywhere else.
- No OS integration: no subprocesses, no system services, no privilege
  changes, no scheduled tasks.

## v2.6.0 — audit working-paper & report v2

- **`--export-audit audit.json`** — a self-contained JSON working-paper for
  transparent review: tool identity and version, the exact (API-key-redacted)
  invocation, per-citation evidence chains (claimed vs registered fields,
  title match scores from both algorithms, author match with cross-language
  skip records, DOI cross-check, retraction signals) and the
  verdict-ladder trace for every citation. A reviewer can replay the entire
  verification from this file alone.
- **HTML report v2** — verdict filter tabs, severity-sorted rows (retracted
  and DOI-splice first, highlighted), a field-level evidence column
  (title/author/journal/year ✓✗—) and a reproducibility footer (redacted
  command line + version + data sources).
- **Reliability** — negative cache entries now expire after 3 days (a
  legitimately new, ahead-of-print PMID is no longer reported "not found"
  for a month), and the circuit breaker self-heals: after a 30 s cooldown it
  admits one probe call and resets on success.

## v2.7.0 — retraction for every PMID, BibTeX export, readiness verdict

- **Retraction detection, source-independent** — the registry's own
  publication type ("Retracted Publication"; present in both NCBI esummary
  and Europe PMC) now flags retracted papers for EVERY citation: no DOI
  required, no `--verify-doi` required, and the flag survives the cache
  (schema v3). Crossref `updated-by` remains the detail source (the
  retraction-notice DOI) when `--verify-doi` is on. A retraction *notice*
  itself is never flagged.
- **`--export-bibtex refs.bib`** — export the verified bibliography: correct
  entries as `@article`, partial entries commented out with their divergence
  note, mismatched/invalid/unknown/retracted entries excluded and counted.
- **Submission-readiness verdict** — every report now leads with one line:
  `SUBMISSION READY` or `NOT SUBMISSION-READY — <per-problem counts>`.
- Cache schema v3 (adds a `retracted` column, auto-migrated).

## v2.8.0 — DOI-native verification & delta audits

- **`--dois "10.x/a, 10.y/b"`** — verify DOIs natively, no PMID required.
  `--source` scans now also extract DOIs from your files automatically.
  Each DOI is resolved via the Crossref works API: not-found on an explicitly
  provided DOI = fabrication signal (invalid, exit 1); on one auto-extracted
  from scanned text it stays a suspect (unknown) — scanned strings are never
  user-endorsed, and DataCite/repository DOIs do not live in Crossref, so
  always double-check at doi.org. Resolved = existence confirmed with the
  registered metadata attached for manual comparison — *existence is never
  dressed up as a match*.
- **`--diff previous-audit.json`** — delta audit against a previous working
  paper: **newly retracted** (the safety signal — a paper retracted after
  your last audit; act on it: swap or drop the citation, cite the retraction
  notice instead, and re-check any conclusion that relied on it), degraded,
  improved, new and dropped citations, with counts in every report format.
  Built for periodic knowledge-base audits: "what changed since last time?"

## v2.9.0 — DOI entries become first-class

- **DOI→PMID linking** — a resolved DOI is linked back to its PMID via the
  Europe PMC DOI field query, pulling the full PubMed record: complete
  metadata, retraction pubtype signal, and cache coverage. A DOI citation
  now gets the same five-state record as a PMID citation (existence
  confirmation only — the verdict remains unknown until claims are
  provided).
- **Parallel DOI resolution** — `--workers N` (default 4, max 8) resolves
  DOI batches on a thread pool (roughly 3x faster on large lists), with
  live progress output. For large `--dois` batches, set `--mailto` to stay
  in Crossref's polite pool.
- **`--export-csv table.csv`** — spreadsheet-friendly audit table
  (key/verdict/flags/fields/details; formula-injection hardened).

## v3.0.0 — arXiv ID verification (three citation types, one audit)

Reference lists carry preprints. v3.0.0 verifies **arXiv IDs** alongside
PMIDs and DOIs: `arXiv:2401.12345` and `arxiv.org/abs/...` patterns are
extracted from scans (or passed via `--arxivs`), checked against the
official arXiv API, and judged — nonexistent ID = fabrication signal
(invalid, exit 1); resolving ID = registered title/year attached, verdict
stays unknown. Malformed IDs (bad YYMM month) are flagged by shape.
Timely: arXiv penalizes submissions containing hallucinated or unverified
references (2026-05 policy) — audit before you submit.

## v3.3.0 — preprint ↔ published-version cross-check

arXiv entries carry the version-of-record DOI their authors registered at
publication (`arxiv:doi`). v3.3.0 puts it to work:

- **Claimed DOI vs registered DOI** — a claims row with both `arxiv_id`
  and `doi` is cross-checked: agreement is reported as evidence
  (`fields.doi ✓`); disagreement caps the verdict at `partial` — the DOI
  belongs to a different paper (same failure class as PMID DOI-splice).
- **Version of record surfaced** — verifying a bare preprint ID now shows
  the registered DOI and, when the published version is PubMed-indexed,
  its linked PMID — cite and verify the final version, not just the
  preprint.
- **Honest accounting** — the readiness line counts arXiv DOI-pairing
  mismatches as problems; DOI/arXiv phase progress (stderr) now includes
  elapsed time and an ETA for large batches.
- Context parsing no longer truncates titles at sentence-internal
  abbreviations ("U.S. population", "e.g.", "vs.", "Vol.").

Pairing example (match → correct with DOI evidence; wrong DOI → partial):

```bash
python3 scripts/verify_pmids.py --claims '[{"arxiv_id":"2005.13892",
  "title":"City size and the spreading of COVID-19 in Brazil",
  "doi":"10.1371/journal.pone.0239699"}]'
```

## v3.4.0 — DOI claims become first-class

Claims rows could carry a PMID or an arXiv ID — a row keyed by DOI alone
was silently ignored, and DOI entries always stayed `unknown` ("no claimed
metadata to cross-verify"). v3.4.0 closes the matrix: all three citation
types now accept claimed metadata.

- A claims row with a `doi` (no PMID, no arXiv ID) is cross-checked against
  the registered metadata — the linked PubMed record when the DOI resolves
  to one, Crossref otherwise — and gets the full verdict ladder:
  correct / mismatch / partial.
- Retraction capping applies as everywhere: a claimed-correct match on a
  retracted paper is capped at partial with the retraction note.
- Without claims, DOI entries stay unknown — existence is never dressed up
  as a match.

```bash
python3 scripts/verify_pmids.py --claims '[{"doi":"10.1371/journal.pone.0239699",
  "title":"City size and the spreading of COVID-19 in Brazil",
  "journal":"PLoS ONE","year":"2020"}]'
```

## v3.5.0 — claims lint & usage-first restructuring

- **`--lint-claims FILE`** — offline pre-flight for claims files
  (JSON/CSV, zero network): ID shape errors, missing titles (the verdict
  would cap at partial), unknown/typo'd columns, DOI prefix checks,
  unusable rows — exit 1 on errors. Fix the format before the run
  instead of guessing from weak verdicts.
- **Documentation restructured around usage**: FAQ, anti-patterns and
  declared boundaries now sit right after Quick start, led by a Top-10
  "don't do this" table; new **Best practices & tuning** section (API-key
  batching, worker tuning, two-phase deep-verification, cache policy,
  scale expectations — and why the verifier is deliberately one file).

## v3.6.0 — BibTeX bibliography audit

**`--bibliography refs.bib`** audits a .bib file directly: entries route by
PMID (the `pmid` field, or a "PMID: NNNN" in the note — including the
notes `--export-bibtex` itself writes) > DOI > arXiv (`eprint`, or an
"arXiv:XXXX.XXXXX" in the journal/note), each carrying its claimed
title/authors/journal/year for the full cross-check. Entries without any
routable ID are counted and skipped. This closes the loop with
`--export-bibtex`: a verified bibliography can be re-audited after edits.
`--lint-claims refs.bib` validates the file offline (unroutable entries,
missing titles, unclosed blocks).

## v3.7.0 — RIS bibliography support

`--bibliography` now accepts **RIS files** (`refs.ris` — Zotero/EndNote/
Mendeley exports) alongside BibTeX: records route by PMID (AN tag, or a
"PMID: NNNN" note) > DOI (DO) > arXiv (UR/eprint), each with claimed
metadata for the full cross-check. **`--export-ris`** completes the loop —
verified entries as `TY JOUR`, partials as `TY DATA` with a PARTIAL note.
`--lint-claims refs.ris` validates offline (unroutable records, missing
titles, duplicates, unterminated records).

## v3.8.0 — verdict-ladder corrections (independent external test audit)

An independent real-data audit (24 scenarios, registry-ground-truthed) found
three judgment-ladder defects; all three are fixed and locked:

- **B1 scan false positives** — when a citation is not the first sentence of
  its block, the author line was taken as the claimed title (correct
  references reported as mismatch). The parser now shifts past an
  author-shaped segment.
- **B2 author mis-attribution** — a claimed author set entirely different
  from the registry (zero surname overlap) was still reported as correct
  when title and journal matched; it now caps at partial. Partial surname
  overlap (abbreviated or reordered names) keeps correct.
- **B3 title-less claims** — author+journal+year matches without a claimed
  title now cap at partial, exactly as the FAQ/anti-patterns/boundaries
  always promised (the same author/journal/year can cover several papers).
  Cross-language author skips follow the same cap.
- Also: duplicate arXiv IDs announce their merge on stderr (run
  `--lint-claims` to catch duplicate claim rows offline); the
  cross-language skip no longer coexists with contradictory details text;
  empty `--claims` gets a one-line hint; docs state that Chinese-language
  citation contexts parse weakly — use `--claims-file`.

## v3.9.0 — Chinese references (GB/T 7714), network pre-flight, Python API

- **GB/T 7714 Chinese references parse** — `……标题[J]. 刊名, 年… PMID: xxx`
  contexts now yield the title (via the `[J]/[M]/[R]` type marker),
  authors, journal, year and any DOI that follows the PMID. The title
  comparison against a Latin registry title is skipped cross-language
  (never a mismatch source); a DOI in the reference is cross-checked
  against the registry like any claims DOI. Requires a PMID marker per
  reference.
- **`--check-net`** — probes the data sources (5 s each), shows your
  proxy state and prints practical next steps when something is
  unreachable. Run it when results come back unknown on a constrained
  network.
- **Python API reference** — `references/python_api.md` documents the
  stable importable surfaces (`fetch_summaries`, `cross_check_citation`,
  `verify_doi_entry`, `parse_citation_context`, `suggest_correct_pmid`)
  with copy-paste examples.

## v4.0.0 — plain-text reference lists & formatted reference list export

- **`--parse-text refs.txt`** — verify a reference list copied straight out
  of a manuscript draft. Numbered entries (`[1]`, `1.`) split cleanly;
  inline PMID / DOI / arXiv IDs route exactly (full five-state
  cross-check); a markerless entry with a parseable title resolves via
  PubMed title search and is marked `resolved_by: title_search` — weaker
  evidence than a supplied ID, honestly labeled, and never a mismatch
  source. A network failure stays unknown with a retry hint, never
  "not found". Entries with no routable ID and no usable title are
  skipped with a note instead of being guessed.
- **`--format-references out.txt --citation-style gbt|vancouver|apa|ama`**
  — the formatting leg of verify-then-format: verified entries rendered as
  a ready-to-paste numbered reference list (GB/T 7714-2015 numeric for
  Chinese submissions, Vancouver, APA 7th, AMA 11th). Formatting stands on
  registry-verified records only: correct entries form the list, partial
  entries go to a manual-review section (never silently dropped), and
  retracted entries are excluded with a warning. Author lists are
  formatted per style without inventing names — a registry-truncated list
  closes with the style's et-al form, and APA discloses the truncation.
- Markerless Latin references now parse through the full sentence
  segmentation (titles feed the title-search leg); CJK entries without a
  PMID/DOI marker keep the documented weak-parsing boundary — supply a
  PMID or DOI for exact routing.
- `examples/refs_list.sample.txt` ships a ready-made parse-text fixture.

## v4.1.0 — OpenAlex fallback & Chinese-reference title search

- **OpenAlex is now the fourth data source** — a DOI that Crossref reports
  404 gets a second look at OpenAlex before any verdict: DataCite, Zenodo,
  SSRN and Chinese-registry DOIs (which do not live in Crossref) become
  fully decidable — resolved, metadata attached, claims cross-checked,
  retractions flagged (`is_retracted`). Only when OpenAlex also comes up
  empty do the original 404 semantics stand (explicit DOI = invalid,
  scanned DOI = suspect). `--check-net` probes five sources now.
- **Chinese references without any ID can now be verified** — a markerless
  CJK entry in `--parse-text` searches OpenAlex by its title (the query is
  the title-shaped segment of the entry, not the whole line); a candidate
  counts only when its registered title appears **verbatim** in your entry
  text with an agreeing year, and the verdict carries
  `resolved_by: openalex_cjk_search`. No hit = honestly unknown; this leg
  never manufactures a mismatch, and a network failure stays unknown.
- Docs: the reports' actual shape is now shown in "What the output looks
  like"; three worked scenarios added to the FAQ (reviewer evidence,
  thesis citation check, PRISMA screening).

## v4.2.0 — retraction replacement suggestions & delta detail panel

- **Retraction replacement suggestions** (`--suggest`) — a retracted entry
  now comes with up to three same-topic live candidates (retracted papers
  and the entry's own PMID excluded), marked `replacement_for_retracted`
  and carrying an honest note: they are search suggestions, NOT verdicts —
  verify each before citing. Answers the reviewer question "this paper is
  retracted, what should I cite instead?" at audit time.
- **Delta audits now show their full detail** — alongside the counts
  line, the HTML report renders a per-category panel (newly retracted /
  degraded / improved / new / dropped, up to 50 rows each); the markdown
  report lists degraded/improved/new/dropped rows too. Built for PRISMA
  re-runs: you only re-read what changed.
- `--check-net` masks proxy credentials (`http://user:****@host:port`) so
  the pre-flight output is paste-safe.
- Docs: "Trigger words" and "Use from Python" sections moved up front.

## v5.4.0 — grouped flags, cheat sheet, citation sort

- **`--help` is grouped by task domain** (inputs / verification depth /
  output & exports / network & performance / institutional & diagnostics)
  — 38 flags in one flat list was the top usability complaint; the same
  grouping now scans top-to-bottom. Zero behavior change: only where each
  flag appears in `--help`.
- **`references/flags.md`** — the scenario→command cheat sheet: the 90%
  scenarios are each ONE command with ZERO extra flags, then the full
  flag map in the same grouping as `--help`. Routed from INDEX and both
  documentation maps.
- **`--sort cited`** — report rows ordered by citation count descending
  (Europe PMC/OpenAlex counts; entries without a count keep their
  severity position at the back). Affects the terminal/JSON/JSONL/
  markdown reports; the HTML report always keeps its severity layout.

## v5.3.0 — retraction reasons, doctor, JSONL, expandable HTML

- **Retraction reasons**: a retracted citation now distills WHY from the
  retraction notice record — the notice abstract when Crossref carries
  one, else the notice title only when it names the offence; the bare
  original title inside "Retraction Note: <original title>" never
  masquerades as a reason. Fields: `retraction_reason`,
  `retraction_notice_title`, `retraction_reason_doi` — in JSON, the
  audit chain, the HTML detail rows and the markdown report. Wired on
  both the PMID `--verify-doi` path and the DOI-native path
  (`--dois`, bibliography routing).
- **`--doctor`**: environment self-check — tool/Python versions, cache
  path and entry count (a stale-table cache reports as a finding),
  NCBI key / mailto / proxy configuration; `--doctor --check-net`
  includes the five-registry probe. Read-only, paste-safe.
- **`--jsonl PATH`**: one citation per line + a final `{"_stats": ...}`
  line — stream-friendly output for agent pipelines.
- **HTML inline evidence**: every table row gains a native
  `<details>` expansion with the full evidence trail (claimed vs
  registered, match booleans, answered-by registry, route, citation
  count, retraction reason) — zero JavaScript, and the verdict filter
  keeps the detail rows in sync.

## v5.2.0 — quantified input guard & citation counts

- **`--max-entries` guard**: the vague "large scans take hours" became a
  number — the de-duplicated workload (PMIDs + DOIs + arXiv IDs +
  title-search entries) is counted and compared against a threshold
  (default 2000); over it, a NOTE prints the actual count, the expected
  cost and a split recommendation. `--max-entries N` raises it, `0`
  silences it.
- **`cited_by_count`**: citation counts ride responses that already carry
  them (Europe PMC `citedCount`, OpenAlex `cited_by_count`) — zero extra
  requests. Surfaces in JSON/markdown ("· 128 cited" in the evidence
  cell). The NCBI path reports none, honestly.
- **Trigger section by pattern**: when-to-invoke is now described as
  patterns (MUST invoke / MUST NOT invoke alone) plus a combination-run
  table, on both language pages — an enumerated keyword list misses
  boundary phrasings.
- Boundary table row now quantifies the guard and the arXiv floor
  (1,000 arXiv IDs ≈ 50+ minutes).

## v5.1.0 — structured retraction detail & explicit precedence

- **Structured retraction detail**: every retraction now carries a
  `retraction_type` (retraction vs **removal** — the paper withdrawn
  from the record entirely, newly detected via Crossref
  `updated-by`), on top of the existing note/date/source. Wired through
  all three registries (NCBI/Europe PMC/Crossref), the JSON/audit
  evidence chain (`retraction.type`) and the markdown report flags
  (`[RETRACTED:removal (2024-03-01)]`).
- **Explicit precedence**: `--pmids` together with `--source` now
  announces on stderr that `--pmids` wins and the scan input is ignored
  — silent no-ops look like bugs from the outside.
- **Mainland-China usage guide**: one concentrated page (pre-flight,
  registry fallback, proxy semantics, package mirror, honest-failure
  contract) on both language pages — the network guidance had scattered
  across sections.
- **Boundary table** gains input-scale/concurrency and
  explicit-precedence rows; the HTML report's structure is now
  described where the text output sample lives.

## v5.0.0 — paste-and-verify, one-flag final pass, leaner main doc

Shaped by the v4.9.0 audit follow-ups (FAQ depth, trigger-boundary
clarity, flag-combination onboarding, main-doc length):

- **`--stdin` — paste-and-verify**: a copied reference list goes straight
  down the pipe (`pbpaste | verify_pmids.py --stdin`, `git show
  HEAD:refs.txt | verify_pmids.py --stdin`). Same numbered/heading parser
  as `--parse-text`; the report labels the source "stdin" — no temp file
  choreography in agent workflows.
- **`--quick` — the pre-submission final pass in one flag**: `--no-cache`
  (fresh registries) + `--verify-doi` (Crossref cross-check) +
  `--suggest` (correct-PMID hints) combined. Explicit user flags always
  win; --quick only sets what wasn't given.
- **FAQ depth**: a format-specific "when parsing fails" table in
  references/usage_guide.md (damaged office files, CJK without IDs,
  numbering variants, fragmented titles, reading the `fields` table,
  all-unknown = network).
- **Trigger boundary made explicit**: a pasted reference list IS the
  input — no explicit "verify" wording required (both language pages).
- **Main doc slimmed**: SKILL.md 579 → ~450 lines (recent-release rows
  sink into references/CHANGELOG.md, orphan historical section removed);
  SKILL_ZH.md mirrors.

## v4.9.0 — PowerPoint input & verdict-ladder monotonicity

Both grown from re-running the real rheumatology-literature audit (the
v4.7.0 acceptance sample) against v4.8.0:

- **`.pptx` decks are read directly** (`--source` and `--parse-text`):
  every slide in numeric order plus the speaker notes (DrawingML
  `a:p`/`a:t`, the same in-memory zip+XML family as .docx) —
  patient-education courseware audits without a copy-paste pass. A
  damaged file falls back to a raw read; directory scanning includes
  `.pptx`.
- **Verdict-ladder monotonicity**: the acceptance rerun surfaced
  citations grading PARTIAL on "title matches but author/journal not
  claimed" — a STRONGER evidence position than the bare existence
  checks that grade correct. On scanned sources, a partial whose only
  gap is the missing author claim (title matched; journal and year
  never claimed) now grades **correct** with `route:
  existence_title_match` and a detail line pointing at `--claims-file`
  for the full pass. An entry claiming journal/year/authors anything
  keeps its partial — those claims were checked and something differed,
  a real doubt. In the acceptance sample this resolved 4 of the 6
  manual-review items; the remaining 2 keep partial for real reasons
  (no title recoverable + author/journal differ; year claimed and
  differing).
- cross_check_citation itself is unchanged — the upgrade lives in the
  pipeline layer, so explicit `--claims-file`/CLI inputs always receive
  the full verdict.

## v4.8.0 — Word/HTML input & the title second-opinion leg

Two capabilities grown from the same medical-document reality testing:

- **`.docx` and `.html` inputs are read directly** (`--source` and
  `--parse-text`): Word paragraphs/tables are extracted in-memory from the
  document XML, exported HTML pages are tag-stripped with block elements
  as newlines. `script`/`style` content is dropped; `href`/`src`/`cite`
  link targets are KEPT (citations live in link targets on exported
  pages). A damaged .docx falls back to a raw read instead of failing the
  scan. Directory scanning now includes `.docx`.
- **The second-opinion leg for title-only claims**: the v4.7.0 mismatch
  gate correctly refuses to accuse on heuristic single-field claims — but
  "honest-but-unhelpful" left real wrong-PMID citations undiscovered. The
  gate now re-checks the claimed title phrase against PubMed's own
  `[Title]` index (quoted-phrase query): corroboration by the SAME PMID
  upgrades the verdict to correct (labeled `route: inline_title_search`,
  weaker evidence than a user-supplied ID — reachable exactly where the
  claimed title is a shortened variant that fails similarity thresholds
  but appears verbatim in the registered title); a phrase hit on a
  DIFFERENT record surfaces the `wrong_pmid_signal` evidence while the
  verdict stays unknown; no hit or a network failure stays unknown. The
  leg only confirms or reports —
  it never manufactures a mismatch, and CJK titles skip it (the OpenAlex
  CJK leg owns those).
- Docs: a documentation map on both main pages (what lives where — full
  version history, full FAQ, Python API reference, task router), the
  Trigger words section now states when `--claims-file` is required and
  where the cite-holmes boundary sits, and the boundary tables cover the
  new input formats and the second-opinion leg.

## v4.7.0 — real medical-document fixes (literature-export testing)

Found by running the verifier against a real rheumatology literature
export (385-entry file, 2026-10-14): 17 of 20 citations were false
mismatches because registry-metadata list lines ("- DOI: ...") directly
above a PMID were taken as the claimed title.

- Metadata list lines and "Year | Journal | Authors" table rows are now
  stripped before citation segmentation; when a flattened export leaves a
  single "## Title" line, that line IS the claim.
- A live PMID with no claimed metadata is an explicit **existence
  confirmation** (`existence_confirmed: true`, counted in the finding
  ledger as answered) — the old "Insufficient claimed metadata" wording
  treated the user's existence check like an error.
- `--source` merges a scanned DOI into its already-verified PMID (one
  paper, one finding; explicit `--dois`/claims are never merged).
- `--parse-text` reads "## Title" heading exports as entry boundaries.

## v4.6.0 — finding ledger & claims skeleton generator

- **Finding ledger** — text and HTML reports close with an explicit
  bookkeeping page: every planned citation is answered (correct / mismatch
  / invalid), partially answered (partial — the manual-review pool), or
  unresolved (unknown) with the reason and the next action, plus a budget
  line (citations checked / network errors).
- **`--claims-template SRC,OUT`** — reverse-generates a claims CSV
  skeleton from a plain-text reference list, .bib or .ris: every routable
  field the parsers can see (PMID, DOI, arXiv ID, title, authors, journal,
  year) is filled; fill the gaps and run `--claims-file` for the exact
  five-state path.
- Docs: capability×limit boundary table; FAQ slimmed to the top-4 with the
  full list in references/usage_guide.md; 30-second entry blocks on every
  reference file; references/INDEX.md task router; anti-pattern table
  gains the don't-repeat-burned-calls row; Skip-when negative triggers in
  the description.

## v4.5.0 — card conversion: icon + search-intent coverage

A proper skill icon (the splice-detection visual) went live with this
release, and the description now covers five more search intents verbatim
(参考文献生成 / 文献真伪 / 文献核对 / 引用核查 / 论文引用), first line
leading on citation authenticity. No code changes.

## v4.4.0 — submission evidence pack & leaner main doc

`--report-bundle DIR` — one command writes the complete evidence pack
(audit + HTML + BibTeX/RIS + CSV + GB/T list + self-describing manifest).
Full version history moved here from SKILL.md; OpenAlex 429 retries back
off at least 5s.

## v4.3.0 — GB/T author-date style & monograph journal fix

- **`--citation-style gbty`** — the second GB/T 7714-2015 form Chinese
  journals and theses actually ask for: unnumbered entries, no [J] type
  tag, sorted by first author (Latin casefold; CJK stays in Unicode order
  — true pinyin sorting needs an external library and is a documented
  manual step). Verified entries only, exactly like the numeric style.
- **Monographs no longer fake a journal** — GB/T parsing extracted the
  segment after the type tag for every entry, so `[M]` (monograph),
  `[R]` (report) and `[D]` (thesis) records picked up the PUBLISHER as
  the claimed journal and manufactured false journal mismatches. Only
  `[J]` entries yield a journal now; the others leave it empty.
- Docs: a "Know before you run" four-limit digest sits at the top of
  SKILL.md (each limit with its one-flag workaround), and the Trigger
  words section gained three request-to-action mappings.
