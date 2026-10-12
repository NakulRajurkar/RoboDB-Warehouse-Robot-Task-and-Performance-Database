-- Archive: move tasks that finished before 2 September out of the live table.
INSERT INTO sp_archive_tasks (before_time) VALUES ('2026-09-02 00:00:00');

SELECT value AS tasks_archived
FROM proc_result
WHERE proc_name = 'sp_archive_tasks';

SELECT (SELECT COUNT(*) FROM tasks)         AS live_tasks,
       (SELECT COUNT(*) FROM tasks_archive) AS archived_tasks,
       (SELECT COUNT(*) FROM task_log)      AS log_rows;