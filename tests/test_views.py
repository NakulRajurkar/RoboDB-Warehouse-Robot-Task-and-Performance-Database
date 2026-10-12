import unittest

from helpers import assign, fresh_db, set_status


class RobotTasksViewTest(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db()

    def tearDown(self):
        self.conn.close()

    def test_robot_tasks_newest_start_first(self):
        rows = self.conn.execute(
            "SELECT task_id, start_time FROM v_robot_tasks WHERE robot_id = 1 "
            "ORDER BY start_time DESC").fetchall()
        self.assertEqual([r[0] for r in rows], [10, 4, 2])

    def test_only_the_chosen_robot_appears(self):
        robots = {r[0] for r in self.conn.execute(
            "SELECT robot_id FROM v_robot_tasks WHERE robot_id = 3")}
        self.assertEqual(robots, {3})

    def test_duration_in_minutes(self):
        row = self.conn.execute(
            "SELECT duration_min FROM v_robot_tasks WHERE task_id = 1").fetchone()
        self.assertEqual(row[0], 60.0)

    def test_unfinished_task_has_no_duration(self):
        row = self.conn.execute(
            "SELECT duration_min FROM v_robot_tasks WHERE task_id = 10").fetchone()
        self.assertIsNone(row[0])

    def test_unstarted_tasks_come_last(self):
        rows = self.conn.execute(
            "SELECT task_id FROM v_robot_tasks WHERE robot_id = 2 "
            "ORDER BY start_time DESC").fetchall()
        self.assertEqual([r[0] for r in rows], [7, 3, 11])


class CompletedSummaryViewTest(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db()

    def tearDown(self):
        self.conn.close()

    def _summary(self):
        return self.conn.execute(
            "SELECT robot_id, completed_tasks, avg_duration_min "
            "FROM v_completed_task_summary").fetchall()

    def test_counts_and_average_durations(self):
        self.assertEqual(self._summary(), [
            (1, 2, 37.5), (2, 1, 20.0), (3, 3, 50.0), (4, 1, 25.0), (5, 0, None),
        ])

    def test_failed_and_cancelled_tasks_are_not_counted(self):
        # Robot 2 failed task 7 and robot 4 cancelled task 9.
        summary = {r[0]: r[1] for r in self._summary()}
        self.assertEqual(summary[2], 1)
        self.assertEqual(summary[4], 1)

    def test_new_completion_updates_the_report(self):
        task_id = assign(self.conn, 5, 2)
        set_status(self.conn, task_id, "in_progress", "2026-09-03 08:00:00")
        set_status(self.conn, task_id, "completed", "2026-09-03 08:12:00")
        self.assertIn((5, 1, 12.0), self._summary())


class LatestTaskViewTest(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db()

    def tearDown(self):
        self.conn.close()

    def _latest(self):
        return self.conn.execute(
            "SELECT robot_id, robot_status, latest_task_id, task_status "
            "FROM v_robot_latest_task").fetchall()

    def test_one_row_per_robot_with_its_latest_task(self):
        self.assertEqual(self._latest(), [
            (1, "busy", 10, "in_progress"),
            (2, "idle", 11, "assigned"),
            (3, "idle", 8, "completed"),
            (4, "maintenance", 9, "cancelled"),
            (5, "charging", None, None),
        ])

    def test_new_assignment_becomes_the_latest(self):
        task_id = assign(self.conn, 3, 1, assigned_at="2026-09-03 08:00:00")
        rows = {r[0]: r for r in self._latest()}
        self.assertEqual(rows[3], (3, "idle", task_id, "assigned"))

    def test_tie_on_assigned_at_picks_the_higher_task_id(self):
        first = assign(self.conn, 2, 1, assigned_at="2026-09-04 08:00:00")
        second = assign(self.conn, 2, 1, assigned_at="2026-09-04 08:00:00")
        rows = {r[0]: r for r in self._latest()}
        self.assertGreater(second, first)
        self.assertEqual(rows[2][2], second)


if __name__ == "__main__":
    unittest.main()