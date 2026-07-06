# Skill 03 — Parser Generator

## Purpose

Create minimal parsers or extractors when no suitable validated parser exists (selection
options 1–5 in skill 02 exhausted — in particular, only after checking the gallery in
`.agent-loop/tools/` for a tool that could be copied and adapted instead).

## Rules

- **Write only under `.cache/scripts/parsers/`**, one subfolder per parser, e.g.
  `.cache/scripts/parsers/struts-config/parser.py`.
- **Keep parsers small.** One artifact type per parser. Extract only what the source
  graph needs (identifiers, structure, spans, relations) — not a full language grammar.
- **Emit JSON** on stdout or to a given output path, conforming to the fragment shape
  used by `contracts/source-graph.schema.json` (nodes and edges with stable ids, paths,
  spans).
- **Include a manifest** (see `contracts/parser-registry.schema.json`) next to the
  parser or directly in `parser-registry.json`, with `origin: generated`.
- **Include smoke tests or examples**: at least one real input from this repository (or
  a minimal representative sample stored beside the parser) plus the expected output
  shape. Run the smoke test; only after it passes may `validation_status` move from
  `unvalidated` → `smoke-tested` → `validated`.
- **Document limitations** in the manifest's `known_limitations` (e.g. "does not handle
  multi-line attributes", "ignores comments").
- **Do not modify source files.** Parsers read the source tree and write only to stdout,
  `.cache/scripts/**`, or `.work/semantic-loop/**`.
- Use a language already available in the environment (check before writing; prefer
  Python or POSIX shell if present). Never install dependencies without explicit
  approval.
- A generated parser **must not be used for final artefacts unless it has passed
  validation**. Unvalidated output may be used only to draft, and must be regenerated
  after validation.
- **Parse properly, or say you didn't.** Prefer a real parse (a masking lexer, a
  stdlib parser, structural matching with brace/paren balancing) over naive line
  regexes; the gallery tools in `.agent-loop/tools/` show the expected standard. If
  only a lexical extractor is feasible, its manifest must say so in
  `known_limitations` — it must not present itself as a full parser.
- **Follow the gallery conventions** (`.agent-loop/tools/README.md`): one artifact type
  per tool, `parser.py --smoke` self-test, JSON source-graph fragments, honest
  `tool.json`-style metadata. This keeps generated parsers eligible for **promotion**:
  after the loop, a generated parser that proved solid may be *proposed* for inclusion
  in the gallery — a human reviews and commits it; the loop itself never writes to
  `.agent-loop/tools/`.
