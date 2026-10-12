-- RoboDB schema: the tables every other script builds on.
-- The build runs the sql/ files in name order, so this one comes first.

PRAGMA foreign_keys = ON;

-- One row per robot on the warehouse floor.
CREATE TABLE robots (
    robot_id   INTEGER PRIMARY KEY,
    model      TEXT    NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'idle'
               CHECK (status IN ('idle', 'busy', 'charging', 'maintenance'))
);

-- The statuses a task may have, and which moves between them are legal.
-- Keeping the rules in a table (not hard-coded in a trigger) means an
-- operator can read them with a plain SELECT.
CREATE TABLE task_transitions (
    from_status TEXT NOT NULL,
    to_status   TEXT NOT NULL,
    PRIMARY KEY (from_status, to_status)
);

INSERT INTO task_transitions (from_status, to_status) VALUES
    ('assigned',    'in_progress'),
    ('assigned',    'cancelled'),
    ('in_progress', 'completed'),
    ('in_progress', 'failed');

-- One row per job a robot is asked to do.
-- assigned_at: when the operator created the task.
-- start_time:  when the robot actually began (status -> in_progress).
-- end_time:    when the task finished (completed, failed or cancelled).
CREATE TABLE tasks (
    task_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    robot_id    INTEGER NOT NULL REFERENCES robots (robot_id),
    description TEXT    NOT NULL DEFAULT '',
    priority    INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 5),
    status      TEXT    NOT NULL DEFAULT 'assigned'
                CHECK (status IN ('assigned', 'in_progress', 'completed',
                                  'failed', 'cancelled')),
    assigned_at TEXT    NOT NULL,
    start_time  TEXT,
    end_time    TEXT,
    CHECK (end_time IS NULL OR start_time IS NULL OR end_time >= start_time)
);

-- Audit trail: one row every time a task is created or changes status.
-- Filled only by triggers, never by hand. task_id has no REFERENCES on
-- purpose: the history must survive when a task is archived away.
CREATE TABLE task_log (
    log_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    INTEGER NOT NULL,
    old_status TEXT,
    new_status TEXT    NOT NULL,
    changed_at TEXT    NOT NULL
);

-- Where the "stored procedures" leave their return value.
-- One row per procedure name; each call overwrites the previous answer.
CREATE TABLE proc_result (
    proc_name TEXT PRIMARY KEY,
    value     INTEGER NOT NULL
);

-- Finished tasks moved out of the live table by the archive script.
CREATE TABLE tasks_archive (
    task_id     INTEGER PRIMARY KEY,
    robot_id    INTEGER NOT NULL,
    description TEXT    NOT NULL,
    priority    INTEGER NOT NULL,
    status      TEXT    NOT NULL,
    assigned_at TEXT    NOT NULL,
    start_time  TEXT,
    end_time    TEXT,
    archived_at TEXT    NOT NULL
);

-- One row per full-database backup taken with "python robodb.py backup".
CREATE TABLE backup_log (
    backup_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name  TEXT    NOT NULL,
    task_count INTEGER NOT NULL,
    created_at TEXT    NOT NULL
);

-- Indexes for the questions operators ask most often:
-- "tasks for robot X, newest first" and "all tasks with status Y".
CREATE INDEX idx_tasks_robot_start ON tasks (robot_id, start_time);
CREATE INDEX idx_tasks_status      ON tasks (status);
CREATE INDEX idx_task_log_task     ON task_log (task_id);