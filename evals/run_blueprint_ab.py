"""A/B de P1 (§5.7): ¿el loop dirige mejor que un solo `generate()`?

Tres brazos, definidos **antes** de la primera run:
- **A** — baseline ya medido en el Hito 1 (H3: 0 citas). No se vuelve a correr.
- **B** — P2 solo: un `generate()` con R1-R7 y la fuente al lado (`api.blueprint`).
- **C** — P1'+P2: el loop reúne evidencia y la tool escribe (`api.blueprint_loop`).

B vs A aísla el prompt. C vs B aísla el loop. **Si C no gana a B en las
comprobaciones mecánicas, P1 se descarta** (§5.7).

Corre a temperature=0.0, la misma del Hito 1, para que la varianza que quede
sea del modelo y no de la temperatura. Cada run se guarda entera: si una
falla a medias se puede reanudar sin repetir las buenas.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bibliotecario import api
from bibliotecario.core import storage
from bibliotecario.knowledge import graph as G

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "result_blueprint_ab.json"
RUNS = 3
ARMS = ("B", "C", "D")

# Mínimo de palabras para que una frase copiada cuente como copia (B11).
_MIN_PHRASE = 8


def _flat(text: str) -> list[str]:
    return re.findall(r"[a-záéíóúñöü]{2,}", text.lower())


def _corpus() -> dict[int, str]:
    with storage.get_conn() as conn:
        return {r["id"]: r["text"] for r in conn.execute("SELECT id, text FROM chunks")}


def score(blueprint: str, corpus: dict[int, str]) -> dict:
    """Comprobaciones mecánicas de §3.1 aplicables sin juez.

    Todas son de la forma «esto tiene que ser verdad literalmente», así que no
    dependen del modelo. Las que sí necesitan juicio (Q1-Q4) van aparte.
    """
    out: dict = {}
    # B7/B8: citas que resuelven a un chunk real.
    cites = [(int(d), int(c)) for d, c in re.findall(r"\[doc:(\d+):(\d+)\]", blueprint)]
    out["citas"] = len(cites)
    out["citas_resueltas"] = sum(1 for d, c in cites if _chunk_exists(d, c))
    # B9: lo entrecomillado aparece idéntico en el corpus.
    quoted = re.findall(r"[\"“«']([^\"”»']{15,})[\"”»']", blueprint)
    joined = " ".join(re.sub(r"\s+", " ", t) for t in corpus.values())
    out["comillados"] = len(quoted)
    out["comillados_literales"] = sum(1 for q in quoted if re.sub(r"\s+", " ", q) in joined)
    # B11: frase larga copiada sin comillas = plagio medido.
    out["frases_largas_copiadas"] = _copied_phrases(blueprint, corpus)
    # R1 y R5: se cumplen en prosa, no con puntero. Se comprueban a mano antes;
    # aquí solo se cuenta si aparecen.
    out["atribucion"] = 1 if re.search(r"(?i)seg[uú]n", blueprint) else 0
    out["declara_silencios"] = 1 if re.search(
        r"(?i)no (especifica|describe|indica|menciona|detalla|proporciona)", blueprint) else 0
    # R7 y B10: la bibliografía, que es lo que 1500 tokens se comía.
    out["biblio"] = _biblio_check(blueprint)
    return out


def _chunk_exists(doc_id: int, chunk_idx: int) -> bool:
    with storage.get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM chunks WHERE doc_id=? AND chunk_idx=?", (doc_id, chunk_idx)
        ).fetchone() is not None


def _copied_phrases(blueprint: str, corpus: dict[int, str]) -> int:
    """Frases de >=8 palabras del blueprint que están en el corpus sin comillas.

    Se salta lo entrecomillado, que es citar correctamente. Se recorre la frase
    con salto: una vez detectada una copia, la siguiente ventana empieza después,
    o la misma frase contaría varias veces por solaparse consigo misma.
    """
    text_flat = " ".join(re.sub(r"\s+", " ", t) for t in corpus.values())
    body = re.sub(r"[\"“«].*?[\"”»]", " ", blueprint)
    words = _flat(body)
    hits, i = 0, 0
    while i <= len(words) - _MIN_PHRASE:
        win = " ".join(words[i:i + _MIN_PHRASE])
        if win in text_flat:
            hits += 1
            i += _MIN_PHRASE
        else:
            i += 1
    return hits


def _biblio_check(blueprint: str) -> dict:
    """R7 y B10: ¿hay sección Bibliografía y sus entradas son documentos reales?"""
    with storage.get_conn() as conn:
        ids = {r["id"] for r in conn.execute("SELECT id FROM documents")}
        titles = {r["title"].lower().rstrip(".") for r in conn.execute("SELECT title FROM documents")}
    has_section = 1 if re.search(r"(?im)^#{1,3}\s*bibliograf", blueprint) else 0
    # Solo lo que hay DESPUÉS del encabezado cuenta como entrada de bibliografía.
    tail = blueprint
    m = re.search(r"(?im)^#{1,3}\s*bibliograf\w*\s*$", blueprint)
    if m:
        tail = blueprint[m.end():]
    cited_ids = {int(d) for d in re.findall(r"\[doc:(\d+)\]", tail)}
    named = sum(1 for t in titles if t and t[:40] in tail.lower())
    return {"seccion": has_section, "entradas": len(cited_ids),
            "resueltas": len(cited_ids & ids), "por_titulo": named}


def _techniques() -> list[str]:
    return sorted(n.label for n in G.find_nodes("", kind="technique", limit=50))


def run_one(arm: str, technique: str, run: int) -> dict:
    goal = "validar mi agente antes de cada release"
    t0 = time.time()
    try:
        if arm == "B":
            r = api.blueprint(technique, goal)
        elif arm == "D":
            r = api.blueprint_verified(technique, goal)
        else:
            r = api.blueprint_loop(technique, goal)
        bp = r.get("blueprint", "")
        return {"arm": arm, "technique": technique, "run": run, "ok": True,
                "secs": round(time.time() - t0, 1),
                "loop_turns": r.get("loop_turns"),
                "procedures": r.get("procedures", []),
                "verificado": r.get("verificado"),
                "sin_punteros": r.get("sin_punteros"),
                "reescrituras": r.get("reescrituras"),
                "violaciones": r.get("violaciones"),
                "blueprint": bp, "checks": score(bp, _corpus()),
                "error": None}
    except Exception as e:  # una run rota no debe tumbar el batch
        return {"arm": arm, "technique": technique, "run": run, "ok": False,
                "secs": round(time.time() - t0, 1), "blueprint": "",
                "checks": {}, "error": str(e)[:300]}


def main() -> int:
    smoke = "--smoke" in sys.argv
    techs = _techniques()
    runs = 1 if smoke else RUNS
    arms = ("B",) if smoke else ARMS

    done = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    seen = {(d["arm"], d["technique"], d["run"]) for d in done if d.get("ok")}

    print("=" * 70)
    print(f"A/B de P1  ·  brazos {list(arms)}  ·  {len(techs)} técnicas  ·  {runs} runs")
    print(f"ya hechas: {len(seen)}   (se reanuda, no se repite)")
    print("=" * 70)

    for arm in arms:
        for tech in techs:
            for run in range(runs):
                if (arm, tech, run) in seen:
                    continue
                print(f"  [{arm}] {tech} run {run} ...", end=" ", flush=True)
                rec = run_one(arm, tech, run)
                done.append(rec)
                OUT.write_text(json.dumps(done, ensure_ascii=False, indent=2), encoding="utf-8")
                if rec["ok"]:
                    c = rec["checks"]
                    print(f"ok {rec['secs']}s  citas={c.get('citas')} "
                          f"resueltas={c.get('citas_resueltas')} "
                          f"comillados={c.get('comillados_literales')}/{c.get('comillados')} "
                          f"copiadas={c.get('frases_largas_copiadas')}")
                else:
                    print(f"FALLO {rec['error']}")
                time.sleep(1)

    _summary(done, smoke)
    return 0


def _summary(done: list[dict], smoke: bool) -> None:
    print("\n" + "=" * 70)
    print("Resumen por brazo")
    print("=" * 70)
    for arm in sorted({d["arm"] for d in done}):
        rows = [d for d in done if d["arm"] == arm and d.get("ok")]
        if not rows:
            continue
        n = len(rows)
        cites = sum(r["checks"].get("citas", 0) for r in rows) / n
        resolved = sum(r["checks"].get("citas_resueltas", 0) for r in rows) / n
        lit = sum(r["checks"].get("comillados_literales", 0) for r in rows) / n
        copied = sum(r["checks"].get("frases_largas_copiadas", 0) for r in rows) / n
        attr = sum(r["checks"].get("atribucion", 0) for r in rows)
        sil = sum(r["checks"].get("declara_silencios", 0) for r in rows)
        with_bib = sum(1 for r in rows if r["checks"].get("biblio", {}).get("seccion", 0))
        trunc = sum(1 for r in rows if len(r.get("blueprint", "")) < 600)
        print(f"  Brazo {arm}  n={n}")
        print(f"    R1 cita con puntero [doc:id:chunk]  {cites:6.2f}/run")
        print(f"    B8 de esas, resuelven a un chunk   {resolved:6.2f}/run")
        print(f"    R1 atribuye en prosa («Según»)    {attr:6d}/{n}")
        print(f"    R5 declara silencios               {sil:6d}/{n}")
        print(f"    R7 seccion Bibliografia            {with_bib:6d}/{n}")
        print(f"    B9 comillados literales            {lit:6.2f}/run")
        print(f"    B11 frases copiadas                {copied:6.2f}/run  (menor = mejor)")
        print(f"    truncados (<600 chars)             {trunc:6d}/{n}")
        if arm == "D":
            ver = [r for r in rows if r.get("verificado") is True]
            sinp = [r for r in rows if r.get("sin_punteros")]
            reesc = [r for r in rows if r.get("reescrituras")]
            print(f"    P3 con punteros verificados        {len(ver):6d}/{n}")
            print(f"    P3 sin punteros (nada que verificar) {len(sinp):6d}/{n}")
            if reesc:
                print(f"    P3 que pagaron reescritura         {len(reesc):6d}/{n}"
                      f"   ({sum(r['reescrituras'] for r in reesc)} llamadas extra)")
    if smoke:
        print("\nMODO HUMO: una sola run por brazo, no sirve para comparar.")


if __name__ == "__main__":
    raise SystemExit(main())
