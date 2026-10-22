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
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bibliotecario import api
from bibliotecario.core import storage
from bibliotecario.knowledge import graph as G
from bibliotecario.knowledge.study import normalize_pointers

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "results" / "result_blueprint_ab.json"
RUNS = 3
# P: Medida 1 (declarada 2026-10-21, ver evals/POSICIONAL_PLAN.md) — citas por
# índice `[N]` mapeadas por código. Se añade sin reabrir B/C/D/E: las runs
# buenas ya están en OUT y `seen` las salta.
ARMS = ("B", "C", "D", "E", "P")

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
    # B9 bajo la dec. 11: la cita literal pasa a ser el ANCLA de la atribución,
    # así que deja de medir copia y pasa a medir cumplimiento — «¿cada
    # atribución lleva su cita?». Se redefine aquí, con el original arriba a la
    # vista (§6 dec. 11): los valores históricos de comillados_literales se
    # leen bajo la definición antigua y así deben leerse.
    anclas = re.findall(r"[\"“«']([^\"”»']{10,})[\"”»']\s*\[doc:(\d+):(\d+)\]", blueprint)
    out["anclas"] = len(anclas)
    # B5/B6 — Integridad (§7, fila B). Los dos gratuitos: leer bloques.
    ok_b5, tot_b5, sin_b5, exentas = _b5_cita_por_modulo(blueprint)
    out["b5_con_cita"] = ok_b5
    out["b5_total"] = tot_b5
    out["b5_sin_cita"] = sin_b5
    out["b5_exentas"] = exentas
    out["b6_completo"], out["b6_motivo"] = _b6_completo(blueprint)
    out["anclas_en_fuente"] = sum(
        1 for q, d, c in anclas
        if re.sub(r"\s+", " ", q) in _chunk_text(int(d), int(c), corpus)
    )
    out["cumplimiento_b9"] = (len(anclas) / len(cites)) if cites else 0.0
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


def _b6_completo(blueprint: str) -> tuple[bool, str]:
    """B6 — ¿el documento termina en una estructura markdown completa?

    Falla si `max_tokens` no alcanzó y nadie se enteró: código sin cerrar,
    tabla que acaba en su fila separadora, o prosa cortada a media frase.
    Detectado originalmente en H1. Cuesta leer las últimas líneas.
    """
    t = blueprint.rstrip()
    if not t:
        return False, "vacio"
    # 1. cercas de codigo sin cerrar
    if t.count("```") % 2 != 0:
        return False, "cerca_de_codigo_sin_cerrar"
    lineas = [l for l in t.split("\n") if l.strip()]
    ult = lineas[-1]
    # 2. la ultima linea es una fila separadora de tabla: la tabla quedo sin filas
    if ult.lstrip().startswith("|") and set(ult.replace("|", "").replace(":", "")
                                            .replace("-", "").replace(" ", "")) == set():
        return False, "tabla_sin_filas"
    # 3. la ultima linea abre un bloque de codigo o un enlace incompleto
    if ult.rstrip().endswith(("`", "[", "![", "(")):
        return False, "bloque_incompleto"
    # 4. prosa cortada: la ultima linea no termina en cierre razonable
    if not re.search(r"[.!?\)\]}`*|>\d]$", ult.rstrip()):
        return False, "prosa_cortada"
    return True, ""


_CABECERA = re.compile(r"^#{2,3}\s", re.MULTILINE)
# cabecera que NOMBRA un módulo concreto («### Módulo 1: …»), singular.
_MODULO_CAB = re.compile(r"^#{2,3}\s*[^\n]*M[oó]dulo(?!s)\b[^\n]*$",
                         re.IGNORECASE | re.MULTILINE)
# sección-contenedor: «Módulos», «Módulos y Dependencias», «Dependencias».
_CONTENEDOR = re.compile(
    r"^#{2,3}\s*[^\n]*(?:M[oó]dulos\b|Dependencias?\b)", re.IGNORECASE | re.MULTILINE)
# item dentro de un contenedor: viñeta o numeración opcional seguida de negrita.
_ITEM = re.compile(r"^(?P<ind>[ \t]*)(?:(?:[-*]|\d+\.)\s+)?\*\*", re.MULTILINE)
_PUNTERO = re.compile(r"\[doc:\d+:\d+\]")
_PROPUESTA = re.compile(r"propuesta del blueprint", re.IGNORECASE)


def _bloques_modulos(texto: str) -> list[str]:
    """Devuelve, en orden, el texto de cada módulo/dependencia principal.

    **Errata séptima (2026-10-12).** B5 contó ya tres cosas distintas:

    1. cualquier `N. **…**` del documento (errata 6) — solo 34/87 medían
       módulos de verdad;
    2. tras corregirlo, solo viñetas dentro de sección-contenedor;
    3. **R8 hizo que el modelo reestructurara**: ahora los módulos son
       **cabeceras** (`### Módulo 1: …`), y 6 de 15 blueprints del brazo G
       salían con 0 items — **sin medir, no aprobados**.

    Hoy se aceptan las dos formas, que §3.1 cubre igual:

    - **cabecera que nombra un módulo** → su cuerpo hasta la siguiente cabecera;
    - **sección-contenedor** (`Módulos`, `Dependencias`) → cada item con
      viñeta o numeración **y negrita**, quedándose con la indentación mínima
      para no contar sub-componentes anidados.
    """
    bloques: list[tuple[int, str]] = []

    for m in _MODULO_CAB.finditer(texto):
        resto = texto[m.end():]
        nxt = _CABECERA.search(resto)
        cuerpo = resto[:nxt.start()] if nxt else resto
        if cuerpo.strip():
            bloques.append((m.start(), m.group(0).strip() + "\n" + cuerpo))

    for m in _CONTENEDOR.finditer(texto):
        # un contenedor que además nombra un módulo singular ya está cogido
        if _MODULO_CAB.match(m.group(0)):
            continue
        resto = texto[m.end():]
        nxt = _CABECERA.search(resto)
        seccion = resto[:nxt.start()] if nxt else resto
        brutas = list(_ITEM.finditer(seccion))
        if brutas:
            min_ind = min(len(x.group("ind").expandtabs(4)) for x in brutas)
            inicios = [x.start() for x in brutas
                       if len(x.group("ind").expandtabs(4)) == min_ind]
            for i, ini in enumerate(inicios):
                fin = inicios[i + 1] if i + 1 < len(inicios) else len(seccion)
                bloques.append((m.start() + ini, seccion[ini:fin]))
            continue
        # Sin viñetas en negrita. R8+R1 puede escribir cada módulo como bloque
        # de cita literal + paráfrasis separado por línea en blanco (medido en
        # G2: PEARL r1, cuatro bloques, los cuatro con puntero). Se toma cada
        # párrafo por bloque. **Caveat**: una línea introductoria del estilo
        # «Según X [doc:0:0]…» cuenta como una unidad más — solo aparece en
        # formatos sin viñetas, y esa propia línea casi siempre lleva puntero.
        trozos = re.split(r"\n\s*\n", seccion)
        pos = 0
        for trozo in trozos:
            inicio_rel = seccion.find(trozo, pos)
            if inicio_rel < 0 or not trozo.strip():
                continue
            pos = inicio_rel + len(trozo)
            bloques.append((m.start() + inicio_rel, trozo))

    bloques.sort(key=lambda x: x[0])
    return [b for _, b in bloques]


def _b5_cita_por_modulo(blueprint: str) -> tuple[int, int, list[int], int]:
    """B5 — ¿cada módulo/dependencia principal lleva su `[doc:chunk]`?

    Se normaliza ANTES de contar: al medir el brazo E se vio que 14 formatos
    distintos conviven y solo 422/900 son canónicos. Un módulo con
    `[doc:5:chunk 13]` SÍ lleva cita; no normalizarlo lo contaría como fallo y
    B5 diría mentira.

    Devuelve `(con_cita, total, lista_sin, exentas)`. `exentas` son los puntos
    marcados `(propuesta del blueprint)`: **no pueden llevar puntero de origen
    porque no tienen fuente**, así que se cuentan aparte (dec. 14). Se reportan
    las dos ratios para que se vea cuánto explica la exención.
    """
    texto, _ = normalize_pointers(blueprint)
    bloques = _bloques_modulos(texto)
    if not bloques:
        return 0, 0, [], 0

    tot = len(bloques)
    sin: list[int] = []
    exentas = 0
    for i, bloque in enumerate(bloques):
        if _PUNTERO.search(bloque):
            continue
        sin.append(i + 1)
        if _PROPUESTA.search(bloque):
            exentas += 1
    return tot - len(sin), tot, sin, exentas


def _chunk_text(doc_id: int, chunk_idx: int, corpus: dict[int, str] | None = None) -> str:
    """Texto del chunk (doc_id, chunk_idx). `corpus` se ignora: está indexado
    por id de chunk, no por el par, así que hay que ir a la BD."""
    with storage.get_conn() as conn:
        r = conn.execute(
            "SELECT text FROM chunks WHERE doc_id=? AND chunk_idx=?",
            (doc_id, chunk_idx),
        ).fetchone()
    return r["text"] if r else ""


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
    # Encabezado con numeración ("## 7. Bibliografía") cuenta igual que sin ella:
    # sin esto el medidor cobraba R7 a los brazos que numeran secciones (bug
    # detectado 2026-10-21 al cerrar POSICIONAL_PLAN.md §5; se corrigió la
    # regex y se repuntuaron todas las filas con --repuntua, umbral intacto).
    _h = r"(?im)^#{1,3}\s*(?:\d+\s*[.)]\s+)?bibliograf"
    has_section = 1 if re.search(_h, blueprint) else 0
    # Solo lo que hay DESPUÉS del encabezado cuenta como entrada de bibliografía.
    tail = blueprint
    m = re.search(_h + r"\w*\s*$", blueprint)
    if m:
        tail = blueprint[m.end():]
    cited_ids = {int(d) for d in re.findall(r"\[doc:(\d+)\]", tail)}
    named = sum(1 for t in titles if t and t[:40] in tail.lower())
    return {"seccion": has_section, "entradas": len(cited_ids),
            "resueltas": len(cited_ids & ids), "por_titulo": named}


def _techniques() -> list[str]:
    return sorted(n.label for n in G.find_nodes("", kind="technique", limit=50))


def _firma_modelo() -> dict:
    """Modelo/proveedor de esta run — las filas viejas no lo traen y comparar
    brazos corridos con modelos distintos sin saberlo costó un falso R7."""
    from bibliotecario.core import llm
    return {"models": llm._models("nvidia"),
            "prov": os.environ.get("LLM_PROVIDERS", "round-robin")}


def run_one(arm: str, technique: str, run: int) -> dict:
    goal = "validar mi agente antes de cada release"
    t0 = time.time()
    try:
        if arm == "B":
            r = api.blueprint(technique, goal)
        elif arm == "D":
            r = api.blueprint_verified(technique, goal)
        elif arm == "E":
            r = api.blueprint_p4(technique, goal)
        elif arm == "P":
            r = api.blueprint_positional(technique, goal)
        else:
            r = api.blueprint_loop(technique, goal)
        bp = r.get("blueprint", "")
        return {"arm": arm, "technique": technique, "run": run, "ok": True,
                "secs": round(time.time() - t0, 1),
                "modelo": _firma_modelo(),
                "loop_turns": r.get("loop_turns"),
                "procedures": r.get("procedures", []),
                "verificado": r.get("verificado"),
                "sin_punteros": r.get("sin_punteros"),
                "reescrituras": r.get("reescrituras"),
                "violaciones": r.get("violaciones"),
                "citas_posicionales": r.get("citas_posicionales"),
                "blueprint": bp, "checks": score(bp, _corpus()),
                "error": None}
    except Exception as e:  # una run rota no debe tumbar el batch
        return {"arm": arm, "technique": technique, "run": run, "ok": False,
                "secs": round(time.time() - t0, 1), "blueprint": "",
                "modelo": _firma_modelo(),
                "checks": {}, "error": str(e)[:300]}


def _repuntua() -> int:
    """Reaplica `score()` a las filas guardadas (sin llamadas LLM).

    Para corregir el instrumento sin redefinir umbrales: el blueprint ya está
    en OUT, así que arreglar una regex del medidor se reaplica a los cinco
    brazos por igual y el único coste es CPU.
    """
    done = json.loads(OUT.read_text(encoding="utf-8"))
    corpus = _corpus()
    n = 0
    for r in done:
        if r.get("ok") and r.get("blueprint"):
            r["checks"] = score(r["blueprint"], corpus)
            n += 1
    OUT.write_text(json.dumps(done, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"repuntuadas {n}/{len(done)} filas con el instrumento corregido")
    _summary(done, False)
    return 0


def main() -> int:
    if "--repuntua" in sys.argv:
        return _repuntua()
    smoke = "--smoke" in sys.argv
    techs = _techniques()
    runs = 1 if smoke else RUNS
    # El humo prueba el brazo nuevo (P); B..E ya están en OUT, `seen` los salta.
    arms = ("P",) if smoke else ARMS
    # `--solo=C`: un solo brazo (re-baseline: re-correr C con el modelo actual
    # para que P vs C no mezcle formato Y modelo).
    for a in sys.argv:
        if a.startswith("--solo="):
            arms = tuple(x for x in ARMS if x == a.split("=", 1)[1].upper())

    done = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    seen = {(d["arm"], d["technique"], d["run"]) for d in done if d.get("ok")}

    # `--previas`: solo las técnicas ya medidas en B..E (5 del A/B previo).
    # Comparar P sobre las 14 con C sobre las 5 mezclaría poblaciones; el
    # criterio de POSICIONAL_PLAN.md se lee sobre la intersección.
    if "--previas" in sys.argv:
        previas = {d["technique"] for d in done if d.get("ok") and d["arm"] != "P"}
        techs = [t for t in techs if t in previas]

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
        print(f"    B9 comillados literales            {lit:6.2f}/run  (def. antigua)")
        anclas = sum(r["checks"].get("anclas", 0) for r in rows) / n
        en_fte = sum(r["checks"].get("anclas_en_fuente", 0) for r in rows) / n
        cumple = sum(r["checks"].get("cumplimiento_b9", 0.0) for r in rows) / n
        print(f"    B9' anclas literales (dec. 11)     {anclas:6.2f}/run")
        print(f"    B9' de esas, estan en la fuente    {en_fte:6.2f}/run")
        print(f"    B9' cumplimiento (anclas/citas)    {cumple:6.2f}     [umbral >= 1,00]")
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
        if arm == "P":
            cpos = [r["citas_posicionales"] for r in rows if r.get("citas_posicionales")]
            if cpos:
                mapeados = sum(c["mapeados"] for c in cpos) / len(cpos)
                fuera = sum(c["fuera_de_rango"] for c in cpos) / len(cpos)
                print(f"    R1' [N]→[doc:id:chunk] mapeados    {mapeados:6.2f}/run")
                print(f"    R1' indice fuera de rango          {fuera:6.2f}/run"
                      f"   [criterio: 0,00]")
                if len(cpos) != n:
                    print(f"    (solo {len(cpos)}/{n} runs devolvieron mapa)")
    if smoke:
        print("\nMODO HUMO: una sola run por brazo, no sirve para comparar.")


if __name__ == "__main__":
    raise SystemExit(main())
