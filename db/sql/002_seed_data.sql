PRAGMA foreign_keys = ON;

INSERT INTO APP_USER (USERNAME, PASSWORD_HASH, DISPLAY_NAME, ROLE, ACTIVE)
VALUES
('operator1', 'demo', 'Olivia Operator', 'OPERATOR', 1),
('operator2', 'demo', 'Oscar Operator', 'OPERATOR', 1),
('manager1', 'demo', 'Marta Manager', 'MANAGER', 1);

INSERT INTO TASK (
    TITLE, DESCRIPTION, STATUS, PRIORITY,
    OWNER_USER_ID, CREATED_BY_USER_ID,
    CREATED_AT, UPDATED_AT, DUE_DATE
)
VALUES
('Validate coupon batch', 'Check imported coupon batch before activation.', 'OPEN', 'HIGH', 1, 3, '2026-06-01T09:00:00', NULL, '2026-06-20'),
('Review invoice mismatch', 'Investigate mismatch between invoice and promotion rule.', 'IN_PROGRESS', 'CRITICAL', 2, 3, '2026-06-02T10:30:00', '2026-06-04T12:00:00', '2026-06-18'),
('Clean obsolete campaign data', 'Remove expired test campaign references.', 'BLOCKED', 'NORMAL', 1, 1, '2026-06-05T14:00:00', NULL, '2026-06-25'),
('Prepare activity report', 'Prepare weekly operational task report.', 'COMPLETED', 'LOW', 2, 3, '2026-06-07T08:45:00', '2026-06-10T16:10:00', '2026-06-12'),
('Check promotion visibility', 'Verify that active promotion rules are visible in the operational screen.', 'OPEN', 'NORMAL', 1, 3, '2026-06-11T11:15:00', NULL, '2026-06-22'),
('Review blocked coupon file', 'Investigate blocked coupon file after nightly import.', 'BLOCKED', 'HIGH', 2, 3, '2026-06-12T15:40:00', NULL, '2026-06-19');

INSERT INTO TASK_COMMENT (TASK_ID, AUTHOR_USER_ID, COMMENT_TEXT, CREATED_AT)
VALUES
(1, 3, 'Initial validation requested by operations.', '2026-06-01T09:10:00'),
(2, 2, 'Mismatch reproduced with latest invoice extract.', '2026-06-03T13:00:00'),
(3, 1, 'Waiting for confirmation before cleanup.', '2026-06-06T10:20:00'),
(4, 2, 'Report prepared and sent.', '2026-06-10T16:12:00'),
(6, 2, 'Blocked during import validation.', '2026-06-12T16:00:00');

INSERT INTO TASK_AUDIT (TASK_ID, ACTION, OLD_VALUE, NEW_VALUE, PERFORMED_BY_USER_ID, PERFORMED_AT)
VALUES
(1, 'CREATE_TASK', NULL, 'OPEN', 3, '2026-06-01T09:00:00'),
(2, 'CREATE_TASK', NULL, 'OPEN', 3, '2026-06-02T10:30:00'),
(2, 'CHANGE_STATUS', 'OPEN', 'IN_PROGRESS', 2, '2026-06-04T12:00:00'),
(3, 'CREATE_TASK', NULL, 'BLOCKED', 1, '2026-06-05T14:00:00'),
(4, 'CREATE_TASK', NULL, 'OPEN', 3, '2026-06-07T08:45:00'),
(4, 'CHANGE_STATUS', 'OPEN', 'COMPLETED', 2, '2026-06-10T16:10:00'),
(5, 'CREATE_TASK', NULL, 'OPEN', 3, '2026-06-11T11:15:00'),
(6, 'CREATE_TASK', NULL, 'BLOCKED', 3, '2026-06-12T15:40:00');
