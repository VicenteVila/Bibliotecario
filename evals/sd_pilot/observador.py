"""Observador HITO20 §0.3: informe por celda/turno desde traces_*.sqlite.

Herramienta reproducible de canal de observación (0 tokens LLM): lee los
spans que dejó TraceForge (llm/turn/tool por celda) y emite un informe
markdown por celda. El informe es la prueba de legibilidad del criterio
E1.4 — no sustituye la evidencia de scores, la complementa.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def cargar_spans(db: Path) -> list[dict]:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT agent, metadata, input, output, tokens_input, tokens_output "
            "FROM spans ORDER BY rowid").fetchall()
    finally:
        conn.close()
    out = []
    for agent, meta, inp, outp, ti, to in rows:
        try:
            metadata = json.loads(meta) if meta else {}
        except (TypeError, ValueError):
            metadata = {}
        out.append({"agent": agent, "metadata": metadata,
                    "input": inp or "", "output": outp or "",
                    "tokens_input": int(ti or 0), "tokens_output": int(to or 0)})
    return out


def agrupar_por_celda(spans: list[dict]) -> dict[str, list[dict]]:
    """Los spans de una celda comparten metadata context (variant/task)."""
    celdas: dict[str, list[dict]] = {}
    for s in spans:
        meta = s["metadata"]
        v, t = meta.get("variant"), meta.get("task")
        key = f"{v}_{t}" if v and t else "sin_contexto"
        celdas.setdefault(key, []).append(s)
    return celdas


def informe_celda(key: str, spans: list[dict]) -> str:
    """Informe markdown de una celda: turno a turno, legible."""
    lineas = [f"# Informe de celda {key}", ""]
    for s in spans:
        if s["agent"] == "llm":
            turn = s["metadata"].get("turn", "?")
            lineas.append(f"## LLM turno {turn}")
            lineas.append(f"- input_tokens={s['tokens_input']} "
                          f"output_tokens={s['tokens_output']}")
            if s["output"]:
                lineas.append(f"- respuesta: {s['output'][:400]}")
        elif s["agent"] == "tool":
            tool = s["metadata"].get("tool_name", "?")
            lineas.append(f"- tool `{tool}` args={s['input'][:200]} "
                          f"-> {s['output'][:200]}")
        elif s["agent"] == "turn":
            lineas.append(f"--- turno {s['metadata'].get('turn', '?')} ---")
    return "\n".join(lineas) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Informes por celda desde trazas")
    ap.add_argument("db", type=Path, help="traces_*.sqlite")
    ap.add_argument("--out-dir", type=Path,
                    default=REPO / "evals" / "results" / "informes_diagb",
                    help="directorio de salida (un .md por celda)")
    args = ap.parse_args(argv)

    if not args.db.is_file():
        print(f"ERROR: no existe {args.db}", file=sys.stderr)
        return 3
    spans = cargar_spans(args.db)
    celdas = agrupar_por_celda(spans)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for key, cs in sorted(celdas.items()):
        out = args.out_dir / f"{key}.md"
        out.write_text(informe_celda(key, cs), encoding="utf-8")
        print(f"informe: {out.relative_to(REPO)} ({len(cs)} spans)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
