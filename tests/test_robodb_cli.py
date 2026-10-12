import contextlib
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path

from helpers import fresh_db, robodb


class SplitStatementsTest(unittest.TestCase):
    def test_keeps_a_trigger_body_in_one_piece(self):
        text = ("CREATE TABLE a (x);\n"
                "CREATE TRIGGER t AFTER INSERT ON a\nBEGIN\n"
                "  INSERT INTO a VALUES (1);\nEND;\n"
                "SELECT * FROM a;\n")
        parts = robodb.split_statements(text)
        self.assertEqual(len(parts), 3)
        self.assertTrue(parts[1].startswith("CREATE TRIGGER"))
        self.assertTrue(parts[1].endswith("END;"))

    def test_handles_windows_line_endings_and_comments(self):
        text = "-- a comment\r\nSELECT 1;\r\n\r\n-- trailing comment\r\n"
        parts = robodb.split_statements(text)
        self.assertEqual(parts, ["-- a comment\nSELECT 1;"])
        self.assertNotIn("\r", parts[0])

    def test_every_query_file_splits_and_runs(self):
        conn = fresh_db()
        queries = robodb.ROOT / "queries"
        for path in sorted(queries.glob("*.sql")):
            if path.name == "05_rejected_call.sql":
                continue
            with contextlib.redirect_stdout(io.StringIO()):
                robodb.run_file(conn, path)
        conn.close()

    def test_rejected_call_file_really_is_rejected(self):
        conn = fresh_db()
        path = robodb.ROOT / "queries" / "05_rejected_call.sql"
        with self.assertRaisesRegex(sqlite3.IntegrityError, "maintenance"):
            robodb.run_file(conn, path)
        conn.close()


class BuildErrorTest(unittest.TestCase):
    def test_error_names_the_broken_file(self):
        with tempfile.TemporaryDirectory() as folder:
            broken = Path(folder) / "02_triggers.sql"
            broken.write_text("CREATE TABLE a (x);\n"
                              "CREATE TRIGGER t AFTER INSERT ON a\nBEGIN\n"
                              "  SELECT 1;\n", encoding="utf-8")
            saved, robodb.SQL_DIR = robodb.SQL_DIR, Path(folder)
            conn = robodb.connect(":memory:")
            try:
                with self.assertRaisesRegex(sqlite3.Error,
                                            "sql/02_triggers.sql: incomplete"):
                    robodb.build_database(conn)
            finally:
                robodb.SQL_DIR = saved
                conn.close()


class FormatTableTest(unittest.TestCase):
    def test_aligns_columns_and_shows_null(self):
        text = robodb.format_table(["id", "name"], [(1, "Robo"), (22, None)])
        self.assertEqual(text.splitlines(), [
            "id | name",
            "---+-----",
            "1  | Robo",
            "22 | NULL",
            "(2 rows)",
        ])


class BackupRestoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.db_path = self.folder / "live.db"
        conn = robodb.connect(self.db_path)
        robodb.build_database(conn)
        conn.close()

    def tearDown(self):
        self.tmp.cleanup()

    def _count(self, path, table):
        conn = sqlite3.connect(str(path))
        try:
            return conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
        finally:
            conn.close()

    def test_backup_writes_a_copy_and_logs_it_inside_the_copy(self):
        conn = robodb.connect(self.db_path)
        target = robodb.backup_database(conn, self.folder / "backups")
        conn.close()
        self.assertTrue(target.exists())
        self.assertTrue((self.folder / "backups" / "robodb-latest.db").exists())
        self.assertEqual(self._count(target, "tasks"), 11)
        self.assertEqual(self._count(target, "backup_log"), 1)
        self.assertEqual(self._count(self.db_path, "backup_log"), 1)

    def test_restore_brings_back_archived_tasks(self):
        conn = robodb.connect(self.db_path)
        target = robodb.backup_database(conn, self.folder / "backups")
        conn.execute("INSERT INTO sp_archive_tasks (before_time) "
                     "VALUES ('2099-01-01 00:00:00')")
        conn.close()
        # Only the running task 10 and the waiting task 11 stay live.
        self.assertEqual(self._count(self.db_path, "tasks"), 2)
        robodb.restore_database(target, self.db_path)
        self.assertEqual(self._count(self.db_path, "tasks"), 11)
        self.assertEqual(self._count(self.db_path, "tasks_archive"), 0)

    def test_restore_gives_up_when_the_database_is_locked(self):
        conn = robodb.connect(self.db_path)
        target = robodb.backup_database(conn, self.folder / "backups")
        conn.execute("BEGIN IMMEDIATE")  # like an uncommitted DBeaver edit
        try:
            with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                robodb.restore_database(target, self.db_path)
        finally:
            conn.execute("ROLLBACK")
            conn.close()

    def test_restore_from_missing_file_leaves_database_alone(self):
        missing = self.folder / "backups" / "nope.db"
        with self.assertRaises(FileNotFoundError):
            robodb.restore_database(missing, self.db_path)
        self.assertFalse(missing.exists())
        self.assertEqual(self._count(self.db_path, "tasks"), 11)


if __name__ == "__main__":
    unittest.main()