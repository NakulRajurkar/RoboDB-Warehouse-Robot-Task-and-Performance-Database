"""Shared set-up: a fresh in-memory RoboDB for every test."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import robodb  # noqa: E402


def fresh_db(seed=True):
    """Build the full schema (and sample data) in memory."""
    conn = robodb.connect(":memory:")
    robodb.build_database(conn, seed=seed)
    return conn


def assign(conn, robot_id, priority, description="test task",
           assigned_at="2026-09-03 08:00:00"):
    """Call sp_assign_task and return the task id it reports."""
    conn.execute(
        "INSERT INTO sp_assign_task (robot_id, priority, description, assigned_at) "
        "VALUES (?, ?, ?, ?)", (robot_id, priority, description, assigned_at))
    return conn.execute(
        "SELECT value FROM proc_result WHERE proc_name = 'sp_assign_task'"
    ).fetchone()[0]


def set_status(conn, task_id, new_status, changed_at):
    """Call sp_update_task_status."""
    conn.execute(
        "INSERT INTO sp_update_task_status (task_id, new_status, changed_at) "
        "VALUES (?, ?, ?)", (task_id, new_status, changed_at))