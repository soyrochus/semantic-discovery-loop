# Specification: Extended Semantic Layer — Documentation and Runtime Evidence

| | |
|---|---|
| **Status** | Draft |
| **Date** | 2026-07-07 |
| **Applies to** | The semantic discovery loop defined in `.agent-loop/LOOP.md` |
| **Supersedes** | Nothing; defines the next loop version |
| **Source analysis** | `extend-semantic-layer.md` (repository root) |

The key words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** in this document are to
be interpreted as described in RFC 2119.

---

## 1. Purpose and scope

This specification extends the semantic discovery loop with two new evidence classes:

- **Asserted evidence** — claims extracted from functional and technical documentation
  found inside the target repository (Extension A).
- **Observed evidence** — facts recorded by executing the target application and
  walking user journeys with Playwright (Extension B).

Today the loop admits exactly one evidence class: static, parser-derived facts from
the local source tree. That discipline enforces the loop's core rule — *the AI
proposes, the repository proves* — but leaves demonstrable gaps, documented in
section 2. Both extensions add evidence without weakening that rule: **code remains
the only sufficient proof of existence.** New evidence classes may confirm, name,
contradict, and propose; only one of them (observed, for behavioural types) may
additionally instantiate.

Out of scope for this specification:

- Evidence from outside the target repository (wikis, Confluence, issue trackers).
  See requirement DOC-6 for the snapshot rule that keeps this boundary intact.
- Any change to Layer 1 (the source graph) beyond what the new phases consume.
- Continuous or scheduled execution. The loop remains manually invoked.

## 2. Motivation

The bundled example run (`examples/`, target `taskdesk-legacy/`) exposes three gaps
that static evidence structurally cannot close:

1. **`Flow` is empty.** `Flow` is in the kernel vocabulary, yet the run instantiated
   none. The existing edge vocabulary (`triggers`, `renders`, `uses`, `part-of`)
   captures single hops; a journey — login → task list → detail → edit → save — is a
   claim about ordered, stateful traversal that static parsing can suggest but never
   prove. The one kernel type reserved for user-visible behaviour over time is
   exactly the one static evidence could not ground.
2. **The run's only `UnknownSemanticConstruct` is a runtime gap.**
   `sem:unknown:runtime-row-semantics` records that the schema parser saw table
   structure but not the business meaning of seed rows. The loop itself flagged that
   its evidence class cannot see behaviour or data semantics.
3. **The graph speaks the code's vocabulary.** Nodes are named `DataObject: TASK`
   and `Action: taskAssign` because identifiers are the only witness. Whether the
   business calls that operation "assignment", "dispatch", or "escalation" is
   invisible, and the report is correspondingly less legible to system owners.

A fourth motivation is disciplinary: documentation evidence has *already* crept into
the graph. The example run grounds its `UnknownSemanticConstruct` in
`db/runtime-data/README.md` with `evidence_type: "documented-row-counts"` — an
asserted claim admitted without a declared evidence class or authority rule. This
specification legalizes and constrains what the loop already found itself needing.

## 3. The evidence model

### 3.1 Three evidence classes

| Class | Definition | Answers | Reproducibility standard |
|---|---|---|---|
| `parsed` | Deterministic facts emitted by registered parsers over the source tree | What exists | Byte-identical |
| `observed` | Facts recorded from executing the target application (traces, HTTP exchanges, screenshots, database diffs) | What happens | Semantic (normalized; see RT-8) |
| `asserted` | Claims extracted from documentation files inside the repository | What is meant | Byte-identical |

### 3.2 The authority rule

**EV-1.** Every provenance entry in the semantic graph MUST carry an evidence
`kind`, one of `parsed`, `observed`, `asserted`. `semantic-graph.schema.json`
(`$defs/provenance`) MUST be extended accordingly. For backward compatibility with
existing artefacts, an absent `kind` MUST be interpreted as `parsed`.

**EV-2.** For **existence** claims, the authority order is:

```text
parsed  >  observed  >  asserted
```

**EV-3.** A node whose `grounded_in` contains only `asserted` evidence MUST NOT
hold status `validated` or `accepted`. It MAY exist as `candidate`, `proposed`, or
as an `UnknownSemanticConstruct`. Asserted evidence is authoritative for **naming
and intent** properties only; it is never sufficient for existence.

**EV-4.** `observed` evidence MAY instantiate accepted nodes of behavioural types
(`Flow`, `SecurityElement`, `Rule`) and prove behavioural edges (e.g. `writes-to`
demonstrated by a database diff). For structural types, observed evidence
corroborates but does not replace parsed evidence.

**EV-5.** Evidence classes may disagree, and **the graph must say so**. When one
class contradicts another (a documented feature with no code; a statically derived
route that returns 404 at runtime), the loop MUST record a conflict — claim,
counter-evidence, status — and MUST NOT silently drop either side. Conflicts are
represented as a `conflicts` property on the affected node (schema addition) and
reported in a dedicated report section. Silent resolution in either direction is a
contract violation.

**EV-6 (asymmetry rule).** Runtime evidence can confirm and add, never veto. A
statically grounded node that a journey did not visit MUST NOT have its confidence
lowered for that reason: absence of observation is not absence of behaviour, and a
symmetric rule would drift the graph toward "what the demo user clicked" instead of
"what the application is". A runtime *contradiction* is recorded per EV-5, not
applied as a deletion.

## 4. Extension A — Documentation evidence (`asserted`)

Implemented as a new optional phase, `skills/10-doc-alignment.md`, running after the
semantic graph builder and before the verifier.

### 4.1 What it does

The phase reads documentation files already inventoried as `DocumentationSection`
nodes in the source graph (26 exist in the example run; nothing semantic is built
from them today) and produces three outputs:

1. **A terminology mapping** — business term ↔ semantic node — applied as naming and
   intent properties on existing nodes. This is the cheapest, highest-leverage use:
   it is what lets the report say "work ticket" where the graph says `TASK`.
2. **A hypothesis agenda** — documented features become *candidate* constructs the
   loop should go looking for. Docs propose; parsed or observed evidence must still
   prove. Nothing changes about what instantiates a node.
3. **Drift findings** — per-claim comparison against the discovered graph. Stale
   documentation is first-class output, not noise; the repository has already
   demonstrated this pattern manually in `article-repo-drift.md`.

The bundled example provides the natural first test case:
`taskdesk-legacy/MIGRATION_SOURCE_CATALOG.md` is a hand-authored catalog of routes,
actions, and business rules that can be parsed into claims and cross-checked against
the discovered graph.

### 4.2 Requirements

**DOC-1.** The phase MUST emit a new artefact,
`.work/semantic-loop/doc-claims.json`, containing every extracted claim with: the
claim text, its provenance (file, span — exactly like source evidence), the semantic
nodes it maps to (if any), and a status of `confirmed`, `contradicted`, or
`unverifiable`. A corresponding `doc-claims.schema.json` MUST be added to
`.agent-loop/contracts/`.

**DOC-2.** Every extracted claim MUST carry file-and-span provenance into the source
document, so a human can check the reading. Claim extraction is interpretation — an
LLM reading prose, not a parser emitting deterministic facts — and this is the first
of three mitigations for that.

**DOC-3.** Claim extraction MUST be registered in the parser registry with a
manifest and smoke tests over fixture documents, even though it is model-driven.
Its fallibility is made visible in the registry rather than hidden in the graph
builder.

**DOC-4.** Wherever possible, extracted claims MUST feed the hypothesis agenda
(section 4.1, item 2) rather than the graph directly. Direct graph effects are
limited to naming/intent properties (EV-3) and conflict records (EV-5).

**DOC-5.** `contradicted` and `unverifiable` claims MUST appear in the final report
in a drift section. They MUST NOT be dropped or down-ranked out of the output.

**DOC-6 (scope rule).** Only documentation files inside the target repository
qualify as evidence. External sources (wikis, Confluence, tickets) MUST first be
snapshotted into the repository as files, with retrieval date recorded, before the
loop may cite them. Otherwise the source-of-truth rule dissolves.

**DOC-7.** The verifier gains a measured dimension, `assertion_grounding`: the
percentage of doc-derived claims resolved to a definite status
(`confirmed | contradicted | unverifiable`), computed by the fixed-formula mechanism
of `contracts/verification.schema.json`. The mutation self-test MUST include at
least one case that forges a doc claim's span; the verifier must catch it.

**DOC-8.** The phase is **degradable**: a repository with no documentation completes
the loop with the doc-alignment layer recorded as an explicit unknown, never as a
gate failure.

### 4.3 What this extension does not require

No new execution environment, no new trust boundary, no change to the read-only
constraint, and no change to byte-identical reproducibility (documents are files).
This is the low-risk extension of the two, which is why it goes first (section 7).

## 5. Extension B — Runtime journeys (`observed`)

Implemented as a new optional phase, `skills/09-journey-walker.md`. This extension
is an explicit scope change: `LOOP.md` currently states *"no web automation… a
manually invoked, file-based, prompt/skill-driven demonstrator."* It therefore
defines a **new loop version with a revised contract** — versioned, not slipped in.

### 5.1 What it does

Driven by the `Flow` hypotheses that doc alignment seeds (and by statically derived
entry points), the phase launches the target application in a sandbox and walks
journeys with Playwright. Each trace step carries a URL (matching a `Route` source
node), a rendered page (matching a `View`), and form submissions (matching an
`Action` and its form-bean fields). This yields, in descending order of value:

1. **`Flow` instantiation.** A replayable trace is a machine-checkable witness for a
   `Flow` node — demonstrated rather than inferred, and the single highest-value
   addition, since it fills the one kernel type the example run left empty.
2. **Corroboration.** Every statically inferred `EntryPoint`/`Action`/`View` triple
   can be visited; agreement is recorded as a per-node confidence boost
   (statically derived + runtime-confirmed) without changing what counts as
   existence proof.
3. **Empirical side-effect edges.** Diffing a disposable database copy before and
   after a journey step converts the weakest static claims (data flow through JDBC
   string concatenation) into observed facts — and directly answers the example
   run's `runtime-row-semantics` unknown, since journeys read and display real rows.
4. **Behavioural grounding for `SecurityElement` and `Rule`.** Running the same
   journey as `operator1` and `manager1` and diffing reachability is direct evidence
   for authorization rules; submitting an invalid form and observing the error path
   grounds validation rules. The example run has exactly one `secured-by` edge;
   journeys multiply that with stronger evidence.
5. **Demonstrable report exhibits.** Traces, screenshots, and HTTP exchanges are
   evidence a human can inspect in seconds; the report gains claims with replayable
   demonstrations, not just file/line citations.

### 5.2 Requirements

**RT-1.** The phase MUST emit a new artefact,
`.work/semantic-loop/runtime/journeys.json`, recording per journey: the steps, trace
references, screenshot hashes, database diffs, the script that produced them, and
the commit and database-snapshot identity they ran against. A corresponding
`journeys.schema.json` MUST be added to `.agent-loop/contracts/`. An observed
provenance entry references this artefact; its shape (trace id, request/response
pair, screenshot hash, DB diff) is distinct from the file/span shape of parsed
evidence, and the provenance schema MUST accommodate both.

**RT-2 (sandbox rule).** Journeys MUST run against a **disposable copy** of the
runtime database and a sandboxed runtime directory under
`.work/semantic-loop/runtime/`. The source tree — including the committed
`db/runtime-data/taskdesk-demo.sqlite` — remains untouched. Running the application
otherwise mutates files inside the read-only tree, violating the loop's central
safety property.

**RT-3 (trust boundary).** With this extension the loop *executes* the target, not
merely reads it; pointed at an arbitrary repository, that is arbitrary code
execution. The runtime phase MUST require explicit user approval before launching
anything, and `LOOP.md` MUST state the sandboxing expectations — mirroring the
existing dependency-installation rule.

**RT-4 (degradability).** The runtime phase is optional and degradable. The target
must build and start for journeys to run, and many legacy codebases — the loop's
natural audience — will not start on the first try. If the application cannot be
launched, the loop MUST complete static-only and record the journey layer as an
explicit unknown, never as a gate failure.

**RT-5.** Observed evidence follows the asymmetry rule EV-6: it confirms and adds,
never vetoes.

**RT-6.** The environment dependencies of the runtime phase (for the bundled
example: Java 8, Maven, Tomcat 9, Node, Playwright browsers) MUST be declared by the
phase and checked before launch; a missing dependency triggers the RT-4 degradation
path.

**RT-7.** The verifier gains a measured dimension, `journey_corroboration`,
computed by fixed formula, with mutation self-tests (e.g. corrupt a trace reference
or screenshot hash in a copy; the verifier must catch it). The verifier MUST know
how to re-resolve observed evidence — at minimum by checking recorded artefact
hashes; optionally by re-running the journey.

**RT-8 (reproducibility split).** The gate's `reproducibility` dimension currently
proves byte-identical re-runs; runtime traces embed timestamps, session ids, and
data-dependent output, so byte-identity is unachievable for them. The standard
splits: static artefacts (including `doc-claims.json`) remain byte-identical;
dynamic artefacts must be **semantically reproducible** — same steps, same status
codes, same DB-diff shape — after a defined normalization (strip volatile fields,
then compare). The normalization rule MUST be written into the verifier contract.
Without this split, `reproducibility` either fails forever or gets quietly
weakened; the latter is the real danger and is expressly prohibited.

## 6. Contract delta (summary of changes)

| # | Change | Files affected |
|---|---|---|
| 1 | `evidence.kind: parsed \| observed \| asserted` on provenance; `conflicts` node property; authority rule stated normatively | `.agent-loop/contracts/semantic-graph.schema.json`, `.agent-loop/LOOP.md` |
| 2 | New artefacts: `doc-claims.json`, `runtime/journeys.json` (+ their schemas) | `.agent-loop/contracts/doc-claims.schema.json`, `.agent-loop/contracts/journeys.schema.json` |
| 3 | Two new optional, degradable phases | `.agent-loop/skills/09-journey-walker.md`, `.agent-loop/skills/10-doc-alignment.md`, conductor sequence in `.agent-loop/skills/00-loop-conductor.md` |
| 4 | Two new measured gate dimensions (`assertion_grounding`, `journey_corroboration`) with mutation self-tests; reproducibility normalization rule | `.agent-loop/contracts/verification.schema.json`, `.agent-loop/skills/07-verifier.md`, `.agent-loop/tools/verifier/` |
| 5 | Explicit approval + sandbox requirements for the runtime phase; removal of the "no web automation" exclusion, replaced by the versioned runtime contract | `.agent-loop/LOOP.md` (scope and safety sections) |
| 6 | Claim extraction registered as a model-driven parser with manifest and fixture smoke tests | `.agent-loop/contracts/parser-registry.schema.json` conventions, parser registry artefact |

The existing gate rule is unchanged: all dimensions — now ten — must score 8 or
higher, every score is `{value, derived_from, measurement}` computed by fixed
formula, and a pass verdict counts only if the mutation self-test has shown the
gate able to fail.

## 7. Implementation sequence

The extensions MUST be implemented in this order:

**Milestone 1 — Evidence model groundwork.** Schema changes from row 1 of the
contract delta: `evidence.kind`, conflict representation, authority rule in
`LOOP.md`. This is shared infrastructure; both extensions depend on it.

**Milestone 2 — Documentation alignment (Extension A).** Phase
`10-doc-alignment.md`, `doc-claims.json`, `assertion_grounding` dimension,
mutation self-test. Validate against `taskdesk-legacy/MIGRATION_SOURCE_CATALOG.md`
as the first fixture: the discovered graph already exists, so confirmed /
contradicted / unverifiable statuses are checkable by hand.

**Milestone 3 — Runtime journeys (Extension B).** Phase `09-journey-walker.md`,
built on the extended evidence model, starting with the narrowest valuable slice:
walk the journeys the (by then doc-seeded) `Flow` hypotheses predict, against a
disposable database copy, and record **corroboration only**. Instantiating new
behavioural nodes, security diffing, and DB-diff side-effect proof follow once the
corroboration slice passes the gate.

Rationale for the order: documentation evidence is cheap, static, reproducible,
needs no new trust boundary, immediately improves the report's language — and its
hardest problem (authority ranking, conflict representation) is exactly the schema
groundwork the runtime extension also needs. Only one of the two extensions can be
added without renegotiating the loop's safety and reproducibility contracts, so it
goes first.

## 8. Risks and mitigations

| Risk | Extension | Mitigation |
|---|---|---|
| Docs lie or go stale; a doc-only node is the "fluent but false diagram" the loop exists to prevent | A | Authority rule EV-2/EV-3: asserted evidence never sufficient for existence; verifier's `semantic_graph_provenance` dimension enforces it, closing the score-inflation loophole |
| Interpretive claim extraction (LLM reading prose) grounding interpretation | A | DOC-2 (span provenance), DOC-3 (registered parser with smoke tests), DOC-4 (claims feed hypotheses, not the graph) |
| Silent resolution of doc/code contradictions | A | EV-5: conflicts are represented, reported, never dropped |
| Coverage bias: graph drifts toward "what the demo user clicked" | B | EV-6/RT-5 asymmetry rule: observe-confirm, never veto |
| Mutation of the read-only source tree by the running app | B | RT-2: disposable DB copy, sandboxed runtime directory |
| Arbitrary code execution against untrusted repositories | B | RT-3: explicit approval gate, documented sandbox expectations |
| Fragile environment; legacy targets that will not start | B | RT-4/RT-6: declared dependencies, degradable phase, unknown-not-failure |
| Quiet weakening of the reproducibility gate | B | RT-8: explicit split standard with a written normalization rule |

## 9. Acceptance criteria

The extension is complete when:

1. A loop run over `taskdesk-legacy/` with documentation alignment enabled produces
   a `doc-claims.json` in which every claim from `MIGRATION_SOURCE_CATALOG.md`
   carries span provenance and a definite status, and the final report contains a
   drift section.
2. No node in the resulting semantic graph holds `validated` or `accepted` status
   on asserted evidence alone (verifier-enforced).
3. A loop run with the runtime phase enabled produces at least one `Flow` node
   grounded in a replayable journey trace, with the source tree (including the
   committed SQLite file) byte-identical before and after the run.
4. The same run, repeated, passes the split reproducibility standard: static
   artefacts byte-identical, `journeys.json` semantically identical after
   normalization.
5. All ten gate dimensions score ≥ 8, and the mutation self-test demonstrates the
   two new dimensions can fail (forged doc span; corrupted trace reference).
6. With documentation absent or the target unable to start, the loop completes
   static-only, recording each missing layer as an explicit unknown.
