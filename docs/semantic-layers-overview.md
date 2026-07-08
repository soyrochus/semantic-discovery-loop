# Semantic Layers Overview

The loop separates raw source facts from application meaning. This keeps parser output
deterministic while still letting the semantic graph answer higher-level questions such
as "which view renders this action?" or "what evidence proves this user story?".

## Layer Model

| Layer | Artefact | Meaning |
| --- | --- | --- |
| Inventory | `inventory.json` | Repository files, languages, sizes, and candidate artifact classes. It scopes parsing but does not claim application meaning. |
| Layer 1: Source Construct Graph | `source-graph.json` | Parser-derived facts: files, classes, methods, XML elements, routes, templates, dependencies, SQL statements, database objects. |
| Type Registry | `semantic-types.json` | The semantic vocabulary and detection rules allowed for the semantic graph. |
| Layer 2: Semantic Construct Graph | `semantic-graph.json` | Application concepts grounded in source, documentation, or runtime evidence. |
| Documentation Claims | `doc-claims.json` | Claims extracted from in-repository documentation. They capture asserted intent and naming. |
| Runtime Journeys | `runtime/journeys.json` | Observed behaviour from approved, replayable runtime walks. |

Only Layer 2 answers application-meaning questions directly. The other layers provide
the evidence, vocabulary, and checks that make those answers auditable.

## Evidence Classes

| Kind | Authority | Typical Evidence |
| --- | --- | --- |
| `parsed` | Highest authority for existence. | Java structures, Struts mappings, JSP links/forms, Maven dependencies, SQL DDL, SQLite schema. |
| `observed` | Confirms and adds behaviour. | HTTP steps, rendered pages, redirects, validation messages, access-control outcomes. |
| `asserted` | Naming and intent only. | User stories, functional specs, README claims, design notes stored in the repository. |

Authority for existence is `parsed > observed > asserted`. Asserted evidence alone may
create a candidate, proposed construct, or `UnknownSemanticConstruct`, but it cannot
validate a stable application construct by itself.

## Registered Kernel Semantic Types

These are the current kernel types named by `.agent-loop/LOOP.md`. Project-specific
types may specialize them, but should only be introduced after trying the kernel,
specialization, and `UnknownSemanticConstruct` first.

This table is the type vocabulary, not the list of semantic nodes found in a run. The
actual node population lives in `.work/semantic-loop/semantic-graph.json` for a local
run, or under `examples/*/semantic-loop/semantic-graph.json` for committed reference
runs.

| Type | Definition |
| --- | --- |
| `Application` | The analyzed software system as a coherent deployable or runnable unit. |
| `Module` | A cohesive subsystem, package, layer, feature area, or build unit inside the application. |
| `EntryPoint` | A callable or invokable boundary into the application, such as a route, servlet mapping, CLI command, scheduled trigger, or bootstrap class. |
| `Interface` | A user, system, or integration surface exposed by the application. |
| `Flow` | A multi-step behaviour or journey through actions, views, rules, and data operations. |
| `Action` | A meaningful operation the application performs in response to input or a trigger. |
| `View` | A rendered or returned presentation artefact, such as a JSP page, template, screen, or response view. |
| `Component` | A reusable implementation unit that supports application behaviour but is not itself a whole module. |
| `DataObject` | A domain or transfer shape represented in code, forms, queries, or persisted records. |
| `DataStore` | A persistence location or external storage resource such as a table, database, file store, or queue. |
| `Rule` | A validation, authorization, routing, transformation, or business constraint. |
| `Integration` | A connection to another system, protocol, service, database, or external dependency. |
| `Job` | A scheduled, background, batch, or asynchronous unit of work. |
| `Configuration` | Runtime or build-time settings that influence application behaviour. |
| `SecurityElement` | Authentication, authorization, session, credential, or access-control mechanism. |
| `UnknownSemanticConstruct` | A disciplined placeholder for locally evidenced meaning that cannot be classified yet. |

## Current Local Graph Snapshot

The current `.work/semantic-loop/semantic-graph.json` contains 55 concrete semantic
nodes and 95 semantic edges. It uses 14 of the 16 registered kernel types:

| Type | Node Count | Examples |
| --- | ---: | --- |
| `Application` | 1 | `TaskDesk Legacy` |
| `Module` | 5 | Web MVC layer, task workflow, persistence, reporting/export, security/session layer |
| `EntryPoint` | 1 | `*.do` Struts ActionServlet |
| `Action` | 11 | `/login`, `/taskSave`, `/taskComplete`, `/taskReport`, `/tasks` |
| `View` | 8 | `/jsp/login.jsp`, `/jsp/taskList.jsp`, `/jsp/taskEdit.jsp`, `/jsp/taskReport.jsp` |
| `Component` | 7 | `TaskService`, `TaskDAO`, `AuditDAO`, `JdbcConnectionManager` |
| `SecurityElement` | 1 | `SecurityUtils` session helpers |
| `DataObject` | 5 | `Task`, `TaskComment`, `TaskAuditEntry`, `User`, `TaskSearchCriteria` |
| `DataStore` | 5 | TaskDesk SQLite database, `APP_USER`, `TASK`, `TASK_AUDIT`, `TASK_COMMENT` |
| `Rule` | 6 | login required, manager assignment, task-save validation, completed-task edit lock |
| `Configuration` | 1 | `TASKDESK_DB_URL` / `taskdesk.db.url` |
| `Integration` | 2 | SQLite JDBC driver, CSV export |
| `Flow` | 1 | login redirects to task list |
| `UnknownSemanticConstruct` | 1 | runtime journey layer not executed under disposable DB control |

`Interface` and `Job` are registered types but are not used by the current local graph.
That is valid: registered types define the vocabulary available to the loop; a run only
uses the types for which it found local evidence.

## Type Status

Every type in `semantic-types.json` has a status:

| Status | Meaning |
| --- | --- |
| `candidate` | A possible type with insufficient support. |
| `proposed` | A plausible type with examples and rules, but not yet stable. |
| `validated` | A type proven useful for the current repository. |
| `accepted` | A stable type allowed in final reports. |
| `deprecated` | A type that remains for compatibility but should not be used for new constructs. |

Only `accepted` and `validated` types should back stable constructs in final reports.

## Source-To-Semantic Mapping

A semantic node should explain both what it is and why the repository proves it. Common
mapping patterns are:

| Source Evidence | Semantic Result |
| --- | --- |
| Struts action mapping plus handler method | `EntryPoint` or `Action` |
| JSP template referenced by a forward | `View` |
| Form bean plus validation rules | `DataObject` and `Rule` |
| DAO method plus SQL/table evidence | `DataStore`, `DataObject`, and read/write edges |
| Maven dependency or endpoint configuration | `Integration` or `Configuration` |
| Runtime trace through pages and actions | `Flow` |
| Documentation user story grounded by source/runtime evidence | Named semantic intent with traceable support |

Edges carry application-level relations such as `part-of`, `triggers`, `renders`,
`reads-from`, `writes-to`, `integrates-with`, `secured-by`, `scheduled-by`, and
`validates`.

## Unknowns and Conflicts

Unknowns are part of the model. A missing database write proof, ambiguous route, or
unvisited branch should be recorded as an unknown rather than converted into a confident
claim.

Conflicts are also explicit. If documentation claims a feature exists but parser and
runtime evidence do not support it, the semantic graph keeps the documentation claim,
records the counter-evidence, and marks the conflict open until later evidence resolves
it.

## Answering Proof Questions

Questions like "prove that US005 is idempotent" become possible when the relevant
artefacts exist and the claim is grounded:

1. `doc-claims.json` identifies US005 and its exact repository document span.
2. `semantic-graph.json` maps US005 to the actions, flows, rules, and data operations
   that implement or contradict it.
3. `source-graph.json` provides parser-derived proof of handlers, queries, tables, and
   configuration.
4. `runtime/journeys.json`, if available, provides observed behaviour for replayed user
   paths.
5. `verification.json` shows whether the evidence is strong enough to trust.

If idempotence depends on data side effects that were not parsed or observed, the
correct answer is an explicit unknown or partial proof, not a guessed yes.
