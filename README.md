# semantic-discovery-loop

> **The AI proposes, the repository proves.** See a complete example run in
> [`examples/taskdesk-legacy-run/`](examples/taskdesk-legacy-run/).

`semantic-discovery-loop` is a small, file-based method for making an AI assistant study
a codebase without hand-waving. It asks the assistant to inspect a repository, build
durable artefacts, cite local evidence, verify its own claims, and iterate when the
evidence is weak.

It is not a service, database, SaaS product, or background daemon. It is a portable loop:
prompts, phase instructions, JSON contracts, prepared parsers, and a verifier. The same
method can be driven by Codex, Claude Code, GitHub Copilot, or another capable coding
assistant.

## Why this exists

LLMs are good at reading code, but a useful software-understanding tool needs more than
a plausible summary. It needs evidence, repeatable artefacts, and a way to say "I do
not know" when the repository does not prove a claim.

This repository demonstrates that pattern. A run produces:

- a deterministic **Source Construct Graph**: what literally exists in the code, built
  by parsers;
- an interpretive **Semantic Construct Graph**: what the code means at application
  level, such as routes, forms, flows, persistence, authorization, and integrations;
- a **Semantic Type Registry**: the vocabulary used by the semantic graph;
- optional **documentation claims** and **runtime journeys** as additional evidence
  layers; and
- an independent **verification report** that scores the result before the loop can
  call itself complete.

The loop verifies its own output against a scored gate and is only complete when every
score in `.work/semantic-loop/verification.json` is 8 or higher.

## Start here

You do not need to run anything to understand the project:

1. Read the finished example report:
   [`examples/taskdesk-legacy-run/semantic-loop/reports/application-structure.md`](examples/taskdesk-legacy-run/semantic-loop/reports/application-structure.md)
2. Inspect the generated semantic graph:
   [`examples/taskdesk-legacy-run/semantic-loop/semantic-graph.json`](examples/taskdesk-legacy-run/semantic-loop/semantic-graph.json)
3. Compare it with the source graph:
   [`examples/taskdesk-legacy-run/semantic-loop/source-graph.json`](examples/taskdesk-legacy-run/semantic-loop/source-graph.json)
4. Look at the verifier output:
   [`examples/taskdesk-legacy-run/semantic-loop/verification.json`](examples/taskdesk-legacy-run/semantic-loop/verification.json)

The bundled target is `taskdesk-legacy/`, a deliberately small but realistic Struts 1 /
JSP application backed by SQLite. It gives the loop enough real structure to discover
actions, views, validation, services, DAOs, tables, rules, and flows.

## What a run produces

All generated files live under `.work/semantic-loop/` during a local run. A completed
run normally includes:

| Artefact | What it answers |
| --- | --- |
| `inventory.json` | What files and artifact types are in scope? |
| `parser-registry.json` | Which parsers were used, where did they come from, and how were they validated? |
| `source-graph.json` | What concrete source constructs exist? |
| `semantic-types.json` | Which semantic vocabulary is registered for this run? |
| `semantic-graph.json` | What application concepts were discovered, and what proves them? |
| `doc-claims.json` | Which in-repository documentation claims were extracted and grounded? |
| `runtime/journeys.json` | What behaviour was observed by approved runtime journeys? |
| `verification.json` | Did the artefacts pass the independent quality gate? |
| `reports/application-structure.md` | Human-readable summary of the discovered application. |

## The guides

- [Semantic Discovery Loop Implementation Guide](docs/semantic-discovery-loop-implementation-guide.md) —
  structure, concepts, state machine, phases, artefacts, and extension points.
- [Semantic Layers Overview](docs/semantic-layers-overview.md) — the source and
  semantic layers, evidence classes, registered semantic types, and current local graph
  snapshot.

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
| `specs/` | Original loop specifications, extension notes, and implementation/evaluation records. |
| `docs/` | Human-oriented implementation guides for the loop and its semantic layers. |

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

## The loop-engineering pattern

This project is an implementation of the loop-engineering pattern described [in this article](https://addyosmani.com/blog/loop-engineering/): it replaces one-off prompting with a bounded, stateful, evidence-backed loop that writes durable artefacts, verifies its own output, and iterates until a defined quality gate passes.

It intentionally stays file-based and manually invoked, so it demonstrates the core loop mechanics without adding scheduled automations, worktree orchestration, connectors, or persistent background agents.

In regards to the features as descrobed in the article and currenlty not implementes, the project would gain the most from:


- Worktree-aware runs

  This would let multiple loop runs analyze different targets or revisions without trampling .work/semantic-loop and .cache/scripts. It fits the article well and would make experimentation safer.

- Run state summaries / triage memory

  The loop already has state.json, but a human-facing runs/index.md or reports/run-history.md could make repeated runs easier to compare: what changed, what failed, what improved, what remains unknown.


---

## Contributing & Principles of Participation

Pull requests are welcome. For major changes, open an issue first to discuss the approach.

Everyone is welcome to contribute: open issues, propose pull requests, share ideas, or improve documentation. Participation is open to all, regardless of background or viewpoint.

This project follows the [FOSS Pluralism Manifesto](./FOSS_PLURALISM_MANIFESTO.md), which affirms respect for people, freedom to critique ideas, and space for diverse perspectives.


## Copyright and License

Copyright © 2026 Iwan van der Kleijn

Licensed under the [MIT License](https://choosealicense.com/licenses/mit/). See the [LICENSE file](./LICENSE) in the repository.
