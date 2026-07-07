# Semantic Source Discovery Loop — Implementation & Run Verification Report

Date: 2026-07-05
Scope of this review: verify the implementation of `semantic-source-discovery-loop-prompt.md` (taking the parser-gallery change into account) and verify the quality/correctness of the discovery run on `taskdesk-legacy` plus `db/`.

## Verdict

**The implementation is successful, and the discovery run produced factually correct results.** Every checkable claim in the generated artefacts was verified against ground truth: all 11 Struts actions, all 4 database tables, all 31 Java classes, provenance on 83/83 evidence entries, and byte-identical reproducibility on re-run. All 9 artefacts validate against their JSON Schema contracts.

The main caveats are process-quality, not correctness: the verifier's scores are largely **hardcoded rather than measured** (the loop grades itself), the run driver is a monolithic script that LOOP.md's own rules discourage, and a handful of nodes carry a slightly misleading `parser_id` attribution. Details below.

---

## 1. Implementation verification (against the prompt spec)

### 1.1 Structure — complete

All files and folders required by the spec exist and contain operational (not decorative) content:

| Spec requirement | Status |
| --- | --- |
| `.agent-loop/README.md`, `LOOP.md` | ✅ present; LOOP.md is a faithful, well-organized rendering of the spec |
| `.agent-loop/contracts/*.schema.json` (7 schemas) | ✅ all 7 present, valid JSON Schema; all artefacts validate against them |
| `.agent-loop/skills/00–08` (9 skills) | ✅ all present, each with Purpose/Responsibilities/rules matching the spec's required content |
| `.agent-loop/prompts/` (run / continue / verify) | ✅ all 3 present |
| `.agent-loop/examples/expected-report-shape.md` | ✅ present |
| `.github/copilot-instructions.md` + prompt file | ✅ present, constraints stated |
| `.claude/skills/semantic-discovery-loop/SKILL.md` | ✅ present, matches spec content |
| `AGENTS.md` | ✅ present, matches spec's 9-point content |
| `.cache/scripts/parsers/README.md` | ✅ present |
| `.work/semantic-loop/README.md` | ✅ present |

### 1.2 The parser-gallery change (`.agent-loop/tools/`)

The implementation adds something the original prompt spec does not describe: a curated **tool gallery** at `.agent-loop/tools/` containing six prepared, deterministic parsers (`java-structure`, `xml-structure`, `jsp-structure`, `properties-config`, `sql-ddl`, `sqlite-schema`), each a `parser.py` + `tool.json` manifest pair.

**This change is documented — but only inside the implementation, not in the originating spec.** It is consistently described in:

- `.agent-loop/tools/README.md` (full gallery-vs-cache protocol, conventions, promotion process)
- `.agent-loop/LOOP.md` §"Parser discipline" (gallery inserted as step 3 of the selection order)
- `.agent-loop/README.md` (folder table)
- `.agent-loop/skills/02-parser-broker.md` and `03-parser-generator.md`
- `.cache/scripts/parsers/README.md`

`semantic-source-discovery-loop-prompt.md` itself still describes the original 5-step parser selection order with no gallery. If the prompt document is meant to remain the authoritative spec, it is now out of date on this point (the spec says it must not be modified here, so this is noted as a documentation gap, not fixed).

The change itself is an improvement and honors the spec's intent: gallery originals are read-only during loop execution, copies go to `.cache/scripts/parsers/` (the spec's designated location), and each copy is registered with `origin: "gallery"` and `gallery_source` in the parser registry. I verified the six cache copies are **byte-identical** to their gallery sources, matching the registry's `"adaptations": []` claims.

### 1.3 Parser validation — verified working

- All 6 gallery parsers and all 6 cache copies pass their built-in smoke tests (12/12 `SMOKE PASS`).
- Parsers are Python 3 stdlib-only (no dependency installation), read-only over the source tree, emit source-graph fragments as JSON — all per the stated conventions.
- Manifests include artifact type, input patterns, invocation, validation status, tests, and honest `known_limitations` (e.g. the JSP tool declares itself a lexical extractor, not a parser).

---

## 2. Discovery-run quality on taskdesk-legacy + db

Artefacts under `.work/semantic-loop/` were checked against the actual repository content.

### 2.1 Factual accuracy — correct

| Claim in artefacts | Ground truth check | Result |
| --- | --- | --- |
| 11 Struts actions (`/login` … `/taskExport`) | `grep 'action path=' struts-config.xml` → 11 identical paths | ✅ exact match, incl. correct `.do` suffix derived from `web.xml` `*.do` mapping |
| 6 JSP views wired to actions | action `input`/`forward` targets in struts-config | ✅ correct (see 3.4 for the two unwired JSPs) |
| 4 tables: `TASK`, `APP_USER`, `TASK_COMMENT`, `TASK_AUDIT` | live introspection of `db/runtime-data/taskdesk-demo.sqlite` | ✅ exact match (internal `sqlite_sequence` correctly excluded); each table triple-grounded in Java SQL literals, `db/sql/001_schema_sqlite.sql` DDL, and SQLite schema introspection |
| 31 Java classes, 8 JSPs, 5 XML, 3 properties, 3 SQL, 1 SQLite, 1 CSS, 3 MD = 55 files | file counts on disk | ✅ match |
| SQLite JDBC integration | `org.xerial:sqlite-jdbc` in pom.xml + `Class.forName("org.sqlite.JDBC")` in `JdbcConnectionManager` | ✅ both present |
| Foreign keys/indexes (TASK→APP_USER etc.) | sqlite-schema parser output vs live DB | ✅ 4 `DatabaseTable` + 6 `DatabaseIndex` nodes with FK edges |
| Struts EntryPoint grounded in `web.xml:8-20` | web.xml servlet block lines 8–16, mapping 18–21 | ✅ substantively correct (span clips the closing tag at 21) |

### 2.2 Artefact integrity — strong

- **Schema validity:** all of `state`, `inventory`, `parser-registry`, `source-graph`, `semantic-types`, `semantic-graph`, `verification` validate against their `.agent-loop/contracts/` schemas.
- **Provenance:** every one of the 30 semantic nodes has `grounded_in` evidence; all 83 evidence entries resolve to a real source-graph node (0 null/dangling references). This exceeds the spec's minimum.
- **Source-graph consistency:** 808 nodes, 782 edges, 0 dangling edges (independently recomputed).
- **Semantic discipline:** only the 16-type kernel vocabulary is used, all `accepted`; no ontology sprawl; one `UnknownSemanticConstruct` (`runtime-row-semantics`) correctly represents the row-data gap, mirrored in `inventory.uncertainties` and the report's Limitations.
- **Database coverage:** the `db/` scope is genuinely analyzed, not just listed — SQL DDL is statement-parsed and the live SQLite file is schema-introspected read-only; the two are cross-linked in the DataStore nodes (`schema_verified: true`).

### 2.3 Reproducibility — verified empirically

Re-running `.cache/scripts/run_taskdesk_semantic_loop.py` regenerates **byte-identical** artefacts (verified by full directory diff); only the two `state.json` history timestamps differ. The reproducibility score of 9 is earned. (The original `state.json` was restored after this test; the working tree is unchanged.)

---

## 3. Findings (issues, by severity)

### 3.1 The verifier mostly grades itself with hardcoded scores — *most significant*

In `run_taskdesk_semantic_loop.py::verify()`:

- Only 3 of 8 scores react to measured conditions (`source_graph_consistency` via dangling-edge count, `semantic_graph_provenance` via provenance check, `report_coverage` via a flag). The other five — `inventory_coverage`, `parser_validity`, `semantic_type_quality`, `unknowns_handling`, `reproducibility` — are **constants** (9, 9, 8, 9, 9).
- The named `checks` array is computed but **not connected to the scores**: if the "inventory scoped coverage" or "parsers validated" check failed, the corresponding score would still be 9 and the gate would still pass.
- The script never prints `ITERATING` on failure (it only exits 1), and the `preliminary = verify(..., False)` result is computed and discarded (dead code).
- Verification is performed by the same script that generates the artefacts — the spec's intent of an independent verification phase (skill 07, `verify-discovery-loop.md` prompt) is structurally weakened.

In this run the outcome is defensible — my independent re-checks confirm the high scores are deserved — but the *mechanism* would not catch regressions. The gate "passed" because the author of the gate also authored the numbers.

### 3.2 Monolithic driver script contradicts LOOP.md's own rule

LOOP.md states: *"One parser per artifact type — no monolithic 'suite' scripts that bundle parsing, graph building, and reporting into one file."* The parsers themselves comply, but `.cache/scripts/run_taskdesk_semantic_loop.py` (614 lines) bundles inventory, ad-hoc parsing, source-graph assembly, semantic-graph assembly, verification, and report writing into a single file. It also lives directly in `.cache/scripts/` and has **no manifest**, unlike everything else in the cache. As a pragmatic reproducibility harness it works well; as a matter of the loop's own discipline it is a deviation.

### 3.3 `parser_id` misattribution on driver-built nodes

The driver extracts Struts routes, `validation.xml` fields, and Maven dependencies with its own inline regex/ElementTree code, yet labels the resulting nodes `parser_id: "xml-structure-v1"` (11 Route nodes, 7 Dependency nodes, validation-field ConfigurationEntry nodes). The content is correct, but the provenance claims these nodes came from a registered, validated parser when they came from unregistered driver code. This blurs exactly the parser-discipline line the setup works hard to draw.

### 3.4 Minor coverage and consistency gaps

- **Views:** 6 of 8 JSPs become `View` nodes. `error.jsp` and `accessDenied.jsp` are reachable only via `<global-forwards>` (struts-config.xml:16–18), which the semantic builder does not model. `tiles-defs.xml` is parsed structurally but not interpreted semantically. Not flagged as an unknown.
- **Silent inventory drop:** `git ls-files taskdesk-legacy db` returns 56 paths; inventory has 55. The dropped path is `taskdesk-legacy/runtime-data/taskdesk-demo.sqlite` — a git-tracked **broken symlink** (it points to `../db/runtime-data/...`, which resolves to the nonexistent `taskdesk-legacy/db/...`). Excluding it is reasonable; excluding it *silently* is not — the spec requires uncertainty to be recorded, and a broken symlink in a migration fixture is worth surfacing.
- **Module inconsistency:** `assumptions.json` says packages `action/service/dao/form/model/util` are modules, but the semantic graph has no `sem:module:util` (it has `view` and `config` instead), and the three `util` classes (`SecurityUtils`, `DateUtils`, `CsvExportUtils`) are never `Component` nodes — `SecurityUtils` appears only as evidence for the SecurityElement.
- **Small evidence-span drift:** the hardcoded pom.xml span for `sqlite-jdbc` (34–38) is off by one (actual block 35–39); `inventory.generated_by` says "git ls-files taskdesk-legacy" but the run included `db` too.
- **State handling:** the driver unconditionally resets `state.json` to iteration 1 rather than loading and continuing, so `continue-discovery-loop.md` semantics (resume, improve weakest score) exist only in documentation, not in the executable path.

---

## 4. Answers to the review questions

**Was the implementation successful?** Yes. The full spec structure exists and is operational; the parser-gallery addition is a well-executed, well-documented (within `.agent-loop/`) improvement over the spec, though the spec document itself was not updated to mention it. All hard constraints were respected: no source files modified, writes confined to `.work/` and `.cache/`, no dependencies installed, evidence-first discipline throughout.

**Did it generate the correct results?** Yes, factually. Every verifiable claim — actions, routes, views, components, data objects, tables, foreign keys, integrations, configuration — matches the ground truth of `taskdesk-legacy` and the live database, with complete and resolvable provenance, explicit assumptions, an honest unknown for row-level semantics, and byte-level reproducibility. The report `application-structure.md` accurately reflects the artefacts and does not invent certainty.

**The qualification:** the *verification gate* passed by construction rather than by measurement (§3.1). The results are correct because the run was done carefully, not because the gate would have caught it if it hadn't been. For the demonstrator's stated goal — proving a disciplined, evidence-backed loop is feasible — that is the one piece where the proof is weaker than the artefacts suggest, and it is the first thing to harden in a next iteration (independent verifier deriving all eight scores from measured checks).

---

## Addendum (2026-07-05, later the same day): findings addressed

All findings above were subsequently fixed; this report is kept as the record of the pre-hardening state.

- **§3.1 (self-graded verifier):** verification now lives in an independent gallery tool (`.agent-loop/tools/verifier/`, cache copy `.cache/scripts/verifier-v1/`). All eight scores are measured objects (`{value, derived_from, measurement}`) computed from named checks — `verification.schema.json` makes bare score integers schema-invalid. The verifier re-runs parser smoke tests, recomputes hashes, re-resolves provenance onto disk, and runs a mutation self-test (4 seeded corruptions, all must be caught) before any verdict is trusted. It prints `ITERATING` with the weakest score on failure.
- **§3.2 (monolithic driver):** the driver is now orchestration-only — all content parsing was moved into two new registered gallery parsers (`struts-config-v1` for routes/forwards/validator fields, `maven-pom-v1` for module/dependencies with exact block spans), and verification is an external subprocess. LOOP.md now states graph building and verification must never share a file.
- **§3.3 (`parser_id` misattribution):** Route, Dependency, and validator-field nodes are emitted by the parsers that own them; the verifier cross-checks every `parser_id` against the registry and its input patterns (this check is one of the self-test mutations).
- **§3.4 (minor gaps):** `error.jsp`/`accessDenied.jsp` are now View nodes grounded in `<global-forwards>`; the broken tracked symlink is recorded as an inventory uncertainty; a `util` module with its three Components exists; the sqlite-jdbc span comes from the parser (35–39, correct); `generated_by` names both scope roots; the `.do` suffix is derived from the parsed `web.xml` `url-pattern` element instead of being assumed; `state.json` continues (iteration+1) after an `iterating` run instead of resetting.
- **Validation of the fix:** the hardened gate proved itself immediately — the first run after the refactor **failed** (`ITERATING`, `semantic_graph_provenance` = 2) because three parsers overcounted file line spans by one (`data.count(b"\n")+1` vs. real line count), a defect the old verifier could never have seen. After fixing the parsers, iteration 2 passed with all measured scores at 10 and a 4/4 self-test. The spec (`semantic-source-discovery-loop-prompt.md`) was updated to describe the gallery, the attribution rule, and the measured-verification contract.

## Addendum (2026-07-07): extended semantic layer, nine dimensions

The contract has since been extended per `docs/implement-extended-semantic-layer.md` (Milestones 1–2): provenance entries carry an evidence `kind` (`parsed | observed | asserted`) under the authority rule `parsed > observed > asserted`, a documentation-alignment phase (skill 10, `doc-claims-v1` tool) produces `doc-claims.json`, and the gate now measures **nine** dimensions (adding `assertion_grounding`) with a 6-mutation self-test (adding `forged-doc-claim` and `asserted-only-accepted`). The "eight" counts in the 2026-07-05 addendum describe the contract as it stood then. `examples/taskdesk-legacy-run/` was regenerated under the nine-dimension contract: all scores 10, self-test 6/6, 8 documentation claims (7 confirmed, 1 unverifiable — the latter now grounds `sem:unknown:runtime-row-semantics` as disciplined asserted evidence with a `claim_ref`).
