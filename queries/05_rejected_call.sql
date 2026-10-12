-- Robot 4 is in maintenance, so the procedure must refuse this task.
INSERT INTO sp_assign_task (robot_id, priority, description)
VALUES (4, 1, 'Sort parcels lane 7');