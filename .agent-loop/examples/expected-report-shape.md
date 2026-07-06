# Expected shape — application-structure.md

This is a *shape reference* for `.work/semantic-loop/reports/application-structure.md`.
Section headings and evidence-citation style are normative; all content below is
illustrative placeholder text, not facts about this repository.

---

# Application Structure — <application name>

Status: FINAL — verification passed (all scores ≥ 8)
<!-- or: Status: PARTIAL — max iterations reached with gate failures: parser_validity -->

Repository fingerprint: `<git HEAD hash>` · Loop iteration: N · Generated: <date>

## Application overview

One or two paragraphs: what the application appears to be and do, stated with explicit
confidence and grounded in named evidence (e.g. "a task management web application
[`sem:application:taskdesk`, confidence 0.9], based on <evidence>").

## Detected technology stack

| Technology | Evidence | Confidence |
|---|---|---|
| e.g. Java 8 / Servlet | `pom.xml:12–18`, `web.xml` | 0.95 |

## Source inventory summary

Totals from `inventory.json`: file counts by language and role, exclusions applied,
inventory uncertainties.

## Major modules/components

One subsection or table row per `sem:module:*` / `sem:component:*` node: name, purpose,
key source locations, confidence.

## Entrypoints

Each `sem:entrypoint:*` node: how the application is entered (HTTP route, main class,
job trigger), citing the grounding evidence file and span.

## Views/screens (if detected)

`sem:view:*` nodes, or an explicit "No views detected; evidence considered: <what>".

## Controllers/actions/handlers (if detected)

`sem:action:*` nodes with their routes/handlers, e.g.
"**Login** (`sem:action:login`, confidence 0.91) — grounded in action mapping
`WEB-INF/struts-config.xml:42–49` and handler `LoginAction.execute`
(`src/main/java/com/example/LoginAction.java:21–73`)."

## Services/domain logic (if detected)

## Data access and persistence (if detected)

`sem:dataobject:*` and `sem:datastore:*` nodes, tables/entities, and which components
read/write them.

## External integrations (if detected)

## Semantic type registry summary

Table of types used: type_id, status, node count. Candidate/proposed types explicitly
marked **not yet accepted**.

## Unresolved unknowns

Every `UnknownSemanticConstruct` node and open uncertainty: what exists, what evidence
was found, why it could not be classified.

## Assumptions

The active assumptions from `assumptions.json` that shape this report (id, statement,
confidence).

## Confidence and evidence notes

How confidence values were assigned; which claims rest on single-source vs. corroborated
evidence; pointers to `semantic-graph.json` for full provenance.

## Limitations

What this analysis did not cover: parser gaps, excluded areas, dynamic behaviour not
inferable statically, and (if partial) the corrective actions still pending.
