"""Fase 0 — calibrar el juez de R4 contra el set dorado verificado.

Por qué este script existe y no basta con llamar a `eval_q1_r4r5.py`:

Al cruzar las 40 acusaciones del brazo C contra los chunks reales, **el juez se
equivocaba sobre si algo estaba en la fuente**. Tres casos comprobados:

    λ_t = 0.125  -> acusado, esta en doc3 chunk43 (y la formula en chunk13)
    Rbest        -> acusado, 3 hits en doc5
    lessons.md   -> acusado, 7 hits en doc4

No alucinaba texto de blueprint —eso lo verificamos—, pero afirmaba
«no está en la fuente» sin comprobarlo. Sobre ese error no se puede medir R4.

Por eso el pipeline nuevo es **mecanico primero, juez despues**:

  1. Términos distintivos del claim, busqueda literal en los chunks.
     Si estan -> PASS. El juez ni se le pregunta.
  2. Solo lo que NO esta en la fuente pasa al juez, y este decide una cosa
     distinta y mucho mas acotada: ¿lo presenta como de la fuente o lo etiqueta
     como propuesta junto a la afirmacion?

Eso es la R4 nueva de la opcion C: puente permitido, etiqueta obligatoria.
El umbral del set es PASS=10, FAIL=4.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bibliotecario.core import storage
from bibliotecario.core.llm import _endpoint, _openai_compat_usage

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "evals" / "calib_r4_gold.json"
OUT = ROOT / "evals" / "results" / "result_calib_r4.json"

JUDGE_MODEL = "openai/gpt-oss-20b"
JUDGE_PROVIDER = "nvidia"

# Palabras que no distinguen: aparecen en cualquier acusacion y no aportan.
_STOP = {"el", "la", "los", "las", "un", "una", "de", "del", "al", "que", "se", "para", "por", "con", "como", "sobre", "donde", "entre", "desde", "hasta", "sino", "todo", "toda", "todos", "todas", "este", "esta", "estos", "estas", "ese", "esa", "eso", "afirma", "indica", "menciona", "asigna", "incluye", "especifica", "describe", "propone", "contiene", "usa", "blueprint", "paper", "fuente", "source", "figura", "aparece", "mencionado", "especificado", "detallado", "mismo", "misma", "tambien", "mas", "menos", "cada", "cual", "cuando", "porque"}


def distinctive_terms(claim: str) -> list[str]:
    """Términos que tendrían que estar en la fuente si el claim es honesto.

    Se guardan números y ficheros tal cual — la primera versión de este filtro
    los perdía al tokenizar (`0.125` se convertía en `0 125` y no llegaba a
    medirse), que era justo el agujero que la ruta 4 tenía que tapar.
    """
    claim = re.sub(r"[\[\]()»“”\"<>¿?¡!;,]", " ", claim)
    terms: list[str] = []
    for m in re.finditer(r"\d+\.?\d*%?|[A-Za-z_][\w.]*\.[A-Za-z]{2,}|\w{5,}", claim):
        t = m.group(0)
        if t.lower() in _STOP or t.lower().startswith(("elblue", "bluepr")):
            continue
        if t not in terms:
            terms.append(t)
    return terms[:12]


def _phrases(claim: str) -> list[str]:
    """Unidades compactas: identificadores, números, ficheros y secuencias de
    3+ palabras significativas contiguas.

    La primera version de este filtro comparaba palabras SUELTAS y aprobaba
    «Módulo de Detección de Rutas Implícitas en el Procedural Graph» porque
    «Procedural Graph» esta en la fuente. Eso no valida el módulo inventado que
    lo describe — medido: 2 de 14 del set dorado salian PASS por esto.
    """
    claim = re.sub(r"[\[\]()»“”\"<>¿?¡!;,]", " ", claim)
    units: list[str] = []
    # identificadores y ficheros, tal cual
    for m in re.finditer(r"\d+\.?\d*%?|[\w-]*\.[A-Za-z]{2,}|[A-Za-z]+[-_][\w-]+", claim):
        t = m.group(0)
        if len(t) >= 3 and t not in units:
            units.append(t)
    # palabras sueltas significativas: solo sirven si el claim ES el termino
    # (se decide en in_source, no aqui)
    for w in claim.split():
        if len(w) >= 4 and w.lower() not in _STOP and w not in units:
            units.append(w)
    # ventanas contiguas de palabras significativas
    words = [w for w in claim.split() if len(w) >= 4 and w.lower() not in _STOP]
    for n in (4, 3):
        for i in range(len(words) - n + 1):
            ph = " ".join(words[i:i + n])
            if ph not in units:
                units.append(ph)
    return units[:30]


def in_source(claim: str, doc_id: int) -> tuple[bool, list[str]]:
    """Búsqueda literal en los chunks del documento. Determinista, gratis.

    PASS solo ante coincidencia TIGHT: un identificador/numero/fichero
    concreto, o una secuencia de 3+ palabras contiguas. Cualquier otra cosa
    pasa al juez — aqui el fallo barato es dar por presente lo presente.
    """
    units = _phrases(claim)
    if not units:
        return False, []
    with storage.get_conn() as conn:
        rows = conn.execute("SELECT text FROM chunks WHERE doc_id=?", (doc_id,)).fetchall()
    if not rows:
        return False, units
    hay = " \n ".join(r["text"] for r in rows).lower()
    found = [u for u in units if u.lower() in hay]
    if not found:
        return False, []
    # Un numero o fichero concreto basta por si solo: son los que el juez
    # se inventaba como ausentes (0.125, lessons.md, Rbest).
    concreto = [u for u in found if re.search(r"\d|\.md|\.yaml|\.txt", u)]
    # Con palabras, hace falta una ventana larga: 3 palabras sueltas no bastan.
    largo = [u for u in found if u.count(" ") >= 2]
    # Si el claim ES un termino corto («Rbest», «self-evolving») y esta, basta.
    termino = len(claim.strip()) <= 22
    return bool(concreto or largo or termino), found


# Marcadores de que algo es propuesta, y no atribucion a la fuente.
_MARCA_PROPUESTA = re.compile(
    r"(?i)propuesta del blueprint|propuesta del sistema|no especifica|no menciona|"
    r"no describe|no esta descrito|no esta en la fuente|se propone|no aparece en")
# Marcadores de lo contrario: que se le atribuye a la fuente.
_MARCA_ATRIB = re.compile(r"(?i)seg[uú]n |el (paper|art[ií]culo) (dice|menciona|describe)")


def marcado_como_propuesta(contexto: str) -> bool:
    """¿La etiqueta esta JUNTO A la afirmacion?

    Se comprueba sintacticamente y no con el juez porque la regla es sintactica
    —«misma linea o la siguiente»—. Con el juez salia inestable: en dos pasadas
    seguidas sobre el mismo set falto uno diferente cada vez, y los dos eran
    exactamente los items de esta categoria. Un umbral que parpadea no sirve
    para medir.
    """
    if not contexto:
        return False
    if _MARCA_PROPUESTA.search(contexto):
        return True
    lineas = contexto.split("\n")
    for i, l in enumerate(lineas):
        if i + 1 < len(lineas) and _MARCA_PROPUESTA.search(lineas[i + 1]):
            return True
        # La marca en la misma frase, salvo que la frase la este atribuyendo:
        # «Según el paper...» no es una declaracion de propuesta.
        if _MARCA_PROPUESTA.search(l) and not _MARCA_ATRIB.search(l):
            return True
    return False


JUDGE_PROMPT = """Eres un revisor de rigor de citacion. Aplica SOLO esta regla:

R4 nueva — No presentar como de la fuente algo que no esta en la fuente.
  Puentear hacia un objetivo que la fuente no trata **esta permitido**, si la
  frase lleva la marca de que es propuesta JUNTO A la afirmacion (misma linea,
  o la linea inmediatamente siguiente del mismo punto). Una etiqueta en otra
  seccion del documento NO cuenta: no se puede saber a que afirmacion se refiere.

Te paso FUENTE (texto real del documento) y CONTEXTO (donde aparece el claim).
La pregunta «esta en la fuente» se resuelve BUSCANDO en FUENTE, no deduciendo.

IMPORTANTE: el blueprint esta en espanol y la fuente en ingles. Al comparar,
traduce mentalmente — «localiza el nodo activo» = "localizes the active node".
Que la frase exacta no aparezca NO significa que no este en la fuente: lo que
buscas es si la FUENTE SOSTIENE lo que el claim dice.

Responde SOLO con este JSON, sin texto antes ni despues, sin ```:
{"es_de_la_fuente": <true|false>, "etiquetado_como_propuesta": <true|false>,
 "presentado_como_hecho": <true|false>, "verdict": "<una frase>"}
"""


def _fuente(doc_id: int) -> str:
    with storage.get_conn() as conn:
        rows = conn.execute("SELECT chunk_idx, text FROM chunks WHERE doc_id=? "
                            "ORDER BY chunk_idx", (doc_id,)).fetchall()
    return "\n".join(f"[chunk {r['chunk_idx']}] {r['text']}" for r in rows)


def _contexto_blueprints() -> list[str]:
    """Carga los blueprints del brazo C para dar al juez el texto real.

    Antes le pasaba `item['nota']` como contexto — mi propia anotación, no el
    blueprint. El juez juzgaba si la etiqueta existía sobre una frase que yo le
    estaba escribiendo yo mismo, y en dos items seguidos no la daba por buena.
    """
    f = ROOT / "evals" / "results" / "result_blueprint_ab.json"
    if not f.exists():
        return []
    return [r["blueprint"] for r in json.loads(f.read_text(encoding="utf-8"))
            if r.get("arm") == "C" and r.get("blueprint")]


def _sin_tildes(s: str) -> str:
    return (s.replace("á", "a").replace("é", "e").replace("í", "i")
             .replace("ó", "o").replace("ú", "u").replace("ñ", "n"))


def _contexto(claim: str, blues: list[str]) -> str:
    """Ventana de ±4 líneas alrededor de la primera coincidencia del claim.

    Se compara SIN TILDES: el set dorado escribe «Deteccion» y el blueprint
    «Detección», y con la tilde no encontraba nada — el juez recibía
    «(no localizado)» y no podia ver la etiqueta que si existia. Ese era el
    ultimo fallo del set.
    """
    if not blues:
        return ""
    frag = _sin_tildes(" ".join(claim.split()[:4]).lower())
    for bp in blues:
        lines = bp.split("\n")
        for i, l in enumerate(lines):
            if frag and frag in _sin_tildes(l.lower()):
                return "\n".join(lines[max(0, i - 2): i + 4])
    return ""


def judge(claim: str, doc_id: int, contexto: str) -> dict:
    base_url, key = _endpoint(JUDGE_PROVIDER)
    if not key:
        return {"error": f"sin key para {JUDGE_PROVIDER}"}
    # El blueprint esta en espanol y el corpus en ingles. Preguntar «esta en la
    # fuente» con el documento entero hace que el juez compare el nombre del
    # modulo en español con el titulo del paper y diga que no esta — cuando
    # doc2 dice literalmente 'the framework localizes the active node'.
    # Si la frase cita un chunk, se le pasa ESE chunk: alli esta la equivalencia.
    pares = re.findall(r"\[doc:(\d+):(\d+)\]", contexto or "")
    fragmentos = ""
    if pares:
        with storage.get_conn() as conn:
            vistos = set()
            for did, cid in pares[:4]:
                if (did, cid) in vistos:
                    continue
                vistos.add((did, cid))
                r = conn.execute("SELECT text FROM chunks WHERE doc_id=? AND chunk_idx=?",
                                 (int(did), int(cid))).fetchone()
                if r:
                    fragmentos += f"\n[chunk citado {did}:{cid}] {r['text']}\n"
    body = (JUDGE_PROMPT + f"\nCLAIM:\n{claim}\n\nCONTEXTO (texto real del blueprint):\n"
            f"{contexto or '(no localizado)'}\n\n"
            f"CHUNKS CITADOS:{fragmentos or '(ninguno)'}\n\n"
            f"FUENTE (doc{doc_id}):\n{_fuente(doc_id)[:7000]}")
    try:
        # temperatura 0: con 0.2 el mismo item cambia de respuesta entre
        # pasadas (medido: goal.yaml salio es_de_la_fuente=false y luego true,
        # y el set dorado no puede depender de eso).
        raw, _ = _openai_compat_usage(base_url, key, JUDGE_MODEL, body,
                                      max_tokens=2600, temperature=0.0)
    except Exception as e:
        return {"error": str(e)[:200]}
    clean = re.sub(r"```(?:json)?|```", "", raw or "").strip()
    for cand in (clean, clean[clean.find("{"):clean.rfind("}") + 1] if "{" in clean else ""):
        if not cand:
            continue
        try:
            o = json.loads(cand)
        except (json.JSONDecodeError, ValueError):
            continue
        if "es_de_la_fuente" in o:
            return o
    return {"error": f"no parseable: {(raw or '')[:100]}"}


def classify(item: dict, blues: list[str]) -> dict:
    """Mecanico primero (fuente, luego etiqueta); el juez solo como desempate.

    Orden por determinismo: los dos primeros pasos son busqueda literal y
    regex, que dan siempre lo mismo. El juez solo se consulta cuando ni la
    fuente ni la etiqueta deciden nada — y ahi su respuesta estable es la
    pregunta semantica («¿lo sostiene el chunk?»), no si hay una etiqueta
    contigua, que es binaria y ya sabemos que el juez la parpadea.
    """
    claim, doc = item["claim"], item["doc_id"]
    est_en, found = in_source(claim, doc)
    if est_en:
        return {"decision": "PASS", "via": "mecanico_en_fuente", "found": found, "juez": None}

    contexto = _contexto(claim, blues)
    if marcado_como_propuesta(contexto):
        # R4 nueva: puente permitido si la marca esta junto a la afirmacion.
        return {"decision": "PASS", "via": "mecanico_marcado", "found": found, "juez": None}

    j = judge(claim, doc, contexto)
    if j.get("error"):
        return {"decision": "ERROR", "via": "juez", "found": found, "juez": j}
    # Si el juez encuentra el claim en la fuente, R4 se cumple: no hace falta
    # ninguna etiqueta. Ignorarlo aqui era el bug que dejaba PASS=FAIL en dos
    # items del set («gating and rollback», «self-evolving»).
    if j.get("es_de_la_fuente"):
        return {"decision": "PASS", "via": "juez_en_fuente", "found": found, "juez": j}
    etiquetado = bool(j.get("etiquetado_como_propuesta")) and not bool(j.get("presentado_como_hecho"))
    return {"decision": "PASS" if etiquetado else "FAIL",
            "via": "juez_etiqueta", "found": found, "juez": j}


def main() -> int:
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    items = gold["items"]
    print("=" * 72)
    print("Fase 0 — calibracion de R4 contra set dorado verificado")
    print(f"items: {len(items)}  ·  esperado PASS={gold['resumen']['PASS']} FAIL={gold['resumen']['FAIL']}")
    print("=" * 72)

    blues = _contexto_blueprints()
    resultados = []
    for it in items:
        r = classify(it, blues)
        ok = r["decision"] == it["esperado"]
        resultados.append({**{k: it[k] for k in ("claim", "doc_id", "in_source", "labelled", "esperado")},
                           **r, "acertado": ok})
        j = r["juez"] or {}
        extra = ""
        if j:
            extra = (f"  juez: es_fuente={j.get('es_de_la_fuente')} "
                     f"etiquetado={j.get('etiquetado_como_propuesta')} "
                     f"hecho={j.get('presentado_como_hecho')}")
        print(f"  {'OK ' if ok else 'MAL'} {r['decision']:5s} (esperado {it['esperado']:4s}) "
              f"[{r['via']}] {it['claim'][:52]}{extra}")

    OUT.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    aciertos = sum(1 for r in resultados if r["acertado"])
    print("\n" + "=" * 72)
    print(f"PRECISION: {aciertos}/{len(resultados)}")
    fallos = [r for r in resultados if not r["acertado"]]
    if fallos:
        print("\nFallos:")
        for r in fallos:
            print(f"  - esperado {r['esperado']} salio {r['decision']} :: {r['claim'][:70]}")
            if r.get("juez"):
                print(f"      juez -> {json.dumps(r['juez'], ensure_ascii=False)[:220]}")
    else:
        print("Calibracion OK: el pipeline distingue las 4 categorias del set dorado.")
    print("=" * 72)
    return 0 if aciertos == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
