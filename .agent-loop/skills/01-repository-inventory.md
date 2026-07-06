# Skill 01 — Repository Inventory

## Purpose

Create `.work/semantic-loop/inventory.json` (schema: `contracts/inventory.schema.json`):
a deterministic inventory of the repository, without modifying anything.

## Responsibilities

- **List source files.** Prefer `git ls-files` (deterministic, respects the repo's own
  tracking); fall back to a recursive listing that excludes `.git/`. Record the method
  used in `generated_by`.
- **Detect likely languages** per file from extensions and, where ambiguous, shallow
  content inspection (e.g. shebangs, XML root elements). Record `null` when unknown.
- **Detect likely framework artefacts** — e.g. `web.xml`, `struts-config.*`, Spring
  context files, `pom.xml`/`build.gradle`, `package.json`, JSP/template directories,
  migration scripts. Record each detected framework with the concrete file paths that
  are the evidence and a confidence value.
- **Detect build files** (Maven, Gradle, Ant, npm, Make, shell build scripts) and mark
  their role as `build`.
- **Detect configuration files** (properties, YAML, XML config, `.env` examples,
  manifests) and mark their role as `configuration`.
- **Detect test files** by conventional locations (`src/test/`, `*Test.*`, `test/`,
  `__tests__/`) and mark their role as `test`.
- **Exclude generated/vendor/build artefacts** where reasonable (`target/`, `build/`,
  `node_modules/`, `dist/`, minified bundles). Record every exclusion with its reason in
  `summary.excluded`. Also exclude the loop's own folders (`.work/`, `.cache/`,
  `.agent-loop/`, assistant adapter folders) — the loop must not analyze itself.
- **Record uncertainty.** Any file whose role or language cannot be determined gets
  `role: unknown` and an `uncertainty` note; broader open questions go in the top-level
  `uncertainties` array. Never guess silently.

## Rules

- Read-only: never touch the source tree.
- Set `repo_fingerprint` (git HEAD hash if available, else null) so downstream artefacts
  can be tied to this snapshot.
- Every classification must be reproducible from the rules above; do not classify from
  memory of "typical projects" without file evidence.
- New assumptions made here (e.g. "`src/main` is production source") must be added to
  `.work/semantic-loop/assumptions.json` with reason, confidence, and status.
