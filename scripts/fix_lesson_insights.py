#!/usr/bin/env python3
"""Limpia `key_insights` de las lecciones escritas con la pregunta dentro.

Medido antes de tocar nada: 275 de 275 lecciones tenían `key_insights` empezando
por `Q: `, es decir la columna no contenía ningún insight, contenía la pregunta.
load_lessons() inyecta las 5 últimas en el prompt, así que en producción cada
pregunta se respondía con las 5 anteriores del golden a la vista.

`loop.py` ya no escribe así (ver _trajectory_fingerprint), pero la limpieza es
necesaria porque load_lessons sigue leyendo el histórico: sin esto, los prompts
siguen contaminándose hasta que se escriban 5 lecciones nuevas.

No borra filas: what_worked conserva los patrones de herramientas, que sí son
útiles. Solo vacía la columna que nunca tuvo contenido real.

Uso:
    python scripts/fix_lesson_insights.py            # dry-run (por defecto)
    python scripts/fix_lesson_insights.py --apply
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bibliotecario.core import storage

MATCH = "Q: %"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true",
                    help="escribe los cambios. Sin esto solo se informa.")
    args = ap.parse_args()

    with storage.get_conn() as conn:
        rows = conn.execute(
            "SELECT id, scope, substr(key_insights, 1, 60) AS preview "
            "FROM lessons WHERE key_insights LIKE ?", (MATCH,)).fetchall()
        n = len(rows)
        if not n:
            print("0 lecciones con 'Q: '. Nada que hacer (ya se aplicó).")
            return 0

        print(f"{n} lecciones con la pregunta en key_insights:")
        for r in rows[:5]:
            print(f"  #{r['id']} [{r['scope']}] {r['preview']!r}")
        if n > 5:
            print(f"  ... y {n - 5} más")

        if not args.apply:
            print("\nDry-run: nada escrito. Repite con --apply.")
            return 0

        conn.execute("UPDATE lessons SET key_insights='' WHERE key_insights LIKE ?",
                     (MATCH,))
        print(f"\nEscrito. {n} lecciones actualizadas.")

    # Verificación post-condición: no debe quedar ninguna.
    with storage.get_conn() as conn:
        left = conn.execute("SELECT COUNT(*) c FROM lessons WHERE key_insights LIKE ?",
                            (MATCH,)).fetchone()["c"]
    print(f"Verificación: quedan {left} con el prefijo (esperado 0).")
    return 0 if left == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
