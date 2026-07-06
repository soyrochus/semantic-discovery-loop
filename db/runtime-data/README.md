# Runtime Database

This folder contains the demo SQLite database:

```text
taskdesk-demo.sqlite
```

Initial row counts:

```json
{
  "APP_USER": 3,
  "TASK": 6,
  "TASK_COMMENT": 5,
  "TASK_AUDIT": 8
}
```

Regenerate it with:

```text
sqlite3 taskdesk-demo.sqlite < ../sql/003_reset_database.sql
```
