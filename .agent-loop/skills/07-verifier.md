# Skill 07 — Verifier

## Purpose

Create `.work/semantic-loop/verification.json` (schema:
`contracts/verification.schema.json`) by auditing all generated artefacts. The verifier
judges; it does not repair. It writes only `verification.json`.

## Independence rules

A verifier the generator wrote for itself, with scores it chose, is not verification.

- **Use the prepared gallery verifier** (`.agent-loop/tools/verifier/`): copy it to
  `.cache/scripts/verifier-v1/` (gallery protocol), run its smoke test, then run it
  against the artefacts. Only if the gallery verifier cannot cover a repository-specific
  dimension may it be extended — in the cache copy, with the change recorded.
- **Never put verification logic in the same file as artefact generation.** The
  verifier reads artefacts and the repository; it shares no code path with the builders.
- **Measure, don't assert.** Every score is `{value, derived_from, measurement}`;
  `value` comes from a fixed formula over the named checks in `checks[]`. Writing a
  literal score constant is a contract violation, whatever the number.
- **Re-derive, don't trust.** Recount dangling edges; re-resolve every `grounded_in`
  reference into `source-graph.json` and onto disk; recompute inventory hashes; re-run
  every registered parser's `--smoke`; double-run parsers on repository samples for
  determinism; compare gallery copies byte-for-byte when `adaptations` is empty;
  cross-check every node's `parser_id` against the registry and its input patterns.
- **Prove the gate can fail before trusting a pass.** Run the mutation self-test
  (corrupt copies of the artefacts — strip provenance, add a dangling edge, forge a
  `parser_id`, break an inventory path, forge a documentation claim's excerpt,
  promote a node to accepted on asserted evidence alone — and require the gate to
  catch each one). A verdict without a passing self-test is not a verdict. Record the
  self-test result in `verification.json` under `verifier.self_test`.

## Scores

Score each dimension 0–10 from concrete checks (each check names the dimension it
feeds):

- **inventory_coverage** — every tracked file in scope is inventoried or explicitly
  explained (exclusions/uncertainties); inventoried files exist on disk; recorded
  hashes match recomputed ones.
- **parser_validity** — complete manifests; every parser `validated`; smoke tests
  re-run green; gallery copies with no claimed adaptations are byte-identical to their
  gallery source; selection order honored (a matching gallery tool skipped for an
  improvised extractor, or a monolithic multi-type script, caps this below 8).
- **source_graph_consistency** — schema-valid; stable `src:` ids, no duplicates; no
  dangling edge endpoints; sane spans; **every `parser_id` resolves to a registered
  parser whose input patterns match the node's path** (null only for structural
  File/Directory/DocumentationSection nodes).
- **semantic_type_quality** — kernel present; used types are accepted/validated;
  detection rules and required evidence operational, not vague; no ontology sprawl.
- **semantic_graph_provenance** — every semantic node has non-empty `grounded_in`;
  every `source_node` resolves; cited files exist and spans fit within them;
  confidences explicit in [0,1]; evidence `kind`s valid. **Any ungrounded node,
  unresolved reference, or node validated/accepted on asserted evidence alone caps
  this score at 5** (the authority rule in LOOP.md — documentation never proves
  existence).
- **assertion_grounding** — documentation claims re-resolved onto the repository:
  every claim in `doc-claims.json` cites an in-repo file, its span fits, its verbatim
  excerpt occurs within that span, statuses are definite
  (`confirmed | contradicted | unverifiable`), confirmed claims map to nodes that
  exist, and every asserted provenance entry / node conflict links back to a real
  claim. When the doc-alignment phase did not run, an absent `doc-claims.json` is a
  recorded unknown, not a failure — but asserted evidence with no claims artefact
  behind it fails.
- **report_coverage** — required sections present; status marker (`FINAL`/`PARTIAL`)
  consistent with the gate outcome — a report claiming FINAL while the gate fails caps
  this at 7.
- **unknowns_handling** — UnknownSemanticConstruct nodes, inventory uncertainties, and
  well-formed explicit assumptions present rather than silently resolved gaps.
- **reproducibility** — one `repo_fingerprint` across artefacts matching git HEAD;
  parsers produce identical output on double runs; assumptions stored as an artefact,
  not only prose.

## Gate

**No final completion unless every score is 8 or higher AND the self-test passed.**
Set `passed: true` only in that case, with `gate_failures: []`.

If any score is below 8:

- print `ITERATING`;
- identify the weakest score (`weakest_score`);
- define the next corrective action (`required_next_action`) — one concrete,
  actionable instruction naming the failing checks, not a restatement of the problem;
- list every failing dimension in `gate_failures`;
- set `passed: false`.

Do not inflate scores to pass the gate. A verifier that rubber-stamps defeats the loop
— and a hardcoded score is a rubber stamp even when it happens to be accurate.
