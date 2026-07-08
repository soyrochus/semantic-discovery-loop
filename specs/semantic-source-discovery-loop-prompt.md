# Semantic Source Discovery Loop — Human Explanation and AI Setup Prompt

## Purpose

This document defines a small, repository-local AI loop demonstrator for semantic source discovery.

It is meant to be read by a human and executed by an AI coding assistant such as GitHub Copilot, Codex, or Claude Code. The goal is not to build a full platform. The goal is to prove that a controlled AI loop can inspect an existing source code repository, generate deterministic discovery artefacts, propose semantic constructs grounded in evidence, verify its own output, and iterate until the result is acceptable.

The AI must create the full setup described in this document.

The setup must be file-based, tool-neutral, and simple enough to test on an existing codebase without introducing infrastructure dependencies.

Do not implement advanced storage, graph databases, SQLite indexing, vector search, long-running automation, or platform integration in this first version. Those belong in the “To be added later” section.

---

## Core idea

The demonstrator should implement a bounded AI loop with two layers of analysis.

The first layer is factual and deterministic. It discovers the source structure of the repository: files, languages, framework artefacts, classes, methods, configuration entries, routes, templates, dependencies, and other low-level constructs.

The second layer is semantic and interpretive. It maps source-level evidence to application-level concepts such as Application, Module, EntryPoint, Action, View, Component, DataObject, DataStore, Rule, Integration, Job, Configuration, SecurityElement, or UnknownSemanticConstruct.

The AI is allowed to infer meaning, but only if that meaning is grounded in local repository evidence.

The source repository remains the source of truth.

The AI may propose semantic constructs. The repository must prove them. The generated artefacts must preserve that proof.

---

## What this demonstrator must prove

The first successful demonstration should prove five things:

1. The AI can inventory a codebase without modifying source files.
2. The AI can create or reuse parsers/extractors in a local cache.
3. The AI can produce a deterministic Source Construct Graph.
4. The AI can produce a compact Semantic Construct Graph with evidence and provenance.
5. The AI refuses to call the result final until verification passes.

This is enough for a first concept validation.

The demonstrator should not try to solve all source code understanding. It should show that a disciplined, evidence-backed loop is feasible.

---

## Repository-local setup

Create the following folder and file structure:

```text
.agent-loop/
  README.md
  LOOP.md

  contracts/
    state.schema.json
    inventory.schema.json
    parser-registry.schema.json
    source-graph.schema.json
    semantic-types.schema.json
    semantic-graph.schema.json
    verification.schema.json

  skills/
    00-loop-conductor.md
    01-repository-inventory.md
    02-parser-broker.md
    03-parser-generator.md
    04-source-graph-builder.md
    05-semantic-type-discovery.md
    06-semantic-graph-builder.md
    07-verifier.md
    08-report-writer.md

  prompts/
    run-discovery-loop.md
    continue-discovery-loop.md
    verify-discovery-loop.md

  examples/
    expected-report-shape.md

  tools/
    README.md
    java-structure/      parser.py + tool.json
    xml-structure/       parser.py + tool.json
    struts-config/       parser.py + tool.json
    maven-pom/           parser.py + tool.json
    jsp-structure/       parser.py + tool.json
    properties-config/   parser.py + tool.json
    sql-ddl/             parser.py + tool.json
    sqlite-schema/       parser.py + tool.json
    verifier/            verify.py + tool.json

.github/
  copilot-instructions.md
  prompts/
    run-semantic-discovery-loop.prompt.md

.claude/
  skills/
    semantic-discovery-loop/
      SKILL.md

AGENTS.md

.cache/
  scripts/
    parsers/
      README.md

.work/
  semantic-loop/
    README.md
```

The `.agent-loop/` folder contains the neutral method.

The `.agent-loop/tools/` folder is a curated **tool gallery**: prepared, human-reviewed,
deterministic parsers/extractors (plus the independent verifier) that the loop copies
into the cache before considering improvised or generated parsers. Gallery originals
are read-only during loop execution.

The `.github/`, `.claude/`, and `AGENTS.md` files are adapters for specific AI coding assistants.

The `.cache/scripts/` folder is for reusable generated or discovered helper scripts, especially parsers and extractors. Gallery tools are copied here (`.cache/scripts/parsers/<parser_id>/`, verifier at `.cache/scripts/verifier-v1/`), adapted only in the copy, and validated before use.

The `.work/semantic-loop/` folder is for generated artefacts, state, verification files, and reports.

---

## Hard constraints

The AI must obey the following constraints.

The source tree is read-only.

Allowed write locations:

```text
.work/semantic-loop/**
.cache/scripts/**
.agent-loop/**
.github/**
.claude/**
AGENTS.md
```

During loop execution, after setup is complete, the AI may write only to:

```text
.work/semantic-loop/**
.cache/scripts/**
```

Forbidden actions:

```text
Modify source files.
Modify build files.
Modify dependency files.
Modify application configuration.
Install dependencies without explicit approval.
Run destructive commands.
Delete files outside .work/semantic-loop or .cache/scripts.
Invent facts about the application.
Treat web search as evidence that something exists in the local repository.
Mark the loop complete while verification fails.
```

If something cannot be determined, the AI must represent it as unknown, with evidence and assumptions.

---

## Loop model

The loop has two analysis layers.

```text
Layer 1 — Source Construct Graph
Deterministic, parser-derived, factual.

Layer 2 — Semantic Construct Graph
Interpretive, application-level, evidence-backed.
```

The loop also uses a semantic type registry.

```text
Semantic Type Registry
Small kernel vocabulary plus project-specific discovered constructs.
```

The source graph should contain factual nodes and edges, for example:

```text
File
Directory
Package
Class
Method
Function
Annotation
Import
XML element
Configuration entry
Route
Template
SQL statement
Build module
Dependency
```

The semantic graph should contain application-level nodes and edges, for example:

```text
Application
Module
EntryPoint
Interface
Flow
Action
View
Component
DataObject
DataStore
Rule
Integration
Job
Configuration
SecurityElement
UnknownSemanticConstruct
```

The semantic graph must never float free from evidence. Every semantic node must refer back to one or more source nodes or source artefacts.

---

## Semantic construct discipline

Do not create a huge fixed ontology.

Use a small kernel vocabulary first:

```text
Application
Module
EntryPoint
Interface
Flow
Action
View
Component
DataObject
DataStore
Rule
Integration
Job
Configuration
SecurityElement
UnknownSemanticConstruct
```

Before proposing a new semantic type, the AI must try the following sequence:

1. Map the construct to an existing accepted type.
2. Map the construct to a specialization of an existing type.
3. Use UnknownSemanticConstruct.
4. Only then propose a new semantic type.

A proposed semantic type must include:

```text
type_id
parent_type
definition
detection rules
required evidence
optional evidence
examples from this repository
confidence
status
```

Allowed statuses:

```text
candidate
proposed
validated
accepted
deprecated
```

Only accepted or validated semantic types may be used as stable constructs in the final report.

Candidate and proposed types may be listed, but they must be marked clearly as not yet accepted.

---

## Parser and extractor discipline

The AI should not immediately generate parsers.

Parser selection order:

1. Use existing deterministic project tooling if available.
2. Use an existing parser already present under `.cache/scripts/parsers/`.
3. Use a prepared gallery tool from `.agent-loop/tools/`: copy it to
   `.cache/scripts/parsers/<parser_id>/`, run its built-in smoke test plus real
   repository samples, adapt only the cache copy if needed, and register it with
   `origin: "gallery"` (or `"gallery-adapted"` with the adaptations recorded).
4. Use a standard local language or format parser if available.
5. Create a simple custom extractor for structured formats.
6. Generate a parser as a last resort.

New tools enter the gallery by promotion only: a generated parser that proved solid may
be proposed for the gallery, and a human reviews and commits it. The loop never writes
to `.agent-loop/tools/`.

Attribution rule: any code that produces source-graph nodes beyond plain structural
listing (File, Directory, DocumentationSection) must be a registered parser, and every
node's `parser_id` must name the tool that actually emitted it. Orchestration code must
not parse artifact content inline and must never stamp another parser's id on its own
output. No monolithic "suite" scripts: one parser per artifact type, and graph building
and verification must never share a file.

Every parser or extractor must have a manifest.

A generated parser must have at least smoke-test examples before it is accepted.

A generated parser must not be used for final artefacts unless it has passed validation.

A parser manifest should include:

```json
{
  "parser_id": "example-parser-v1",
  "artifact_type": "example",
  "input_patterns": ["*.example"],
  "script_path": ".cache/scripts/parsers/example/parser.py",
  "output_schema": "source-graph-fragment-v1",
  "validation_status": "validated",
  "tests": ["smoke-test-1"],
  "known_limitations": [],
  "writes_source_tree": false,
  "network_required": false
}
```

The exact implementation language of helper scripts is not prescribed. Prefer whatever is already available in the repository environment. Do not install dependencies without explicit approval.

---

## Generated artefacts

The loop should generate the following artefacts:

```text
.work/semantic-loop/
  state.json
  assumptions.json
  inventory.json
  parser-registry.json
  source-graph.json
  semantic-types.json
  semantic-graph.json
  doc-claims.json       (optional — documentation claims, when docs are in scope)
  runtime/journeys.json (optional — runtime journeys, when the approval-gated phase runs)
  verification.json
  reports/
    application-structure.md
```

The artefacts should be valid JSON where applicable.

The final report must be Markdown.

---

## State file

Create `.work/semantic-loop/state.json`.

The state file tracks the loop over iterations.

It should contain at least:

```json
{
  "loop_id": "semantic-source-discovery",
  "iteration": 0,
  "max_iterations": 6,
  "status": "initialized",
  "repo_fingerprint": null,
  "scope": "read-only semantic source discovery",
  "cache_dir": ".cache/scripts",
  "work_dir": ".work/semantic-loop",
  "last_completed_phase": null,
  "weakest_score": null,
  "next_action": null
}
```

The loop must read this file at the start of each run.

If it does not exist, create it.

---

## Assumptions file

Create `.work/semantic-loop/assumptions.json`.

All assumptions must be explicit.

Example:

```json
{
  "assumptions": [
    {
      "id": "assumption-001",
      "statement": "Files under src/main are assumed to be production source files.",
      "reason": "Detected conventional Maven-style structure.",
      "confidence": 0.8,
      "status": "active"
    }
  ]
}
```

Never hide assumptions inside the final report only. Store them in the assumptions file.

---

## Source graph

Create `.work/semantic-loop/source-graph.json`.

The source graph must describe deterministic source-level constructs.

Each node should include:

```json
{
  "id": "src:file:example",
  "layer": "source",
  "type": "File",
  "name": "Example.java",
  "path": "src/main/java/example/Example.java",
  "span": null,
  "hash": "optional-source-hash",
  "properties": {}
}
```

Each edge should include:

```json
{
  "id": "edge-001",
  "source_id": "src:class:Example",
  "target_id": "src:method:Example.run",
  "type": "contains",
  "confidence": 1.0,
  "properties": {}
}
```

The source graph should not contain speculative application meaning.

---

## Semantic type registry

Create `.work/semantic-loop/semantic-types.json`.

The semantic type registry defines the application-level concepts used in the semantic graph.

It should include the kernel vocabulary by default.

Example semantic type:

```json
{
  "type_id": "Action",
  "parent_type": null,
  "definition": "A user-triggered or system-triggered operation represented by source-level handlers, commands, routes, or equivalent mechanisms.",
  "detection_rules": [
    "Look for source constructs that represent executable application behaviour exposed through a route, command, event, controller, action mapping, or handler."
  ],
  "required_evidence": [
    "source-level handler or invocation mechanism"
  ],
  "optional_evidence": [
    "route",
    "view transition",
    "service call",
    "validation rule"
  ],
  "status": "accepted",
  "version": 1
}
```

For discovered project-specific semantic types, use the same structure.

---

## Semantic graph

Create `.work/semantic-loop/semantic-graph.json`.

The semantic graph must describe evidence-backed application-level constructs.

Example node:

```json
{
  "id": "sem:action:login",
  "layer": "semantic",
  "type": "Action",
  "name": "Login",
  "confidence": 0.91,
  "status": "accepted",
  "grounded_in": [
    {
      "source_node": "src:xml:struts-config.xml:/action[@path='/login']",
      "file": "WEB-INF/struts-config.xml",
      "span": {
        "start_line": 42,
        "end_line": 49
      },
      "evidence_type": "action-mapping"
    },
    {
      "source_node": "src:java:com.example.LoginAction.execute",
      "file": "src/main/java/com/example/LoginAction.java",
      "span": {
        "start_line": 21,
        "end_line": 73
      },
      "evidence_type": "handler-method"
    }
  ],
  "properties": {
    "route": "/login",
    "entrypoint": "LoginAction.execute"
  }
}
```

Every semantic node must have provenance.

If provenance is missing, verification must fail.

---

## Verification

Create `.work/semantic-loop/verification.json`.

The verifier must score the loop output from 0 to 10 on:

```text
inventory_coverage
parser_validity
source_graph_consistency
semantic_type_quality
semantic_graph_provenance
assertion_grounding
journey_corroboration
report_coverage
unknowns_handling
reproducibility
```

The loop may only be marked complete if all required scores are 8 or higher.

Verification must be independent and measured:

```text
Verification logic must not live in the same script that generates artefacts.
Use the prepared gallery verifier (.agent-loop/tools/verifier/), copied to
.cache/scripts/verifier-v1/.

Every score must be derived from named, measured checks — a bare asserted
score constant is a contract violation, whatever the number.

The verifier re-derives facts instead of trusting generator bookkeeping:
it recounts dangling edges, re-resolves every provenance reference into the
source graph and onto disk, recomputes inventory hashes, re-runs parser
smoke tests, double-runs parsers for determinism, and cross-checks every
node's parser_id against the registry and its input patterns.

A pass verdict counts only if the gate has been shown able to fail: the
verifier's mutation self-test corrupts copies of the artefacts (strip
provenance, add a dangling edge, forge a parser_id, break an inventory
path) and must catch every mutation before the real verdict is trusted.
```

The verification file should include (each score an object naming the checks it was
computed from, plus the self-test result):

```json
{
  "iteration": 1,
  "passed": false,
  "verifier": {
    "tool": "verifier-v1",
    "gallery_source": ".agent-loop/tools/verifier",
    "self_test": { "mutations_applied": 4, "mutations_detected": 4, "passed": true }
  },
  "scores": {
    "parser_validity": {
      "value": 7,
      "derived_from": ["reg-manifests-complete", "reg-smoke-tests", "reg-gallery-fidelity"],
      "measurement": "8 parsers; 1 smoke failure, 0 fidelity failures"
    }
  },
  "weakest_score": "parser_validity",
  "required_next_action": "Improve parser_validity: fix reg-smoke-tests (…).",
  "gate_failures": [
    "parser_validity below 8"
  ],
  "checks": [
    { "check": "reg-smoke-tests", "score": "parser_validity", "result": "fail", "detail": "…" }
  ]
}
```

(The full shape is defined in `.agent-loop/contracts/verification.schema.json`; the
`scores` object carries all ten dimensions.)

If any score is below 8:

```text
Print ITERATING.
Name the weakest score.
Define the next corrective action.
Do not claim completion.
```

The next iteration must improve the weakest score first.

---

## Final report

Create:

```text
.work/semantic-loop/reports/application-structure.md
```

The final report must contain:

```text
Application overview
Detected technology stack
Source inventory summary
Major modules/components
Entrypoints
Views/screens if detected
Controllers/actions/handlers if detected
Services/domain logic if detected
Data access and persistence if detected
External integrations if detected
Semantic type registry summary
Unresolved unknowns
Assumptions
Confidence and evidence notes
Limitations
```

The final report must not invent certainty.

If something is not known, say so.

Each important claim should refer to evidence from the generated artefacts.

---

## Loop execution process

When asked to run the loop, execute this process:

```text
1. Read .agent-loop/LOOP.md.
2. Read .agent-loop/skills/00-loop-conductor.md.
3. Load or create .work/semantic-loop/state.json.
4. Inventory the repository.
5. Detect artifact types.
6. Locate, validate, or generate parsers/extractors.
7. Build the Source Construct Graph.
8. Build or update the Semantic Type Registry.
9. Build the Semantic Construct Graph.
10. Verify all artefacts with the independent gallery verifier (including its
    mutation self-test).
11. If verification passes, write the final report.
12. If verification fails:
    a. print ITERATING;
    b. identify the weakest score;
    c. improve the weakest score first;
    d. update state.json;
    e. continue until verification passes or max_iterations is reached.
13. If max_iterations is reached, write a partial report with unresolved items.
```

---

## Required skill files

Create the following skill files.

### `.agent-loop/skills/00-loop-conductor.md`

This file must instruct the AI to coordinate the bounded loop.

It must include:

```text
Purpose:
Coordinate the semantic source-discovery loop.

Responsibilities:
- maintain state
- enforce allowed write locations
- coordinate phases
- stop source modification
- call verification
- identify weakest score
- trigger next iteration
- write final or partial report

Completion rule:
Never call the loop complete unless verification passes.
```

### `.agent-loop/skills/01-repository-inventory.md`

This file must instruct the AI to inspect repository structure.

It must include:

```text
Purpose:
Create inventory.json.

Responsibilities:
- list source files
- detect likely languages
- detect likely framework artefacts
- detect build files
- detect configuration files
- detect test files
- exclude generated/vendor/build artefacts where reasonable
- record uncertainty
```

### `.agent-loop/skills/02-parser-broker.md`

This file must instruct the AI to choose parsers and extractors.

It must include:

```text
Purpose:
Select the best available parser or extractor for each detected artifact type.

Selection order:
1. project tooling
2. cached parser
3. standard local parser
4. simple structured extractor
5. generated parser as last resort

Never accept a parser without manifest and validation.
```

### `.agent-loop/skills/03-parser-generator.md`

This file must instruct the AI to generate parsers only when needed.

It must include:

```text
Purpose:
Create minimal parsers or extractors when no suitable validated parser exists.

Rules:
- write only under .cache/scripts/parsers
- keep parsers small
- emit JSON
- include a manifest
- include smoke tests or examples
- document limitations
- do not modify source files
```

### `.agent-loop/skills/04-source-graph-builder.md`

This file must instruct the AI to build the deterministic source graph.

It must include:

```text
Purpose:
Create source-graph.json from inventory and parser results.

Rules:
- source graph is factual
- no speculative semantic meaning
- every node should have stable ID
- every edge should have type and confidence
- preserve file path and span where possible
```

### `.agent-loop/skills/05-semantic-type-discovery.md`

This file must instruct the AI to create or update the semantic type registry.

It must include:

```text
Purpose:
Create semantic-types.json.

Rules:
- start from small kernel vocabulary
- avoid ontology sprawl
- use UnknownSemanticConstruct when needed
- propose new types only after checking existing types
- web search may explain framework concepts but does not prove local existence
- every accepted type needs detection rules and required evidence
```

### `.agent-loop/skills/06-semantic-graph-builder.md`

This file must instruct the AI to build the semantic graph.

It must include:

```text
Purpose:
Create semantic-graph.json.

Rules:
- every semantic node must have provenance
- semantic nodes must map back to source nodes
- confidence must be explicit
- unknowns must be represented
- do not invent application behaviour
```

### `.agent-loop/skills/07-verifier.md`

This file must instruct the AI to verify the loop output.

It must include:

```text
Purpose:
Create verification.json.

Independence:
- use the prepared gallery verifier (.agent-loop/tools/verifier/)
- never put verification logic in artefact-generating code
- every score derived from named, measured checks — no asserted constants
- re-derive facts; do not trust generator bookkeeping
- run the mutation self-test before trusting a pass verdict

Scores:
- inventory_coverage
- parser_validity
- source_graph_consistency
- semantic_type_quality
- semantic_graph_provenance
- assertion_grounding
- journey_corroboration
- report_coverage
- unknowns_handling
- reproducibility

Gate:
No final completion unless every score is 8 or higher and the self-test passed.

If any score is below 8:
- print ITERATING
- identify weakest score
- define next corrective action
```

### `.agent-loop/skills/08-report-writer.md`

This file must instruct the AI to write the final or partial report.

It must include:

```text
Purpose:
Create reports/application-structure.md.

Rules:
- report only what is supported
- include unknowns and limitations
- include semantic type summary
- include evidence notes
- distinguish final report from partial report
```

---

## Required prompt files

Create the following prompt files.

### `.agent-loop/prompts/run-discovery-loop.md`

This file must instruct an AI to start the loop from scratch.

It should say:

```text
Run the semantic source-discovery loop defined in .agent-loop/LOOP.md.

Start by reading:
- .agent-loop/skills/00-loop-conductor.md
- .agent-loop/skills/01-repository-inventory.md

Create or reset .work/semantic-loop/state.json.

Respect all constraints:
- source tree is read-only
- write only to .work/semantic-loop and .cache/scripts during loop execution
- every semantic claim requires provenance
- no final completion unless verification passes
```

### `.agent-loop/prompts/continue-discovery-loop.md`

This file must instruct an AI to continue an existing loop.

It should say:

```text
Continue the semantic source-discovery loop.

Read:
- .work/semantic-loop/state.json
- .work/semantic-loop/verification.json if it exists
- .agent-loop/LOOP.md
- .agent-loop/skills/00-loop-conductor.md

If verification previously failed, improve the weakest score first.

Do not restart unless state is missing or invalid.
```

### `.agent-loop/prompts/verify-discovery-loop.md`

This file must instruct an AI to verify the current loop artefacts.

It should say:

```text
Verify the current semantic source-discovery artefacts.

Read:
- .work/semantic-loop/inventory.json
- .work/semantic-loop/parser-registry.json
- .work/semantic-loop/source-graph.json
- .work/semantic-loop/semantic-types.json
- .work/semantic-loop/semantic-graph.json
- .work/semantic-loop/doc-claims.json if present
- .work/semantic-loop/runtime/journeys.json if present
- .work/semantic-loop/reports/application-structure.md if present

Write:
- .work/semantic-loop/verification.json

Do not modify source files.
Do not rewrite artefacts except verification.json.
```

---

## GitHub Copilot adapter

Create:

```text
.github/copilot-instructions.md
.github/prompts/run-semantic-discovery-loop.prompt.md
```

The Copilot instructions file should explain that this repository contains a semantic discovery loop and that loop-specific work must follow `.agent-loop/LOOP.md`.

The prompt file should contain:

```markdown
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
- If verification fails, improve the weakest score first and continue until the gate passes or the iteration limit is reached.

Start by reading `.agent-loop/LOOP.md`.
```

---

## Claude Code adapter

Create:

```text
.claude/skills/semantic-discovery-loop/SKILL.md
```

The file should contain:

```markdown
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
```

---

## Codex adapter

Create:

```text
AGENTS.md
```

The file should contain:

```markdown
# AGENTS.md

This repository contains an AI semantic source-discovery loop.

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
```

---

## Main setup instruction for the AI

The AI coding assistant must now create the full setup described in this document.

Do not analyze the repository yet.

First create the reusable loop infrastructure.

Create all folders, Markdown files, prompt files, skill files, adapter files, README files, and JSON schemas.

The created setup must be sufficient for a later instruction such as:

```text
Run the semantic source-discovery loop on this repository.
```

At that later point, the AI should be able to execute the loop using the created files.

---

## Implementation quality requirements

The generated files should be practical, not decorative.

Each skill file must contain operational instructions, not vague principles.

Each JSON schema must be valid JSON Schema.

The README files must explain the purpose of their folder.

The setup must be understandable to a human reviewer.

The setup must also be executable by an AI coding assistant without additional explanation.

Avoid over-engineering.

Do not introduce a runtime framework.

Do not implement SQLite, vector search, graph databases, web automation, scheduling, or persistent background agents.

Keep this version as a prompt/skill-driven demonstrator.

---

## To be added later

The following items are explicitly out of scope for the first demonstrator.

They may be added after the file-based loop has proven useful on a real repository.

### SQLite-backed local graph/search store

A later version may add SQLite as a local execution index for:

```text
exact node lookup
full-text search
graph-like edge traversal
provenance queries
JSON filtering
gap analysis
```

JSON should remain the portable interchange format.

SQLite should be an index and query substrate, not necessarily the only source of truth.

### Rich graph traversal

A later version may add graph queries such as:

```text
Starting from this route, find controller, service, repository, tables, and view.
Find all views not reachable from an action.
Find all actions without a detected handler.
Find all data stores touched by multiple modules.
Find high-centrality UnknownSemanticConstruct nodes.
```

### Vector or embedding search

Vector search is not required for the first version.

It may be useful later for:

```text
searching comments and documentation
matching business terms to code constructs
finding similar semantic patterns
finding naming variants
```

It should not replace deterministic source evidence.

### Framework-specific semantic packs

A later version may add reusable semantic packs for:

```text
Struts/JSP
Spring MVC
Spring Boot
Angular
React
JPA/Hibernate
Batch frameworks
Legacy XML-driven applications
```

These should be optional extensions, not a large hardcoded ontology.

### Web-assisted framework understanding

A later version may allow controlled web search to help define framework concepts and detection heuristics.

The rule should remain:

```text
Web search may explain framework meaning.
Only local repository evidence may instantiate semantic nodes.
```

### Long-running automation

A later version may add scheduled or triggered execution.

The first version is manually invoked.

### Integration into a larger product

A later version may integrate the loop into a broader workbench or semantic analysis product.

The first version must remain standalone and repository-local.

---

## Summary

This document defines a bounded AI loop for semantic source discovery.

It creates a clear separation between:

```text
source syntax
static source facts
semantic interpretation
semantic type governance
verification
reporting
```

The AI is used as conductor, toolsmith, verifier, and analyst.

The repository remains the source of truth.

The loop is valid only if it produces durable artefacts, records assumptions, preserves provenance, handles unknowns explicitly, and refuses final completion until the verification gate passes.
