-- Operator job 4: completed tasks per robot, with average duration.
SELECT * FROM v_completed_task_summary;

-- Operator job 5: each robot's status and its latest task, in one query.
SELECT * FROM v_robot_latest_task;