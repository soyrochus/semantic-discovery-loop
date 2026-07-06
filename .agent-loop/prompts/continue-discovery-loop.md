# Prompt — Continue the discovery loop

Continue the semantic source-discovery loop.

Read:

- `.work/semantic-loop/state.json`
- `.work/semantic-loop/verification.json` if it exists
- `.agent-loop/LOOP.md`
- `.agent-loop/skills/00-loop-conductor.md`

If verification previously failed, improve the weakest score first — follow the
`required_next_action` recorded in `verification.json` (mirrored in
`state.json.next_action`) before anything else.

Do not restart unless state is missing or invalid. If `state.json` is missing or does
not conform to `.agent-loop/contracts/state.schema.json`, fall back to
`.agent-loop/prompts/run-discovery-loop.md`.

All constraints from `LOOP.md` remain in force: read-only source tree, writes only to
`.work/semantic-loop/**` and `.cache/scripts/**`, provenance on every semantic claim,
and no completion while any verification score is below 8.
