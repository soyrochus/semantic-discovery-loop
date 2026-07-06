# TaskDesk Legacy Application Structure

Status: FINAL - verification passed (all scores >= 8)

## Application overview
TaskDesk Legacy is represented as `sem:application:taskdesk-legacy`, grounded in the Maven WAR module (`taskdesk-legacy/pom.xml`) and the Struts servlet mapping (`taskdesk-legacy/src/main/webapp/WEB-INF/web.xml`).

## Detected technology stack
- Maven WAR packaging, Struts 1.x, JSP/JSTL, Servlet 2.5, SQLite JDBC, SQL DDL, and a live SQLite demo database are detected from `pom.xml`, `web.xml`, `struts-config.xml`, `taskdesk.properties`, `db/sql/001_schema_sqlite.sql`, and `db/runtime-data/taskdesk-demo.sqlite`.

## Source inventory summary
- Scope: `taskdesk-legacy/**` plus `db/**`; files inventoried: 55.
- Language/format counts: {"CSS": 1, "JSP": 8, "Java": 31, "Markdown": 3, "Properties": 3, "SQL": 3, "SQLite": 1, "XML": 5}.

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
- `sem:datastore:sqlite` is grounded in the `taskdesk.db.url` configuration entry, `JdbcConnectionManager.java`, and `db/runtime-data/taskdesk-demo.sqlite`.
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

## Unresolved unknowns
- `sem:unknown:runtime-row-semantics`: schema and row counts are known, but row contents and business meaning of seed records were not read by the schema parser.

## Assumptions
- Scope is limited to `taskdesk-legacy/**` plus `db/**`; package directories are treated as modules; Struts paths use the `.do` suffix from the parsed `web.xml` url-pattern.
- A tracked symlink under `taskdesk-legacy/runtime-data/` is recorded as an inventory uncertainty rather than followed.

## Confidence and evidence notes
- Route/action/view claims are high confidence because the struts-config-v1 parser extracts action paths, action classes, forms, and forwards with element spans.
- Table claims are high confidence because they are grounded in Java SQL literals, SQL DDL, and SQLite schema introspection.

## Limitations
- JSP extraction is lexical and does not parse scriptlet Java.
- Java parsing is structural and does not do expression-level symbol resolution.
- SQLite parser reads schema only, not row data.

## Verification
- Verified by `verifier-v1` (.agent-loop/tools/verifier); self-test caught 4/4 seeded mutations.
- Scores (measured): {"inventory_coverage": 10, "parser_validity": 10, "report_coverage": 10, "reproducibility": 10, "semantic_graph_provenance": 10, "semantic_type_quality": 10, "source_graph_consistency": 10, "unknowns_handling": 10}.
