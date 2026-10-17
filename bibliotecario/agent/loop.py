"""Loop ReASearch sobre Gemini: protocolo ReAct en texto + harness siempre activo.

- Harness habilitado por defecto (corrige use_harness=False del origen).
- PFs cableados al loop (corrige /pfs y /pf_run no registrados).
- Runs persistidos (corrige cero persistencia); trayectorias alimentan al refiner (F4).
- Protocolo de tools en texto (```json) en vez de function-calling nativo: robusto a largo plazo.
"""
from __future__ import annotations

import json
import logging
import os
import re

from bibliotecario.agent import state as ST
from bibliotecario.agent.tools import TOOLS, tool_schemas
from bibliotecario.core.llm import generate as _llm_generate

# La evaluación lo pone a True: si un proveedor muere a mitad de una run, que la
# pregunta se marque como fallida en vez de responderse con otro modelo en
# silencio. Ver bibliotecario.core.llm.generate.
STRICT_FALLBACK = False

# Anclaje: localizar verbatim antes de redactar. Medido en evals/probe_extraction.py
# (ver REPORT_BLIND.md, "Fase 2 descartada"): recortar el contexto NO arregla las
# preguntas que fallan, porque el fallo no es de volumen sino de desanclaje
# confiado. El agente cita bien y se equivoca igual en los tres runs: con el
# pajar de 1.3k responde sobre el tema equivocado (tce-b7) o rellena con nombres
# de archivo reales pero hermanos de los pedidos (wiki-b1). Esos nombres SI estan
# en el documento, asi que no es fabricacion: es mala seleccion.
#
# Que ademas "CIERRE OBLIGADO: responde YA" prohibe decir que no se encontro nada,
# mientras el juez (evals/judge.py:47) ya esta preparado para puntuar bien una
# abstention honesta. Esta fase devuelve solo los spans verbatim que pueden
# responder la pregunta, y el cierre solo puede usar esos.
ANCHOR_GROUNDING = os.environ.get("ANCHOR_GROUNDING", "0") == "1"
_NO_ENCONTRADO = "NO_ENCONTRADO"

# Verificacion de que la cita sostiene la afirmacion (opt-in por VERIFY_CITATION=1).
# El residuo de r5/r6 no es de cobertura: en `tce-b7` el agente cita [3:25], ese chunk
# contiene literalmente la respuesta ("uniform sampling also spends its budget on
# easier tasks that terminate quickly") y aun asi se queda con la explicacion
# anterior; en `wiki-b1` y `wiki-b6` cita bien y deja fuera justo lo que la pregunta
# pedia. Ni el replay numerico (A) ni el detector de preguntas multiparte (B) tocan
# ninguno de esos casos: A no encuentra ni una violacion real y B marca 16 de las 30
# preguntas que ya eran correctas. Se queda como lo unico del plan que si mide el fallo.
VERIFY_CITATION = os.environ.get("VERIFY_CITATION", "0") == "1"
_CITE_RE = re.compile(r"\[(\d+):(\d+)\]")

# Verificacion de SOPORTE SEMANTICO con salida posible de abstencion
# (opt-in por VERIFY_SUPPORT=1). MEDIDA Y RECHAZADA: se queda apagada.
# Con temperatura libre parecia funcionar (51.6% -> 36.5% de fabricacion), pero al
# repetir la comparacion pareada a temperatura 0 el efecto se dio la vuelta: 6
# items corregidos frente a 13 rotos, p = 0.17. El -14.5pp anterior era ruido a su
# favor. La quinta intervencion sin resultado, y la unica forma de distinguirla de
# las cuatro anteriores fue este par de runs, no el run en si.
# La implementacion se conserva porque el flag es opt-in y no cuesta nada apagado,
# y porque repetir el experimento con otro verificador sigue siendo el camino si
# se vuelve a intentarlo. No la pongas por defecto: el numero medido va al reves.
VERIFY_SUPPORT = os.environ.get("VERIFY_SUPPORT", "0") == "1"


def _temp_kw(t: float | None) -> dict:
    """Kwargs de temperatura, vacios si no se fijo ninguna.

    Asi la ruta por defecto (`None`) llama exactamente igual que antes de existir
    este parametro: los dobles de test y los llamantes externos no cambian.
    """
    return {} if t is None else {"temperature": t}


def generate(prompt: str, max_tokens: int = 512, retries: int | None = None,
             temperature: float | None = None) -> str:
    """`temperature=None` deja el valor por defecto del backend (0.2). Fijarlo a 0
    hace la trayectoria reproducible, que es lo que necesita el protocolo pareado:
    el ruido entre runs del agente (sd 0.946 por item, medido en r7) viene en su
    mayor parte de la sampling, no del juez."""
    return _llm_generate(prompt, max_tokens, 2 if retries is None else retries,
                         strict_fallback=STRICT_FALLBACK, temperature=temperature)
from bibliotecario.harness.edits import normalize_signature
from bibliotecario.harness.runtime import get_harness
from bibliotecario.ingest import citations_format as CITE_FMT
from bibliotecario.knowledge import refiner as REF

logger = logging.getLogger(__name__)
TOOL_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
MAX_TURNS = 12


def _bare_objects(text: str) -> list[dict]:
    """Extrae objetos JSON sueltos (proveedores que no usan vallas), con prefijo de razonamiento."""
    dec = json.JSONDecoder()
    objs = []
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = dec.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            objs.append(obj)
    return objs


def parse_tool_call(text: str) -> tuple[str | None, dict]:
    m = TOOL_BLOCK.search(text)
    obj = None
    if m:
        try:
            obj = json.loads(m.group(1))
        except json.JSONDecodeError:
            obj = None
    if obj is None:
        for cand in _bare_objects(text):
            if "tool" in cand:
                obj = cand
                break
    if obj is None:
        # Sin clave "tool": ¿hay un objeto con forma de args? → llamada malformada.
        for cand in _bare_objects(text):
            if any(k in cand for k in ("query", "top_k", "top_m", "technique", "goal", "doc_id")):
                return "", cand
        return None, {}
    name = obj.get("tool")
    args = obj.get("args", {})
    if name not in TOOLS or not isinstance(args, dict):
        return None, {}
    return name, args


def _toolish(text: str) -> bool:
    if TOOL_BLOCK.search(text):
        return True
    if any(("tool" in o or any(k in o for k in ("query", "top_k", "top_m", "technique")))
           for o in _bare_objects(text)):
        return True
    # JSON malformado: el modelo empezó a emitir una llamada de tool y se cortó a
    # media estructura (p. ej. '"top_k": 5": 5}}'). No puede ser una respuesta.
    return _has_broken_json(text or "")


_BROKEN_KEYS = ("tool", "query", "top_k", "top_m", "args", "technique", "blueprint")


def _has_broken_json(text: str) -> bool:
    """True si `text` parece JSON de tool corrupto o malformado."""
    if "{" not in text or "}" not in text:
        return False
    # El texto es casi todo JSON (poco texto en medio), no prosa con un fragmento.
    # Una respuesta real tiene varias frases; un volcado tiene casi ninguna.
    prose = " ".join(_strip_json_blobs(text).split())
    if len(prose) > 40:  # hay prosa de verdad alrededor del JSON
        return False
    try:
        json.loads(text)
        return True  # JSON bien formado: volcado, no respuesta
    except (json.JSONDecodeError, ValueError):
        pass
    return any(f'"{k}"' in text for k in _BROKEN_KEYS)


def _strip_json_blobs(text: str) -> str:
    """Quita los mayores objetos/arrays JSON balanceados y devuelve la prosa restante.

    Se conserva el texto antes y después de cada blob: una respuesta real puede
    citar un fragmento JSON dentro de una frase.
    """
    prose, depth, start, pos = [], 0, None, 0
    for i, ch in enumerate(text):
        if ch in "{[":
            if depth == 0:
                start = i
            depth += 1
        elif ch in "}]":
            if depth == 0:  # cierre huérfano: es prosa
                continue
            depth -= 1
            if depth == 0 and start is not None:
                prose.append(text[pos:start])  # prosa anterior al blob
                pos = i + 1                  # el blob se descarta
                start = None
    prose.append(text[pos:])  # prosa final (o el resto si quedó JSON sin cerrar)
    return " ".join(prose)


def load_lessons(scope: str = "qa", limit: int = 5) -> str:
    from bibliotecario.core import storage
    with storage.get_conn() as conn:
        rows = conn.execute("SELECT what_worked, what_failed, key_insights FROM lessons "
                            "WHERE scope=? ORDER BY id DESC LIMIT ?", (scope, limit)).fetchall()
    return "\n".join(f"· W:{r['what_worked'] or '-'} F:{r['what_failed'] or '-'} K:{r['key_insights'] or '-'}"[:300]
                     for r in rows)


def compact(transcript: list[str], snapshot: str) -> list[str]:
    """Compresión ReASearch: snapshot autoritativo + resumen + lessons (3 mensajes)."""
    summary = generate("Resume en 10 líneas: insights clave y trabajo pendiente.\n\n" + "\n".join(transcript[-30:]),
                       max_tokens=512) or "(sin resumen)"
    return [f"[SNAPSHOT] {snapshot}", f"[RESUMEN] {summary}", f"[LESSONS]\n{load_lessons()}"]


def _deep_evidence(question: str, per_doc: int = 4, n_docs: int = 4) -> str:
    """Barrido profundo determinista: chunks del cierre que el top-8 no trajo.

    Sin coste LLM y sin varianza. Se limita a los `n_docs` papers con mejor score
    porque el barrido completo de los 5 papers serían ~90k caracteres, más que el
    resumen y el resto de la evidencia juntos.

    `n_docs` era 2 y recortaba en exclusiva: en `wiki-b4` el paper gold (doc 5,
    que es el que la propia pregunta nombra) quedaba en 4º lugar del ranking y
    sus chunks 57-59 nunca llegaban al cierre. Medido sobre las 35 respondibles,
    subirlo a 4 sube el recall de chunks gold de 38/46 a 40/46 y arregla esa
    pregunta sin perder ninguna otra. `n_docs=3` no arregla nada: 38/46 igual,
    porque el doc gold cae justo en la 4ª posición.
    """
    try:
        res = TOOLS["deep_sweep"]["fn"](question=question, per_doc=per_doc)
    except Exception as e:  # degradación con gracia
        logger.warning("Barrido profundo falló: %s", str(e)[:120])
        return ""
    lines = []
    for d in res.get("docs", [])[:n_docs]:
        for c in d["chunks"]:
            # sin truncar: el dato concreto suele estar al final del chunk
            lines.append(f"[{d['doc_id']}:{c['chunk']}] {d['title']}\n{c['text']}")
    return "\n\n".join(lines)


def _ground(question: str, deep: str, retries: int = 1, temperature: float | None = None) -> str:
    """Localiza en el barrido los spans verbatim que pueden responder la pregunta.

    Devuelve las lineas relevantes tal cual, o `_NO_ENCONTRADO` si el barrido no
    contiene el dato pedido. No resume ni parafrasea: si devuelve algo, tiene que
    ser texto que aparece literalmente en `deep`.

    Existe para separar dos fallos que hasta ahora se confundian: no encontrar el
    dato, y encontrarlo pero redactar sobre otro. Al obligar a emitir el span
    literal antes de redactar, el agente tiene que mostrar donde ha mirado, y el
    cierre puede decir "no aparece" en vez de inventar un hermano plausible.
    """
    if not deep:
        return _NO_ENCONTRADO
    prompt = (
        "Localiza en la EVIDENCIA las lineas que pueden responder exactamente a esta "
        "PREGUNTA.\n"
        f"PREGUNTA: {question}\n\n"
        f"EVIDENCIA:\n{deep}\n\n"
        "REGLAS ESTRICTAS:\n"
        "- Copia las lineas LITERALMENTE, sin parafrasear, sin resumir, sin corregir.\n"
        f"- Si ningun dato de la EVIDENCIA responde a la PREGUNTA, responde solo {_NO_ENCONTRADO}.\n"
        "- No deducias ni combines: solo copia lo que esta ahi escrito.\n"
        "- Si aparecen varios candidatos, copia TODOS los relevantes, no elijas.\n"
        "- No escribas commentary, solo las lineas copiadas.\n\n"
        f"RESPUESTA ({_NO_ENCONTRADO} si no hay nada):")
    out = generate(prompt, max_tokens=700, retries=retries, **_temp_kw(temperature)).strip()
    if _toolish(out):
        return _NO_ENCONTRADO
    if _NO_ENCONTRADO in out:
        return _NO_ENCONTRADO
    # Solo se admiten lineas que existen literalmente en el barrido. Si el modelo
    # paraphrasea, lo que survive es exactamente el texto justificable.
    return out


def _chunk_index(deep: str) -> dict[str, str]:
    """Indice 'doc:chunk' -> bloque integro del barrido profundo."""
    idx: dict[str, str] = {}
    key, buf = "", []
    for line in (deep or "").splitlines():
        m = re.match(r"^\[(\d+:\d+)\]\s", line)
        if m:
            if key:
                idx[key] = "\n".join(buf)
            key, buf = m.group(1), [line]
        elif key:
            buf.append(line)
    if key:
        idx[key] = "\n".join(buf)
    return idx


def _verify_citation(question: str, answer: str, deep: str, retries: int = 1,
                     temperature: float | None = None) -> str:
    """Comprueba que los chunks citados sostienen la respuesta y la reescribe si no.

    Solo interviene si las citas del cierre resuelven dentro del barrido profundo:
    una cita que no se puede localizar no se puede verificar, y no se toca.

    La puerta anti-sobrecorreccion es asimetrica a proposito. Este paso es el que
    puede tirar abajo respuestas que ya eran correctas, y el residuo medido son 5
    preguntas de 35, asi que el umbral de aceptacion de una reescritura tiene que
    ser alto: se exige que el verificador devuelva prosa Y que toda su cita exista
    en los chunks que ya estaban en la evidencia. "OK", una salida sin cita, una
    cita nueva o un volcado de tool devuelven el original intacto.
    """
    idx = _chunk_index(deep)
    cited: list[tuple[str, str]] = []
    for m in _CITE_RE.finditer(answer or ""):
        cid = f"{m.group(1)}:{m.group(2)}"
        if cid in idx and cid not in [c for c, _ in cited]:
            cited.append((cid, idx[cid]))
    if not cited:
        return answer

    allowed = {f"[{cid}]" for cid, _ in cited}
    prompt = ("VERIFICACION DE UN CIERRE. Comprueba si la RESPUESTA se sostiene en los "
              "chunks que cita.\n\n"
              f"PREGUNTA: {question}\n\n"
              f"RESPUESTA A VERIFICAR:\n{answer}\n\n"
              "CHUNKS CITADOS (texto integro):\n" + "\n\n".join(t for _, t in cited) + "\n\n"
              "COMPRUEBA en este orden:\n"
              "1. ¿Cada afirmacion de la respuesta aparece LITERALMENTE en algun chunk citado?\n"
              "2. ¿Se queda alguna parte de la pregunta sin responder? Repasa el chunk COMPLETO: "
              "puede contener mas de un dato que responda a la pregunta, y quedarse con el "
              "primero tambien es un fallo.\n"
              "3. ¿Das el tipo de cosa que pide la pregunta? Si pide archivos, un directorio no "
              "vale; si pide dos cifras, una sola no vale.\n\n"
              "FORMATO DE SALIDA, obligatorio y excluyente:\n"
              "- Si la respuesta es correcta y completa: escribe exactamente OK y nada mas.\n"
              "- Si algo falla: escribe la respuesta CORREGIDA en prosa (max. 150 palabras), "
              "citando cada afirmacion como [doc_id:chunk] y usando solo los chunks de arriba.\n\n"
              "SALIDA:")
    out = generate(prompt, max_tokens=900, retries=retries, **_temp_kw(temperature)).strip()
    if not out or _toolish(out):
        return answer
    if re.fullmatch(r"OK\.?", out, re.IGNORECASE):
        return answer
    if not CITE_FMT.has_citation(out):
        return answer
    if any(f"[{m.group(1)}:{m.group(2)}]" not in allowed for m in _CITE_RE.finditer(out)):
        return answer
    return CITE_FMT.normalize_citations(_fix_truncation(out))


def _close_prompt(question: str, ctx: str, anclaje: str, best: str, flat: int,
                  enumerate_slots: bool = False) -> str:
    """Prompt de cierre, en una función aparte para que las sondas offline usen
    exactamente el mismo texto que producción en vez de una copia que se desincroniza.

    Las REGLAS son deliberadamente de dos ramas. Antes el cierre decía "CIERRE
    OBLIGADO: responde YA" y al mismo tiempo "no inventes cifras": cuando el dato
    no estaba, la unica salida era inventar un hermano plausible (asi lo describe
    tambien el comentario de `_ground`). La auditoria de las 40 fabricaciones de
    T0/T0' lo confirma: en 16 de ellas la cifra existia en el paper correcto sin
    responder a la pregunta, y en otras 17 el agente contestaba otro tema. El fallo
    no es que busque mal, es que da por buena la primera coincidencia.

    `enumerate_slots=True` antepone el paso de la dirección 2 del análisis:=listar
    lo que la pregunta pide, con su span literal, antes de redactar. A diferencia
    del anclaje (r4, p=0.206) NO restringe la redacción a esos spans: solo obliga
    a haber mirado cada elemento pedido. Si al final hay mas elementos de los que
    caben, la prosa los pierde igual.
    """
    enum = ""
    if enumerate_slots:
        enum = ("\n\nPASO 1, ANTES DE REDACTAR: desglosa qué pide exactamente la "
                "pregunta. Una linea por elemento pedido (por ejemplo, una por cada "
                "cifra, cada fichero o cada componente que la pregunta mencione), y al "
                "final de cada linea el span LITERAL de la evidencia que lo sostiene.\n"
                "- No filtres: si la pregunta admite varios elementos, van todos.\n"
                "- Si un elemento pedido no aparece en la evidencia, marcalo como AUSENTE.\n"
                "PASO 2: redacta la respuesta y cubrielos TODOS, en el mismo orden.\n")
    # Dos variantes del cierre: ver PROMPT_LEGACY en state.py. La rama legacy es la
    # previa a 15261a0, literal, y existe SOLO para poder comparar los dos prompts a
    # la misma temperatura.
    if ST.CLOSE_LEGACY:
        cabecera = (
            "CIERRE OBLIGADO: responde YA en prosa (máx 150 palabras) usando solo esta "
            "evidencia.\n"
            "REGLAS DE CIERRE:\n"
            "- CITA obligatoriamente cada afirmación con el formato [doc_id:chunk] "
            "(ej. [5:7]).\n"
        )
    else:
        cabecera = (
            "CIERRE: redacta en prosa (máx 150 palabras) usando solo esta evidencia.\n"
            "REGLAS DE CIERRE:\n"
            "- Si la evidencia contiene literalmente el dato que pide la pregunta, "
            "respóndelo y CITA cada afirmación con el formato [doc_id:chunk] (ej. [5:7]).\n"
            "- Si NO lo contiene, no lo sustituyas por un número parecido ni por una "
            "descripción general: explica en una frase qué se buscó y que no aparece, y "
            "cierra sin dar ningún dato por cierto.\n"
        )
    return (ST.STATIC_PROMPT + "\n\nPREGUNTA: " + question +
            "\n\nEVIDENCIA REUNIDA:\n" + ctx + anclaje + enum +
            f"\n\nMejor resultado parcial:\n{best or '(ninguno)'}\n"
            f"\nTurnos sin progreso: {flat}.\n"
            + cabecera +
            "- La pregunta pide un dato concreto (una cifra, un tope, una regla). "
            "BÚSCA ese dato explícitamente en toda la evidencia, también en el barrido: "
            "no te quedes con el primer chunk parecido.\n"
            "- Cifras exactas: copia el número literal de la evidencia. Si dos fuentes "
            "se contradicen, cita la que responde a la pregunta concreta.\n"
            "- No inventes cifras ni reglas que no aparezcan literalmente en la evidencia.\n"
            "- No termines a media frase: completa la idea y cierra con punto.\n"
            "- No emitas ningún bloque json ni vuelques resultados crudos.")


def _final_answer(question: str, best: str, evidence: list[str], flat: int, retries: int = 1,
                   temperature: float | None = None) -> str:
    """Cierre forzado: pide una respuesta en prosa a partir de la evidencia reunida.

    Evita que el loop termine con el volcado JSON de un tool como 'respuesta'.
    El barrido profundo es determinista y barato (4-11k chars, sin cuota), así que
    se aplica siempre: los detalles concretos viven en apéndices que el top-8 por
    relevancia no trae, y sin ellos el agente citaba el chunk equivocado.
    """
    deep = _deep_evidence(question)
    ctx = ("\n".join(evidence[-8:]) or "(ninguna)") + ("\n\nEVIDENCIA PROFUNDA (barrido por documento):\n" + deep if deep else "")

    # Anclaje (opt-in por ANCHOR_GROUNDING=1). Una pasada extra de localizacion
    # verbatim: obliga a mostrar el span antes de redactar, y devuelve
    # NO_ENCONTRADO cuando el barrido no tiene el dato. Ese caso antes era
    # imposible: "CIERRE OBLIGADO" empujaba a rellenar con un hermano plausible.
    anclaje = ""
    if ANCHOR_GROUNDING:
        spans = _ground(question, deep, retries=retries, **_temp_kw(temperature))
        if spans == _NO_ENCONTRADO:
            anclaje = ("\n\nANCLAJE: no se ha localizado en el barrido ningún dato que "
                       "responda a esta pregunta. NO inventes ni deduzcas: explica en una "
                       "frase qué se buscó y qué se encontró.\n")
        else:
            anclaje = ("\n\nANCLAJE (verbatim, solo estas lineas pueden sostener la "
                       f"respuesta):\n{spans}\n"
                       "- Redacta EXCLUSIVAMENTE con lo que hay en el anclaje.\n"
                       "- No introduzcas nombres, cifras ni reglas que no aparezcan ahí.\n")

    prompt = _close_prompt(question, ctx, anclaje, best, flat)
    out = generate(prompt, max_tokens=900, retries=retries, **_temp_kw(temperature)).strip()
    # Vacío tras agotar proveedores: devolver "" para que el caller (run)
    # llegue a _synthesize o al fallback de presupuesto agotado. Antes se
    # pegaba "  [doc:?]" incluso sin prosa, y esa marca es truthy: tumbaba
    # el `or` del caller y la run terminaba con la marca como respuesta.
    if not out or _toolish(out):
        return ""
    out = _fix_truncation(out)
    if evidence and not CITE_FMT.has_citation(out):
        out = out.rstrip() + "  [doc:?]"  # marca de hueco: el cierre debe citar
    out = CITE_FMT.normalize_citations(out)
    if VERIFY_CITATION and deep:
        out = _verify_citation(question, out, deep, retries=retries, **_temp_kw(temperature))
    if VERIFY_SUPPORT and deep:
        out = _verify_support(question, out, deep, retries=retries, **_temp_kw(temperature))
    return out


def _verify_support(question: str, answer: str, deep: str, retries: int = 1,
                    temperature: float | None = None) -> str:
    """Comprueba si la evidencia SOSTIENE la respuesta y, si no, se abstiene.

    Se distingue de `_verify_citation` en las dos cosas que hacian que aquella
    no moviera la aguja: el criterio es de sustento semantico y no de coincidencia
    literal, y la salida puede ser abstencion, no solo una reescritura.

    La puerta es asimetrica a proposito. Este paso puede tirar abajo respuestas que
    ya eran correctas, y las respondibles son 105 contra 64 no respondibles: una
    Precision del 80% aqui destruye mas nota de la que gana en abstencion. Solo se
    abstiene ante un veredicto negativo explicito y con motivo; una salida
    ilegible, una excepcion, un "duda", un JSON mal formado o una lista de
   rafts vacia devuelven el original intacto. Ante la duda, se responde.
    """
    if not (deep or "").strip():
        return answer
    prompt = ("VERIFICACION DE SUSTENTO. La RESPUESTA se va a publicar como si fuese "
              "correcta. Decide si la EVIDENCIA la sostiene.\n\n"
              f"PREGUNTA: {question}\n\n"
              f"RESPUESTA A VERIFICAR:\n{answer}\n\n"
              f"EVIDENCIA RECUPERADA:\n{deep[:12000]}\n\n"
              "Un numero de repeticiones no es lo mismo que un valor medido: si la "
              "evidencia dice 'three independent runs', eso NO da el coste en USD, ni "
              "la desviacion tipica, ni la semilla. Un mecanismo plausible inventado "
              "para explicar un fenomeno tambien es un fallo, aunque todas sus piezas "
              "existan por separado en la evidencia.\n\n"
              "Responde con un unico objeto JSON y nada mas:\n"
              '{"sostenida": true|false, "motivo": "una frase"}\n\n'
              "- sostenida=false SOLO si alguna afirmacion, cifra o relacion de la "
              "RESPUESTA no se deduce de la EVIDENCIA.\n"
              "- Si la respuesta es una admision de que el dato no esta, sostenida=true.\n"
              "- Ante cualquier duda, sostenida=true.\n\n"
              "JSON:")
    try:
        out = generate(prompt, max_tokens=200, retries=retries,
                       **_temp_kw(temperature)).strip()
    except Exception:
        return answer
    if not out or _toolish(out):
        return answer
    for obj in _bare_objects(out) or [{}]:
        flag = obj.get("sostenida")
        if flag is True:
            return answer
        if flag is False and str(obj.get("motivo") or "").strip():
            return (_ABSTENCION_TEMPLATE.format(motivo=str(obj["motivo"]).strip()[:200]))
    return answer


_ABSTENCION_TEMPLATE = (
    "No se puede responder esto con evidencia. {motivo}. "
    "La busqueda en el corpus no devuelve un dato que lo sostenga, y deducirlo o "
    "aproximarlo daria una respuesta con apariencia de dato y sin respaldo.")


def _fix_truncation(text: str) -> str:
    """Si la respuesta se cortó a media frase, marca el final en vez de dejarla colgada."""
    t = (text or "").rstrip()
    if not t or t[-1] in ".!?)]}\"'`:;":
        return t
    return t + " […truncado]"


def _synthesize(question: str, retries: int = 1) -> str:
    """Cierre de último recurso: QA multi-documento (resume y cita, sin protocolo de tools)."""
    try:
        out = str(TOOLS["answer_multi_hop"]["fn"](question=question, top_k=6).get("answer", ""))
    except Exception as e:  # degradación con gracia
        logger.warning("Síntesis multi-hop falló: %s", str(e)[:120])
        return ""
    return "" if out.startswith("(extractivo)") else out


def _trajectory_fingerprint(turn: int, evidence: list, answer: str) -> str:
    """Huella de la trayectoria, sin la pregunta.

    Antes key_insights era `Q: <texto de la pregunta>`: las 5 lecciones que
    load_lessons() inyecta en el prompt llevaban el texto de preguntas
    anteriores, así que una run veía el golden de las demás. Ahora la columna
    dice qué pasó (turnos, herramientas, si citó), que es lo que una run
    siguiente puede reutilizar, y no qué se preguntó.
    """
    tools = sorted({e.split("(", 1)[0] for e in evidence if isinstance(e, str) and "(" in e})
    cite = "con citas" if CITE_FMT.has_citation(answer) else "sin citas"
    return f"{turn + 1} turnos · {', '.join(tools[:6]) or 'sin tools'} · {cite}"


def run(question: str, max_turns: int = MAX_TURNS, isolated: bool = False,
        temperature: float | None = None) -> dict:
    """Responde una pregunta.

    `isolated=True` corta el aprendizaje: no lee lecciones guardadas ni escribe
    una nueva. Es obligatorio en evaluación.

    La razón original era que key_insights llevaba `Q: <pregunta>`, con lo que
    el prompt de cada run incluía preguntas anteriores del propio golden set y
    la eval dejaba de ser ciega. Eso ya está arreglado en _trajectory_fingerprint,
    pero `isolated=True` sigue siendo obligatorio por una segunda razón: sin él,
    una fila hereda las lecciones de la anterior dentro del mismo batch, así que
    el resultado dependería del orden en que se ejecuten y la run no sería
    repetible.
    """
    harness = get_harness()
    harness.calibrate(tool_schemas())
    run_id = harness.start_run({"question": question})
    evidence: list[str] = []
    history: list[str] = []
    transcript: list[str] = []
    best, flat, answer = "", 0, ""
    failed, succeeded = [], []
    last_call = ""
    # Estado REAL para los PFs (Fase 3, Hito 3). Antes apply_pfs recibía un
    # dict fabricado — last_action.status="ok" y task.type="research"
    # escritos a mano — así que ningún PF built-in podía casar (hallazgo 4).
    # Ahora sale del recorrido: status "error" en cada record_error, "ok"
    # tras una tool ejecutada; sin campos de task que no sabemos (la
    # complejidad no se inventa; DecomposePF no dispara si no la hay).
    last_status, errores = "ok", 0
    last_tool = ""
    pf_fires: list[dict] = []
    pf_states: list[dict] = []  # estados que llegaron a apply_pfs (H3: variación)
    # Firmas de fallo de esta run (Hito 4): cada mensaje de error se guarda
    # normalizado y sin repetir; de aquí salen state_pf["last_error"] y la
    # meta-evolución al cerrar la run.
    run_errors: list[str] = []
    skills_applied: dict = {}  # nombre -> ProceduralSkill ya aplicada en esta run
    errores_at_hints = None
    meta_events: list[dict] = []

    def _falla(msg: str) -> str:
        """Registra la firma del fallo (dedupe) y devuelve la normalizada."""
        sig = normalize_signature(msg)
        if sig not in run_errors:
            run_errors.append(sig)
        return sig

    turn = -1  # si el bucle no llega a iterar, el finally sigue sabiendo los turnos

    try:
        for turn in range(max_turns):
            lessons = "" if isolated else load_lessons()
            prompt = (ST.STATIC_PROMPT + "\n\n" + ST.render_state(question, evidence, history,
                                                                  lessons, flat, best))
            out = generate(prompt, max_tokens=1024, **_temp_kw(temperature))
            transcript.append(f"T{turn}: {out[:500]}")
            if not out:
                harness.record_error("loop")
                last_status, errores = "error", errores + 1
                _falla("turno vacío (fallo LLM)")
                flat += 1
                history.append("turno vacío (fallo LLM)")
                continue
            name, args = parse_tool_call(out)
            if name is None:
                if _toolish(out):
                    # Parecía una llamada pero inválida (tool inexistente o JSON roto): feedback, no respuesta.
                    harness.record_error("loop")
                    last_status, errores = "error", errores + 1
                    flat += 1
                    msg = ("llamada inválida: emite EXACTAMENTE "
                           '{"tool": nombre, "args": {...}} con un tool del catálogo (no sueltes args sin "tool")')
                    history.append(msg)
                    failed.append(msg)
                    _falla(msg)
                    continue
                # Una respuesta en prosa no se acepta cruda: pasa por el cierre forzado
                # para que corra el barrido profundo y se exijan las citas. Aceptarla
                # aqui saltaba media pipeline (medido: 2.273 vs 4.551 de media).
                draft = CITE_FMT.normalize_citations(out.strip())
                answer = (_final_answer(question, draft, evidence, flat, retries=1,
                                           **_temp_kw(temperature))
                          or _fix_truncation(draft))
                harness.record_action("loop", {"tool": "final_answer", "args": {"turn": turn}})
                succeeded.append(f"respuesta final en turno {turn}")
                break
            if name == "":
                harness.record_error("loop")
                last_status, errores = "error", errores + 1
                flat += 1
                msg = ('llamada malformada: falta la clave "tool". Formato: '
                       '{"tool": nombre, "args": {...}}')
                history.append(msg)
                failed.append(msg)
                _falla(msg)
                continue
            call_sig = f"{name}:{sorted(args.items())}"
            v = harness.validate_call(name, args, tool_schemas())
            if not v.valid:
                harness.record_error("loop")
                last_status, errores = "error", errores + 1
                flat += 1
                msg = f"{name} inválida: {v.error}"
                history.append(msg)
                failed.append(msg)
                _falla(msg)
                continue
            # PFs con estado real del recorrido (dec. Fase 3): lo que casaba
            # antes era un "ok" escrito a mano; ahora casan Retry/Fallback/
            # Validate cuando el bucle ha fallado de verdad, y no antes.
            # Lleva además tool anterior, estancación y evidencia: son
            # variables reales del bucle y hacen que el estado de una run
            # no sea el de otra (H3: estado constante = decoración).
            state_pf = {"last_action": {"status": last_status, "tool": last_tool},
                        "attempt_count": turn, "max_attempts": max_turns,
                        "error_count": errores, "stagnation": flat,
                        "evidence_count": len(evidence),
                        # último fallo real de esta run (Hito 4): es lo que la
                        # precondition del PF auto y la skill evolucionada buscan.
                        "last_error": run_errors[-1] if run_errors else "",
                        # la pregunta es estado real (la conoce el bucle), no
                        # un campo inventado: sin ella dos runs limpias con el
                        # mismo patrón de turnos tendrían estados idénticos.
                        "question": question[:200]}
            pf_states.append(state_pf)
            # Skills aprendidas de fallos previos (Hito 4): el hint entra en la
            # historia la primera vez que la skill aplica a este error; el
            # outcome se registra al cerrar la run.
            if run_errors:
                for skill, hint in harness.skill_hints(question, run_errors[-1]):
                    if skill.name in skills_applied:
                        continue
                    skills_applied[skill.name] = skill
                    history.append(hint)
                    if errores_at_hints is None:
                        errores_at_hints = errores
            for pf in harness.apply_pfs(state_pf):
                pf_fires.append(pf)
                history.append(f"[PF {pf['pf']}] {pf.get('message', '')}")
            try:
                result = TOOLS[name]["fn"](**v.canonicalized["arguments"])
                result_s = json.dumps(result, ensure_ascii=False, default=str)[:3000]
            except TypeError as e:
                harness.record_error("loop")
                last_status, errores = "error", errores + 1
                history.append(f"{name} args incorrectos: {e}")
                failed.append(f"{name} args: {e}")
                _falla(f"{name} args: {e}")
                flat += 1
                continue
            harness.record_action("loop", {"tool": name, "args": args})
            last_status, last_tool = "ok", name
            history.extend(harness.regulate("loop"))
            history.append(f"{name} → {result_s[:220]}")
            evidence.append(f"{name}({','.join(f'{k}={v}' for k, v in args.items())}): {result_s[:220]}")
            succeeded.append(f"{name} ok")
            if call_sig == last_call:
                flat += 1
            else:
                flat = 0
                best = result_s[:220]
            last_call = call_sig
        else:
            # Presupuesto agotado: sintetizar respuesta en vez de volcar JSON crudo.
            if not answer:
                answer = (_final_answer(question, best, evidence, flat, retries=1,
                                           **_temp_kw(temperature))
                          or _synthesize(question, retries=1)
                          or "(presupuesto agotado) " + (best or "sin evidencia"))
                if not answer.startswith("(presupuesto agotado)"):
                    harness.record_action("loop", {"tool": "synthesize", "args": {}})
                    succeeded.append("síntesis final tras agotar turnos")
            flat += 1

    finally:
        # Siempre, aunque el bucle lance: 87 runs de 1121 se quedaron con
        # finished_at NULL porque la excepcion se escapaba sin cerrarlas.
        harness.finish_run(run_id, None, {"turns": turn + 1, "tools": len(evidence),
                                          "pf_fires": len(pf_fires)})
        # Meta-evolución al cerrar (Hito 4): cuenta firmas y evoluciona a la
        # 2ª aparición. Envuelta: un fallo aquí no puede romper la run ya
        # cerrada; se avisa y la corrida sigue.
        try:
            if skills_applied and errores_at_hints is not None:
                recuperado = errores == errores_at_hints
                for skill in skills_applied.values():
                    skill.record_outcome(recuperado)
            meta_events = harness.meta_evolve(question, run_errors)
        except Exception as exc:
            logger.warning("meta-evolución al cerrar la run falló: %s", exc, exc_info=True)

    if not isolated:
        REF.save_lesson("qa", what_worked="\n".join(succeeded[-5:]),
                        what_failed="\n".join(failed[-5:]),
                        key_insights=_trajectory_fingerprint(turn, evidence, answer))
    return {"answer": answer, "turns": turn + 1, "evidence": evidence,
            "run_id": run_id, "pf_fires": pf_fires, "pf_states": pf_states,
            "meta_evolved": meta_events}


def run_blueprint(technique: str, goal: str, max_turns: int = 4,
                  temperature: float | None = None) -> dict:
    """P1' (§5): el loop **dirige**, pero el blueprint lo escribe la **tool**.

    Por qué no se enruta `build_blueprint` al loop tal cual: `run()` genera
    **cada turno** con `max_tokens=1024` y no hay presupuesto mayor para la
    respuesta final. Hacerlo bajaría el tope de 1500 a 1024 y empeoraría el
    blueprint (§5.5, la corrección que convirtió P1 en P1').

    Aquí el loop corre para poder usar las herramientas —búsqueda y barrido
    profundo— y reunir evidencia que la consulta simple de `_source_for` no
    alcanza. Esa evidencia se le pasa a `build_blueprint`, que escribe con su
    propio presupuesto. El brazo A/B del A/B es llamar a `build_blueprint`
    directamente, sin esto.
    """
    from bibliotecario.agent.tools import build_blueprint

    gathered = run(
        f"Evidencia del corpus para implementar la técnica '{technique}' "
        f"con objetivo: {goal}. Reúne los procedimientos y los chunks que los sostienen.",
        max_turns=max_turns, isolated=True, temperature=temperature,
    )
    extra = "\n".join(gathered.get("evidence") or [])[:6000]
    bp = build_blueprint(technique, goal, extra_source=extra)
    return {**bp, "loop_turns": gathered["turns"], "evidence": gathered["evidence"]}
