#!/usr/bin/env python3
# Rev 0.1.1
import sqlite3, sys, pathlib

DB = sys.argv[1] if len(sys.argv) > 1 else "data/tracker.db"
TITLE_TARGETS = {
    "projects": "title",
    "tasks": "title",
    "subtasks": "title",
}
ACTOR_COLS = {"created_by","updated_by","modified_by","author_id","actor_id","user_id","assigned_by"}

def table_cols(cur, table):
    cur.execute(f"PRAGMA table_info({table})")
    return {r[1] for r in cur.fetchall()}

def rename_col(cur, table, old, new):
    print(f"- {table}: rename {old} -> {new}")
    cur.execute(f'ALTER TABLE "{table}" RENAME COLUMN "{old}" TO "{new}"')

def drop_col(cur, table, col):
    print(f"- {table}: drop {col}")
    cur.execute(f'ALTER TABLE "{table}" DROP COLUMN "{col}"')

def main():
    if not pathlib.Path(DB).exists():
        print(f"error: DB not found at {DB}", file=sys.stderr); sys.exit(2)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys=ON")
    cur = con.cursor()

    # 1) rename title -> name where present
    for tbl, old in TITLE_TARGETS.items():
        cols = table_cols(cur, tbl)
        if old in cols and "name" not in cols:
            rename_col(cur, tbl, old, "name")

    # 2) drop actor columns where present
    #    Scan all user tables
    cur.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
    """)
    tables = [r[0] for r in cur.fetchall()]
    for tbl in tables:
        cols = table_cols(cur, tbl)
        for col in sorted(cols & ACTOR_COLS):
            drop_col(cur, tbl, col)

    con.commit()
    print("done.")
    con.close()

if __name__ == "__main__":
    main()

