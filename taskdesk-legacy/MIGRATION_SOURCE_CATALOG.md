# TaskDesk Legacy Migration Source Catalog

## Struts Routes

| Route | Action | Form | Success/Input Views | Tables |
| --- | --- | --- | --- | --- |
| `/login.do` | `LoginAction` | `LoginForm` | `/jsp/login.jsp`, `/tasks.do` | Reads `APP_USER` |
| `/logout.do` | `LogoutAction` | none | `/jsp/login.jsp` | none |
| `/tasks.do` | `TaskListAction` | `TaskSearchForm` | `/jsp/taskList.jsp` | Reads `TASK`, `APP_USER` |
| `/taskDetail.do` | `TaskDetailAction` | `TaskForm` | `/jsp/taskDetail.jsp` | Reads `TASK`, `TASK_COMMENT`, `TASK_AUDIT`, `APP_USER` |
| `/taskEdit.do` | `TaskEditAction` | `TaskForm` | `/jsp/taskEdit.jsp`, `/jsp/error.jsp` | Reads `TASK`, `APP_USER` |
| `/taskSave.do` | `TaskSaveAction` | `TaskForm` | `/jsp/taskEdit.jsp`, `/jsp/taskDetail.jsp` | Reads/writes `TASK`, `TASK_COMMENT`, `TASK_AUDIT` |
| `/taskAssign.do` | `TaskAssignAction` | `TaskAssignForm` | `/jsp/taskAssign.jsp`, `/jsp/taskDetail.jsp` | Reads `TASK`, `APP_USER`; writes `TASK`, `TASK_COMMENT`, `TASK_AUDIT` |
| `/taskComplete.do` | `TaskCompleteAction` | `TaskForm` | `/jsp/taskDetail.jsp` | Reads/writes `TASK`, `TASK_AUDIT` |
| `/taskReopen.do` | `TaskReopenAction` | `TaskForm` | `/jsp/taskDetail.jsp` | Reads/writes `TASK`, `TASK_AUDIT` |
| `/taskReport.do` | `TaskReportAction` | `TaskReportForm` | `/jsp/taskReport.jsp` | Reads `TASK_AUDIT`, `APP_USER` |
| `/taskExport.do` | `TaskReportAction` | `TaskReportForm` | CSV response | Reads `TASK`, `APP_USER` |

## Action Classes

- `LoginAction`: authenticates users and initializes `currentUser`, `currentRole`, and `flashMessage`.
- `LogoutAction`: invalidates the HTTP session.
- `TaskListAction`: builds search criteria, applies operator owner scoping, stores `lastTaskSearchFilter`.
- `TaskDetailAction`: loads task, comments, audit entries, active users, and stores `lastVisitedTaskId`.
- `TaskEditAction`: populates the overloaded `TaskForm` for create/edit and blocks completed edits.
- `TaskSaveAction`: handles create, edit, and comment flows through `TaskForm`; mixes manual validation and service calls.
- `TaskAssignAction`: performs manager role check and assignment orchestration.
- `TaskCompleteAction`: allows managers or assigned operators to complete tasks.
- `TaskReopenAction`: manager-only reopen operation.
- `TaskReportAction`: manager activity report plus CSV export handling.

## Form Classes

- `LoginForm`: `username`, `password`.
- `TaskSearchForm`: `status`, `priority`, `ownerUserId`, `dueDateFrom`, `dueDateTo`, `sortBy`, `sortDirection`.
- `TaskForm`: `taskId`, `title`, `description`, `status`, `priority`, `ownerUserId`, `dueDate`, `commentText`, `mode`.
- `TaskAssignForm`: `taskId`, `ownerUserId`, `assignmentReason`.
- `TaskReportForm`: `fromDate`, `toDate`, `groupBy`, `includeCompleted`.

## JSP Views

- `/jsp/login.jsp`
- `/jsp/taskList.jsp`
- `/jsp/taskEdit.jsp`
- `/jsp/taskDetail.jsp`
- `/jsp/taskAssign.jsp`
- `/jsp/taskReport.jsp`
- `/jsp/error.jsp`
- `/jsp/accessDenied.jsp`

`taskList.jsp` and `taskReport.jsp` contain limited scriptlets for count calculations. `taskDetail.jsp` and `taskList.jsp` contain role/status conditional rendering.

## DAO Methods

### `TaskDAO`

- `findTasks(TaskSearchCriteria criteria)`: reads `TASK`, `APP_USER`.
- `findTaskById(Long taskId)`: reads `TASK`, `APP_USER`.
- `insertTask(Task task)`: writes `TASK`.
- `updateTask(Task task)`: writes `TASK`.
- `updateTaskStatus(Long taskId, String status)`: writes `TASK`.
- `updateTaskOwner(Long taskId, Long ownerUserId)`: writes `TASK`.
- `insertComment(TaskComment comment)`: writes `TASK_COMMENT`.
- `findCommentsByTaskId(Long taskId)`: reads `TASK_COMMENT`, `APP_USER`.

### `UserDAO`

- `findUserByUsername(String username)`: reads `APP_USER`.
- `findActiveUsers()`: reads `APP_USER`.
- `findUserById(Long userId)`: reads `APP_USER`.

### `AuditDAO`

- `insertAuditEntry(TaskAuditEntry entry)`: writes `TASK_AUDIT`.
- `findAuditEntriesForTask(Long taskId)`: reads `TASK_AUDIT`, `APP_USER`.
- `findActivityReport(Date from, Date to)`: reads `TASK_AUDIT`, `APP_USER`.

## Validation Sources

- `WEB-INF/validation.xml`: required login fields, required task title/priority, due date format, assignment fields.
- `TaskSaveAction`: manual title, priority, due date, and critical-owner checks.
- `TaskEditAction`: blocks editing completed tasks before reaching the form.
- `TaskAssignAction`, `TaskReopenAction`: manager role checks.
- `TaskCompleteAction`: manager or assigned-operator role/ownership check.
- `TaskService`: due-date-vs-created-date, critical owner, completed edit protection, lifecycle persistence checks.

## Session Attributes

- `currentUser`: `User` object for the logged-in user.
- `currentRole`: role string, `OPERATOR` or `MANAGER`.
- `lastTaskSearchFilter`: last `TaskSearchCriteria` used by `/tasks.do`.
- `lastVisitedTaskId`: last task loaded by `/taskDetail.do`.
- `flashMessage`: success or navigation message displayed once by JSPs.

## Database Tables By Flow

| Flow | Tables Read | Tables Written |
| --- | --- | --- |
| Login | `APP_USER` | none |
| Logout | none | none |
| Task list/filter | `TASK`, `APP_USER` | none |
| Task detail | `TASK`, `TASK_COMMENT`, `TASK_AUDIT`, `APP_USER` | none |
| Task create | `APP_USER` | `TASK`, `TASK_AUDIT` |
| Task edit/save | `TASK`, `APP_USER` | `TASK`, `TASK_AUDIT` |
| Task assignment | `TASK`, `APP_USER` | `TASK`, `TASK_COMMENT`, `TASK_AUDIT` |
| Add comment | `TASK` | `TASK_COMMENT`, `TASK_AUDIT` |
| Complete task | `TASK` | `TASK`, `TASK_AUDIT` |
| Reopen task | `TASK` | `TASK`, `TASK_AUDIT` |
| Activity report | `TASK_AUDIT`, `APP_USER` | none |
| CSV export | `TASK`, `APP_USER` | none |
