---
name: semantic-discovery-loop
description: Run a bounded semantic discovery loop over a source repository, producing source and semantic graphs with evidence-backed reporting.
---

# Semantic Discovery Loop

Use this skill to inspect an existing codebase without modifying source files.

Primary instructions:
- Read `.agent-loop/LOOP.md`.
- Use `.agent-loop/skills/00-loop-conductor.md` as the governing procedure.
- Use the remaining `.agent-loop/skills/*.md` files as phase-specific instructions.

Allowed writes:
- `.work/semantic-loop/**`
- `.cache/scripts/**`

Forbidden:
- modifying source files
- installing dependencies without explicit approval
- inventing unsupported semantic constructs
- marking the loop complete while any verification score is below 8

Final output:
- `.work/semantic-loop/reports/application-structure.md`
- `.work/semantic-loop/verification.json`
