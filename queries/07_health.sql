-- Monitoring: how big is each table?
SELECT 'robots' AS table_name, COUNT(*) AS row_count FROM robots
UNION ALL SELECT 'tasks', COUNT(*) FROM tasks
UNION ALL SELECT 'tasks_archive', COUNT(*) FROM tasks_archive
UNION ALL SELECT 'task_log', COUNT(*) FROM task_log
UNION ALL SELECT 'backup_log', COUNT(*) FROM backup_log;

-- Optimising: refresh the statistics the query planner uses.
ANALYZE;

-- Performance: does the per-robot query use an index or scan the table?
EXPLAIN QUERY PLAN
SELECT task_id, start_time FROM tasks WHERE robot_id = 3 ORDER BY start_time DESC;

-- Safety: is the database file healthy?
PRAGMA integrity_check;