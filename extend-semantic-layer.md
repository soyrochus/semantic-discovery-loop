# Extending the semantic layer: runtime journeys and documentation as evidence

An analysis of two candidate extensions to the semantic discovery loop — Playwright-driven
user journeys and the incorporation of functional/technical documentation — focused on
what each contributes to the **Semantic Construct Graph**, and what each costs.

## Where the current model stops

The loop today admits exactly one evidence class: **static, parser-derived facts from the
local source tree**. That discipline is the repo's core rule ("the AI proposes, the
repository proves") and it works — but the bundled example run shows precisely where it
runs out:

- **Zero `Flow` nodes.** `Flow` is in the kernel vocabulary, yet the taskdesk-legacy run
  instantiated none. The edge vocabulary (`triggers`, `renders`, `uses`, `part-of`)
  captures single hops — Action renders View, Action uses Component — but a *journey*
  (login → task list → detail → edit → save) is a claim about ordered, stateful
  traversal that static parsing of `struts-config.xml` forwards can suggest but never
  prove. The one construct the kernel reserves for user-visible behaviour over time is
  exactly the one static evidence could not ground.
- **The run's only `UnknownSemanticConstruct` is a runtime gap.** Node
  `sem:unknown:runtime-row-semantics` records that the schema parser saw table
  structure but not "row contents and business meaning of seed records." The loop
  itself, honestly applied, flagged that its evidence class cannot see behaviour or
  data semantics.
- **Names come from identifiers.** `DataObject: TASK`, `Action: taskAssign` — the graph
  speaks the code's vocabulary because code is the only witness. Whether the business
  calls that "assignment", "dispatch", or "escalation" is invisible.

Both extensions attack these gaps from different sides: Playwright adds **observed
evidence** (what the running application actually does); documentation adds **asserted
evidence** (what humans claim it does and what they call it). The design question is the
same for both: how to admit a new evidence class without breaking the rule that the
repository proves existence.

---

## Part 1 — Playwright: observed runtime evidence

### Possibilities

**1. Instantiating `Flow` — the missing kernel type.**
A Playwright script that logs in as `operator1`, opens the task list, edits a task, and
saves is a machine-checkable witness for a `Flow` node. Each trace step carries a URL
(→ matches a `Route` source node), a rendered page (→ matches a `View`), and a form
submission (→ matches an `Action` and its form bean fields). A `Flow` grounded in a
replayable trace is *stronger* evidence than anything static analysis produces for it,
because it is demonstrated rather than inferred. This is the single highest-value
addition: it fills the one kernel type the example run left empty.

**2. Corroborating the statically-derived graph.**
Every statically inferred `EntryPoint`/`Action`/`View` triple can be *visited*: does
`/taskDetail.do` actually render `taskDetail.jsp`'s output? Do the form fields in the
rendered HTML match the `FormBean` properties the parser extracted? Corroboration turns
a one-witness claim into a two-witness claim and could be recorded as a confidence
boost per node (statically derived + runtime-confirmed) without changing what counts as
existence proof.

**3. Proving side-effect edges empirically.**
The graph asserts Action → DataStore write edges from SQL parsing. With a disposable
copy of `taskdesk-demo.sqlite`, the loop can diff the database before and after a
journey step and *observe* that `/taskSave.do` inserted a `TASK_AUDIT` row. That
converts the weakest static claims (data-flow through JDBC string concatenation) into
observed facts — and directly answers the run's own `UnknownSemanticConstruct` about
seed-row semantics, since journeys read and display real rows.

**4. Grounding `SecurityElement` and `Rule` behaviourally.**
Role-based behaviour (manager-only reopen, operator owner-scoping) is scattered across
session checks in Java code — statically visible as fragments, behaviourally visible as
a whole. Running the same journey as `operator1` and `manager1` and diffing what is
reachable is direct evidence for `SecurityElement` nodes and authorization `Rule`s.
Likewise validation `Rule`s: submit an empty form, observe the error path. The example
run has exactly one `secured-by` edge; journeys would multiply that with stronger
evidence.

**5. Demonstrable evidence in the report.**
Traces, screenshots, and HTTP exchanges are evidence a *human* can inspect in seconds.
The report stops being "claims with file/line citations" and gains "claims with
replayable demonstrations" — a `journeys.json` artefact plus per-step screenshots would
be the most persuasive artefact the loop produces. "Demonstrate user journeys" is not
just evidence collection; it is the report's best exhibit.

### Consequences

**1. It is an explicit scope change.**
`LOOP.md` currently states: *"No web automation… This version is a manually invoked,
file-based, prompt/skill-driven demonstrator."* Adding Playwright is not an incremental
tweak; it is a new loop version with a revised contract. That is fine — but it must be
versioned, not slipped in.

**2. The evidence taxonomy and schemas must be extended.**
Provenance today is `{source_node, file, span}` — a file/line claim. A runtime witness
is a different shape: trace id, request/response pair, screenshot hash, DB-diff, the
journey script that produced it, and the commit + DB snapshot it ran against.
`semantic-graph.schema.json` needs an evidence `kind` (`parsed | observed`), and the
verifier needs to know how to *re-resolve* observed evidence (re-run the journey? check
the trace file hash?). This is real contract work, not decoration.

**3. Reproducibility — the gate's hardest dimension — gets strictly harder.**
The verifier currently proves byte-identical re-runs. Runtime traces embed timestamps,
session ids, and data-dependent output; byte-identity is gone. The gate needs either
normalization (strip volatile fields, then compare) or a split standard: static
artefacts stay byte-identical, dynamic artefacts must be *semantically* reproducible
(same steps, same status codes, same DB-diff shape). Without this, `reproducibility`
either fails forever or gets quietly weakened — the latter being the real danger.

**4. The read-only constraint needs a carve-out done carefully.**
Running the app *mutates* `db/runtime-data/taskdesk-demo.sqlite` — which is inside the
read-only source tree — and deploying a WAR writes outside the allowed paths. The rule
must become: journeys run against a **disposable copy** of the database and a sandboxed
runtime directory under `.work/semantic-loop/runtime/`; the source tree, including the
committed SQLite file, remains untouched. Violating this casually would break the
loop's central safety property.

**5. Executing the target is a trust-boundary change.**
Today the loop *reads* the repository; with Playwright it *runs* it. For the bundled
example that is harmless; pointed at an arbitrary repository, it is arbitrary code
execution. The contract must say so explicitly (runtime phase requires explicit
approval, sandboxing expectations), the same way dependency installation already does.

**6. Heavy, fragile environment dependencies.**
The loop currently needs `python3` and `git`. Journeys need Java 8, Maven, Tomcat 9,
Node, and Playwright browsers — and the target must actually build and start. Many
legacy codebases (the loop's natural audience) will not start on the first try. The
design consequence: the runtime phase must be **optional and degradable** — if the app
cannot be launched, the loop completes static-only and records the journey layer as an
explicit unknown, never as a gate failure.

**7. Coverage bias: absence of observation is not absence of behaviour.**
A journey proves what it walked; it says nothing about what it did not. If corroboration
raises confidence, unvisited-but-real constructs must not be *lowered* — otherwise the
graph drifts toward "what the demo user clicked" instead of "what the application is".
The rule should be asymmetric: runtime evidence can confirm and add, never veto a
statically-grounded node (a runtime *contradiction* — route 404s, view never renders —
becomes a recorded conflict, not a silent deletion).

---

## Part 2 — Functional and technical documentation as evidence

### Possibilities

**1. Domain vocabulary the code cannot supply.**
Functional docs are where "TASK" becomes "work ticket", where `taskReopen` becomes "the
escalation exception path". The semantic layer's whole purpose is to speak
application-level language, yet its only naming source today is identifiers. A
terminology mapping (business term ↔ semantic node) sourced from functional docs makes
the graph — and especially the final report — legible to the people who own the system.
This is the cheapest, highest-leverage use.

**2. Hypothesis seeding — docs propose, the repository still proves.**
A functional spec listing "users can export the activity report as CSV" is a *candidate*
`Flow`/`Action` the loop should go looking for. Docs become a source of expected
constructs that static (and runtime) evidence must confirm. This slots perfectly into
the existing kernel rule: nothing changes about what instantiates a node; docs only
supply the search agenda. The bundled example already contains the perfect test case:
`taskdesk-legacy/MIGRATION_SOURCE_CATALOG.md` is a hand-authored functional/technical
catalog (routes, actions, business rules) that could be parsed into claims and
cross-checked against the discovered graph.

**3. Drift detection as a first-class output.**
Where a doc claims X and the code proves Y (or nothing), that mismatch is *valuable
output*, not noise — stale documentation is one of the primary facts a discovery loop
can surface about a legacy system. This repo has already demonstrated the pattern
manually: `article-repo-drift.md` is exactly a claims-vs-repository verification, done
by hand. A `doc-claims.json` artefact with per-claim status
(`confirmed | contradicted | unverifiable`) generalizes it.

**4. Boundaries and intent from technical docs.**
`Module` boundaries, `Integration` declarations, and the *why* of `Configuration`
entries are notoriously under-determined by code. An architecture doc saying "reporting
is isolated because of the nightly batch window" gives `Module` and `Job` nodes intent
properties no parser can derive. The example run's 8 `Module` nodes are
package-structure guesses; a technical doc could confirm or correct the partitioning.

**5. It is already half-happening — undisciplined.**
The example run's `UnknownSemanticConstruct` is grounded in
`db/runtime-data/README.md` with `evidence_type: "documented-row-counts"` — asserted
documentation evidence has *already* crept into the graph, without a declared evidence
class or authority rule. Formalizing documentation evidence is partly just legalizing
and disciplining what the loop already found itself needing. `DocumentationSection`
nodes (26 in the run) exist in the source graph; today nothing semantic is built from
them.

### Consequences

**1. Docs lie, and go stale — authority ranking is mandatory.**
The single biggest risk: a semantic node grounded *only* in documentation is exactly the
"fluent but false architecture diagram" the loop exists to prevent. The evidence classes
need an explicit authority order for **existence** claims: `parsed` (code) > `observed`
(runtime) > `asserted` (docs) — with docs authoritative only for *naming and intent*,
never sufficient for existence. Concretely: an asserted-only construct may exist in the
graph only as `UnknownSemanticConstruct` or a `candidate` type, never as an accepted
node. The verifier's `semantic_graph_provenance` dimension must be taught this, or docs
become a score-inflation loophole.

**2. Contradictions need representation, not resolution.**
When the doc says "managers approve tasks" and no approval code exists, the graph must
record a *conflict* (claim, counter-evidence, status), not silently drop one side.
That is a new construct (or a property convention) in the semantic graph schema and a
new section in the report. Silent resolution in either direction destroys the loop's
honesty guarantee.

**3. Extracting claims from prose is itself interpretation.**
Parsers emit deterministic facts; "parse the functional spec" is an LLM reading prose —
interpretation grounding interpretation, the double-hermeneutic problem. Mitigations
that fit the existing discipline: (a) every extracted claim carries file + span
provenance into the doc, exactly like source evidence, so a human can check the
reading; (b) claim extraction is a registered "parser" with a manifest and smoke tests
on fixture docs, even though it is model-driven — making its fallibility visible in the
parser registry rather than hidden in the graph builder; (c) claims feed the hypothesis
agenda (see Possibility 2) rather than the graph directly wherever possible.

**4. Scope: local repository only, or the rule breaks.**
"Only local repository evidence may instantiate semantic nodes" extends cleanly to docs
*in the repo*. Confluence pages and wikis do not qualify; if they matter, they must be
snapshotted into the repository first (with retrieval date), becoming local artefacts
with provenance. Otherwise the source-of-truth rule quietly dissolves.

**5. Verification cost is modest — unlike Playwright.**
Unlike the runtime extension, documentation evidence needs no new execution
environment, keeps byte-identical reproducibility (docs are files), and respects
read-only trivially. The gate needs one new measured dimension (e.g.
`assertion_grounding`: % of doc-derived claims resolved to
confirmed/contradicted/unverifiable) and a mutation self-test case (forge a doc claim's
span; the verifier must catch it). This is the *low-risk* extension of the two.

---

## Synthesis: three evidence classes, one rule

| | `parsed` (static) | `observed` (Playwright) | `asserted` (docs) |
|---|---|---|---|
| Answers | what exists | what happens | what is meant |
| Kernel types served best | EntryPoint, Component, DataStore, Configuration | **Flow**, SecurityElement, Rule, side-effect edges | naming/intent everywhere; Module boundaries, Integration, candidate types |
| May instantiate accepted nodes? | yes | yes (behavioural types) | **no** — hypotheses, names, intent, conflicts only |
| Reproducibility | byte-identical | semantic (normalized traces) | byte-identical |
| New failure modes | — | flaky env, coverage bias, code execution | stale/false claims, interpretive extraction |
| Cost | in place | high (env, contract, gate rework) | low-moderate |

The invariant that must survive both extensions: **evidence classes may disagree, and
the graph must say so.** Runtime confirms or contradicts static claims; docs propose and
name them; the repository's code remains the only sufficient proof of existence.

### If implemented, the minimal contract delta

1. `evidence.kind: parsed | observed | asserted` in `semantic-graph.schema.json`, with
   the authority rule stated in `LOOP.md`.
2. Two new artefacts: `journeys.json` (steps, trace refs, DB-diffs, screenshots under
   `.work/semantic-loop/runtime/`) and `doc-claims.json` (claim, doc provenance,
   status).
3. Two new optional phases/skills — `09-journey-walker.md`, `10-doc-alignment.md` —
   both **degradable**: their absence is a recorded unknown, not a gate failure.
4. Two new measured gate dimensions (`journey_corroboration`, `assertion_grounding`)
   with mutation self-tests, and a normalization rule so `reproducibility` survives
   dynamic artefacts.
5. Explicit approval + sandbox requirements for the runtime phase (it executes the
   target), mirroring the existing dependency-installation rule.

### Recommendation

Sequence them. **Documentation first**: it is cheap, static, reproducible, needs no new
trust boundary, immediately improves the report's language, and its hardest problem
(authority ranking, conflict representation) is exactly the schema groundwork the
runtime extension also needs. **Playwright second**, built on that extended evidence
model, starting with the narrowest valuable slice: walk the journeys the (by then
doc-seeded) `Flow` hypotheses predict, against a disposable database copy, and record
corroboration only. The loop's empty `Flow` column and its lone runtime-shaped unknown
show both extensions are aimed at real gaps — but only one of them can be added without
renegotiating the loop's safety and reproducibility contracts, so it should go first.
