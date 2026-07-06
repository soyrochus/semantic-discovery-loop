# .agent-loop/

This folder contains the **tool-neutral method** for the semantic source-discovery loop:
a bounded, evidence-backed AI loop that inspects this repository without modifying it and
produces a deterministic Source Construct Graph plus an interpretive, provenance-backed
Semantic Construct Graph.

Nothing in this folder is specific to any one AI coding assistant. Assistant-specific
adapters live in `.github/` (Copilot), `.claude/` (Claude Code), and `AGENTS.md` (Codex);
all of them delegate to the files here.

## Contents

| Path | Purpose |
| --- | --- |
| `LOOP.md` | The governing loop definition: layers, phases, constraints, verification gate. |
| `contracts/` | JSON Schemas for every generated artefact. Artefacts must validate against these. |
| `tools/` | Curated gallery of prepared parsers/extractors. The loop copies these into `.cache/scripts/parsers/` and adapts the copies — never the originals. |
| `skills/` | Phase-specific operational instructions (`00` conducts, `01`–`08` execute phases). |
| `prompts/` | Ready-to-use prompts to start, continue, or verify a loop run. |
| `examples/` | Shape references for expected outputs (e.g. the final report). |

## Where things get written

The loop never modifies the source tree. During loop execution, writes are restricted to:

- `.work/semantic-loop/**` — state, artefacts, verification, reports
- `.cache/scripts/**` — reusable parsers/extractors with manifests

## How to run it

Give an AI assistant the contents of `prompts/run-discovery-loop.md` (first run) or
`prompts/continue-discovery-loop.md` (resume). The loop is complete only when every
score in `.work/semantic-loop/verification.json` is 8 or higher.
