-- Operator job 3: every task robot 3 has had, newest start first.
SELECT task_id, description, status, start_time, end_time, duration_min
FROM v_robot_tasks
WHERE robot_id = 3
ORDER BY start_time DESC, task_id DESC;
