-- Operator job 1: give robot 3 a new task and get its task id back.
-- assigned_at is optional; leave it out and the current time is used.
INSERT INTO sp_assign_task (robot_id, priority, description, assigned_at)
VALUES (3, 2, 'Move pallet C07 to dock 2', '2026-09-03 08:00:00');

-- The procedure's return value: the id of the task it just created.
SELECT value AS new_task_id
FROM proc_result
WHERE proc_name = 'sp_assign_task';

-- The new task as it is stored.
SELECT task_id, robot_id, description, priority, status, assigned_at
FROM tasks
WHERE task_id = (SELECT value FROM proc_result
                 WHERE proc_name = 'sp_assign_task');