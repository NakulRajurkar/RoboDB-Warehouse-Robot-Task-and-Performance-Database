-- RoboDB views: the read-only windows operators query in DBeaver.

-- Every task with its robot, newest start first. Filter it per robot:
--   SELECT * FROM v_robot_tasks WHERE robot_id = 1;
-- Tasks not started yet have no start_time; they sort last.
CREATE VIEW v_robot_tasks AS
SELECT t.robot_id,
       r.model,
       t.task_id,
       t.description,
       t.priority,
       t.status,
       t.assigned_at,
       t.start_time,
       t.end_time,
       ROUND((julianday(t.end_time) - julianday(t.start_time)) * 1440, 1)
           AS duration_min
FROM tasks AS t
INNER JOIN robots AS r ON r.robot_id = t.robot_id
ORDER BY t.start_time DESC, t.task_id DESC;

-- Report: completed tasks per robot with their average duration.
-- LEFT JOIN keeps robots that have completed nothing (count 0).
CREATE VIEW v_completed_task_summary AS
SELECT r.robot_id,
       r.model,
       COUNT(t.task_id) AS completed_tasks,
       ROUND(AVG((julianday(t.end_time) - julianday(t.start_time)) * 1440), 1)
           AS avg_duration_min
FROM robots AS r
LEFT JOIN tasks AS t
       ON t.robot_id = r.robot_id
      AND t.status = 'completed'
GROUP BY r.robot_id, r.model
ORDER BY r.robot_id;

-- Every robot's current status next to its most recently assigned task.
-- The subquery in the ON clause picks exactly one task per robot.
CREATE VIEW v_robot_latest_task AS
SELECT r.robot_id,
       r.model,
       r.status      AS robot_status,
       t.task_id     AS latest_task_id,
       t.description AS latest_task,
       t.status      AS task_status,
       t.assigned_at
FROM robots AS r
LEFT JOIN tasks AS t
       ON t.task_id = (SELECT t2.task_id
                       FROM tasks AS t2
                       WHERE t2.robot_id = r.robot_id
                       ORDER BY t2.assigned_at DESC, t2.task_id DESC
                       LIMIT 1)
ORDER BY r.robot_id;