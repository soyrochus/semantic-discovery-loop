# .agent-loop/tools/ — Parser & Extractor Gallery

A curated gallery of prepared, quality parsers/extractors the loop picks from **before**
writing anything itself. The gallery exists because an agent improvising a parser
mid-loop tends to reach for line regexes; a prepared tool can afford to do it properly
(real tokenization, real XML parsing, real schema introspection).

## Gallery vs. cache

- **`.agent-loop/tools/`** (here) — the curated source. Committed, human-reviewed,
  read-only during loop execution (loop writes are restricted to `.work/` and
  `.cache/`).
- **`.cache/scripts/parsers/`** — the working area. The agent **copies** a gallery tool
  there, adapts it if the repository needs it, smoke-tests it, and registers it in
  `parser-registry.json`. Gallery originals are never modified in place by the loop.

## Usage protocol (for the loop)

1. Match the detected artifact type against each tool's `tool.json`
   (`artifact_type`, `input_patterns`).
2. Copy the tool folder to `.cache/scripts/parsers/<parser_id>/`.
3. Run its built-in smoke test (`python3 parser.py --smoke`) **and** run it against a
   few real files from this repository; inspect the output.
4. If it works unmodified: register with `origin: "gallery"` and
   `gallery_source: ".agent-loop/tools/<tool>"`.
5. If it needs adaptation: modify the **cache copy only**, record what changed in the
   manifest's `known_limitations`/notes, register with `origin: "gallery-adapted"`, and
   re-run the smoke test plus repository samples before use.
6. Only if no gallery tool is adaptable do the later selection steps apply (standard
   local parser, custom extractor, generated parser — see
   `.agent-loop/skills/02-parser-broker.md`).

## Conventions every gallery tool follows

- One artifact type per tool; one folder per tool: `parser.py` + `tool.json`.
- Python 3 standard library only — no installation ever required.
- Read-only over the source tree; JSON to stdout.
- Output is a source-graph fragment: `{"parser_id", "nodes": [...], "edges": [...]}`
  with node/edge shapes from `.agent-loop/contracts/source-graph.schema.json`
  (stable `src:` ids, paths, line spans, confidence on edges).
- `parser.py --smoke` runs a self-contained smoke test (embedded sample input,
  assertions, prints `SMOKE PASS`); `parser.py <files...>` parses real files.
- `tool.json` records the parsing approach honestly (`parsing_approach`) and its
  `known_limitations`. A lexical extractor must say so; it must not present itself as a
  full parser.

## Current tools

| Tool | Artifact type | Approach |
| --- | --- | --- |
| `java-structure/` | Java sources | Tokenizer + brace matching (comment/string aware), packages, imports, types, methods with spans |
| `xml-structure/` | XML files | Real XML parse (`xml.sax`) with line numbers, element paths, attributes |
| `struts-config/` | Struts 1.x config (`struts-config.xml`, `validation.xml`) | Real XML parse: Route nodes per action mapping (forwards, form beans, input), global-forwards, plug-ins, validator fields |
| `maven-pom/` | Maven `pom.xml` | Real XML parse: BuildModule + Dependency nodes with exact `<dependency>` block spans; skips dependencyManagement/plugins |
| `jsp-structure/` | JSP templates | Lexical extractor: directives, includes, taglib usage, forms/links, scriptlets |
| `properties-config/` | `.properties` files | Line parser with comments, separators, continuations |
| `sql-ddl/` | `.sql` scripts | Comment/string-aware statement splitter + DDL object extraction |
| `sqlite-schema/` | SQLite database files | Schema introspection via stdlib `sqlite3` (read-only), incl. foreign-key edges |
| `doc-claims/` | Documentation claims (`doc-claims.json`) | Deterministic half of doc alignment (skill 10): anchor mode lists a document's claimable units (headings, list items, table rows) with spans; check mode re-resolves every extracted claim's excerpt/span/node mappings onto the repository. The claim *reading* itself is model-driven and stays outside this tool |
| `verifier/` | Loop artefacts (not a parser) | Independent gate: measures all ten verification scores from named checks and proves the gate can fail via mutation self-test |

The `verifier/` tool is special: it is not registered in `parser-registry.json`
(it emits `verification.json`, not source-graph fragments). Its cache copy goes to
`.cache/scripts/verifier-v1/`, and its identity plus self-test result are recorded in
`verification.json` under `verifier`.

The `doc-claims/` tool is also special: it emits claim anchors and check reports, not
source-graph fragments, and it *is* registered in `parser-registry.json` — as the
manifest of the model-driven claim extraction it disciplines (see skill
10-doc-alignment), so that extraction's fallibility is visible in the registry.

## Growing the gallery

New tools enter the gallery by **promotion**, not during loop execution: when the loop
had to generate a parser (skill 03) and it proved solid, the agent may *propose*
promoting the cache copy into the gallery. A human reviews and commits it. Gallery
tools must meet the conventions above before promotion.
