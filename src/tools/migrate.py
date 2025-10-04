import argparse
import hashlib
import os
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

# Where the project lives
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_DEFAULT = PROJECT_ROOT / "data" / "tracker.db"
MIGRATIONS_DIR = PROJECT_ROOT / "data" / "migrations"
BACKUPS_DIR = PROJECT_ROOT / "data" / "backups"
SCHEMA_SQL = PROJECT_ROOT / "data" / "schema.sql"

VERSION_RE = re.compile(r"^(\d{4})_(.+)\.sql$")

def db_path() -> Path:
    env = os.environ.get("TRACKERZ_DB")
    return Path(env) if env else DB_DEFAULT

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def ensure_dirs():
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

def open_db(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(f"DB not found: {path}")
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def ensure_migrations_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at_utc TEXT NOT NULL
        );
    """)
    conn.commit()

def list_files():
    files = []
    for p in sorted(MIGRATIONS_DIR.glob("*.sql")):
        m = VERSION_RE.match(p.name)
        if not m:
            continue
        version, name = m.group(1), m.group(2)
        files.append((version, name, p))
    return files

def read_file(p: Path) -> str:
    return p.read_text(encoding="utf-8")

def get_applied(conn: sqlite3.Connection):
    rows = conn.execute("SELECT version, name, checksum, applied_at_utc FROM schema_migrations ORDER BY version").fetchall()
    return {r[0]: {"name": r[1], "checksum": r[2], "applied_at_utc": r[3]} for r in rows}

def backup_db(path: Path) -> Path:
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    dest = BACKUPS_DIR / f"backup-{ts}.db"
    shutil.copy2(path, dest)
    return dest

def apply_one(conn: sqlite3.Connection, version: str, name: str, sql_text: str, checksum: str):
    with conn:
        conn.executescript(sql_text)
        conn.execute("""
            INSERT INTO schema_migrations (version, name, checksum, applied_at_utc)
            VALUES (?, ?, ?, strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        """, (version, name, checksum))

def init_from_schema():
    """Create 0001_base.sql from data/schema.sql if migrations are empty."""
    files = list_files()
    if files:
        print("Migrations directory is not empty; refusing to init from schema.")
        return 2
    if not SCHEMA_SQL.exists():
        print(f"Missing schema file: {SCHEMA_SQL}")
        return 2
    target = MIGRATIONS_DIR / "0001_base.sql"
    target.write_text(SCHEMA_SQL.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Created {target} from schema.sql")
    return 0

def do_list(conn: sqlite3.Connection):
    applied = get_applied(conn)
    files = list_files()
    if not files:
        print("(no migration files)")
        return 0
    for version, name, p in files:
        tag = "[APPLIED]" if version in applied else "[PENDING]"
        print(f"{tag} {version} {name}  {p.name}")
    return 0

def do_fake(conn: sqlite3.Connection, target: str):
    files = list_files()
    target_file = None
    for version, name, p in files:
        if version == target:
            target_file = (version, name, p)
            break
    if not target_file:
        print(f"Version {target} not found.")
        return 2
    version, name, p = target_file
    checksum = sha256_text(read_file(p))
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO schema_migrations (version, name, checksum, applied_at_utc)
            VALUES (?, ?, ?, strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        """, (version, name, checksum))
    print(f"Faked {version}_{name} as applied.")
    return 0

def do_apply(conn: sqlite3.Connection, target: str | None):
    files = list_files()
    if not files:
        print("No migration files to apply.")
        return 0

    applied = get_applied(conn)
    to_apply = []
    for version, name, p in files:
        if version in applied:
            continue
        to_apply.append((version, name, p))
        if target and version == target:
            break

    if not to_apply:
        print("Nothing to apply.")
        return 0

    dbfile = db_path()
    bkp = backup_db(dbfile)
    print(f"Backup created: {bkp}")

    for version, name, p in to_apply:
        sql_text = read_file(p)
        checksum = sha256_text(sql_text)
        print(f"Applying {version}_{name} ...")
        apply_one(conn, version, name, sql_text, checksum)
        print(f"OK {version}_{name}")
    return 0

def main():
    parser = argparse.ArgumentParser(description="trackerZ SQLite migration runner")
    parser.add_argument("--db", type=Path, default=None, help="Path to tracker.db (defaults to env TRACKERZ_DB or data/tracker.db)")
    parser.add_argument("--list", action="store_true", help="List migrations and status")
    parser.add_argument("--apply", action="store_true", help="Apply all pending migrations")
    parser.add_argument("--target", type=str, help="Apply up to this version (e.g., 0003)")
    parser.add_argument("--fake", type=str, metavar="VERSION", help="Mark VERSION as applied without running")
    parser.add_argument("--init-from-schema", action="store_true", help="Bootstrap 0001_base.sql from data/schema.sql")

    args = parser.parse_args()
    ensure_dirs()

    if args.init_from_schema:
        return init_from_schema()

    # choose DB
    path = args.db if args.db else db_path()
    conn = open_db(path)
    ensure_migrations_table(conn)

    if args.list:
        return do_list(conn)

    if args.fake:
        return do_fake(conn, args.fake)

    if args.apply or args.target:
        return do_apply(conn, args.target)

    # default: show help
    parser.print_help()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

