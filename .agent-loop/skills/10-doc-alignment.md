# Skill 10 — Documentation Alignment

## Purpose

Align the discovered semantic graph with what the repository's documentation *claims*
about the application. Produce `.work/semantic-loop/doc-claims.json` (schema:
`contracts/doc-claims.schema.json`) and apply the results to the semantic graph as
**asserted** evidence — naming, intent, hypotheses, and conflicts, never existence.

Runs after the semantic graph builder (skill 06) and before verification (skill 07).

## The rule this phase lives under

Docs propose, the repository proves. Asserted evidence obeys the authority order in
`LOOP.md` (`parsed > observed > asserted`):

- A claim never instantiates a `validated`/`accepted` node. A documented construct
  that no parsed evidence supports may enter the graph only as `candidate`/`proposed`
  or as an `UnknownSemanticConstruct`.
- Docs *are* authoritative for naming and intent: business terminology and the "why"
  behind constructs go onto existing nodes as properties, with an asserted provenance
  entry (`kind: "asserted"`, `claim_ref` pointing into `doc-claims.json`).
- Where docs and code disagree, record a conflict on the affected node (`conflicts`:
  claim, counter-evidence, status) — stale documentation is a first-class finding,
  not noise, and silent resolution in either direction is a contract violation.

## Inputs

- `DocumentationSection`/`File` nodes in `source-graph.json` pointing at documentation
  files (`*.md`, `*.txt`, and any prose files the inventory classified as docs).
- Only files **inside the repository** qualify. External sources (wikis, Confluence,
  tickets) must first be snapshotted into the repository with a retrieval date;
  otherwise they do not exist for this loop.
- `semantic-graph.json` and `semantic-types.json` as built so far.

## Procedure

1. **Collect documents.** List every documentation file in scope from the source
   graph/inventory. If there are none, write no `doc-claims.json`; record the missing
   layer as an explicit unknown (an assumption in `assumptions.json` and, where a
   construct is affected, an entry in its `unknowns`) and stop — the phase is
   degradable and its absence is never a gate failure.
2. **Anchor.** Copy the gallery tool `.agent-loop/tools/doc-claims/` to
   `.cache/scripts/parsers/doc-claims-v1/` (gallery protocol), run its smoke test,
   then run anchor mode over the collected documents. Anchors (headings, list items,
   table rows, each with a line span) are the addressable units claims cite.
3. **Extract claims.** Read the documents and state each checkable claim against the
   contract: id, `claim_type` (`terminology | feature | rule | boundary | intent |
   data | other`), normalized `text`, **verbatim** `excerpt`, `file`, and `span`.
   This step is model-driven interpretation — that is exactly why every claim must
   carry a span a human can re-read. Prefer claims anchored to extracted anchors;
   a claim read from prose must cite its paragraph's lines directly. Do not
   manufacture claims the document does not make.
4. **Resolve each claim** against the graphs, and set its status:
   - `confirmed` — parsed evidence supports it; list the supporting semantic nodes in
     `mapped_nodes` (required non-empty) and say how in `status_evidence`.
   - `contradicted` — parsed evidence refutes it; record what was found instead, and
     add a `conflicts` entry (with `claim_ref`) to the node the claim is about when
     one exists.
   - `unverifiable` — nothing local can settle it; say what was searched.
5. **Apply the aligned results to the semantic graph:**
   - **Terminology:** put confirmed business terms on the mapped nodes (e.g.
     `properties.business_term`, `properties.business_description`) with an asserted
     provenance entry carrying `claim_ref`.
   - **Intent:** attach documented rationale for `Module` boundaries, `Integration`s,
     `Configuration` entries the same way.
   - **Hypotheses:** for documented constructs with no parsed evidence, either add a
     `candidate` node grounded in the claim (asserted-only ⇒ status must stay
     `candidate`/`proposed`) or record the gap as an `UnknownSemanticConstruct` —
     and hand the hypothesis to the next iteration's agenda: a doc-claimed flow or
     action is a search instruction for skills 04–06, not a graph fact.
6. **Check before verifying.** Run the tool's check mode
   (`parser.py --check doc-claims.json --repo . --semantic-graph
   .work/semantic-loop/semantic-graph.json`) and fix what it reports; the verifier
   will re-derive the same facts independently and less forgivingly.
7. **Register the extraction** in `parser-registry.json`: parser_id `doc-claims-v1`,
   origin `gallery` (or `gallery-adapted`), artifact type `documentation-claims`,
   with the smoke test listed. Registration makes the extractor's fallibility
   visible; it does not make its output deterministic — the anchors and checks are
   deterministic, the reading is not, and `known_limitations` must say so.

## Rules

- Write only `.work/semantic-loop/**` and `.cache/scripts/**`; documentation files
  are source and stay untouched.
- Every claim's `excerpt` must occur verbatim within its cited span — the verifier
  re-resolves this (`assertion_grounding`), and a forged span is a gate failure.
- Never lower a parsed-grounded node's confidence because documentation is silent
  about it. Docs confirm, name, and dispute; they do not veto.
- Never delete a claim because it turned out `contradicted` — drift is output. The
  report (skill 08) gets a **Documentation drift** section listing contradicted and
  unverifiable claims whenever this phase ran.
- Claim ids are stable across iterations (`claim:<doc-slug>:<claim-slug>`), so
  conflicts and provenance keep resolving after a re-run.
