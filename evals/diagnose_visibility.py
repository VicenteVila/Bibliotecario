"""Diagnostico: cuanta evidencia ve realmente el agente por pregunta.

El loop hace result_s = json.dumps(result)[:3000] y luego guarda solo
result_s[:220] en history y en evidence, que es lo que se le pasa al modelo. Con
search_papers el volcado JSON empieza por score/doc_id/chunk y el title (que
solo para WikiSkill ocupa 90 caracteres), asi que de los 220 apenas quedan unos
35 de texto de chunk, de ~1300. El agente ve ~2.7% de lo que recupera.

Este script cuantifica el margen para las 35 respondibles, sin gastar un solo
token: solo retrieval (embeddings locales).

Tres categorias, y son mutuamente excluyentes:
  invisible   el keyword no esta ni en el volcado de 3000 chars -> fallo de retrieval
  truncado    esta en los 3000 pero no en la ventana de 220     -> fallo de tuberia
  visible     esta en la ventana                                 -> fallo de extraccion

Uso: python evals/diagnose_visibility.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

EVALS = Path(__file__).parent
sys.path.insert(0, str(EVALS.parent))

from bibliotecario.agent.loop import TOOLS

GOLDEN = EVALS / "golden_blind_qa.jsonl"


def windows(question: str, top_k: int = 8) -> tuple[str, str]:
    """Reproduce exactamente lo que el loop construye: volcado y corte."""
    try:
        res = TOOLS["search_papers"]["fn"](query=question, top_k=top_k)
    except Exception:
        return "", ""
    dumped = json.dumps(res, ensure_ascii=False, default=str)[:3000]
    return dumped, dumped[:220]


def main() -> dict:
    rows = [json.loads(l) for l in GOLDEN.read_text().splitlines() if l.strip()]
    ans = [r for r in rows if not r.get("unanswerable")]
    # Nota media por pregunta en las 3 runs, para correlacionar.
    scores: dict[str, list] = {}
    for r in (1, 2, 3):
        f = EVALS / f"result_blind_r{r}.json"
        if not f.exists():
            continue
        for row in json.loads(f.read_text())["rows"]:
            if row["judge"] is not None:
                scores.setdefault(row["id"], []).append(row["judge"])

    out = []
    for q in ans:
        dumped, win = windows(q["question"])
        kws = q.get("keywords") or []
        cat = {"invisible": [], "truncado": [], "visible": []}
        for k in kws:
            if k in win:
                cat["visible"].append(k)
            elif k in dumped:
                cat["truncado"].append(k)
            else:
                cat["invisible"].append(k)
        n = max(1, len(kws))
        out.append({
            "id": q["id"], "doc_id": q["doc_id"], "difficulty": q["difficulty"],
            "judge_mean": round(st.mean(scores[q["id"]]), 2) if q["id"] in scores else None,
            "n_keywords": len(kws),
            "frac_visible": round(len(cat["visible"]) / n, 2),
            "frac_truncado": round(len(cat["truncado"]) / n, 2),
            "frac_invisible": round(len(cat["invisible"]) / n, 2),
            "categoria": ("invisible" if cat["invisible"] and not cat["visible"]
                          else "truncado" if cat["truncado"] and not cat["visible"]
                          else "visible"),
            "detalle": {k: v for k, v in cat.items() if v},
        })

    by_cat: dict[str, list] = {}
    for o in out:
        by_cat.setdefault(o["categoria"], []).append(o)

    print(f"{len(out)} respondibles. Ventana real del agente: 220 chars del volcado JSON.\n")
    print(f"{'categoria':11} {'n':>3} {'judge medio':>12}")
    for cat in ("visible", "truncado", "invisible"):
        g = by_cat.get(cat, [])
        if not g:
            continue
        js = [x["judge_mean"] for x in g if x["judge_mean"] is not None]
        print(f"{cat:11} {len(g):3} {st.mean(js):12.2f}" if js else f"{cat:11} {len(g):3} {'-':>12}")
    print()
    print(f"fracción de keywords visible, media: {st.mean([o['frac_visible'] for o in out]):.3f}")
    print(f"fracción truncada (recuperada pero no vista): "
          f"{st.mean([o['frac_truncado'] for o in out]):.3f}")
    print(f"fracción invisible (ni siquiera recuperada): "
          f"{st.mean([o['frac_invisible'] for o in out]):.3f}")
    print()
    print("Correlación entre lo que se ve y la nota (Pearson sobre frac_visible):")
    xs = [o["frac_visible"] for o in out if o["judge_mean"] is not None]
    ys = [o["judge_mean"] for o in out if o["judge_mean"] is not None]
    if len(xs) > 2:
        mx, my = st.mean(xs), st.mean(ys)
        cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        sx = sum((x - mx) ** 2 for x in xs) ** 0.5
        sy = sum((y - my) ** 2 for y in ys) ** 0.5
        print(f"  r = {cov / (sx * sy):.3f}")
    print()
    print("Las 8 con menos evidencia visible:")
    for o in sorted(out, key=lambda x: x["frac_visible"])[:8]:
        print(f"  {o['id']:10} visible={o['frac_visible']:.2f} truncado={o['frac_truncado']:.2f} "
              f"invisible={o['frac_invisible']:.2f} judge={o['judge_mean']}")

    (EVALS / "result_visibility.json").write_text(
        json.dumps({"aggregate": {"n": len(out),
                                  "frac_visible_media": round(st.mean([o["frac_visible"] for o in out]), 3),
                                  "frac_truncado_media": round(st.mean([o["frac_truncado"] for o in out]), 3),
                                  "frac_invisible_media": round(st.mean([o["frac_invisible"] for o in out]), 3),
                                  "por_categoria": {c: len(v) for c, v in by_cat.items()}},
                    "rows": out}, indent=1, ensure_ascii=False))
    print(f"\n-> {EVALS / 'result_visibility.json'}")
    return out


if __name__ == "__main__":
    main()