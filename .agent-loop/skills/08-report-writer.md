# Skill 08 — Report Writer

## Purpose

Create `.work/semantic-loop/reports/application-structure.md`: the human-readable
outcome of the loop. See `.agent-loop/examples/expected-report-shape.md` for the
expected shape.

## Rules

- **Report only what is supported.** Every important claim must trace to the generated
  artefacts (semantic graph nodes, source graph nodes, inventory entries) — cite node
  ids and file paths inline. The report must not invent certainty; if something is not
  known, say so.
- **Include unknowns and limitations.** Dedicated sections for unresolved unknowns
  (UnknownSemanticConstruct nodes and open `uncertainties`) and for the limitations of
  this analysis (parser gaps, unexamined areas, low-confidence regions).
- **Include the semantic type summary**: which types were used, which were proposed and
  at what status, and clearly mark `candidate`/`proposed` types as not yet accepted.
- **Include evidence notes**: for the main claims, note the evidence kind and location
  (e.g. "grounded in action mapping, `WEB-INF/struts-config.xml:42–49`") and the
  confidence recorded in the graph.
- **Distinguish final report from partial report.** The first line under the title must
  state either `Status: FINAL — verification passed (all scores ≥ 8)` or
  `Status: PARTIAL — max iterations reached with gate failures: <list>`. A partial
  report additionally lists the unresolved items and the corrective actions that were
  still pending.
- Include the assumptions (from `assumptions.json`) that materially shape the report —
  but the assumptions file remains the source of record; never document an assumption
  only in the report.

## Required sections

```text
Application overview
Detected technology stack
Source inventory summary
Major modules/components
Entrypoints
Views/screens (if detected)
Controllers/actions/handlers (if detected)
Services/domain logic (if detected)
Data access and persistence (if detected)
External integrations (if detected)
Semantic type registry summary
Unresolved unknowns
Assumptions
Confidence and evidence notes
Limitations
```

"If detected" sections that found nothing must still appear, stating that nothing was
detected and with what confidence — absence of evidence is itself a finding.
