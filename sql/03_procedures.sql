-- RoboDB "stored procedures".
-- SQLite has no CREATE PROCEDURE, so each procedure is an empty view with
-- an INSTEAD OF INSERT trigger. The view's columns are the parameters;
-- "calling" the procedure is an INSERT into the view:
--   INSERT INTO sp_assign_task (robot_id, priority, description)
--   VALUES (3, 2, 'Move pallet A12 to dock 4');
-- A procedure that returns a value writes it to proc_result.

-- sp_assign_task(robot_id, priority, description, assigned_at)
-- Creates a task in status 'assigned' and returns its new task_id.
-- assigned_at is optional; it defaults to the current local time.
CREATE VIEW sp_assign_task AS
SELECT robot_id, priority, description, assigned_at FROM tasks WHERE 0;

CREATE TRIGGER sp_assign_task_run
INSTEAD OF INSERT ON sp_assign_task
BEGIN
    SELECT RAISE(ABORT, 'sp_assign_task: robot does not exist')
    WHERE NOT EXISTS (SELECT 1 FROM robots WHERE robot_id = NEW.robot_id);

    SELECT RAISE(ABORT, 'sp_assign_task: robot is in maintenance')
    WHERE EXISTS (SELECT 1 FROM robots
                  WHERE robot_id = NEW.robot_id AND status = 'maintenance');

    SELECT RAISE(ABORT, 'sp_assign_task: priority must be 1 to 5')
    WHERE NEW.priority IS NULL OR NEW.priority NOT BETWEEN 1 AND 5;

    INSERT INTO tasks (robot_id, priority, description, assigned_at)
    VALUES (
        NEW.robot_id,
        NEW.priority,
        COALESCE(NEW.description, ''),
        COALESCE(NEW.assigned_at,
                 strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
    );

    INSERT OR REPLACE INTO proc_result (proc_name, value)
    VALUES ('sp_assign_task', last_insert_rowid());
END;

-- sp_update_task_status(task_id, new_status, changed_at)
-- Moves a task to a new status and stamps start_time / end_time.
-- The triggers on tasks check the move is legal and write task_log.
-- changed_at is optional; it defaults to the current local time.
CREATE VIEW sp_update_task_status AS
SELECT task_id, status AS new_status, end_time AS changed_at
FROM tasks WHERE 0;

CREATE TRIGGER sp_update_task_status_run
INSTEAD OF INSERT ON sp_update_task_status
BEGIN
    SELECT RAISE(ABORT, 'sp_update_task_status: task does not exist')
    WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE task_id = NEW.task_id);

    SELECT RAISE(ABORT, 'sp_update_task_status: task already has that status')
    WHERE EXISTS (SELECT 1 FROM tasks
                  WHERE task_id = NEW.task_id AND status = NEW.new_status);

 UPDATE tasks
    SET start_time = CASE
        WHEN NEW.new_status = 'in_progress'
        THEN COALESCE(
            NEW.changed_at,
            strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
        )
        ELSE start_time
    END,
    end_time = CASE
        WHEN NEW.new_status IN ('completed', 'failed', 'cancelled')
        THEN COALESCE(
            NEW.changed_at,
            strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
        )
        ELSE end_time
    END,
    status = NEW.new_status
    WHERE task_id = NEW.task_id;

    UPDATE tasks
    SET start_time = CASE
            WHEN NEW.new_status = 'in_progress'
            THEN COALESCE(
                NEW.changed_at,
                strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
            )
            ELSE start_time
        END,
        end_time = CASE
            WHEN NEW.new_status IN ('completed', 'failed', 'cancelled')
            THEN COALESCE(
                NEW.changed_at,
                strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
            )
            ELSE end_time
        END,
        status = NEW.new_status
    WHERE task_id = NEW.task_id;
END;

-- sp_archive_tasks(before_time)
-- Moves finished tasks whose end_time is before before_time into
-- tasks_archive and returns how many were moved. task_log keeps
-- their history.
CREATE VIEW sp_archive_tasks AS
SELECT end_time AS before_time FROM tasks WHERE 0;

CREATE TRIGGER sp_archive_tasks_run
INSTEAD OF INSERT ON sp_archive_tasks
BEGIN
    SELECT RAISE(ABORT, 'sp_archive_tasks: before_time is required')
    WHERE NEW.before_time IS NULL;

    INSERT OR REPLACE INTO proc_result (proc_name, value)
    SELECT 'sp_archive_tasks', COUNT(*) FROM tasks
    WHERE status IN ('completed', 'failed', 'cancelled')
      AND end_time < NEW.before_time;

    INSERT INTO tasks_archive
    SELECT task_id, robot_id, description, priority, status,
           assigned_at, start_time, end_time,
           strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
    FROM tasks
    WHERE status IN ('completed', 'failed', 'cancelled')
      AND end_time < NEW.before_time;

    DELETE FROM tasks
    WHERE status IN ('completed', 'failed', 'cancelled')
      AND end_time < NEW.before_time;
END;