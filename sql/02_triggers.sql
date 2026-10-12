-- RoboDB triggers: rules the database enforces on every change,
-- whether it comes from a procedure, DBeaver or a test.

-- 1. A new task is logged as "created" (old_status is NULL).
CREATE TRIGGER trg_tasks_log_insert
AFTER INSERT ON tasks
BEGIN
    INSERT INTO task_log (task_id, old_status, new_status, changed_at)
    VALUES (NEW.task_id, NULL, NEW.status, NEW.assigned_at);
END;

-- 2. Refuse status moves that are not listed in task_transitions
--    (for example completed -> assigned, or assigned -> completed).
CREATE TRIGGER trg_tasks_check_transition
BEFORE UPDATE OF status ON tasks
WHEN NEW.status IS NOT OLD.status
BEGIN
    SELECT RAISE(ABORT, 'illegal status change for this task')
    WHERE NOT EXISTS (
        SELECT 1 FROM task_transitions
        WHERE from_status = OLD.status AND to_status = NEW.status
    );
END;

-- 3. Log every real status change. The time comes from the column the
--    change filled in; a hand-written UPDATE that sets neither falls
--    back to the current time.
CREATE TRIGGER trg_tasks_log_status
AFTER UPDATE OF status ON tasks
WHEN NEW.status IS NOT OLD.status
BEGIN
    INSERT INTO task_log (task_id, old_status, new_status, changed_at)
    VALUES (
        NEW.task_id,
        OLD.status,
        NEW.status,
        COALESCE(
            CASE WHEN NEW.status = 'in_progress' THEN NEW.start_time
                 ELSE NEW.end_time END,
            strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
        )
    );
END;

-- 4. Keep robots.status in step with their work:
--    starting a task makes the robot busy ...
CREATE TRIGGER trg_tasks_robot_busy
AFTER UPDATE OF status ON tasks
WHEN NEW.status = 'in_progress'
BEGIN
    UPDATE robots SET status = 'busy' WHERE robot_id = NEW.robot_id;
END;

--    ... and finishing its last running task makes it idle again.
CREATE TRIGGER trg_tasks_robot_idle
AFTER UPDATE OF status ON tasks
WHEN NEW.status IN ('completed', 'failed', 'cancelled')
BEGIN
    UPDATE robots SET status = 'idle'
    WHERE robot_id = NEW.robot_id
      AND status = 'busy'
      AND NOT EXISTS (
          SELECT 1 FROM tasks
          WHERE robot_id = NEW.robot_id AND status = 'in_progress'
      );
END;

-- 5. Data security: the audit log is append-only.
CREATE TRIGGER trg_task_log_no_update
BEFORE UPDATE ON task_log
BEGIN
    SELECT RAISE(ABORT, 'task_log is append-only');
END;

CREATE TRIGGER trg_task_log_no_delete
BEFORE DELETE ON task_log
BEGIN
    SELECT RAISE(ABORT, 'task_log is append-only');
END;