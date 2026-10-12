import sqlite3
import unittest

from helpers import assign, fresh_db, set_status


class AssignTaskTest(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db()

    def tearDown(self):
        self.conn.close()

    def test_returns_the_new_task_id(self):
        new_id = assign(self.conn, 3, 2)
        self.assertEqual(new_id, 12)  # the seed creates tasks 1-11

    def test_inserts_an_assigned_task_with_the_given_values(self):
        new_id = assign(self.conn, 3, 2, "Move pallet C07 to dock 2")
        row = self.conn.execute(
            "SELECT robot_id, priority, description, status, assigned_at, "
            "start_time, end_time FROM tasks WHERE task_id = ?",
            (new_id,)).fetchone()
        self.assertEqual(row, (3, 2, "Move pallet C07 to dock 2", "assigned",
                               "2026-09-03 08:00:00", None, None))

    def test_each_call_returns_a_different_id(self):
        first = assign(self.conn, 1, 3)
        second = assign(self.conn, 2, 3)
        self.assertEqual(second, first + 1)

    def test_assigned_at_defaults_to_now(self):
        self.conn.execute(
            "INSERT INTO sp_assign_task (robot_id, priority) VALUES (2, 4)")
        assigned_at = self.conn.execute(
            "SELECT assigned_at FROM tasks WHERE task_id = 12").fetchone()[0]
        self.assertRegex(assigned_at, r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$")

    def test_rejects_unknown_robot(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, "does not exist"):
            assign(self.conn, 99, 2)
        self.assertEqual(self._task_count(), 11)

    def test_rejects_robot_in_maintenance(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, "maintenance"):
            assign(self.conn, 4, 1)
        self.assertEqual(self._task_count(), 11)

    def test_rejects_priority_out_of_range(self):
        for bad in (0, 6, None):
            with self.assertRaisesRegex(sqlite3.IntegrityError, "priority"):
                assign(self.conn, 1, bad)
        self.assertEqual(self._task_count(), 11)

    def _task_count(self):
        return self.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]


class UpdateTaskStatusTest(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db()
        self.task_id = assign(self.conn, 3, 2)

    def tearDown(self):
        self.conn.close()

    def _task(self):
        return self.conn.execute(
            "SELECT status, start_time, end_time FROM tasks WHERE task_id = ?",
            (self.task_id,)).fetchone()

    def test_in_progress_sets_start_time(self):
        set_status(self.conn, self.task_id, "in_progress", "2026-09-03 08:10:00")
        self.assertEqual(self._task(),
                         ("in_progress", "2026-09-03 08:10:00", None))

    def test_completed_sets_end_time_and_keeps_start_time(self):
        set_status(self.conn, self.task_id, "in_progress", "2026-09-03 08:10:00")
        set_status(self.conn, self.task_id, "completed", "2026-09-03 08:52:00")
        self.assertEqual(self._task(), ("completed", "2026-09-03 08:10:00",
                                        "2026-09-03 08:52:00"))

    def test_cancel_before_starting(self):
        set_status(self.conn, self.task_id, "cancelled", "2026-09-03 08:05:00")
        self.assertEqual(self._task(),
                         ("cancelled", None, "2026-09-03 08:05:00"))

    def test_rejects_skipping_in_progress(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, "illegal"):
            set_status(self.conn, self.task_id, "completed", "2026-09-03 09:00:00")
        self.assertEqual(self._task(), ("assigned", None, None))

    def test_rejects_reopening_a_completed_task(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, "illegal"):
            set_status(self.conn, 1, "assigned", "2026-09-03 09:00:00")

    def test_rejects_unknown_status(self):
        with self.assertRaises(sqlite3.IntegrityError):
            set_status(self.conn, self.task_id, "lost", "2026-09-03 09:00:00")
        self.assertEqual(self._task(), ("assigned", None, None))

    def test_rejects_same_status(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, "already"):
            set_status(self.conn, self.task_id, "assigned", "2026-09-03 09:00:00")

    def test_rejects_unknown_task(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, "does not exist"):
            set_status(self.conn, 999, "in_progress", "2026-09-03 09:00:00")

    def test_rejects_end_before_start(self):
        set_status(self.conn, self.task_id, "in_progress", "2026-09-03 08:10:00")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "CHECK"):
            set_status(self.conn, self.task_id, "completed", "2026-09-03 08:00:00")
        self.assertEqual(self._task()[0], "in_progress")


class ArchiveTasksTest(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db()

    def tearDown(self):
        self.conn.close()

    def test_moves_old_finished_tasks_and_reports_how_many(self):
        self.conn.execute("INSERT INTO sp_archive_tasks (before_time) "
                          "VALUES ('2026-09-02 00:00:00')")
        moved = self.conn.execute("SELECT value FROM proc_result "
                                  "WHERE proc_name = 'sp_archive_tasks'"
                                  ).fetchone()[0]
        archived = [r[0] for r in self.conn.execute(
            "SELECT task_id FROM tasks_archive ORDER BY task_id")]
        live = [r[0] for r in self.conn.execute(
            "SELECT task_id FROM tasks ORDER BY task_id")]
        self.assertEqual(moved, 7)
        self.assertEqual(archived, [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(live, [8, 9, 10, 11])

    def test_keeps_unfinished_tasks_and_their_history(self):
        self.conn.execute("INSERT INTO sp_archive_tasks (before_time) "
                          "VALUES ('2099-01-01 00:00:00')")
        statuses = {r[0] for r in self.conn.execute("SELECT status FROM tasks")}
        self.assertEqual(statuses, {"in_progress", "assigned"})
        log_rows = self.conn.execute("SELECT COUNT(*) FROM task_log").fetchone()[0]
        self.assertEqual(log_rows, 29)

    def test_archived_ids_are_never_reused(self):
        self.conn.execute("INSERT INTO sp_archive_tasks (before_time) "
                          "VALUES ('2099-01-01 00:00:00')")
        self.conn.execute("DELETE FROM tasks")
        self.assertEqual(assign(self.conn, 1, 1), 12)


if __name__ == "__main__":
    unittest.main()