# examples/

Worked examples of semantic-discovery-loop output.

## taskdesk-legacy-run/

The committed output of one complete loop run against the bundled example repo
(`taskdesk-legacy/` + `db/`), kept as a reference for what a finished run looks like:

- `semantic-loop/` — the artefacts the loop wrote under `.work/semantic-loop/`:
  inventory, source graph, semantic graph, semantic types, documentation claims,
  runtime journeys (`runtime/journeys.json` plus normalized traces and screenshots
  under `runtime/traces/` and the journey script under `runtime/scripts/`),
  assumptions, verification scores, state, and the final report under `reports/`.
- `cache-scripts/` — the adapted parsers and verifier the loop staged under
  `.cache/scripts/` during that run.

The runtime layer's `node_modules/` and the disposable database copy under
`runtime/db/` are excluded from the committed example (heavy and disposable; the
source database stays byte-identical across a run).

Live runs regenerate everything under `.work/` and `.cache/`, which are gitignored;
nothing in this directory is read by the loop. The canonical parser gallery lives in
`.agent-loop/tools/`, and `.agent-loop/examples/expected-report-shape.md` describes the
expected report shape.
