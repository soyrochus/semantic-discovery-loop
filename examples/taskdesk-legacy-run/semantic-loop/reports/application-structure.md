# TaskDesk Legacy Application Structure

Status: FINAL - verification passed (all scores >= 8)

## Application overview
TaskDesk Legacy is represented as `sem:application:taskdesk-legacy`, grounded in the Maven WAR module (`taskdesk-legacy/pom.xml`) and the Struts servlet mapping (`taskdesk-legacy/src/main/webapp/WEB-INF/web.xml`). Its README describes it as a simulated Struts 1.x / JSP / JDBC application packaged as a WAR — a description confirmed by, and recorded as asserted evidence alongside, the parsed build and configuration facts.

## Detected technology stack
- Maven WAR packaging, Struts 1.x, JSP/JSTL, Servlet 2.5, SQLite JDBC, SQL DDL, and a live SQLite demo database are detected from `pom.xml`, `web.xml`, `struts-config.xml`, `taskdesk.properties`, `db/sql/001_schema_sqlite.sql`, and `db/runtime-data/taskdesk-demo.sqlite`.
- The documented Tomcat 9 requirement (javax.servlet, not jakarta.servlet) is confirmed by the provided-scope `javax.servlet:servlet-api` 2.5 dependency.

## Source inventory summary
- Scope: `taskdesk-legacy/**` plus `db/**`; files inventoried: 56.
- Language/format counts: {"CSS": 1, "JSP": 8, "Java": 31, "Markdown": 2, "Properties": 3, "SQL": 3, "SQLite": 1, "Shell": 2, "XML": 5}.

## Major modules/components
- Modules: action, service, DAO, form, model, util, view, and configuration modules are represented as `sem:module:*` nodes.
- Components detected: AuditDAO, AuditService, CsvExportUtils, DateUtils, JdbcConnectionManager, SecurityUtils, TaskDAO, TaskService, UserDAO, UserService.

## Entrypoints
- `sem:entrypoint:struts-action-servlet-do` maps `*.do` URLs to Struts ActionServlet; the suffix is derived from the parsed `url-pattern` element in `web.xml`.

## Views/screens (if detected)
- Detected JSP views: /jsp/accessDenied.jsp, /jsp/error.jsp, /jsp/login.jsp, /jsp/taskAssign.jsp, /jsp/taskDetail.jsp, /jsp/taskEdit.jsp, /jsp/taskList.jsp, /jsp/taskReport.jsp.
- `accessDenied.jsp` and `error.jsp` are reachable only through struts-config `<global-forwards>`, not from a specific action.

## Controllers/actions/handlers (if detected)
- Detected Struts actions: /login.do, /logout.do, /taskAssign.do, /taskComplete.do, /taskDetail.do, /taskEdit.do, /taskExport.do, /taskReopen.do, /taskReport.do, /taskSave.do, /tasks.do.

## Services/domain logic (if detected)
- Service classes are represented as `Component` nodes where Java classes are under `src/main/java/com/example/taskdesk/service/`, including task, user, and audit services.

## Data access and persistence (if detected)
- DAO components touch `TASK`, `APP_USER`, `TASK_COMMENT`, and `TASK_AUDIT`; each table is represented as a `DataStore` from Java SQL literals, `db/sql/001_schema_sqlite.sql`, and live SQLite schema introspection.
- `sem:datastore:sqlite` is grounded in the `taskdesk.db.url` configuration entry, `JdbcConnectionManager.java`, and `db/runtime-data/taskdesk-demo.sqlite`; the README-documented override order (system property, then `TASKDESK_DB_URL`, then classpath properties) is confirmed by `JdbcConnectionManager.loadDatabaseUrl`.
- Foreign-key and index evidence is present in the source graph from `sqlite-schema-v1`, including TASK to APP_USER, comments/audit to TASK and APP_USER, and indexes on status, priority, owner, due date, comment task, and audit task.
- Class-to-table `references` edges (word-boundary literal match, confidence 0.85, line evidence on every edge):
- `APP_USER` is referenced by: AuditDAO, TaskDAO, UserDAO.
- `TASK` is referenced by: TaskDAO.
- `TASK_AUDIT` is referenced by: AuditDAO.
- `TASK_COMMENT` is referenced by: TaskDAO.

## External integrations (if detected)
- `sem:integration:sqlite-jdbc` is grounded in the `org.xerial:sqlite-jdbc` Maven dependency (span from the maven-pom parser) and `Class.forName("org.sqlite.JDBC")`.

## Semantic type registry summary
- The kernel semantic vocabulary is used with accepted status only; no project-specific candidate types were needed.

## Documentation drift
- 9 claims were extracted from `taskdesk-legacy/README.md`, `db/runtime-data/README.md` by `doc-claims-v1` (model-driven reading; every claim carries a verbatim excerpt and span, re-resolved deterministically by check mode and the verifier): 8 confirmed, 0 contradicted, 1 unverifiable.
- Unverifiable `claim:db-readme:seed-row-counts` (db/runtime-data/README.md:9): The runtime demo database initially contains 3 APP_USER, 6 TASK, 5 TASK_COMMENT, and 8 TASK_AUDIT rows. — sqlite-schema-v1 introspects schema only and no parser reads row data from db/runtime-data/taskdesk-demo.sqlite, so the documented counts of the live database file cannot be settled statically. The seed SQL suggests but does not prove the current file contents. Recorded as asserted evidence on sem:unknown:runtime-row-semantics.
- No contradicted claims: documentation and code agree everywhere a claim could be checked against parsed evidence.
- Confirmed claims were applied to the semantic graph as asserted evidence (naming and intent only, per the authority rule): business descriptions on the application and SQLite datastore, the documented DB-URL override order on `sem:configuration:taskdesk-db-url` and `JdbcConnectionManager`, documented demo users on `sem:datastore:table:app_user`, and the documented runtime row counts now ground `sem:unknown:runtime-row-semantics` via `claim_ref`.

## Runtime journeys
- The runtime phase ran with recorded user approval against a **disposable copy** of `db/runtime-data/taskdesk-demo.sqlite` (`runtime/db/taskdesk-demo.sqlite`); the committed file's sha256 was recorded at launch and is re-verified by the gate (`jr-source-db-untouched`).
- `journey:login-task-review` (operator1): /login (200) -> /login (302) -> /taskDetail (200). Corroborates 7 statically derived nodes; instantiates `sem:flow:login-task-review` from 3 replayable trace files under `runtime/traces/` (sha256-referenced, screenshots included). Hypothesis: claim:taskdesk-readme:login-entry plus the static route chain /login -> /tasks -> /taskDetail from struts-config forwards.
- `journey:role-denied-operator` (operator1): /login (302) -> /taskAssign (200). Corroborates 3 statically derived nodes; instantiates `sem:flow:role-denied-operator` from 2 replayable trace files under `runtime/traces/` (sha256-referenced, screenshots included). Hypothesis: static role check in TaskAssignAction (SecurityUtils.isManager -> findForward("denied")); tests sem:rule:manager-role-checks behaviourally.
- `journey:role-allowed-manager` (manager1): /login (302) -> /taskAssign (200). Corroborates 4 statically derived nodes; instantiates `sem:flow:role-allowed-manager` from 2 replayable trace files under `runtime/traces/` (sha256-referenced, screenshots included). Hypothesis: same route as journey:role-denied-operator, walked as a manager; the diff proves the role rule is enforced, not merely declared.
- `journey:login-validation` (anonymous): /login (200) -> /login (200). Corroborates 3 statically derived nodes; instantiates `sem:flow:login-validation` from 2 replayable trace files under `runtime/traces/` (sha256-referenced, screenshots included). Hypothesis: Struts validator required fields on loginForm (validation.xml username/password); tests sem:rule:validator-required-fields behaviourally.
- Traces are normalized per the RT-8 rule (no timestamps, session ids, cookie/date values); observed evidence carries `kind: "observed"` with a `journey_ref` and boosts confidence without ever being required for existence of statically grounded nodes.
- Flow nodes instantiated from observed evidence: sem:flow:login-task-review, sem:flow:login-validation, sem:flow:role-allowed-manager, sem:flow:role-denied-operator.

### Behaviourally verified rules
- **Manager-only access is really enforced.** Behaviourally confirmed on /taskAssign.do: operator1 was denied (accessDenied) and manager1 was allowed (the action's own view). The role check fires at runtime, not merely in source. This is the operator-vs-manager diff: the same route, two actors, opposite outcomes — stronger than the source-only evidence, which could only show the check *exists*.
- **Required-field validation really fires.** Behaviourally confirmed: an empty login submission was rejected and returned to the login view with an error banner (journey:login-validation).
- No runtime contradictions: every rule the journeys probed behaved as the static evidence predicted. (A mismatch would have been recorded as an open `conflicts` entry on the affected node, never silently passed.)

### Runtime coverage and what it does NOT show
- **Walked routes:** `/login`, `/taskAssign`, `/taskDetail`. Absence of observation is not absence of behaviour — unwalked routes keep their static grounding untouched (EV-6); runtime only ever confirms and adds.
- **Write side-effects were NOT verified.** `sem:unknown:runtime-write-side-effects` records this explicitly: the phase confirmed write actions are reachable and authorization-gated, but took no before/after database diff, so whether a save actually persists rows is unverified by runtime evidence (only by static SQL reading). Deferred deliberately — the corroboration and access-control slices come first. This is reported, not hidden.
- The runtime picture is intentionally partial: it demonstrates login, navigation, access control, and validation, and is honest about the persistence behaviour it has not yet observed.

## Unresolved unknowns
- `sem:unknown:runtime-row-semantics`: schema and documented row counts are known, but row contents and business meaning of seed records in the live database file were not read by the schema parser. The documented counts are recorded as asserted evidence (`claim:db-readme:seed-row-counts`), which cannot prove the live file's contents.

## Assumptions
- Scope is limited to `taskdesk-legacy/**` plus `db/**`; package directories are treated as modules; Struts paths use the `.do` suffix from the parsed `web.xml` url-pattern; documentation alignment reads the two in-scope READMEs only.
- A tracked symlink under `taskdesk-legacy/runtime-data/` is recorded as an inventory uncertainty rather than followed.

## Confidence and evidence notes
- Route/action/view claims are high confidence because the struts-config-v1 parser extracts action paths, action classes, forms, and forwards with element spans.
- Table claims are high confidence because they are grounded in Java SQL literals, SQL DDL, and SQLite schema introspection.
- Asserted (documentation) evidence carries `kind: "asserted"` and a `claim_ref` into `doc-claims.json`; it contributes naming and intent only and never raises a node's status or confidence.

## Limitations
- JSP extraction is lexical and does not parse scriptlet Java.
- Java parsing is structural and does not do expression-level symbol resolution.
- SQLite parser reads schema only, not row data.
- Claim extraction is model-driven interpretation; anchors, spans, and excerpts are deterministic and re-checked, the reading is not.

## Verification
- Verified by `verifier-v1` (.agent-loop/tools/verifier); self-test caught 8/8 seeded mutations.
- Scores (measured, ten dimensions): {"assertion_grounding": 10, "inventory_coverage": 10, "journey_corroboration": 10, "parser_validity": 10, "report_coverage": 10, "reproducibility": 10, "semantic_graph_provenance": 10, "semantic_type_quality": 10, "source_graph_consistency": 10, "unknowns_handling": 10}.
