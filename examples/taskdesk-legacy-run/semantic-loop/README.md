# .work/semantic-loop/

Generated artefacts of the semantic source-discovery loop (see `.agent-loop/LOOP.md`).
Everything in this folder is produced by the loop and may be regenerated; nothing here
is hand-maintained except this README.

Expected contents after a run:

```text
state.json            loop state across iterations       (contracts/state.schema.json)
assumptions.json      all explicit assumptions
inventory.json        repository inventory                (contracts/inventory.schema.json)
parser-registry.json  parser/extractor manifests          (contracts/parser-registry.schema.json)
source-graph.json     Layer 1 — deterministic source facts (contracts/source-graph.schema.json)
semantic-types.json   semantic type registry              (contracts/semantic-types.schema.json)
semantic-graph.json   Layer 2 — evidence-backed semantics (contracts/semantic-graph.schema.json)
doc-claims.json       documentation claims — optional     (contracts/doc-claims.schema.json)
verification.json     gate scores, 8+ required on all     (contracts/verification.schema.json)
reports/
  application-structure.md   final (or clearly marked partial) report
```

Schema paths are relative to `.agent-loop/`. The loop is complete only when every score
in `verification.json` is 8 or higher.
