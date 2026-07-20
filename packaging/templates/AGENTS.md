# AGENTS.md

This repository, {{PROJECT_NAME}}, contains a semantic source-discovery loop.

When asked to run the semantic discovery loop:

1. Read `.agent-loop/LOOP.md`.
2. Follow `.agent-loop/skills/00-loop-conductor.md`.
3. Use the phase-specific skills in `.agent-loop/skills/`.
4. Write artefacts only under `.work/semantic-loop/` and `.cache/scripts/`.
5. Do not modify source files.
6. Do not install dependencies unless explicitly requested.
7. Every semantic claim must be grounded in local source evidence.
8. If verification fails, fix the weakest score first.
9. Do not call the task complete until all verification gate criteria pass.