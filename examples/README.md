# examples/

Worked examples of semantic-discovery-loop output.

## taskdesk-legacy-run/

The committed output of one complete loop run against the bundled example repo
(`taskdesk-legacy/` + `db/`), kept as a reference for what a finished run looks like:

- `semantic-loop/` — the artefacts the loop wrote under `.work/semantic-loop/`:
  inventory, source graph, semantic graph, semantic types, assumptions, verification
  scores, state, and the final report under `reports/`.
- `cache-scripts/` — the adapted parsers and verifier the loop staged under
  `.cache/scripts/` during that run.

Live runs regenerate everything under `.work/` and `.cache/`, which are gitignored;
nothing in this directory is read by the loop. The canonical parser gallery lives in
`.agent-loop/tools/`, and `.agent-loop/examples/expected-report-shape.md` describes the
expected report shape.
