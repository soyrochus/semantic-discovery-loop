# Skill 06 — Semantic Graph Builder

## Purpose

Create `.work/semantic-loop/semantic-graph.json` (schema:
`contracts/semantic-graph.schema.json`): the Layer 2 graph of evidence-backed,
application-level constructs.

## Rules

- **Every semantic node must have provenance.** `grounded_in` is mandatory and
  non-empty: each entry names the evidence `file`, a line `span` where applicable, an
  `evidence_type`, and ideally the `source_node` id it corresponds to. A semantic node
  without provenance is a defect; the verifier must fail it.
- **Semantic nodes must map back to source nodes.** Prefer `source_node` references
  into `source-graph.json` over bare file paths; use bare paths only for artefacts not
  represented as nodes, and note why.
- **Use only registered types.** `type` must be a `type_id` from
  `semantic-types.json`. Nodes typed with `candidate`/`proposed` types inherit that
  status and must not be presented as stable.
- **Confidence must be explicit** on every node and edge, 0.0–1.0, reflecting how
  strongly the local evidence supports the interpretation. Multiple independent evidence
  sources justify higher confidence; a single heuristic match does not.
- **Unknowns must be represented.** Constructs that exist but resist interpretation
  become `UnknownSemanticConstruct` nodes (with provenance). Unresolved aspects of an
  otherwise-classified node go in its `unknowns` array. Do not omit what you cannot
  explain.
- **Do not invent application behaviour.** No node or edge may assert behaviour
  (triggers, reads-from, writes-to, integrates-with) that is not visible in local source
  evidence. Framework knowledge from the web may guide where to look; it never
  substitutes for evidence.
- Edge endpoints must reference existing semantic node ids; edges asserting non-obvious
  relations should carry their own `grounded_in` evidence.
- Use stable ids: `sem:<type-lowercase>:<name>`, reproducible across runs.
