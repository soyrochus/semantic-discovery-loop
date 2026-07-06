---
name: semantic-discovery-loop
description: Run the repository semantic discovery loop
agent: agent
tools: ['search/codebase', 'runCommands', 'editFiles']
---

Run the semantic source-discovery loop defined in:

- `.agent-loop/LOOP.md`
- `.agent-loop/skills/00-loop-conductor.md`

Use the skills in `.agent-loop/skills/` as operational instructions.

Respect these hard constraints:
- Do not modify source files.
- Write only to `.work/semantic-loop/**` and `.cache/scripts/**` during loop execution.
- Prefer deterministic local evidence over interpretation.
- Every semantic claim must have provenance.
- If verification fails, improve the weakest score first and continue until the gate
  passes or the iteration limit is reached.

Start by reading `.agent-loop/LOOP.md`.
