# Semantic Discovery Loop Implementation Guide

This guide explains how the semantic discovery loop is structured and how a run moves
from a repository tree to verified source and semantic artefacts. The governing contract
is `.agent-loop/LOOP.md`; this document is a practical map of the implementation.

## Purpose

The loop inspects an existing repository without modifying it. It produces:

1. `source-graph.json`: deterministic facts about what exists in the tree.
2. `semantic-graph.json`: application-level meaning, grounded in source, docs, or
   runtime evidence.

The core rule is simple: the AI can propose interpretations, but local repository
evidence has to prove them. Unknowns stay explicit instead of being smoothed over.

## Repository Structure

| Path | Role |
| --- | --- |
| `.agent-loop/LOOP.md` | Governing contract: scope, constraints, phases, evidence rules, verification gate. |
| `.agent-loop/skills/` | Phase instructions. `00-loop-conductor.md` coordinates the run; `01`-`10` perform inventory, parsing, graph building, verification, reporting, runtime journeys, and doc alignment. |
| `.agent-loop/contracts/` | JSON Schemas for every generated artefact. These are the machine-checkable interface between phases. |
| `.agent-loop/tools/` | Curated parser/extractor gallery plus the verifier. Tools are copied into the cache before use. |
| `.cache/scripts/` | Working area for parser and verifier copies. Cache copies may be adapted during a run. |
| `.work/semantic-loop/` | Run output: state, inventory, graphs, claims, journeys, verification, and reports. |
| `examples/` | Committed reference output from a completed run. |
| `specs/` | Design notes, original specifications, and historical implementation records. |
| `docs/` | Human-facing implementation and semantic-layer guides. |

During an actual loop run, writes are limited to `.work/semantic-loop/**` and
`.cache/scripts/**`. The analyzed source tree is read-only.

## Main Concepts

**Source Construct Graph**

Layer 1 is built from deterministic parsers. It records files, Java classes, methods,
XML elements, JSP structures, Maven dependencies, SQL objects, SQLite schema objects,
and similar concrete constructs. It should not infer business meaning.

**Semantic Construct Graph**

Layer 2 maps source constructs to application concepts such as `Application`, `Module`,
`Action`, `View`, `Flow`, `DataObject`, `DataStore`, `Rule`, and `Integration`. Every
semantic node must have provenance in `grounded_in`.

**Semantic Type Registry**

`semantic-types.json` defines the allowed vocabulary. It contains kernel types plus any
project-specific discovered types. New types must state their parent, definition,
detection rules, required evidence, examples, confidence, status, and version.

**Evidence Classes**

Semantic provenance has three classes:

| Kind | Source | Used For |
| --- | --- | --- |
| `parsed` | Deterministic parser output over repository files | Proving what exists. |
| `observed` | Runtime journey traces | Proving what happens during approved execution. |
| `asserted` | Claims extracted from in-repository documentation | Capturing naming and intent. |

For existence claims, authority is `parsed > observed > asserted`. Documentation alone
cannot validate a construct. Runtime observations can add and corroborate behaviour,
but a failed or absent observation becomes an unknown or conflict, not a deletion.

**Unknowns and Conflicts**

When evidence is incomplete, the loop records unknowns. When evidence classes disagree,
the semantic graph records a conflict with the claim, counter-evidence, and status.

## State Machine

Run state lives in `.work/semantic-loop/state.json` and follows
`.agent-loop/contracts/state.schema.json`.

```text
initialized
  -> running
  -> verification
      -> complete   when all gate scores are 8 or higher
      -> iterating  when any score is below 8 and max_iterations remains
      -> partial    when max_iterations is reached without passing
      -> aborted    when the run is stopped
```

Key state fields:

| Field | Meaning |
| --- | --- |
| `loop_id` | Always `semantic-source-discovery`. |
| `iteration` | Current iteration number; `0` means initialized. |
| `max_iterations` | Default limit is `6`. |
| `status` | `initialized`, `running`, `iterating`, `complete`, `partial`, or `aborted`. |
| `repo_fingerprint` | Source revision fingerprint, usually the git HEAD hash. |
| `last_completed_phase` | Resume marker for the last successful phase. |
| `weakest_score` | Lowest verification dimension from the previous gate run. |
| `next_action` | Corrective action the next iteration must address first. |

When verification fails, the conductor prints `ITERATING`, records the weakest score,
sets `next_action`, and improves that score first.

## Phase Pipeline

The conductor runs phases in the order defined by `.agent-loop/LOOP.md`:

1. Load or create state.
2. Inventory the repository.
3. Detect artifact types.
4. Select, validate, copy, adapt, or generate parsers.
5. Build `source-graph.json`.
6. Build or update `semantic-types.json`.
7. Build `semantic-graph.json`.
8. Align documentation claims into `doc-claims.json` when in-repository docs exist.
9. Walk runtime journeys when explicitly approved and the target can run.
10. Verify all artefacts with the independent verifier.
11. Write the final or partial report.

Each generated JSON artefact is expected to conform to its schema before later phases
depend on it.

## Parser Lifecycle

Parser selection is conservative:

1. Prefer deterministic project tooling if available.
2. Reuse a validated cached parser.
3. Copy a gallery tool from `.agent-loop/tools/` into `.cache/scripts/parsers/`.
4. Adapt only the cache copy if needed.
5. Use a standard local parser or simple structured extractor.
6. Generate a parser only as a last resort.

Every parser has a manifest in `parser-registry.json`. Generated or adapted parsers
need smoke tests and real repository samples before their output can feed final
artefacts. Graph builders and verifiers must not hide parser logic inside themselves.

## Runtime Journeys

Runtime journeys are optional and approval-gated because they execute the target
application. When used, the phase records `observed` evidence in
`.work/semantic-loop/runtime/journeys.json`, normalized traces, screenshots, and the
scripts that produced them.

Runtime artefacts follow a split reproducibility rule: structured traces are normalized
so reruns compare byte-equal, while screenshots are hash-checked rather than expected
to be byte-identical.

## Verification Gate

The verifier measures ten dimensions:

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

Every score must be at least `8`. The verifier re-derives facts from artefacts and disk
instead of trusting generator bookkeeping. It also runs mutation self-tests to prove the
gate can fail before a pass verdict is trusted.

## Extending the Loop

To extend the loop, prefer changing the contract first:

1. Add or update schemas in `.agent-loop/contracts/`.
2. Update the relevant skill instruction in `.agent-loop/skills/`.
3. Add or promote gallery tools under `.agent-loop/tools/` only after they are proven.
4. Regenerate example artefacts under `examples/` when behaviour changes materially.
5. Keep semantic claims grounded in local evidence and preserve verifier independence.

The semantic layers are summarized in `docs/semantic-layers-overview.md`.
