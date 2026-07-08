# TaskDesk Functional Design Specification

## 1. Purpose

TaskDesk is a web application for tracking operational tasks, assigning work to users, recording comments, and reviewing task activity. It supports two primary roles:

- **Operator**: works through assigned tasks, views task details, updates work status, and contributes comments.
- **Manager**: oversees the task queue, assigns ownership, reopens completed work, reviews activity, and exports task data.

The application is designed for small operational teams that need a shared task board with lightweight workflow controls and an auditable history.

## 2. Scope

### In Scope

- User authentication.
- Role-based access for operators and managers.
- Task listing with filters and sorting.
- Task detail viewing.
- Task creation and editing.
- Task assignment by managers.
- Task completion and reopening.
- Task comments.
- Activity reporting.
- CSV export of task data.
- Basic audit trail for task changes.

### Out Of Scope

- Self-service user registration.
- Password reset flows.
- Email or chat notifications.
- File attachments.
- Calendar integration.
- Multi-tenant account separation.
- Fine-grained custom permissions beyond the operator and manager roles.

## 3. Personas

### Operator

Operators handle day-to-day work. They primarily need to see tasks assigned to them, inspect task details, add comments, and mark work complete when allowed.

Goals:

- Quickly find relevant tasks.
- Understand task priority, due date, and current status.
- Add progress notes.
- Complete assigned work.

### Manager

Managers coordinate work across the team. They need broader visibility, assignment controls, reporting, and the ability to reopen tasks when needed.

Goals:

- Review all tasks across operators.
- Assign or reassign tasks.
- Monitor activity by date range or action.
- Export task data for offline analysis.
- Control protected workflow transitions.

## 4. Roles And Permissions

| Capability | Operator | Manager |
| --- | --- | --- |
| Sign in and sign out | Yes | Yes |
| View task list | Yes | Yes |
| View task detail | Yes | Yes |
| Create task | Yes | Yes |
| Edit non-completed task | Yes | Yes |
| Add task comment | Yes | Yes |
| Complete task | Own assigned tasks only, unless otherwise permitted by business policy | Yes |
| Assign task owner | No | Yes |
| Reopen task | No | Yes |
| View activity report | No | Yes |
| Export task CSV | Yes | Yes |

When an operator attempts to access a manager-only assignment action, the application displays an access-denied screen.

## 5. Main Navigation And Screens

### Login

The login screen accepts a username and password. On successful sign-in, the user is redirected to the task list. On failed sign-in, an invalid-credentials message is shown and the user remains on the login screen.

### Task List

The task list is the main workspace. It shows tasks and supports filtering by status, priority, owner, and due-date range. Operators default to their own tasks when no owner filter is provided. Managers can view tasks across users.

### Task Detail

The task detail screen shows the task record, comments, audit entries, and available workflow actions. It is the primary place for reviewing a task before completing, assigning, reopening, or commenting.

### Task Edit

The task edit screen supports creating a new task or editing an existing non-completed task. The form captures title, description, status, priority, owner, and due date.

### Assign Task

The assignment screen is available to managers. It allows a manager to select an owner for a task and optionally provide an assignment reason. Assignment can create an audit entry and, when a reason is provided, add a task comment.

### Activity Report

The activity report is available to managers. It summarizes task activity over a selected date range and can group results by action or another supported grouping option.

### CSV Export

The CSV export endpoint returns task data as a downloadable CSV file for reporting or spreadsheet analysis.

### Access Denied

The access-denied screen is shown when an authenticated user attempts an action that their role cannot perform.

## 6. User Stories

### Authentication

**US-001: Sign in**

As a user, I want to sign in with my username and password so that I can access TaskDesk.

Acceptance criteria:

- Given valid credentials, when I submit the login form, then I am redirected to the task list.
- Given missing or invalid credentials, when I submit the login form, then I remain on the login screen and see an error message.
- After sign-in, my current user and role are stored for the session.

**US-002: Sign out**

As a user, I want to sign out so that my session is ended.

Acceptance criteria:

- When I sign out, the current session is invalidated.
- After sign-out, protected task screens require sign-in again.

### Task Discovery

**US-003: View task list**

As an operator, I want to see my task list so that I can decide what to work on next.

Acceptance criteria:

- The task list displays task title, status, priority, owner, creator, created date, updated date, and due date where available.
- Operators default to tasks assigned to themselves when no owner filter is selected.
- Managers can view tasks for all owners.

**US-004: Filter and sort tasks**

As a user, I want to filter and sort tasks so that I can focus on the right work.

Acceptance criteria:

- I can filter by status.
- I can filter by priority.
- I can filter by owner.
- I can filter by due-date range.
- I can sort by due date, priority, status, or created date.
- Sort direction defaults to ascending unless descending is selected.

### Task Detail And Comments

**US-005: View task detail**

As a user, I want to open a task detail screen so that I can review all information about a task.

Acceptance criteria:

- The screen shows the task attributes.
- The screen shows comments for the task.
- The screen shows audit entries for the task.
- If the task does not exist, the application shows an error or not-found response.

**US-006: Add a comment**

As a user, I want to add a comment to a task so that I can record progress or context.

Acceptance criteria:

- Comment text is required.
- Saved comments are associated with the task and the author.
- Saved comments appear on the task detail screen.
- Adding a comment creates an audit entry.

### Task Creation And Editing

**US-007: Create task**

As a user, I want to create a task so that new work can be tracked.

Acceptance criteria:

- Title is required.
- Priority is required.
- Status defaults to OPEN when no status is provided.
- Created-by user and created timestamp are recorded.
- After save, the user is shown the task detail.
- Creation creates an audit entry.

**US-008: Edit task**

As a user, I want to edit a task so that task details stay accurate.

Acceptance criteria:

- Existing task values are loaded into the edit form.
- Title and priority are required.
- Due date must use the expected date format.
- A critical-priority task must have an owner.
- Completed tasks cannot be edited.
- After save, the user is shown the task detail.
- Updates create an audit entry.

### Assignment And Status

**US-009: Assign task**

As a manager, I want to assign a task to a user so that ownership is clear.

Acceptance criteria:

- Only managers can open the assignment screen.
- The assignment screen shows active users.
- Owner is required for assignment.
- Optional assignment reason is recorded as a task comment.
- Assignment creates an audit entry.
- Operators attempting to assign a task see an access-denied screen.

**US-010: Complete task**

As a permitted user, I want to complete a task so that finished work is recorded.

Acceptance criteria:

- Managers can complete tasks.
- Operators can complete tasks assigned to them.
- Completion changes status to COMPLETED.
- Completion creates an audit entry.
- Unauthorized users see an access-denied screen.

**US-011: Reopen task**

As a manager, I want to reopen a task so that work can continue after a task was completed.

Acceptance criteria:

- Only managers can reopen tasks.
- Reopening changes status to OPEN.
- Reopening creates an audit entry.
- Operators attempting to reopen a task see an access-denied screen.

### Reporting

**US-012: View activity report**

As a manager, I want to view a task activity report so that I can understand team activity.

Acceptance criteria:

- Only managers can view the activity report.
- The report supports a from-date and to-date.
- The report can group activity according to supported grouping options.
- The report can include or exclude completed work depending on the selected option.

**US-013: Export task data**

As a user, I want to export task data to CSV so that I can analyze tasks outside TaskDesk.

Acceptance criteria:

- The export returns a CSV response.
- The response is downloadable as a file.
- The export includes task data from the current task set or default task query.

## 7. Runtime User Journeys

### Journey A: Manager Reviews And Exports Work

Actor: Manager

1. Manager opens the login screen.
2. Manager submits valid credentials.
3. System redirects to the task list.
4. Manager opens a task detail screen.
5. Manager opens the assignment screen for the task.
6. Manager opens the activity report.
7. Manager exports task data as CSV.

Expected results:

- Login succeeds.
- Task list renders.
- Task detail renders.
- Assignment form renders for the manager.
- Activity report renders for the manager.
- CSV export returns a CSV response.

### Journey B: Operator Attempts Manager-Only Assignment

Actor: Operator

1. Operator opens the login screen.
2. Operator submits valid credentials.
3. System redirects to the task list.
4. Operator attempts to open the assignment screen for a task.

Expected results:

- Login succeeds.
- Task list renders.
- Assignment screen is not shown.
- Access-denied screen is displayed.

## 8. Functional Rules

### Authentication Rules

- A user must be signed in to access task screens.
- Invalid login attempts do not create an authenticated session.
- Session state includes the current user and role.

### Authorization Rules

- Manager-only capabilities include task assignment, task reopening, and activity report access.
- Operators are restricted from task assignment.
- Operators are scoped to their own tasks by default on the task list.
- Protected actions redirect or forward to an access-denied screen when authorization fails.

### Task Validation Rules

- Task title is required.
- Task priority is required.
- Due date must be a valid date.
- Critical-priority tasks require an owner.
- Completed tasks cannot be edited.
- Comment text is required.

### Audit Rules

- Creating a task records a CREATE_TASK audit event.
- Updating a task records an UPDATE_TASK audit event.
- Changing task status records a CHANGE_STATUS audit event.
- Assigning a task records an ASSIGN_TASK audit event.
- Adding a comment records an ADD_COMMENT audit event.

## 9. Data Description

### User

Represents a person who can sign in to TaskDesk.

Fields:

- User ID.
- Username.
- Password hash or stored credential value.
- Display name.
- Role: OPERATOR or MANAGER.
- Active flag.

### Task

Represents work tracked by the application.

Fields:

- Task ID.
- Title.
- Description.
- Status: OPEN, IN_PROGRESS, BLOCKED, COMPLETED, or CANCELLED.
- Priority: LOW, NORMAL, HIGH, or CRITICAL.
- Owner user ID.
- Created-by user ID.
- Created timestamp.
- Updated timestamp.
- Due date.

### Task Comment

Represents a user-entered note on a task.

Fields:

- Comment ID.
- Task ID.
- Author user ID.
- Comment text.
- Created timestamp.

### Task Audit Entry

Represents a recorded task event.

Fields:

- Audit ID.
- Task ID.
- Action.
- Old value.
- New value.
- Performed-by user ID.
- Performed timestamp.

### Task Search Criteria

Represents filters and sorting options applied to the task list.

Fields:

- Status.
- Priority.
- Owner user ID.
- Due date from.
- Due date to.
- Sort by.
- Sort direction.

## 10. Data Relationships

- A task may have one owner user.
- A task has one creator user.
- A task may have many comments.
- A task may have many audit entries.
- A comment has one author user.
- An audit entry has one performing user.

## 11. Screen-Level Requirements

### Login Screen

Inputs:

- Username.
- Password.

Outputs:

- Success redirect to task list.
- Error message for invalid credentials.

### Task List Screen

Inputs:

- Status filter.
- Priority filter.
- Owner filter.
- Due-date range.
- Sort field.
- Sort direction.

Outputs:

- Filtered task table.
- Available users for owner filtering.

### Task Detail Screen

Inputs:

- Task ID.

Outputs:

- Task details.
- Comments.
- Audit entries.
- Available users for assignment-related controls.

### Task Edit Screen

Inputs:

- Title.
- Description.
- Status.
- Priority.
- Owner.
- Due date.

Outputs:

- Validation errors.
- Saved task detail.

### Task Assignment Screen

Inputs:

- Task ID.
- Owner user ID.
- Assignment reason.

Outputs:

- Updated task detail.
- Access-denied screen for non-manager users.

### Activity Report Screen

Inputs:

- From date.
- To date.
- Grouping option.
- Include completed flag.

Outputs:

- Activity report rows.
- Report grouping.

### CSV Export

Inputs:

- Current or default task query.

Outputs:

- CSV file response.

## 12. Error And Empty States

- Invalid credentials: show invalid username or password message.
- Missing task ID: show not-found or error response.
- Unknown task ID: show not-found or error response.
- Unauthorized action: show access-denied screen.
- Invalid task form: show validation messages and keep user on the form.
- Invalid comment: show comment validation message and remain on task detail.

## 13. Reporting Requirements

The activity report should help managers answer:

- Which task actions occurred during a time range?
- Which users performed those actions?
- Which tasks changed status, owner, or content?
- How much completed work should be included in the report view?

The CSV export should support offline analysis and should include task attributes useful for spreadsheet review.

## 14. Non-Functional Requirements

### Usability

- Primary workflows should require minimal navigation.
- Validation messages should identify the field or action that failed.
- Access-denied responses should provide a clear path back to the task list.

### Security

- Protected screens require authentication.
- Role checks must be enforced server-side.
- Session data must identify the current user and role.

### Auditability

- Mutating task actions should create audit entries.
- Audit history should remain visible from task detail.

### Data Integrity

- Foreign-key relationships should protect task, user, comment, and audit consistency.
- Task status and priority should remain within allowed values.
- Required fields should be validated before persistence.

## 15. Open Product Questions

- Should operators be allowed to create tasks for other users, or only for themselves?
- Should CSV export be manager-only, or intentionally available to all authenticated users?
- Should task completion by operators be limited strictly to assigned tasks in every workflow?
- Should the activity report include task comments, or only audit events?
- Should assignment require an owner in all cases, or allow unassignment?
- Should password storage be upgraded to a stronger credential model before production use?
