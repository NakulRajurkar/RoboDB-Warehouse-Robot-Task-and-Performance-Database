-- Operator job 2: robot 3 starts task 12, then finishes it.
INSERT INTO sp_update_task_status (task_id, new_status, changed_at)
VALUES (12, 'in_progress', '2026-09-03 08:10:00');

-- While the task runs, the robot shows as busy.
SELECT robot_id, status FROM robots WHERE robot_id = 3;

INSERT INTO sp_update_task_status (task_id, new_status, changed_at)
VALUES (12, 'completed', '2026-09-03 08:52:00');

-- The trigger wrote one log row per change.
SELECT log_id, task_id, old_status, new_status, changed_at
FROM task_log
WHERE task_id = 12
ORDER BY log_id;

-- Finished: the robot is idle again.
SELECT robot_id, status FROM robots WHERE robot_id = 3;