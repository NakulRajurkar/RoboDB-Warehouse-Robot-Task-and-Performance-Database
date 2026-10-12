"""RoboDB command line: build the database, run SQL files, back it up.

Commands:
    build           create robodb.db from the files in sql/
    run FILE        run every statement in a .sql file, print the results
    backup          copy robodb.db into backups/
    restore FILE    put a backup back in place of robodb.db
"""
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SQL_DIR = ROOT / "sql"
DB_PATH = ROOT / "robodb.db"
BACKUP_DIR = ROOT / "backups"
SCRIPT = Path(__file__).name
SEED_FILE = "05_seed.sql"


def connect(path=DB_PATH):
    """Open a connection in autocommit mode, like DBeaver's default."""
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def build_database(conn, seed=True):
    """Run every sql/0*.sql file in name order; the seed file is optional."""
    for path in sorted(SQL_DIR.glob("0*.sql")):
        if path.name == SEED_FILE and not seed:
            continue
        try:
            conn.executescript(path.read_text(encoding="utf-8"))
        except sqlite3.Error as error:
            # Say which file broke; the bare SQLite message does not.
            raise sqlite3.OperationalError(
                "in sql/%s: %s" % (path.name, error)) from error


def split_statements(sql_text):
    """Cut a script into complete statements, keeping BEGIN...END intact."""
    statements, current = [], ""
    for line in sql_text.splitlines():
        current += line + "\n"
        if sqlite3.complete_statement(current):
            code = [ln for ln in current.splitlines()
                    if ln.strip() and not ln.strip().startswith("--")]
            if code:
                statements.append(current.strip())
            current = ""
    if current.strip() and any(not ln.strip().startswith("--")
                               for ln in current.splitlines() if ln.strip()):
        statements.append(current.strip())
    return statements


def format_table(headers, rows):
    """Lay rows out as a plain text grid, showing NULL like DBeaver."""
    text_rows = [["NULL" if v is None else str(v) for v in row]
                 for row in rows]
    widths = [len(h) for h in headers]
    for row in text_rows:
        widths = [max(w, len(v)) for w, v in zip(widths, row)]
    lines = [" | ".join(h.ljust(w) for h, w in zip(headers, widths)).rstrip(),
             "-+-".join("-" * w for w in widths)]
    for row in text_rows:
        lines.append(
            " | ".join(v.ljust(w) for v, w in zip(row, widths)).rstrip())
    lines.append("(%d row%s)" % (len(rows), "" if len(rows) == 1 else "s"))
    return "\n".join(lines)


def run_file(conn, path):
    """Run each statement; print the result of every one that returns rows."""
    text = Path(path).read_text(encoding="utf-8")
    for statement in split_statements(text):
        cursor = conn.execute(statement)
        if cursor.description:
            headers = [col[0] for col in cursor.description]
            print(format_table(headers, cursor.fetchall()))
            print()


def backup_database(conn, backup_dir=BACKUP_DIR):
    """Full copy with VACUUM INTO, then record it in backup_log.

    Each backup gets its own time-stamped file (the history) and is also
    copied to robodb-latest.db (the one to restore from in a hurry).
    """
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = backup_dir / ("robodb-%s.db" % stamp)
    # Log first, so the backup file carries its own backup_log row and a
    # restore does not forget that the backup was ever taken.
    cursor = conn.execute(
        "INSERT INTO backup_log (file_name, task_count, created_at) "
        "SELECT ?, COUNT(*), strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime') "
        "FROM tasks", (target.name,))
    try:
        conn.execute("VACUUM INTO ?", (str(target),))
    except sqlite3.Error:
        conn.execute("DELETE FROM backup_log WHERE backup_id = ?",
                     (cursor.lastrowid,))
        raise
    shutil.copyfile(target, backup_dir / "robodb-latest.db")
    return target


def restore_database(backup_path, target_path=DB_PATH):
    """Overwrite the live database page by page from a backup file."""
    # sqlite3.connect would quietly create a missing file, and copying
    # that empty database over the live one would wipe it.
    if not Path(backup_path).is_file():
        raise FileNotFoundError("no backup file at %s" % backup_path)
    source = sqlite3.connect(str(backup_path))
    target = sqlite3.connect(str(target_path), timeout=5,
                             isolation_level=None)
    try:
        # backup() retries a locked target forever. Take the write lock
        # first: if DBeaver holds it, this fails after 5 seconds instead.
        target.execute("BEGIN IMMEDIATE")
        target.execute("ROLLBACK")
        source.backup(target)
    finally:
        source.close()
        target.close()


def main(argv):
    if not argv or argv[0] not in ("build", "run", "backup", "restore"):
        print(__doc__)
        return 1
    command = argv[0]
    if command == "build":
        try:
            if DB_PATH.exists():
                DB_PATH.unlink()
        except PermissionError:
            print("robodb.db is open in another program. "
                  "Disconnect it in DBeaver and try again.")
            return 1
        conn = connect()
        try:
            build_database(conn)
        except sqlite3.Error as error:
            conn.close()
            print("SQL error %s" % error)
            return 1
        for table in ("robots", "tasks", "task_log"):
            count = conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
            print("%-9s %d rows" % (table, count))
        conn.close()
        print("Built robodb.db")
        return 0
    if command in ("run", "restore") and len(argv) < 2:
        print("Give a file name, for example: python %s %s %s"
              % (SCRIPT, command, "queries/01_assign_task.sql" if command == "run"
                 else "backups/robodb-latest.db"))
        return 1
    if command == "restore":
        try:
            restore_database(ROOT / argv[1])
        except (sqlite3.Error, FileNotFoundError) as error:
            print("Restore failed: %s" % error)
            return 1
        print("Restored robodb.db from " + Path(argv[1]).name)
        return 0
    if not DB_PATH.exists():
        print("robodb.db not found. Run: python %s build" % SCRIPT)
        return 1
    conn = connect()
    try:
        if command == "run":
            run_file(conn, ROOT / argv[1])
        else:
            target = backup_database(conn)
            print("Backup written: backups/" + target.name)
    except sqlite3.Error as error:
        print("SQL error: %s" % error)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))