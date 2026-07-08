# semantic-discovery-loop

> **The AI proposes, the repository proves.** See a complete example run in
> [`examples/taskdesk-legacy-run/`](examples/taskdesk-legacy-run/).

A bounded, evidence-backed AI agent loop that inspects a source repository **without
modifying it** and produces two artefacts:

- a deterministic **Source Construct Graph** — what literally exists in the code, built
  by parsers, and
- an interpretive, provenance-backed **Semantic Construct Graph** — what the code means
  (routes, forms, flows, persistence, authorization, …), where every claim points back to
  local source evidence.

The loop verifies its own output against a scored gate and is only complete when every
score in `.work/semantic-loop/verification.json` is 8 or higher.

## The articles

This repository is the working example for a two-part article series,
*From AI Loops to Semantic Software Understanding*:

1. [From Prompts to Loops](https://www.linkedin.com/pulse/from-ai-loops-semantic-software-understanding-1-2-iwan-van-der-kleijn-i8jie/) —
   making AI work verifiable: bounded loops, durable artefacts, and an independent
   verification gate.
2. [Beyond ASTs — Why AI needs a semantic layer to understand software](https://www.linkedin.com/pulse/from-ai-loops-semantic-software-understanding-2-iwan-van-der-kleijn-nspee/) —
   the two-layer source/semantic model the loop builds.

## Repository layout

| Path | Purpose |
| --- | --- |
| `.agent-loop/` | The tool-neutral method: loop definition, contracts, skills, prompts, parser gallery. |
| `.agent-loop/LOOP.md` | The governing loop definition: layers, phases, constraints, verification gate. |
| `.agent-loop/contracts/` | JSON Schemas every generated artefact must validate against. |
| `.agent-loop/skills/` | Phase-specific operational instructions (`00` conducts, `01`–`08` build the static graphs and report, `09` walks runtime journeys, `10` aligns documentation). |
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
  types, documentation claims, runtime journeys (under `runtime/`), assumptions,
  verification scores, and the final report under `.work/semantic-loop/reports/`.
- `.cache/scripts/**` — adapted parsers/extractors with manifests.

Both directories are gitignored; every run regenerates them. Each artefact must validate
against its schema in `.agent-loop/contracts/`.

Contract version 2 adds two optional, degradable evidence layers on top of the static
parse: **documentation alignment** (skill 10, `asserted` evidence — claims extracted
from in-repo docs, naming and intent only) and the **runtime journey phase** (skill 09,
`observed` evidence). The runtime phase *executes* the target and therefore requires
**explicit user approval**; it runs the app against a disposable copy of its database in
a sandbox under `.work/semantic-loop/runtime/`, leaving the source tree — including any
committed database — byte-identical. Both layers are degradable: absent approval, docs,
or a startable target, the loop completes static-only and records the missing layer as an
explicit unknown. The verifier scores ten dimensions; all must be ≥ 8.

### Running the optional runtime journey phase

The static and documentation layers only *read* the repository — no build or run needed.
The runtime journey phase (skill 09) is the exception: it drives the live app with
Playwright to gather `observed` evidence (instantiating `Flow` nodes, corroborating
statically-derived routes, and behaviourally testing access-control and validation
rules). It needs a one-time environment, none of which is committed to the repo:

1. Build and deploy the example app to Tomcat 9 — see `taskdesk-legacy/README.md`.
   On Linux, the tested setup is system OpenJDK plus Maven and Tomcat 9 under `~/opt`.
2. Install the browser driver: `npm install playwright && npx playwright install chromium`.
3. Start Tomcat against a **disposable copy** of the database (never the committed file),
   e.g. `TASKDESK_DB_URL=jdbc:sqlite:/abs/path/.work/semantic-loop/runtime/db/taskdesk-demo.sqlite`.
4. Walk the journeys with the phase's script (see the committed reference at
   [`examples/…/runtime/scripts/walk-journeys.mjs`](examples/taskdesk-legacy-run/semantic-loop/runtime/scripts/walk-journeys.mjs)),
   then run the verifier.

The walk records **normalized, replayable traces** (no timestamps or session ids, so
re-runs compare byte-equal) and screenshots. Runtime evidence only ever confirms and
adds — it never vetoes a statically-grounded node; a runtime contradiction is recorded
as a conflict, and behaviour the phase did not probe (e.g. database write side-effects)
is recorded as an explicit unknown rather than assumed. See the
[example run's report](examples/taskdesk-legacy-run/semantic-loop/reports/application-structure.md)
for what this produces, including its "what runtime did NOT verify" section.

## The bundled example: TaskDesk Legacy

`taskdesk-legacy/` is a synthetic but realistic legacy Struts 1 / JSP web application,
and `db/` holds the SQLite database it reads (`db/runtime-data/taskdesk-demo.sqlite`)
plus the schema and seed SQL. Together they are the default target the loop runs
against — a codebase with enough real structure (actions, forms, JSPs, DAOs, validation,
configuration) to exercise every phase.

`examples/taskdesk-legacy-run/` contains the full output of one completed run against
this example, so you can see what a finished run produces without running one yourself.

The example app is runnable (Java 8+, Maven, Tomcat 9); see `taskdesk-legacy/README.md`.
Running it is not required for the static and documentation layers — those only read the
source tree and the SQLite file — but it *is* what the optional runtime journey phase
drives (see "Running the optional runtime journey phase" above).

---

## Contributing & Principles of Participation

Pull requests are welcome. For major changes, open an issue first to discuss the approach.

Everyone is welcome to contribute: open issues, propose pull requests, share ideas, or improve documentation. Participation is open to all, regardless of background or viewpoint.

This project follows the [FOSS Pluralism Manifesto](./FOSS_PLURALISM_MANIFESTO.md), which affirms respect for people, freedom to critique ideas, and space for diverse perspectives.


## Copyright and License

Copyright © 2026 Iwan van der Kleijn

Licensed under the [MIT License](https://choosealicense.com/licenses/mit/). See the [LICENSE file](./LICENSE) in the repository.
