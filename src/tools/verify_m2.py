# src/tools/verify_m2.py
import sqlite3, sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

DB_PATH = Path("data/tracker.db")
EXPECTED_TABLES = ["attachments", "purchases", "expenses", "settings"]

def fail(msg: str) -> None:
    print(f"❌ {msg}")
    sys.exit(1)

def ok(msg: str) -> None:
    print(f"✅ {msg}")

def note(msg: str) -> None:
    print(f"ℹ️  {msg}")

def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (name,)
    ).fetchone()
    return row is not None

def table_columns(conn: sqlite3.Connection, name: str) -> List[Tuple]:
    # cid, name, type, notnull, dflt_value, pk
    return conn.execute(f"PRAGMA table_info({name});").fetchall()

def required_cols(cols: List[Tuple]) -> List[Tuple[str, str]]:
    req = []
    for cid, name, ctype, notnull, dflt, pk in cols:
        if pk == 1 and name.lower() == "id":
            continue
        if notnull == 1 and dflt is None:
            req.append((name, ctype))
    return req

def choose_first_existing(cols: List[str], candidates: List[str]) -> Optional[str]:
    lower = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    return None

def default_for_type(ctype: str) -> Any:
    t = (ctype or "").upper()
    if "INT" in t:
        return 0
    if any(x in t for x in ["REAL", "FLOA", "DOUB"]):
        return 0.0
    return "."

def fk_map(conn: sqlite3.Connection, table: str) -> Dict[str, Tuple[str, str, str]]:
    """
    Map of from_col -> (ref_table, on_update, on_delete)
    """
    rows = conn.execute(f"PRAGMA foreign_key_list({table});").fetchall()
    return {r[3]: (r[2], r[5].upper(), r[6].upper()) for r in rows}  # from -> (table, on_upd, on_del)

def insert_row(conn: sqlite3.Connection, table: str, base_values: Dict[str, Any]) -> int:
    cols_info = table_columns(conn, table)
    if not cols_info:
        fail(f"Could not introspect table {table}")

    all_col_names = [c[1] for c in cols_info]

    # Ensure required columns are populated
    for name, ctype in required_cols(cols_info):
        if name not in base_values:
            base_values[name] = default_for_type(ctype)

    # Build INSERT using only columns that actually exist
    cols = [c for c in base_values.keys() if c in all_col_names]
    if not cols:
        fail(f"No valid columns to insert for {table}. (keys don’t match schema)")

    placeholders = ",".join(["?"] * len(cols))
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders});"
    conn.execute(sql, tuple(base_values[c] for c in cols))
    return conn.execute("SELECT last_insert_rowid();").fetchone()[0]

def foreign_key_health(conn: sqlite3.Connection) -> None:
    problems = conn.execute("PRAGMA foreign_key_check;").fetchall()
    if problems:
        details = "; ".join([f"{t} rowid={rid} -> {p} (fk={fkid})" for t, rid, p, fkid in problems[:5]])
        fail(f"Foreign key violations detected: {details}")
    ok("Foreign key integrity check passed.")

def ensure_default_phase(conn: sqlite3.Connection) -> Optional[int]:
    """
    Ensure at least one row exists in phases. Return its id (first row).
    If phases table doesn't exist, return None.
    """
    if not table_exists(conn, "phases"):
        return None
    row = conn.execute("SELECT id FROM phases LIMIT 1;").fetchone()
    if row:
        return row[0]
    # create a minimal 'Open' phase
    # tolerate flexible schemas: try typical columns, fall back to only id autoincrement
    cols = [c[1] for c in table_columns(conn, "phases")]
    vals: Dict[str, Any] = {}
    label_col = choose_first_existing(cols, ["name", "title", "label"])
    if label_col:
        vals[label_col] = "Open"
    if "slug" in [c.lower() for c in cols]:
        # find real-case slug column
        real_slug = [c for c in cols if c.lower() == "slug"][0]
        vals[real_slug] = "open"
    # timestamps if present
    for ts in ["created_at_utc", "updated_at_utc"]:
        if ts in cols:
            vals[ts] = "2025-10-03T20:00:00Z"
    phase_id = insert_row(conn, "phases", vals)
    ok(f"Seeded default phase id={phase_id}.")
    return phase_id

def apply_required_phase_ids(conn: sqlite3.Connection, table: str, base: Dict[str, Any], default_phase_id: Optional[int]) -> None:
    """
    If table has required phase FKs (e.g., phase_id/current_phase_id with NOT NULL and no default),
    fill them with default_phase_id (if available).
    """
    if default_phase_id is None:
        return
    cols_info = table_columns(conn, table)
    required = {name for name, _ in required_cols(cols_info)}
    candidate_cols = {"phase_id", "current_phase_id"}
    for col in candidate_cols:
        # choose real-case name if present
        real = next((c[1] for c in cols_info if c[1].lower() == col), None)
        if real and real in required and real not in base:
            base[real] = default_phase_id

def main() -> None:
    if not DB_PATH.exists():
        fail(f"Database not found at {DB_PATH}. Run your migration tool first.")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON;")

    try:
        conn.execute("BEGIN;")

        # 0) Ensure new tables exist
        for t in EXPECTED_TABLES:
            if not table_exists(conn, t):
                fail(f"Missing table: {t}")
            if not table_columns(conn, t):
                fail(f"Could not read columns for table: {t}")
            ok(f"{t} exists and is introspectable.")

        # 1) Ensure there is at least one phase (if phases table exists)
        default_phase_id = ensure_default_phase(conn)

        # 2) Create minimal project → task → subtask chain
        # Projects
        proj_cols = [c[1] for c in table_columns(conn, "projects")]
        proj_label_col = choose_first_existing(proj_cols, ["name", "title", "label", "project_name"])
        project_vals = {
            (proj_label_col or "IGNORED"): "VerifyM2 Project",
            "created_at_utc": "2025-10-03T20:00:00Z",
            "updated_at_utc": "2025-10-03T20:00:00Z",
        }
        if proj_label_col is None:
            project_vals.pop("IGNORED", None)
        apply_required_phase_ids(conn, "projects", project_vals, default_phase_id)
        project_id = insert_row(conn, "projects", project_vals)

        # Tasks
        task_cols = [c[1] for c in table_columns(conn, "tasks")]
        task_label_col = choose_first_existing(task_cols, ["title", "name", "summary", "label"])
        task_vals = {
            "project_id": project_id,
            (task_label_col or "IGNORED"): "VerifyM2 Task",
            "created_at_utc": "2025-10-03T20:01:00Z",
            "updated_at_utc": "2025-10-03T20:01:00Z",
        }
        if task_label_col is None:
            task_vals.pop("IGNORED", None)
        apply_required_phase_ids(conn, "tasks", task_vals, default_phase_id)
        task_id = insert_row(conn, "tasks", task_vals)

        # Subtasks (if any)
        if table_exists(conn, "subtasks"):
            subtask_cols = [c[1] for c in table_columns(conn, "subtasks")]
            subtask_label_col = choose_first_existing(subtask_cols, ["title", "name", "summary", "label"])
            subtask_vals = {
                "task_id": task_id,
                (subtask_label_col or "IGNORED"): "VerifyM2 Subtask",
                "created_at_utc": "2025-10-03T20:02:00Z",
                "updated_at_utc": "2025-10-03T20:02:00Z",
            }
            if subtask_label_col is None:
                subtask_vals.pop("IGNORED", None)
            apply_required_phase_ids(conn, "subtasks", subtask_vals, default_phase_id)
            subtask_id = insert_row(conn, "subtasks", subtask_vals)
        else:
            subtask_id = None
            note("Table 'subtasks' missing; skipping subtask part of the chain.")

        # 3) Attachment linked to project + task
        attach_vals = {
            "project_id": project_id,
            "task_id": task_id,
            "filename": "log.txt",
            "stored_path": "attachments/log.txt",
            "mime_type": "text/plain",
            "size_bytes": 12,
            "sha256_hex": None,
            "created_at_utc": "2025-10-03T20:03:00Z",
            "updated_at_utc": "2025-10-03T20:03:00Z",
            "note": "test attachment",
        }
        attachment_id = insert_row(conn, "attachments", attach_vals)

        # 4) purchases + expenses
        purchase_vals = {
            "project_id": project_id,
            "task_id": task_id,
            "status": "submitted",
            "vendor": "VendorCo",
            "reference_code": "PO-123",
            "description": "Test purchase",
            "total_cents": 12345,
            "currency": "USD",
            "requested_by": "tester",
            "created_at_utc": "2025-10-03T20:04:00Z",
            "updated_at_utc": "2025-10-03T20:04:00Z",
        }
        purchase_id = insert_row(conn, "purchases", purchase_vals)

        expense_vals = {
            "project_id": project_id,
            "task_id": task_id,
            "category": "materials",
            "description": "Test expense",
            "amount_cents": 2345,
            "currency": "USD",
            "incurred_at_utc": "2025-10-03T19:00:00Z",
            "receipt_attachment_id": attachment_id,
            "created_at_utc": "2025-10-03T20:05:00Z",
            "updated_at_utc": "2025-10-03T20:05:00Z",
        }
        expense_id = insert_row(conn, "expenses", expense_vals)

        # Basic FK integrity at this point
        foreign_key_health(conn)

        # 5) Try safe cleanup order depending on typical FKs:
        # Delete subtask first (if exists), then attachment (if NO ACTION), then task, then project.
        if subtask_id is not None:
            try:
                conn.execute("DELETE FROM subtasks WHERE id = ?;", (subtask_id,))
            except sqlite3.IntegrityError:
                # If subtasks has other dependents, skip strict delete
                note("Could not delete subtask first; continuing with remaining checks.")

        # If expenses.receipt_attachment_id is NO ACTION, null it before deleting the attachment/task.
        # Detect FK action:
        exp_fks = fk_map(conn, "expenses")
        rec_fk = exp_fks.get("receipt_attachment_id")
        if rec_fk and rec_fk[2] not in ("SET NULL", "CASCADE"):
            conn.execute(
                "UPDATE expenses SET receipt_attachment_id = NULL WHERE id = ?;",
                (expense_id,)
            )
            ok("Manually nulled expenses.receipt_attachment_id to avoid NO ACTION breakage.")

        # If attachments.task_id is NO ACTION, delete attachment before task:
        att_fks = fk_map(conn, "attachments")
        att_task_fk = att_fks.get("task_id")
        if att_task_fk and att_task_fk[2] not in ("SET NULL", "CASCADE"):
            conn.execute("DELETE FROM attachments WHERE id = ?;", (attachment_id,))
            ok("Deleted attachment explicitly (NO ACTION on attachments.task_id).")
            attachment_id = None

        # Now delete task
        try:
            conn.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
            ok("Deleted task.")
        except sqlite3.IntegrityError as e:
            fail(f"Could not delete task due to FK constraints: {e}")

        # If purchases/expenses FKs are SET NULL, verify; otherwise tolerate.
        pur_fks = fk_map(conn, "purchases")
        exp_task_fk = exp_fks.get("task_id")
        pur_task_fk = pur_fks.get("task_id")

        if pur_task_fk and pur_task_fk[2] == "SET NULL":
            row = conn.execute("SELECT task_id FROM purchases WHERE id = ?;", (purchase_id,)).fetchone()
            if row is None or row[0] is not None:
                fail("Purchase.task_id did not become NULL after task deletion.")
            ok("Purchase.task_id SET NULL on task delete verified.")

        if exp_task_fk and exp_task_fk[2] == "SET NULL":
            row = conn.execute("SELECT task_id FROM expenses WHERE id = ?;", (expense_id,)).fetchone()
            if row is None or row[0] is not None:
                fail("Expense.task_id did not become NULL after task deletion.")
            ok("Expense.task_id SET NULL on task delete verified.")

        # If attachment still exists and was CASCADE-deleted via task, ensure expense's receipt pointer is valid
        if attachment_id is not None:
            # Attachment still present; fine either way.
            pass
        else:
            # Attachment likely deleted; if expenses has SET NULL, it should already be NULL.
            if rec_fk and rec_fk[2] == "SET NULL":
                row = conn.execute("SELECT receipt_attachment_id FROM expenses WHERE id = ?;", (expense_id,)).fetchone()
                if row and row[0] is not None:
                    fail("Expense.receipt_attachment_id not NULL after attachment removal.")
                ok("Expense.receipt_attachment_id NULL behavior verified.")

        foreign_key_health(conn)

        # 6) Delete project; if NO ACTION on purchases/expenses, clean manually.
        try:
            conn.execute("DELETE FROM projects WHERE id = ?;", (project_id,))
            ok("Deleted project.")
        except sqlite3.IntegrityError:
            conn.execute("DELETE FROM purchases WHERE project_id = ?;", (project_id,))
            conn.execute("DELETE FROM expenses  WHERE project_id = ?;", (project_id,))
            conn.execute("DELETE FROM projects  WHERE id = ?;", (project_id,))
            ok("Manual cleanup + project delete succeeded.")

        foreign_key_health(conn)

        conn.execute("ROLLBACK;")
        ok("All checks passed (DB rolled back, no changes persisted).")
        sys.exit(0)

    except SystemExit:
        raise
    except Exception as e:
        conn.execute("ROLLBACK;")
        fail(f"Exception during verification: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()

