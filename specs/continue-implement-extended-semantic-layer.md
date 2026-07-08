# Continuation instructions: extended semantic layer implementation

**Audience:** an AI assistant (or human) picking up this work on a fresh machine with
no memory of the previous session.

**Governing spec:** `specs/implement-extended-semantic-layer.md`. Read it first — it
defines the requirements this work implements, with numbered requirement IDs
(EV-1…EV-6, DOC-1…DOC-8, RT-1…RT-8) that this document refers to. The original
analysis it was distilled from is `extend-semantic-layer.md` at the repository root
(background reading; the spec supersedes it).

> **UPDATE 2026-07-07: all three milestones are complete.** Milestone 2's validating
> loop run was performed and its example committed; Milestone 3 (runtime journeys,
> contract version 2) was then implemented and validated end-to-end — all ten gate
> dimensions at 10, 8/8 mutation self-test, `sem:flow:login-task-review` instantiated
> from replayable traces, source tree byte-identical before/after, repeat-run
> reproducibility confirmed. See the 2026-07-07 addenda in
> `specs/loop-implementation-report.md`. The text below is the original handoff and is
> kept as the record of what was planned; sections 3a/3b are now history, not TODO.

**State of the work (original handoff):** Milestones 1 and 2 of the spec (section 7)
are **code-complete but uncommitted**, and Milestone 2's end-to-end validating loop run
has **not** been performed. Milestone 3 is **entirely unimplemented** (deliberately —
the spec sequences it last). Details below.

---

## 1. Decisions made during implementation (not all in the spec)

These were settled in conversation with the user and must be respected:

1. **`taskdesk-legacy/MIGRATION_SOURCE_CATALOG.md` stays deleted.** It was an
   artefact of a previous project; real legacy targets won't have such a catalog.
   Do not restore it, and do not treat its absence as a problem. The spec's fixture
   references were already updated to `taskdesk-legacy/README.md` and
   `db/runtime-data/README.md`.
2. **No external spec tooling** (OpenSpec etc.). The repo's own contract machinery
   (`.agent-loop/LOOP.md` + `contracts/*.schema.json` + verifier gate) is the spec
   system; the implement-* doc is the change proposal; requirement IDs are the
   checklist.
3. **Backward compatibility choice (EV-1):** an absent `kind` on a provenance entry
   means `parsed`, so pre-existing semantic graphs stay schema-valid.
4. **`observed` is declared but reserved.** The schema knows the kind; no phase may
   produce it until Milestone 3 renegotiates the contract (see LOOP.md "Out of
   scope" section, which now says exactly this).
5. **Degradability implementation (DOC-8):** when `doc-claims.json` is absent the
   verifier's `assertion_grounding` dimension scores 10 with a `warn` check noting
   the layer stands as a recorded unknown — *but* any `kind: "asserted"` provenance
   in the semantic graph without a claims artefact behind it is a hard fail
   (check `doc-asserted-backed`). Absence is tolerated; unbacked asserted evidence
   is not.
6. **The claim extractor is split into a deterministic and a model-driven half**
   (DOC-3). The gallery tool `.agent-loop/tools/doc-claims/parser.py` provides the
   deterministic half (anchor extraction + claim checking); the *reading* of prose
   into claims is done by the agent during skill 10 and is disciplined by mandatory
   verbatim excerpts + spans that the tool and verifier re-resolve.
7. **The committed example run (`examples/taskdesk-legacy-run/`) is a historical
   snapshot** of the previous eight-dimension contract and an earlier repo state
   (it still inventories the deleted catalog file, and two source files changed
   since). It intentionally was NOT modified. It should be regenerated from a fresh
   loop run (see section 3), not hand-edited.
8. **Formatting caution:** `.agent-loop/contracts/*.schema.json` are hand-formatted
   (compact one-line sub-objects). Do not round-trip them through
   `json.dumps(indent=2)` — that reformats the whole file and churns the diff. Use
   targeted string edits. (This mistake was made and reverted once already.)

## 2. What is implemented (Milestones 1 and 2)

All changes are in the working tree, **uncommitted**, on branch `main`. Run
`git status` / `git diff` to see them. Inventory of changes:

### Milestone 1 — evidence model groundwork (spec §3, EV-1…EV-6)

- **`.agent-loop/contracts/semantic-graph.schema.json`**
  - `$defs/provenance` gained `kind` (`parsed | observed | asserted`, absent =
    parsed) and `claim_ref` (link into doc-claims.json for asserted entries).
  - New `$defs/conflict` (`claim`, `claim_ref`, `counter_evidence`,
    `status: open | resolved`, `properties`) and a `conflicts` array on
    `semanticNode` (EV-5).
  - An `allOf`/`if`/`then` conditional on `semanticNode` enforces EV-3 in the
    schema itself: a node whose `grounded_in` entries are all `kind: "asserted"`
    and whose type is not `UnknownSemanticConstruct` may only hold status
    `candidate | proposed | deprecated`.
- **`.agent-loop/LOOP.md`**
  - New section "Evidence classes and the authority rule" (the three-kind table,
    `parsed > observed > asserted` for existence, asserted = naming/intent only,
    conflicts represented never silently resolved, EV-6 no-veto asymmetry).
  - Hard constraints: documentation counts as evidence only as in-repo files;
    external sources must be snapshotted in with retrieval date (DOC-6).
  - Artefact tree includes `doc-claims.json` (optional).
  - Execution process has a new step 10 (doc alignment, optional and degradable);
    subsequent steps renumbered (verify is now 11, report 12, iterate 13, partial 14).
  - Verification gate lists **nine** dimensions (added `assertion_grounding`).
  - "Out of scope" now states `observed` is reserved for a future versioned
    contract change, pointing at the spec's Extension B.

### Milestone 2 — documentation alignment (spec §4, DOC-1…DOC-8)

- **`.agent-loop/contracts/doc-claims.schema.json`** (new; DOC-1) — the artefact
  contract for `.work/semantic-loop/doc-claims.json`: `repo_fingerprint`,
  `extracted_by`, optional `documents[]`, and `claims[]` where each claim has
  `id` (pattern `^claim:`), `claim_type`
  (`terminology|feature|rule|boundary|intent|data|other`), normalized `text`,
  **verbatim** `excerpt`, `file`, `span`, `status`
  (`confirmed|contradicted|unverifiable`), `mapped_nodes[]` (pattern `^sem:`;
  conditionally required non-empty when status is `confirmed`), and
  `status_evidence`.
- **`.agent-loop/tools/doc-claims/`** (new gallery tool: `parser.py` + `tool.json`)
  - *Anchor mode* (`parser.py <docs...>`): deterministically lists claimable units
    of markdown-ish docs — headings, list items (with indented continuation lines
    joined), table rows (separator rows skipped) — each with a line span and text
    capped at 300 chars. Deterministic ⇒ passes the verifier's double-run check.
  - *Check mode* (`parser.py --check <doc-claims.json> --repo DIR
    [--semantic-graph FILE]`): re-resolves every claim — required keys, id/status/
    type enums, duplicate ids, path must not escape the repo (no absolute paths or
    `..`), file exists, span fits the file, whitespace-normalized excerpt occurs
    within the span text, confirmed ⇒ non-empty `mapped_nodes`, mapped nodes exist
    in the graph when given, node `conflicts[].claim_ref` resolve to claim ids.
    Exit 0 iff clean.
  - `--smoke` covers all of the above including forged span, reworded excerpt,
    path escape, and dangling conflict ref. Prints `SMOKE PASS`.
  - `known_limitations` in `tool.json` are honest: markdown-oriented, prose
    paragraphs unanchored, checker proves location not interpretation, no setext
    headings.
- **`.agent-loop/tools/verifier/verify.py`** — the gate, extended:
  - `DIMENSIONS` now has nine entries (`assertion_grounding` inserted after
    `semantic_graph_provenance`); loads `doc-claims.json` as an optional artefact.
  - `score_provenance` gained `sem-kind-valid` (unknown kinds fail) and
    `sem-asserted-not-sufficient` (EV-3: asserted-only node with status
    validated/accepted and type ≠ UnknownSemanticConstruct **caps the dimension at
    5**, same severity as an ungrounded node).
  - New `score_assertions` (DOC-7): absent artefact ⇒ warn + 10 + the
    `doc-asserted-backed` coupling check (see decision 5). Present artefact ⇒
    checks `doc-spans-resolve`, `doc-excerpts-match`, `doc-status-definite`,
    `doc-nodes-resolve`, `doc-refs-linked` (asserted `claim_ref`s and node
    `conflicts[].claim_ref`s must resolve); value = 10 − 3·fails.
  - `score_report` conditionally requires a **"Documentation drift"** section
    whenever `doc-claims.json` exists (DOC-5).
  - Mutation self-test grew from 4 to 6 mutations: `forged-doc-claim` (corrupts a
    claim's excerpt, or plants a claims file citing a missing doc when none
    exists — works either way) targeting `assertion_grounding`, and
    `asserted-only-accepted` (promotes a node to accepted on asserted-only
    evidence) targeting `semantic_graph_provenance`.
  - Built-in `--smoke` extended: fixture now includes a repo doc (`NOTES.md`), a
    clean doc-claims artefact, the drift report section, and corrupted variants
    asserting both new failure paths.
- **`.agent-loop/contracts/verification.schema.json`** — `assertion_grounding`
  added to `scores.required`, `scores.properties`, and the `checks[].score` enum
  (three targeted edits; formatting preserved).
- **`.agent-loop/skills/10-doc-alignment.md`** (new; the phase itself) — collect
  in-repo docs from the source graph (degrade to a recorded unknown if none);
  copy the gallery tool to `.cache/scripts/parsers/doc-claims-v1/` per the gallery
  protocol; anchor; extract claims (model-driven, every claim span-cited and
  verbatim-excerpted); resolve each to confirmed/contradicted/unverifiable;
  apply terminology/intent to mapped nodes as asserted provenance with
  `claim_ref`; unproven documented constructs become candidates or unknowns and
  feed the next iteration's hypothesis agenda (DOC-4); run check mode before the
  verifier; register `doc-claims-v1` in the parser registry (DOC-3). Rules encode
  EV-6 (docs never veto), stable claim ids, and drift-is-output.
- **Wiring edits:** `skills/00-loop-conductor.md` (phase order 01–06, 10, 07–08),
  `skills/07-verifier.md` (new dimension description, authority-rule cap, new
  mutations listed), `skills/08-report-writer.md` ("Documentation drift" in the
  required sections + a rule on reporting drift and using confirmed business
  terminology), `.agent-loop/tools/README.md` (gallery table row + special-status
  note for doc-claims), `.agent-loop/tools/verifier/tool.json` (nine dimensions,
  claim re-resolution, authority rule), `.agent-loop/prompts/verify-discovery-loop.md`
  (nine dimensions, doc-claims in the reads list).
- **`specs/implement-extended-semantic-layer.md`** — fixture references updated
  (decision 1).

### Validation already performed (all passing)

- `python3 .agent-loop/tools/verifier/verify.py --smoke` → `SMOKE PASS`.
- `python3 .agent-loop/tools/doc-claims/parser.py --smoke` → `SMOKE PASS`; anchor
  mode also exercised on the real `taskdesk-legacy/README.md`.
- All three touched/new schemas validate under
  `jsonschema.Draft202012Validator.check_schema` (the `jsonschema` lib was
  available on the previous machine).
- Against a **copy** of `examples/taskdesk-legacy-run/semantic-loop/` with
  `--repo .`: `--self-test` detects **6/6 mutations**; a pure verification run
  (no subprocesses) scores `assertion_grounding` 10 via the degradable path and
  fails overall **only** on genuine drift (the deleted catalog in the old
  inventory, two changed file hashes, and the consequent FINAL-status
  inconsistency). That is expected and correct; see decision 7.

## 3. What is left to implement

### 3a. Immediately next: the Milestone 2 validating loop run (small)

Nothing new to code — this is executing the loop with the new contract to satisfy
spec acceptance criteria 1, 2, 5 (nine-dimension part), and 6:

1. Run the discovery loop over this repository's `taskdesk-legacy/` target — the
   repo has a user-invocable `semantic-discovery-loop` skill; the governing files
   are `.agent-loop/LOOP.md` and `skills/00-loop-conductor.md`. The loop writes to
   `.work/semantic-loop/**` and `.cache/scripts/**` only.
2. The run must now include phase 10: expect a `doc-claims.json` built from
   `taskdesk-legacy/README.md` and `db/runtime-data/README.md` (roles,
   setup/behaviour notes, documented seed-row counts — the latter should let the
   run *properly* ground what the old run recorded as the
   `sem:unknown:runtime-row-semantics` unknown with an undisciplined
   `documented-row-counts` evidence type; that node's evidence should become
   `kind: "asserted"` with a `claim_ref`).
3. The report must contain the **Documentation drift** section; the gate must pass
   all nine dimensions with the 6-mutation self-test recorded in
   `verification.json`.
4. Acceptance criterion 2 check: no node in the resulting graph holds
   validated/accepted status on asserted evidence alone (the verifier enforces it;
   confirm the run didn't have to fight it).
5. **Refresh the example:** replace `examples/taskdesk-legacy-run/` contents with
   the new run's artefacts (same layout: `semantic-loop/` + `cache-scripts/`), so
   the committed example matches the current repo state and nine-dimension
   contract. Check `examples/README.md` (and the root `README.md`, plus
   `specs/loop-implementation-report.md` if it enumerates dimensions) for stale
   "eight dimensions" / catalog references while at it.
6. Commit — the user has not committed any of this; ask or follow their lead on
   commit granularity (suggest: M1+M2 code as one commit, refreshed example as a
   second).

Caveat: phase 10's claim extraction is model-driven — *you* (the agent running the
loop) do the reading, disciplined by skill 10. Keep claims few and checkable rather
than exhaustive; every one needs a verbatim excerpt that survives
`parser.py --check` and the verifier's independent re-resolution.

### 3b. Milestone 3 — runtime journeys, Extension B (large, all of spec §5)

Nothing exists yet beyond the schema-level reservation of `kind: "observed"` and
the spec itself. Implement in this order:

1. **Environment feasibility first** (RT-6): check for Java 8, Maven, Tomcat 9 (or
   the embedded/jetty route if `taskdesk-legacy/pom.xml` supports one — verify how
   the app actually starts; its README documents prerequisites), Node, Playwright.
   If the target cannot be built/started on the machine, Milestone 3 work can still
   proceed on contracts/skills, but end-to-end validation cannot — say so rather
   than faking it.
2. **`contracts/journeys.schema.json`** (RT-1): journeys with steps, trace refs,
   screenshot hashes, DB-diffs, the producing script, and the commit + DB-snapshot
   identity they ran against. Provenance shape for observed evidence differs from
   file/span — extend `$defs/provenance` in `semantic-graph.schema.json`
   accordingly (e.g. allow a `journey_ref`/trace reference when
   `kind: "observed"`), keeping parsed entries unchanged.
3. **`skills/09-journey-walker.md`** (RT-2…RT-5): explicit user approval before
   launching anything (RT-3 — mirror the existing dependency-installation rule);
   disposable copy of `db/runtime-data/taskdesk-demo.sqlite` and a sandboxed
   runtime dir under `.work/semantic-loop/runtime/` — the source tree, including
   the committed SQLite file, must stay byte-identical (RT-2); degradable: app
   won't start ⇒ static-only completion with a recorded unknown (RT-4); observed
   evidence confirms and adds, never vetoes (EV-6/RT-5) — a runtime contradiction
   becomes a `conflicts` entry.
4. **Start with the narrowest slice** (spec §7 Milestone 3): walk the journeys the
   doc-seeded `Flow` hypotheses predict and record **corroboration only**
   (confidence boosts + `Flow` instantiation from replayable traces). Security
   diffing (operator vs manager), invalid-form validation-rule probing, and
   DB-diff side-effect proof come after the corroboration slice passes the gate.
5. **Verifier work** (RT-7, RT-8): tenth dimension `journey_corroboration` with
   mutations (corrupt a trace ref / screenshot hash); update
   `verification.schema.json`, `skills/07-verifier.md`, LOOP.md (ten dimensions);
   and the **reproducibility split** — static artefacts stay byte-identical,
   `journeys.json` must be semantically reproducible after a *written*
   normalization rule (strip timestamps/session ids/volatile fields; same steps,
   same status codes, same DB-diff shape). Do not let `reproducibility` get
   quietly weakened — that is the failure mode the spec explicitly prohibits.
6. **LOOP.md contract renegotiation** (RT-3 + spec §5 preamble): remove "no web
   automation" from out-of-scope in favour of the versioned runtime phase with its
   approval + sandbox rules; un-reserve `observed`. This is a new loop version —
   version it visibly in LOOP.md, don't slip it in.
7. Validate per acceptance criteria 3–5: at least one `Flow` node grounded in a
   replayable trace; source tree byte-identical before/after; repeated run passes
   the split reproducibility standard; all ten dimensions ≥ 8 with the new
   mutations shown able to fail.

## 4. How to verify your own work as you go

- `python3 .agent-loop/tools/verifier/verify.py --smoke` — self-contained gate test.
- `python3 .agent-loop/tools/doc-claims/parser.py --smoke` — claim tooling test.
- `python3 .agent-loop/tools/verifier/verify.py --self-test --work <workdir> --repo .`
  — proves the gate can fail against real artefacts (must be 6/6 now, 8/8 after
  Milestone 3's two new mutations… count per what you add).
- Full gate: `python3 .agent-loop/tools/verifier/verify.py --work .work/semantic-loop`
  (runs self-test + subprocess checks + writes `verification.json`).
- The loop's own rule applies to this work too: the verifier judges, generators
  never score themselves, and a pass only counts once the gate has been shown able
  to fail.
