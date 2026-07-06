# Prompt — Verify the discovery loop artefacts

Verify the current semantic source-discovery artefacts, following
`.agent-loop/skills/07-verifier.md`.

Use the prepared, independent gallery verifier — do not improvise verification logic
and never score by assertion:

```bash
python3 .cache/scripts/verifier-v1/verify.py --work .work/semantic-loop
```

(Copy it from `.agent-loop/tools/verifier/` first if the cache copy is missing, and
run its smoke test: `python3 verify.py --smoke`.)

The verifier reads:

- `.work/semantic-loop/inventory.json`
- `.work/semantic-loop/parser-registry.json`
- `.work/semantic-loop/source-graph.json`
- `.work/semantic-loop/semantic-types.json`
- `.work/semantic-loop/semantic-graph.json`
- `.work/semantic-loop/assumptions.json` and `state.json`
- `.work/semantic-loop/reports/application-structure.md` if present

and writes:

- `.work/semantic-loop/verification.json` (shape:
  `.agent-loop/contracts/verification.schema.json`)

All eight dimensions are scored 0–10 from measured, named checks; its mutation
self-test must pass before any verdict is trusted. `passed: true` requires every score
value >= 8. On failure it prints `ITERATING`, names the weakest score, and defines the
next corrective action.

Do not modify source files.
Do not rewrite artefacts except `verification.json`.
