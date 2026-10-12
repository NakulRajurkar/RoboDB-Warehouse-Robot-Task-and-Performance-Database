import sqlite3
import unittest

from helpers import assign, fresh_db, set_status


class TaskLogTriggerTest(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db()
        self.task_id = assign(self.conn, 3, 2)

    def tearDown(self):
        self.conn.close()

    def _log(self):
        return self.conn.execute(
            "SELECT old_status, new_status, changed_at FROM task_log "
            "WHERE task_id = ? ORDER BY log_id", (self.task_id,)).fetchall()

    def test_new_task_is_logged(self):
        self.assertEqual(self._log(), [(None, "assigned", "2026-09-03 08:00:00")])

    def test_every_status_change_is_logged_in_order(self):
        set_status(self.conn, self.task_id, "in_progress", "2026-09-03 08:10:00")
        set_status(self.conn, self.task_id, "completed", "2026-09-03 08:52:00")
        self.assertEqual(self._log(), [
            (None, "assigned", "2026-09-03 08:00:00"),
            ("assigned", "in_progress", "2026-09-03 08:10:00"),
            ("in_progress", "completed", "2026-09-03 08:52:00"),
        ])

    def test_rejected_change_leaves_no_log_row(self):
        with self.assertRaises(sqlite3.IntegrityError):
            set_status(self.conn, self.task_id, "completed", "2026-09-03 09:00:00")
        self.assertEqual(len(self._log()), 1)

    def test_hand_written_update_is_also_logged(self):
        self.conn.execute("UPDATE tasks SET status = 'in_progress' "
                          "WHERE task_id = ?", (self.task_id,))
        last = self._log()[-1]
        self.assertEqual(last[:2], ("assigned", "in_progress"))
        self.assertRegex(last[2], r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$")

    def test_hand_written_illegal_update_is_refused(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, "illegal"):
            self.conn.execute("UPDATE tasks SET status = 'completed' "
                              "WHERE task_id = ?", (self.task_id,))

    def test_update_of_other_columns_is_not_logged(self):
        self.conn.execute("UPDATE tasks SET priority = 5 WHERE task_id = ?",
                          (self.task_id,))
        self.assertEqual(len(self._log()), 1)

    def test_seed_produced_full_history(self):
        count = self.conn.execute(
            "SELECT COUNT(*) FROM task_log WHERE task_id <= 11").fetchone()[0]
        self.assertEqual(count, 29)

    def test_log_cannot_be_edited(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
            self.conn.execute("UPDATE task_log SET new_status = 'completed'")

    def test_log_cannot_be_deleted(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
            self.conn.execute("DELETE FROM task_log")


class RobotStatusTriggerTest(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db()

    def tearDown(self):
        self.conn.close()

    def _robot_status(self, robot_id):
        return self.conn.execute("SELECT status FROM robots WHERE robot_id = ?",
                                 (robot_id,)).fetchone()[0]

    def test_seed_left_expected_statuses(self):
        statuses = self.conn.execute(
            "SELECT status FROM robots ORDER BY robot_id").fetchall()
        self.assertEqual([s[0] for s in statuses],
                         ["busy", "idle", "idle", "maintenance", "charging"])

    def test_starting_a_task_makes_robot_busy_and_finishing_makes_it_idle(self):
        task_id = assign(self.conn, 3, 2)
        set_status(self.conn, task_id, "in_progress", "2026-09-03 08:10:00")
        self.assertEqual(self._robot_status(3), "busy")
        set_status(self.conn, task_id, "completed", "2026-09-03 08:52:00")
        self.assertEqual(self._robot_status(3), "idle")

    def test_robot_stays_busy_while_another_task_runs(self):
        task_a = assign(self.conn, 3, 2)
        task_b = assign(self.conn, 3, 2)
        set_status(self.conn, task_a, "in_progress", "2026-09-03 08:10:00")
        set_status(self.conn, task_b, "in_progress", "2026-09-03 08:11:00")
        set_status(self.conn, task_a, "failed", "2026-09-03 08:20:00")
        self.assertEqual(self._robot_status(3), "busy")

    def test_finishing_does_not_overwrite_charging(self):
        self.conn.execute("UPDATE robots SET status = 'idle' WHERE robot_id = 5")
        task_id = assign(self.conn, 5, 2)
        set_status(self.conn, task_id, "in_progress", "2026-09-03 08:10:00")
        self.conn.execute("UPDATE robots SET status = 'charging' WHERE robot_id = 5")
        set_status(self.conn, task_id, "completed", "2026-09-03 08:30:00")
        self.assertEqual(self._robot_status(5), "charging")


if __name__ == "__main__":
    unittest.main()