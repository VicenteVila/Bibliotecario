"""Pool de tareas de validación con historial de outcomes (base de Task-CoEvolve).

Cada tarea guarda (p̄_t, n_t): media histórica y nº de observaciones.
"""
from __future__ import annotations

from bibliotecario.core import storage


def add_task(task_text: str, kind: str, expected_answer: str = "", metadata: str = "") -> int:
    assert kind in ("qa", "retrieval_judge", "blueprint_check"), kind
    with storage.get_conn() as conn:
        cur = conn.execute("INSERT INTO validation_tasks (task_text, kind, expected_answer, metadata) "
                           "VALUES (?,?,?,?)", (task_text, kind, expected_answer, metadata))
        return cur.lastrowid


def record_outcome(task_id: int, success: bool, harness_run_id: str = "") -> None:
    with storage.get_conn() as conn:
        conn.execute("INSERT INTO task_outcomes (task_id, harness_run_id, success) VALUES (?,?,?)",
                     (task_id, harness_run_id, 1 if success else 0))


def task_stats() -> list[dict]:
    """Una fila por tarea: (id, p̄, n)."""
    with storage.get_conn() as conn:
        rows = conn.execute(
            "SELECT t.id, COALESCE(AVG(o.success), 0.5) AS pbar, COUNT(o.id) AS n "
            "FROM validation_tasks t LEFT JOIN task_outcomes o ON o.task_id=t.id "
            "GROUP BY t.id ORDER BY t.id").fetchall()
    return [{"id": r["id"], "pbar": float(r["pbar"]), "n": int(r["n"])} for r in rows]


def count() -> int:
    with storage.get_conn() as conn:
        return conn.execute("SELECT COUNT(*) c FROM validation_tasks").fetchone()["c"]
