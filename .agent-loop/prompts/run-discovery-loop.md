# Prompt — Run the discovery loop (fresh start)

Run the semantic source-discovery loop defined in `.agent-loop/LOOP.md`.

Start by reading:

- `.agent-loop/skills/00-loop-conductor.md`
- `.agent-loop/skills/01-repository-inventory.md`

Create or reset `.work/semantic-loop/state.json` (shape:
`.agent-loop/contracts/state.schema.json`), then execute the phases in order using the
skills in `.agent-loop/skills/`.

Respect all constraints:

- the source tree is read-only;
- write only to `.work/semantic-loop/**` and `.cache/scripts/**` during loop execution;
- every semantic claim requires provenance grounded in local repository evidence;
- represent what cannot be determined as unknown, with evidence and assumptions;
- no final completion unless verification passes (every score in
  `.work/semantic-loop/verification.json` is 8 or higher).

If verification fails, print `ITERATING`, name the weakest score, define the next
corrective action, and continue until the gate passes or `max_iterations` is reached.
