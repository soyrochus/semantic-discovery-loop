# Skill 02 — Parser Broker

## Purpose

Select the best available parser or extractor for each artifact type detected in
`inventory.json`, and record every selection in `.work/semantic-loop/parser-registry.json`
(schema: `contracts/parser-registry.schema.json`).

## Selection order

For each artifact type, try in this exact order and stop at the first workable option:

1. **Project tooling** — deterministic tools already present in the repository
   (compilers, linters, framework CLIs) that can emit structure without side effects.
2. **Cached parser** — an existing parser under `.cache/scripts/parsers/` whose manifest
   matches the artifact type and whose `validation_status` is `validated`.
3. **Gallery tool** — a prepared parser from `.agent-loop/tools/` (see its README for
   the full protocol). Match `tool.json` against the artifact type, **copy** the tool
   folder to `.cache/scripts/parsers/<parser_id>/`, run its built-in smoke test
   (`parser.py --smoke`) *and* run it against real files from this repository, then
   register it with `origin: "gallery"` and its `gallery_source`. If the repository
   needs changes, adapt the **cache copy only** (never the gallery original), record
   what changed, register as `origin: "gallery-adapted"`, and re-validate.
4. **Standard local parser** — a language/format parser already available in the
   environment (e.g. Python's `xml.etree`, `json`, `csv`, `ast` modules; `jq`; `awk` for
   line-oriented formats). No installation.
5. **Simple structured extractor** — a small custom extractor for structured formats
   (regex/line-based for properties files, XML path walks for config), written under
   `.cache/scripts/parsers/` with a manifest.
6. **Generated parser** — last resort only; hand off to skill 03.

## Rules

- **Never accept a parser without manifest and validation.** Every entry in the registry
  needs a complete manifest; generated or custom parsers additionally need
  `validation_status: validated` (via smoke tests, see skill 03) before their output may
  feed final artefacts.
- Record the selection **origin** (`project-tooling`, `cached`, `gallery`,
  `gallery-adapted`, `standard-local`, `custom-extractor`, `generated`) for every
  artifact type, including how it is invoked.
- **One parser per artifact type.** Do not bundle parsing for multiple artifact types —
  or parsing plus graph building plus reporting — into a single monolithic script; that
  defeats reuse, per-parser validation, and honest manifests.
- Parsers must be read-only over the source tree (`writes_source_tree: false`, always)
  and must not require the network unless explicitly recorded and justified.
- Do not install dependencies without explicit user approval; prefer what is already
  available in the environment.
- If no parser can be selected or built for an artifact type, record that gap in the
  registry's manifest `known_limitations` and surface it in `uncertainties` /
  assumptions — do not silently drop the artifact type.
