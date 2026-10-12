-- RoboDB sample data: five robots and two days of warehouse work.
-- Tasks go in through the procedures, exactly as an operator would,
-- so task_log and robot statuses are filled by the triggers.

INSERT INTO robots (robot_id, model) VALUES
    (1, 'AMR-200 Picker'),
    (2, 'AMR-200 Picker'),
    (3, 'HeavyLift HL-9'),
    (4, 'Sorter S-3'),
    (5, 'HeavyLift HL-9');

-- Tasks 1-11, in the order they were assigned.
INSERT INTO sp_assign_task (robot_id, priority, description, assigned_at) VALUES
    (3, 2, 'Unload truck at dock 1',      '2026-09-01 07:00:00'),
    (1, 2, 'Move pallet A12 to dock 4',   '2026-09-01 08:00:00'),
    (2, 1, 'Pick order #5519',            '2026-09-01 08:30:00'),
    (1, 3, 'Restock aisle 7 shelf C',     '2026-09-01 09:00:00'),
    (3, 2, 'Move pallet B04 to rack 12',  '2026-09-01 10:00:00'),
    (4, 3, 'Sort parcels lane 5',         '2026-09-01 12:00:00'),
    (2, 4, 'Inventory scan zone B',       '2026-09-01 13:00:00'),
    (3, 1, 'Load truck at dock 3',        '2026-09-02 06:30:00'),
    (4, 3, 'Sort parcels lane 6',         '2026-09-02 09:00:00'),
    (1, 1, 'Pick order #5521',            '2026-09-02 10:00:00'),
    (2, 3, 'Move returns to bay 2',       '2026-09-02 11:00:00');

-- Their progress, in time order.
INSERT INTO sp_update_task_status (task_id, new_status, changed_at) VALUES
    (1,  'in_progress', '2026-09-01 07:05:00'),
    (1,  'completed',   '2026-09-01 08:05:00'),
    (2,  'in_progress', '2026-09-01 08:05:00'),
    (3,  'in_progress', '2026-09-01 08:31:00'),
    (2,  'completed',   '2026-09-01 08:35:00'),
    (3,  'completed',   '2026-09-01 08:51:00'),
    (4,  'in_progress', '2026-09-01 09:10:00'),
    (4,  'completed',   '2026-09-01 09:55:00'),
    (5,  'in_progress', '2026-09-01 10:00:00'),
    (5,  'completed',   '2026-09-01 10:40:00'),
    (6,  'in_progress', '2026-09-01 12:00:00'),
    (6,  'completed',   '2026-09-01 12:25:00'),
    (7,  'in_progress', '2026-09-01 13:15:00'),
    (7,  'failed',      '2026-09-01 13:40:00'),
    (8,  'in_progress', '2026-09-02 06:40:00'),
    (8,  'completed',   '2026-09-02 07:30:00'),
    (9,  'cancelled',   '2026-09-02 09:20:00'),
    (10, 'in_progress', '2026-09-02 10:02:00');

-- Robot 4 went in for a service; robot 5 is on its charger.
UPDATE robots SET status = 'maintenance' WHERE robot_id = 4;
UPDATE robots SET status = 'charging'    WHERE robot_id = 5;

-- The seed calls leave their last answer behind; start clean.
DELETE FROM proc_result;