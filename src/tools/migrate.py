# File: src/tools/migrate.py
# Python 3.12+
# Usage examples:
#   python -m src.tools.migrate up
#   python -m src.tools.migrate status
#   python -m src.tools.migrate rebuild --seed
#   python -m src.tools.migrate up --db /path/to/tracker.db
#
# Notes:
# - DB path defaults to env TRACKERZ_DB or data/tracker.db
# - Applies data/schema.sql on rebuild or if DB is empty
# - Applies data/migrations/*.sql in lexicographic order
# - Records applied migrations (name + sha256) in schema_migrations
# - Seeds from data/seed.sql or data/seeds.sql when --seed is given

from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import sys
from datetime import datetime, timezone
from glob import glob
from pathlib import Path
from typing import Iterable, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]  # repo root
DEFAULT_DB = Path(os.environ.get("TRACKERZ_DB", ROOT / "data" / "tracker.db"))
DEFAULT_SCHEMA = ROOT / "data" / "schema.sql"
DEFAULT_MIGRATIONS_DIR = ROOT / "data" / "migrations"
DEFAULT_SEED_FILES = [ROOT / "data" / "seed.sql", ROOT / "data" / "seeds.sql"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8") as f:
        return f.read()


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def connect(db_path: Path) -> sqlite3.Connection:
    ensure_parent_dir(db_path)
    conn = sqlite3.connect(db_path)
    conn.isolation_level = None  # we'll manage transactions
    conn.execute("PRAGMA foreign_keys = ON;")
    # journaling & perf pragmas
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


def exec_script(conn: sqlite3.Connection, sql_text: str) -> None:
    # Use executescript inside an explicit transaction for safety.
    conn.execute("BEGIN;")
    try:
        conn.executescript(sql_text)
    except Exception:
        conn.execute("ROLLBACK;")
        raise
    else:
        conn.execute("COMMIT;")


def ensure_migrations_table(conn: sqlite3.Connection) -> None:
    exec_script(
        conn,
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL UNIQUE,
            sha256 TEXT NOT NULL,
            applied_at_utc TEXT NOT NULL
        );
        """,
    )


def get_applied(conn: sqlite3.Connection) -> dict[str, Tuple[str, str]]:
    cur = conn.execute(
        "SELECT filename, sha256, applied_at_utc FROM schema_migrations ORDER BY filename;"
    )
    rows = cur.fetchall()
    return {r[0]: (r[1], r[2]) for r in rows}


def list_migration_files(migrations_dir: Path) -> list[Path]:
    files = sorted(Path(migrations_dir).glob("*.sql"))
    return files


def db_is_empty(conn: sqlite3.Connection) -> bool:
    cur = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%';"
    )
    (count,) = cur.fetchone()
    return count == 0


def apply_schema_if_needed(conn: sqlite3.Connection, schema_path: Path, force: bool) -> bool:
    if force or db_is_empty(conn):
        if not schema_path.exists():
            raise FileNotFoundError(f"schema.sql not found at: {schema_path}")
        print(f"→ Applying schema: {schema_path}")
        exec_script(conn, read_text(schema_path))
        return True
    return False


def apply_migrations(
    conn: sqlite3.Connection, migrations: Iterable[Path], stop_on_changed_hash: bool = False
) -> list[str]:
    ensure_migrations_table(conn)
    applied = get_applied(conn)
    applied_now: list[str] = []

    for path in migrations:
        name = path.name
        sql = read_text(path)
        digest = sha256_bytes(sql.encode("utf-8"))

        if name in applied:
            recorded_hash, when = applied[name]
            if recorded_hash != digest:
                msg = (
                    f"⚠️  Hash changed for already applied migration {name}.\n"
                    f"    recorded={recorded_hash}\n"
                    f"    current ={digest}\n"
                    "    This suggests the file was edited after application."
                )
                if stop_on_changed_hash:
                    raise RuntimeError(msg)
                else:
                    print(msg)
            # skip re-apply
            continue

        print(f"→ Applying migration: {name}")
        exec_script(conn, sql)
        conn.execute(
            "INSERT INTO schema_migrations (filename, sha256, applied_at_utc) VALUES (?, ?, ?);",
            (name, digest, utc_now_iso()),
        )
        applied_now.append(name)

    return applied_now


def seed_if_requested(conn: sqlite3.Connection, seed_files: list[Path]) -> Optional[Path]:
    for path in seed_files:
        if path.exists():
            print(f"→ Seeding from: {path}")
            exec_script(conn, read_text(path))
            return path
    return None


def cmd_status(db: Path, migrations_dir: Path) -> int:
    conn = connect(db)
    try:
        ensure_migrations_table(conn)
        applied = get_applied(conn)
        mig_files = list_migration_files(migrations_dir)

        print(f"DB: {db}")
        print(f"Migrations dir: {migrations_dir}")
        print(f"Applied count: {len(applied)}")
        for name, (h, when) in applied.items():
            print(f"  ✔ {name}  ({when})")

        pending = [p.name for p in mig_files if p.name not in applied]
        if pending:
            print(f"Pending count: {len(pending)}")
            for name in pending:
                print(f"  ⧗ {name}")
        else:
            print("Pending count: 0")
        return 0
    finally:
        conn.close()


def cmd_up(db: Path, schema: Path, migrations_dir: Path, seed: bool) -> int:
    conn = connect(db)
    try:
        created = apply_schema_if_needed(conn, schema, force=False)
        ensure_migrations_table(conn)
        pending = apply_migrations(conn, list_migration_files(migrations_dir))
        if created or pending:
            print("✓ Database is up to date.")
        else:
            print("✓ No changes. Database already up to date.")
        if seed:
            seeded = seed_if_requested(conn, DEFAULT_SEED_FILES)
            if not seeded:
                print("ℹ️  Seed requested but no seed.sql/seeds.sql found.")
        return 0
    finally:
        conn.close()


def cmd_rebuild(db: Path, schema: Path, migrations_dir: Path, seed: bool) -> int:
    # Drop DB file and rebuild from schema + migrations
    if db.exists():
        print(f"⟲ Rebuilding: removing existing DB {db}")
        db.unlink()
    conn = connect(db)
    try:
        apply_schema_if_needed(conn, schema, force=True)
        ensure_migrations_table(conn)
        apply_migrations(conn, list_migration_files(migrations_dir))
        if seed:
            seeded = seed_if_requested(conn, DEFAULT_SEED_FILES)
            if not seeded:
                print("ℹ️  Seed requested but no seed.sql/seeds.sql found.")
        print("✓ Rebuild complete.")
        return 0
    finally:
        conn.close()


def cmd_verify(db: Path) -> int:
    conn = connect(db)
    try:
        # Minimal structural assertions that reflect your roadmap (M2/M3)
        required_tables = [
            "projects",
            "tasks",
            "subtasks",
            "task_updates",
            "subtask_updates",
            "phases",
            "phase_transitions",
            "attachments",
            "purchases",
            "expenses",
            "settings",
            "schema_migrations",
        ]
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        )
        names = {r[0] for r in cur.fetchall()}
        missing = [t for t in required_tables if t not in names]
        if missing:
            print("❌ Missing tables:", ", ".join(missing))
            return 2

        # Check a couple of triggers exist (names can be adjusted to yours)
        expected_triggers = [
            "trg_tasks_phase_validate",
            "trg_subtasks_phase_validate",
            "trg_tasks_touch_updated_at_on_phase",
            "trg_subtasks_touch_updated_at_on_phase",
        ]
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger';"
        )
        trig = {r[0] for r in cur.fetchall()}
        trig_missing = [t for t in expected_triggers if t not in trig]
        if trig_missing:
            print("❌ Missing triggers:", ", ".join(trig_missing))
            return 3

        # journal mode
        (mode,) = conn.execute("PRAGMA journal_mode;").fetchone()
        if str(mode).lower() != "wal":
            print(f"❌ journal_mode is not WAL (got {mode})")
            return 4

        print("✓ Verification passed.")
        return 0
    finally:
        conn.close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="trackerZ-migrate", description="SQLite migration runner for trackerZ")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp: argparse.ArgumentParser):
        sp.add_argument("--db", type=Path, default=DEFAULT_DB, help=f"Path to SQLite DB (default: {DEFAULT_DB})")
        sp.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA, help=f"Path to schema.sql (default: {DEFAULT_SCHEMA})")
        sp.add_argument("--migrations-dir", type=Path, default=DEFAULT_MIGRATIONS_DIR, help=f"Migrations directory (default: {DEFAULT_MIGRATIONS_DIR})")

    s_up = sub.add_parser("up", help="Apply schema if empty and run pending migrations")
    add_common(s_up)
    s_up.add_argument("--seed", action="store_true", help="Seed after applying")

    s_rebuild = sub.add_parser("rebuild", help="Drop and recreate DB from schema + migrations")
    add_common(s_rebuild)
    s_rebuild.add_argument("--seed", action="store_true", help="Seed after rebuild")

    s_status = sub.add_parser("status", help="Show applied and pending migrations")
    add_common(s_status)

    s_verify = sub.add_parser("verify", help="Lightweight structural verification")
    s_verify.add_argument("--db", type=Path, default=DEFAULT_DB, help=f"Path to SQLite DB (default: {DEFAULT_DB})")

    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    ns = parse_args(argv or sys.argv[1:])
    if ns.cmd == "status":
        return cmd_status(ns.db, ns.migrations_dir)
    if ns.cmd == "up":
        return cmd_up(ns.db, ns.schema, ns.migrations_dir, ns.seed)
    if ns.cmd == "rebuild":
        return cmd_rebuild(ns.db, ns.schema, ns.migrations_dir, ns.seed)
    if ns.cmd == "verify":
        return cmd_verify(ns.db)
    raise SystemExit(1)


if __name__ == "__main__":
    raise SystemExit(main())

