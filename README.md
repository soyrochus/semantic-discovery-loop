# semantic-discovery-loop

A bounded, evidence-backed AI agent loop that inspects a source repository **without
modifying it** and produces two artefacts:

- a deterministic **Source Construct Graph** — what literally exists in the code, built
  by parsers, and
- an interpretive, provenance-backed **Semantic Construct Graph** — what the code means
  (routes, forms, flows, persistence, authorization, …), where every claim points back to
  local source evidence.

The loop verifies its own output against a scored gate and is only complete when every
score in `.work/semantic-loop/verification.json` is 8 or higher.

## Repository layout

| Path | Purpose |
| --- | --- |
| `.agent-loop/` | The tool-neutral method: loop definition, contracts, skills, prompts, parser gallery. |
| `.agent-loop/LOOP.md` | The governing loop definition: layers, phases, constraints, verification gate. |
| `.agent-loop/contracts/` | JSON Schemas every generated artefact must validate against. |
| `.agent-loop/skills/` | Phase-specific operational instructions (`00` conducts, `01`–`08` execute phases). |
| `.agent-loop/prompts/` | Ready-to-use prompts to start, continue, or verify a loop run. |
| `.agent-loop/tools/` | Curated gallery of prepared parsers/extractors and the verifier. The loop copies these into `.cache/scripts/` and adapts the copies — never the originals. |
| `taskdesk-legacy/` + `db/` | Bundled example target (see below). |
| `examples/` | Committed output of a past loop run against the example, kept as a reference. |
| `docs/` | The loop's spec (`semantic-source-discovery-loop-prompt.md`) and evaluation (`loop-implementation-report.md`). |

## How to run the loop

The method is assistant-neutral; thin adapters exist for the major coding assistants,
and all of them delegate to `.agent-loop/`:

- **Claude Code** — invoke the `semantic-discovery-loop` skill
  (`.claude/skills/semantic-discovery-loop/SKILL.md`).
- **GitHub Copilot** — use `.github/prompts/run-semantic-discovery-loop.prompt.md`
  (repo-wide guardrails in `.github/copilot-instructions.md`).
- **Codex** — `AGENTS.md` points the agent at the loop.
- **Anything else** — paste `.agent-loop/prompts/run-discovery-loop.md` (first run) or
  `continue-discovery-loop.md` (resume) into the assistant.

## Output contract

The loop never modifies the source tree. All writes are restricted to:

- `.work/semantic-loop/**` — state, inventory, source graph, semantic graph, semantic
  types, assumptions, verification scores, and the final report under
  `.work/semantic-loop/reports/`.
- `.cache/scripts/**` — adapted parsers/extractors with manifests.

Both directories are gitignored; every run regenerates them. Each artefact must validate
against its schema in `.agent-loop/contracts/`.

## The bundled example: TaskDesk Legacy

`taskdesk-legacy/` is a synthetic but realistic legacy Struts 1 / JSP web application,
and `db/` holds the SQLite database it reads (`db/runtime-data/taskdesk-demo.sqlite`)
plus the schema and seed SQL. Together they are the default target the loop runs
against — a codebase with enough real structure (actions, forms, JSPs, DAOs, validation,
configuration) to exercise every phase.

`examples/taskdesk-legacy-run/` contains the full output of one completed run against
this example, so you can see what a finished run produces without running one yourself.

The example app is runnable (Java 8+, Maven, Tomcat 9); see `taskdesk-legacy/README.md`.
Running it is not required for the discovery loop — the loop only reads the source tree
and the SQLite file.

---

## Contributing & Principles of Participation

Pull requests are welcome. For major changes, open an issue first to discuss the approach.

Everyone is welcome to contribute: open issues, propose pull requests, share ideas, or improve documentation. Participation is open to all, regardless of background or viewpoint.

This project follows the [FOSS Pluralism Manifesto](./FOSS_PLURALISM_MANIFESTO.md), which affirms respect for people, freedom to critique ideas, and space for diverse perspectives.


## Copyright and License

Copyright © 2026 Iwan van der Kleijn

Licensed under the [MIT License](https://choosealicense.com/licenses/mit/). See the [LICENSE file](./LICENSE) in the repository.
