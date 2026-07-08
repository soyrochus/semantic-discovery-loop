# LOOP.md — Semantic Source-Discovery Loop

**Contract version 2.** Version 1 admitted static evidence only ("no web automation").
Version 2 admits the sandboxed, approval-gated **runtime journey phase** (skill 09,
`observed` evidence) alongside documentation alignment (skill 10, `asserted` evidence).
This is a renegotiated contract, not an incremental tweak — the trust-boundary,
sandbox, and reproducibility rules below are part of the version change.

This file is the governing definition of the loop. Every run starts by reading this file
and `skills/00-loop-conductor.md`. The skills in `skills/` are the operational
instructions for each phase. The schemas in `contracts/` define the required shape of
every generated artefact.

## Purpose

Inspect an existing source repository without modifying it, and produce:

1. **Layer 1 — Source Construct Graph** (`source-graph.json`): deterministic,
   parser-derived, factual. Files, classes, methods, configuration entries, routes,
   templates, SQL, dependencies. No speculative application meaning.
2. **Layer 2 — Semantic Construct Graph** (`semantic-graph.json`): interpretive,
   application-level, evidence-backed. Concepts such as Application, Module, EntryPoint,
   Action, View, DataObject, DataStore, Integration. Every semantic node must be grounded
   in one or more source nodes or source artefacts. **The repository is the source of
   truth: the AI may propose semantic constructs, the repository must prove them.**

A **Semantic Type Registry** (`semantic-types.json`) governs the vocabulary: a small
kernel plus project-specific discovered types, each with detection rules and required
evidence.

## Hard constraints

- The source tree is **read-only**.
- During loop execution, write only to `.work/semantic-loop/**` and `.cache/scripts/**`.
- Never modify source files, build files, dependency files, or application configuration.
- Never install dependencies without explicit approval.
- **Never execute the target application without explicit user approval.** The runtime
  journey phase (skill 09) runs the target — pointed at an arbitrary repository that is
  arbitrary code execution. Approval must be obtained per run and recorded in
  `runtime/journeys.json`; the app runs against a **disposable copy** of its runtime
  database in a sandboxed directory under `.work/semantic-loop/runtime/`, and the
  source tree — including any committed database file — stays byte-identical
  (verifier-checked).
- Never run destructive commands.
- Never delete files outside `.work/semantic-loop/` or `.cache/scripts/`.
- Never invent facts about the application. If something cannot be determined, represent
  it as **unknown**, with evidence and assumptions.
- Web search may explain framework concepts, but is never evidence that something exists
  in this repository. Only local repository evidence may instantiate semantic nodes.
  Documentation counts as evidence only when it is a file inside the repository;
  external sources (wikis, Confluence, tickets) must first be snapshotted into the
  repository, with retrieval date recorded, before the loop may cite them.
- Never mark the loop complete while verification fails.

## Evidence classes and the authority rule

Every provenance entry in the semantic graph carries an evidence `kind`
(`semantic-graph.schema.json`); an absent `kind` means `parsed`:

```text
kind        source                                          answers
parsed      deterministic parser output over the tree       what exists
observed    recorded from executing the target (skill 09)   what happens
asserted    claims extracted from in-repo documentation     what is meant
```

For **existence** claims the authority order is `parsed > observed > asserted`:

- `parsed` evidence instantiates nodes of any type.
- `observed` evidence may instantiate **behavioural** types (`Flow`) from replayable
  journey traces and corroborate structural ones (a bounded confidence boost, recorded
  as an observed provenance entry with a `journey_ref`). Observed evidence confirms
  and adds, never vetoes: a runtime contradiction (route 404s, view never renders)
  becomes a recorded conflict, not a deletion, and unvisited constructs are untouched —
  absence of observation is not absence of behaviour.
- `asserted` evidence is authoritative for **naming and intent only** — it is never
  sufficient for existence. A node grounded solely in asserted evidence may exist only
  as `candidate`, `proposed`, or as an `UnknownSemanticConstruct`, never as
  `validated`/`accepted`. Documentation claims otherwise feed the hypothesis agenda:
  docs propose, the repository must still prove.
- Evidence classes may disagree, and **the graph must say so**: a documented claim the
  code contradicts becomes a recorded conflict (`conflicts` on the affected node —
  claim, counter-evidence, status), never a silent resolution in either direction.
  Absence of one class is not veto power for another.

## Kernel semantic vocabulary

```text
Application  Module  EntryPoint  Interface  Flow  Action  View  Component
DataObject  DataStore  Rule  Integration  Job  Configuration  SecurityElement
UnknownSemanticConstruct
```

Before proposing a new semantic type, try in order: (1) map to an existing accepted
type; (2) map to a specialization of an existing type; (3) use
`UnknownSemanticConstruct`; (4) only then propose a new type, with `type_id`,
`parent_type`, definition, detection rules, required/optional evidence, repository
examples, confidence, and status (`candidate | proposed | validated | accepted |
deprecated`). Only `accepted` or `validated` types may be used as stable constructs in
the final report; `candidate`/`proposed` types must be clearly marked as not yet
accepted.

## Parser discipline

A curated **tool gallery** of prepared parsers lives in `.agent-loop/tools/` (see its
README for the usage protocol). `.cache/scripts/parsers/` is the **working area**:
gallery tools are copied there, adapted if the repository needs it, and validated —
gallery originals are never modified during loop execution.

Selection order:

1. Existing deterministic project tooling.
2. Existing validated parser already under `.cache/scripts/parsers/`.
3. **Gallery tool from `.agent-loop/tools/`** — copy to the cache, run its smoke test
   plus real repository samples, adapt the cache copy if needed.
4. Standard local language/format parser.
5. Simple custom extractor for structured formats.
6. Generated parser as a last resort.

Every parser/extractor needs a manifest (see `contracts/parser-registry.schema.json`),
including its origin (`gallery` / `gallery-adapted` for gallery copies). Generated
parsers need smoke-test examples and must pass validation before their output feeds
final artefacts. One parser per artifact type — no monolithic "suite" scripts that
bundle parsing, graph building, and reporting into one file, and graph building and
verification must never share a file.

**Attribution rule:** any code that produces source-graph nodes beyond plain structural
listing (`File`, `Directory`, `DocumentationSection`) must be a registered parser, and
every node's `parser_id` must name the tool that actually emitted it. Orchestration
code must not parse artifact content inline and must never stamp another parser's id
on its own output — the verifier cross-checks every `parser_id` against the registry
and the parser's input patterns.

## Generated artefacts

```text
.work/semantic-loop/
  state.json            # loop state across iterations   (contracts/state.schema.json)
  assumptions.json      # all explicit assumptions
  inventory.json        # repository inventory            (contracts/inventory.schema.json)
  parser-registry.json  # parser/extractor manifests      (contracts/parser-registry.schema.json)
  source-graph.json     # Layer 1                         (contracts/source-graph.schema.json)
  semantic-types.json   # type registry                   (contracts/semantic-types.schema.json)
  semantic-graph.json   # Layer 2                         (contracts/semantic-graph.schema.json)
  doc-claims.json       # documentation claims — optional (contracts/doc-claims.schema.json)
  runtime/
    journeys.json       # runtime journeys — optional     (contracts/journeys.schema.json)
    traces/**           # normalized per-step traces + screenshots referenced by journeys.json
    scripts/**          # the journey scripts that produced them
  verification.json     # gate scores                     (contracts/verification.schema.json)
  reports/
    application-structure.md
```

All JSON artefacts must be valid JSON and conform to their schema. The final report is
Markdown.

## Execution process

```text
 1. Read .agent-loop/LOOP.md (this file).
 2. Read .agent-loop/skills/00-loop-conductor.md.
 3. Load or create .work/semantic-loop/state.json.
 4. Inventory the repository                       (skills/01-repository-inventory.md).
 5. Detect artifact types.
 6. Locate, validate, or generate parsers          (skills/02-parser-broker.md,
                                                    skills/03-parser-generator.md).
 7. Build the Source Construct Graph               (skills/04-source-graph-builder.md).
 8. Build/update the Semantic Type Registry        (skills/05-semantic-type-discovery.md).
 9. Build the Semantic Construct Graph             (skills/06-semantic-graph-builder.md).
10. Align documentation claims                     (skills/10-doc-alignment.md) —
    optional and degradable: with no documentation in scope, record the layer as an
    explicit unknown and continue; never fail the gate for its absence.
11. Walk runtime journeys                          (skills/09-journey-walker.md) —
    optional, degradable, and approval-gated: requires explicit user approval to
    execute the target; without approval, a satisfied environment, or a startable
    target, record the layer as an explicit unknown and continue static-only.
12. Verify all artefacts                           (skills/07-verifier.md).
13. If verification passes, write the final report (skills/08-report-writer.md).
14. If verification fails:
    a. print ITERATING;
    b. identify the weakest score;
    c. improve the weakest score first;
    d. update state.json;
    e. continue until verification passes or max_iterations is reached.
15. If max_iterations is reached, write a partial report with unresolved items,
    clearly marked as partial.
```

## Verification gate

The verifier scores ten dimensions from 0–10:

```text
inventory_coverage        parser_validity         source_graph_consistency
semantic_type_quality     semantic_graph_provenance
assertion_grounding       journey_corroboration   report_coverage
unknowns_handling         reproducibility
```

`reproducibility` applies a **split standard** (see `contracts/journeys.schema.json`):
static artefacts must be byte-identical across re-runs; runtime artefacts must be
*semantically* reproducible — written pre-normalized (no timestamps, session ids,
cookie/date values, durations, or absolute user paths), so two runs over the same
repository state and DB snapshot compare byte-equal, with screenshots exempt from
byte-identity and integrity-checked by recorded hash instead. Weakening this quietly
is prohibited; the normalization rule is enforced by a named verifier check.

**The loop may only be marked complete if all scores are 8 or higher.** If any score is
below 8: print `ITERATING`, name the weakest score, define the next corrective action,
and do not claim completion. The next iteration must improve the weakest score first.

Verification must be **independent and measured** (see `skills/07-verifier.md`):

- Run the prepared verifier from the gallery (`.agent-loop/tools/verifier/`) — do not
  write verification logic inside artefact-generating code.
- Every score is an object `{value, derived_from, measurement}` computed by a fixed
  formula over named checks (`contracts/verification.schema.json`). Bare asserted
  score constants are a contract violation.
- The verifier re-derives facts (recounts edges, re-resolves provenance onto disk,
  recomputes hashes, re-runs parser smoke tests) instead of trusting generator
  bookkeeping.
- **A pass verdict counts only if the gate has been shown able to fail**: the verifier's
  mutation self-test corrupts artefact copies and must catch every mutation before the
  real verdict is trusted.

## Out of scope for this version

No SQLite/graph databases, no vector search, no scheduling, no persistent background
agents, no platform integration. This remains a manually invoked, file-based,
prompt/skill-driven demonstrator.

Web automation is **in scope since contract version 2**, but only as the runtime
journey phase defined by `skills/09-journey-walker.md` and
`contracts/journeys.schema.json`: explicit per-run user approval, sandboxed execution
against a disposable database copy, hypothesis-driven journeys, and the split
reproducibility standard. Free crawling, scheduled runs, and journeys against
unapproved targets stay out of scope. Background and spec:
`specs/implement-extended-semantic-layer.md`, Extension B.
