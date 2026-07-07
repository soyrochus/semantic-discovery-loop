# Skill 09 — Journey Walker

## Purpose

Execute the target application in a sandbox and walk **hypothesis-driven user
journeys**, producing `.work/semantic-loop/runtime/journeys.json` (schema:
`contracts/journeys.schema.json`) plus per-step trace files and screenshots under
`.work/semantic-loop/runtime/`. Apply the results to the semantic graph as
**observed** evidence: `Flow` instantiation and corroboration of statically derived
constructs.

Runs after documentation alignment (skill 10) — journeys walk what the doc-seeded
`Flow` hypotheses and the statically derived entry points predict — and before
verification (skill 07).

## The trust boundary this phase crosses (RT-3)

Every other phase *reads* the repository; this one *runs* it. Pointed at an
arbitrary repository, that is arbitrary code execution.

- **Explicit user approval is required before launching anything** — building the
  target, starting a container, installing runtime dependencies. Approval must be
  obtained in conversation and recorded in `journeys.json` under `approval`
  (`granted`, `statement`). No approval ⇒ the phase does not run and the layer is
  recorded as an explicit unknown (see degradation).
- This mirrors the existing dependency-installation rule: the loop never expands
  its execution footprint silently.

## Sandbox rules (RT-2)

- The application runs against a **disposable copy** of the runtime database,
  copied to `.work/semantic-loop/runtime/`; the committed database file and the
  rest of the source tree stay byte-identical. Record the committed file's sha256
  at launch in `db_snapshot.source_sha256` — the verifier recomputes it.
- All runtime state (deployed artefacts where possible, scripts, traces,
  screenshots, logs, the DB copy) lives under `.work/semantic-loop/runtime/`.
  A container installation outside the tree (e.g. a local Tomcat) may be used to
  host the WAR, but everything the app *writes* must be redirected to the sandbox
  (for the bundled example: `TASKDESK_DB_URL` pointing at the disposable copy).
- After the run, verify the source tree is untouched (`git status --porcelain`
  must not change; the committed DB hash must match) before recording results.

## Environment feasibility (RT-6)

Declare and check the runtime dependencies **before** launching; record each in
`environment.declared_dependencies` with `satisfied: true|false`. For the bundled
example: Java 8+, Maven, Tomcat 9 (javax.servlet), Node, Playwright (Chromium).
Any unsatisfied dependency triggers the degradation path — never a fabricated run.

## Degradation (RT-4)

The phase is optional and degradable. If approval is withheld, a dependency is
missing, or the target cannot be built/started: write **no** `journeys.json`,
record the missing layer as an explicit unknown (an assumption in
`assumptions.json`, plus `unknowns` entries on affected nodes), and let the loop
complete static-only. The verifier scores `journey_corroboration` as a recorded
unknown (warn, not failure) when the artefact is absent. Never fake a trace; a
target that will not start is a finding, not an obstacle.

## Journey discipline

- **Hypothesis-driven, not exploratory.** Each journey names its
  `flow_hypothesis`: the doc-claims claim id and/or static route chain that
  predicted it. Walk what the graph predicts; do not free-crawl.
- **Narrow slice first** (spec §7 Milestone 3): corroboration and `Flow`
  instantiation only. Security-role diffing, invalid-form probing, and DB-diff
  side-effect proof come after the corroboration slice has passed the gate.
- Every step records: normalized URL, matched `route` (must correspond to a parsed
  `Route` node — the verifier cross-checks), response status, matched
  `rendered_view` with the page evidence that matched it, and a `trace_ref`
  (sha256-hashed trace file). Screenshots are optional exhibits.
- Journey ids are stable (`journey:<slug>`), reproducible across runs.

## Applying results to the semantic graph (RT-5 / EV-6)

Observed evidence **confirms and adds; it never vetoes**:

- **`Flow` instantiation:** a completed journey is a machine-checkable witness for
  a `Flow` node — grounded in observed provenance (`kind: "observed"`,
  `journey_ref`, optional `trace_ref`), edges (`traverses`) to the Actions/Views
  it walked. This is existence proof for behavioural types: a replayable trace is
  demonstrated, not inferred.
- **Corroboration:** nodes listed in a journey's `corroborates` gain an observed
  provenance entry and a bounded confidence boost (deterministic formula, e.g.
  `min(0.99, confidence + 0.02)`); their existence status does not depend on it.
- **Contradiction:** a route that 404s or a view that never renders becomes a
  `conflicts` entry (claim, counter-evidence, status `open`) on the affected node —
  never a deletion, never a confidence cut. Unvisited constructs are untouched:
  absence of observation is not absence of behaviour.

## Normalization rule (RT-8)

`journeys.json` and every trace file are written **pre-normalized** so that two
runs over the same repository state and DB snapshot are byte-identical:

- no wall-clock timestamps, durations, or dates;
- no session identifiers — strip `;jsessionid=…` from URLs, omit cookie values
  and `Set-Cookie`/`Date` headers entirely;
- no absolute filesystem paths outside the runtime directory;
- screenshots are exempt from byte-identity (rendering is not deterministic);
  they are integrity-checked by their recorded sha256 instead.

The verifier enforces this (`rep-journeys-normalized`): volatile content in the
runtime artefacts fails `reproducibility`.

## Rules

- Write only `.work/semantic-loop/**` and `.cache/scripts/**`; the source tree,
  including the committed database, stays byte-identical (verifier-checked).
- The journey script that produced the artefact is itself recorded
  (`produced_by`) and kept under `.work/semantic-loop/runtime/scripts/`.
- The walker never writes `verification.json` and never scores itself; the
  verifier re-derives trace integrity, journey refs, route matches, and the
  untouched-source proof independently (`journey_corroboration`).
