# Skill 05 — Semantic Type Discovery

## Purpose

Create or update `.work/semantic-loop/semantic-types.json` (schema:
`contracts/semantic-types.schema.json`): the registry of application-level concepts the
semantic graph is allowed to use.

## Rules

- **Start from the small kernel vocabulary**, seeded with status `accepted`:

  ```text
  Application  Module  EntryPoint  Interface  Flow  Action  View  Component
  DataObject  DataStore  Rule  Integration  Job  Configuration  SecurityElement
  UnknownSemanticConstruct
  ```

  Each kernel type still needs a real definition, detection rules, and required
  evidence written for it in the registry — no empty placeholders.

- **Avoid ontology sprawl.** Before proposing any new type, apply this sequence and stop
  at the first fit:
  1. Map the construct to an existing accepted type.
  2. Map it to a specialization of an existing type (set `parent_type`).
  3. Use `UnknownSemanticConstruct`.
  4. Only then propose a new semantic type.

- **Use `UnknownSemanticConstruct` when needed.** A construct that clearly exists but
  resists classification is recorded as unknown — never forced into a wrong type and
  never dropped.

- **Proposed types start as `candidate` or `proposed`**, and must include: `type_id`,
  `parent_type`, `definition`, `detection_rules`, `required_evidence`,
  `optional_evidence`, `examples` from this repository, `confidence`, and `status`.
  Promotion to `validated`/`accepted` requires at least one concrete grounded example in
  the current semantic graph. Only `accepted`/`validated` types back stable constructs
  in the final report.

- **Web search may explain framework concepts but does not prove local existence.**
  External documentation may inform a type's definition or detection rules; a semantic
  type may only be instantiated from evidence found in this repository.

- **Every accepted type needs detection rules and required evidence** concrete enough
  that a different assistant could apply them to the same repository and find the same
  constructs.
