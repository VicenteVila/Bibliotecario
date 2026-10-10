"""Eval end-to-end: loop completo + juez pineado.

Métricas corregidas (F0 del plan de evaluación):

- El juez NO es el mismo modelo que el agente (ver evals/judge.py): usa
  gpt-oss-20b, familia distinta. Antes ambos usaban la misma generate(), así que
  el juez se auto-favorecía.
- Una pregunta cuyo juez no parsea cuenta como 0, NO se descarta de la media.
  Antes `scored = [r for r in rows if r["judge"]]` las eliminaba en silencio: el
  juez falla justo con respuestas largas (las difíciles), así que la media salía
  inflada. Ahora se reporta n_total, n_scored y n_errors por separado.
- La provenance se mide contra `answerable_docs` (lista), no contra un único
  doc_id: una pregunta multi-paper no puede dar 1.0 con un solo campo.
  Se separan precisión de cita y cobertura del gold.
- Se guardan los tokens usados, para poder decidir si el barrido profundo
  (que mete decenas de miles de caracteres) sale rentable. Esto incluye los del
  AGENTE, no solo los del juez: sin coste del agente no se puede decidir nada.
- Las preguntas `unanswerable` no se puntúan con la rúbrica 1-5: se pide al juez
  que decida si el agente se abstuvo o inventó. Una abstención no es un "1".

Uso:
  python evals/eval_end2end.py --turns 5
  python evals/eval_end2end.py --ids wiki-2,tce-3 --turns 5
  python evals/eval_end2end.py --golden golden_blind_qa.jsonl --workers 4 \
      --out result_blind_r1.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

EVALS = Path(__file__).parent
sys.path.insert(0, str(EVALS.parent))

import bibliotecario.core.llm as LLM
from bibliotecario.agent import loop as LOOP
from bibliotecario.coevolve import task_pool
from bibliotecario.harness.runtime import get_harness
from bibliotecario.ingest import citations_format as CITE_FMT
from evals.judge import JUDGE_MODEL, judge, judge_abstention


def save(out, agg=None, path: Path | None = None, meta: dict | None = None):
    (path or (EVALS / "result_end2end.json")).write_text(
        json.dumps({"meta": meta or {}, "aggregate": agg or {}, "rows": out},
                   indent=1, ensure_ascii=False),
        encoding="utf-8")


def gold_docs(q: dict) -> list[int]:
    """Documentos que la pregunta necesita. Acepta doc_id o answerable_docs."""
    if q.get("answerable_docs"):
        return list(q["answerable_docs"])
    return [q["doc_id"]] if "doc_id" in q else []


# Lenguaje de abstención. Distingue "no está en el corpus" de "lo respondí".
# Hace falta en las DOS direcciones: si el agente se abstiene en una pregunta
# respondible porque no recuperó el chunk, el fallo es de retrieval y no debe
# mezclarse con la calidad de la respuesta. En la run 1 abstain_rate fue 1.0
# sobre las no respondibles y aun así 2 de 7 abstenciones eran falsas.
_ABSTAIN_WORDS = re.compile(
    r"(no se encontr[oó]|not found|no .{0,25}evidencia espec|"
    r"does not (explicitly )?(report|mention|state)|"
    r"no (encuentra|aparece|consta|se menciona|indica)|"
    r"La evidencia disponible no|insufficient evidence|could not find|"
    r"no (hay|hay datos|dice|consta) (evidencia|datos|informaci[oó]n))", re.IGNORECASE)


def looks_abstained(answer: str) -> bool:
    return bool(_ABSTAIN_WORDS.search(answer or ""))


# Umbral de éxito de una run: 0.75 = (4-1)/4, la frontera que la rúbrica del juez
# marca entre "correcta" (4) y "parcialmente correcta" (3). Un 3 significa
# literalmente "falta O altera el dato principal pedido", así que para un agente
# de investigación no es un acierto: aceptarlo certificaría como buena una
# respuesta que se equivoca en lo que se preguntó.
# Medido sobre 313 runs (media 4.23): juez>=3 da p=0.847 (var 0.130) y juez>=2
# da p=0.971 (var 0.028, saturado: task_stats daría p̄~1 siempre y el selector
# de varianza de Task-CoEvolve no tendría nada que elegir). juez>=4 da
# p=0.725, var 0.199. No se eligió juez>=5 aunque su varianza es mayor (0.216)
# porque rechazaría como fallo una respuesta que la rúbrica define como correcta.
SUCCESS_MIN_SCORE = 0.75


def run_score(row: dict) -> float | None:
    """Score 0-1 de la run, o None si no hay dato. Una sola escala para dos poblaciones.

    Respondibles: (judge-1)/4 con clamp. El juez devuelve 0 en fallback, y sin
    clamp eso daría -0.25: un fallo de infraestructura no puede puntuar por
    debajo del mínimo de la escala.
    No respondibles: 1.0 si se abstuvo, 0.0 si fabricó. Meter una abstención en
    la rúbrica 1-5 la castigaría por comportarse bien, que es el error que este
    harness ya cometió.
    Infraestructura: None, igual que aggregate la saca de la media. NULL significa
    "nadie lo midió", no "fue 0".
    """
    if row.get("infra_error"):
        return None
    if row.get("unanswerable"):
        abst = row.get("abstained")
        return None if abst is None else (1.0 if abst else 0.0)
    judge = row.get("judge")
    if judge is None:
        return None
    return min(1.0, max(0.0, (judge - 1) / 4))


def run_success(row: dict) -> bool | None:
    """Si la run hizo lo correcto. None si no hay dato (no se registra outcome).

    En respondibles exige además cita. La rúbrica prohíbe al juez valorarlas
    ("No premies la longitud, el estilo ni las citas"), así que es una dimensión
    que el juez no puede ver por diseño, y una respuesta correcta sin atribución
    no es auditable en un agente de investigación. Coste medido: 1 run de 313.
    """
    score = run_score(row)
    if score is None:
        return None
    if score < SUCCESS_MIN_SCORE:
        return False
    if row.get("unanswerable"):
        return True
    return bool(row.get("answer_has_cite"))


def citation_metrics(q: dict, answer: str, evidence: list) -> dict:
    """Precisión y cobertura de citas contra los documentos que la pregunta pide.

    Antes esto era una sola cifra contra un doc_id, lo que punishaba a las
    preguntas multi-paper por construcción (techo de 0.5).
    """
    gold = set(gold_docs(q))
    cites = CITE_FMT.parse_citations(answer)
    cited_docs = {d for d, _ in cites}
    ev_docs = {e.get("doc_id") for e in evidence if isinstance(e, dict)}
    all_docs = cited_docs | ev_docs
    precision = len(cited_docs & gold) / len(cited_docs) if cited_docs else 0.0
    coverage = len(cited_docs & gold) / len(gold) if gold else 0.0
    stray = len(all_docs - gold)
    return {"cite_precision": round(precision, 3), "cite_coverage": round(coverage, 3),
            "stray_docs": stray, "answer_cites": len(cites), "n_evid": len(evidence),
            "cite_ids": [f"{d}:{i}" for d, i in cites],
            "evidence_ids": [f"{e['doc_id']}:{e.get('chunk_idx')}" for e in evidence
                             if isinstance(e, dict) and e.get("chunk_idx") is not None]}


_INFRA_MARKERS = ("504", "502", "503", "500", "429", "408", "timeout", "timed out",
                  "gateway", "bad gateway", "sobrecargad", "overloaded", "high demand",
                  "rate limit", "todos los proveedores", "sin proveedores", "aparcado",
                  "dead", "conexion", "connection")


def _classify_run_error(e: Exception) -> str:
    """Distingue caida de infraestructura de error de programacion.

    Un 504 o un tier agotado son ruido de la red: la fila se marca `infra_error` y
    aggregate la saca de la media. Un TypeError o un AttributeError son un bug
    nuestro, y camuflado de "infraestructura" pasaria desapercibido mientras se
    pierde una pregunta. Estos ultimos relanzan: una run con un bug dentro no es
    un dato, es un error de quien la lanza.
    """
    msg = f"{type(e).__name__}: {str(e)[:160]}"
    bajo = msg.lower()
    if isinstance(e, (TypeError, AttributeError, NameError, ImportError,
                      SyntaxError, KeyError, IndexError)):
        raise e
    if not any(m in bajo for m in _INFRA_MARKERS):
        raise e
    return msg


def run_one(q: dict, turns: int, temperature: float | None = None,
            task_id: int | None = None) -> dict:
    """Ejecuta una pregunta y devuelve su fila. No lanza: todo error va a la fila.

    Trampa: el pineo de proveedor (LLM_PROVIDERS) lo pone main(), no este
    módulo. Si se llama a run_one() desde un script suelto sin fijar la variable,
    el round-robin usa Gemini y la fila se mezcla con los runs de la eval. Para
    eso está --provider en la CLI; desde código, fija LLM_PROVIDERS antes.

    `task_id` es el validation_task que esta pregunta representa: con él, cada
    run deja un outcome en task_outcomes y task_stats() deja de dar 0.5 por
    defecto. Es opcional porque los dobles de test no lo tienen.
    """
    LLM.reset_usage()
    t0 = time.time()
    infra_error = None
    # Solo se pasa `temperature` si se pidio: con None la llamada a LOOP.run es
    # identica a la de siempre y los dobles que la sustituyen siguen valiendo.
    temp_kw = {} if temperature is None else {"temperature": temperature}
    try:
        # isolated=True: sin lecciones. key_insights ya no lleva la pregunta
        # (arreglado en _trajectory_fingerprint), pero sin aislamiento una fila
        # del batch hereda las lecciones de la anterior y el resultado pasa a
        # depender del orden en que los hilos dejan filas, que es otra forma de
        # que la medida no sea repetible.
        r = LOOP.run(q["question"], max_turns=turns, isolated=True, **temp_kw)
    except Exception as e:
        infra_error = _classify_run_error(e)
        r = {"answer": "", "evidence": [], "turns": 0, "error": infra_error}
    usage = LLM.usage_totals()
    ans = r.get("answer", "")
    evidence = r.get("evidence", [])
    cm = citation_metrics(q, ans, evidence)
    fallback = ans.startswith(("(presupuesto agotado)", "(extractivo)"))
    unanswerable = bool(q.get("unanswerable"))

    # Caída de infraestructura = el proveedor no llegó a responder, no que el
    # agente respondiera mal. Se marca en la fila y aggregate la saca de la media:
    # si no, un 504 se puntúa 0 y baja judge_mean como si fuera culpa del agente.
    # Pasó de verdad en r2: pg-b4 y tce-b6 con answer="" y judge=0, y
    # n_judge_errors=0 porque 0 no es None. La media 4.229 estaba sesgada abajo
    # por ruido de red y no habia forma de verlo.
    if infra_error is None and not ans and not (fallback or unanswerable):
        infra_error = "respuesta vacia sin error reported (posible agotamiento de tier)"
    # Un fallback por presupuesto es degradacion conocida del harness, tambien
    # infraestructura: la respuesta no la escribio el agente.
    if fallback:
        infra_error = infra_error or f"fallback: {ans[:60]}"

    if unanswerable:
        # Puntuarla de 1 a 5 no tiene sentido: lo que se mide es si se abstuvo.
        j = ({"abstained": False, "fabricated_value": None, "justification": "sin respuesta",
              "usage": {}, "error": "fallback sin LLM"}
             if (fallback or not ans)
             else judge_abstention(q["question"], ans))
    elif infra_error:
        # No se llama al juez: no hay respuesta que juzgar. judge=None lo saca de
        # la media y n_infra lo hace visible. Antes era judge=0, indistinguible.
        j = {"score": None, "verdict": "omitido (fallo de infraestructura)", "error": infra_error,
             "model": JUDGE_MODEL, "usage": {}}
    elif fallback or not ans:
        j = {"score": 0, "verdict": "omitido (fallback sin LLM)", "error": None,
             "model": JUDGE_MODEL, "usage": {}}
    else:
        j = judge(q["question"], q["reference"], ans)

    row = {"id": q["id"], "doc_id": q.get("doc_id"), "difficulty": q.get("difficulty"),
           "unanswerable": unanswerable, "turns": r.get("turns"), **cm,
           "answer_has_cite": CITE_FMT.has_citation(ans),
           "truncated": ans.rstrip().endswith("[…truncado]"),
           "judge": j.get("score"), "judge_error": j.get("error"),
           "infra_error": infra_error,
           "judge_model": j.get("model"), "judge_usage": j.get("usage"),
           "abstained": j.get("abstained"),
           "fabricated_value": j.get("fabricated_value"),
           "looks_abstained": looks_abstained(ans),
           "fallback": fallback, "latency_s": round(time.time() - t0),
           "agent_usage": usage,
           "answer": ans}  # respuesta completa: los 400 chars impedían auditar

    # El loop no tiene juez, así que el score de harness_runs solo puede
    # escribirse aquí. Sin run_id no hay fila que puntuar y NO se toca la BD:
    # es lo que separa un test de una escritura en producción.
    run_id = r.get("run_id")
    if run_id:
        get_harness().record_score(
            run_id, run_score(row),
            {"eval_id": row["id"], "score_source": "abstention" if unanswerable else "judge",
             # Se graba lo que este proceso pidio, no lo que meta dice pedir: era
             # exactamente la confusion que escondio el bug (--temperature aparecia
             # en meta con 0.0 mientras los dos brazos corrian a 0.2). None =
             # sin fijar, o sea el default del backend en llm.py.
             "temperature": temperature})
    if task_id is not None:
        # None = sin dato (infra o juez no parseable): no se registra outcome y
        # la tarea sigue sin observar, que es como task_stats aplica el prior 0.5.
        ok = run_success(row)
        if ok is not None:
            task_pool.record_outcome(task_id, ok, run_id or "")

    return {**row, "run_id": run_id}


def aggregate(out: list, turns: int, retries: int) -> dict:
    """Agregados. Las no respondibles NO entran en judge_mean.

    Meter abstenciones en la media de 1-5 baja la nota por comportarse bien, y
    es justo el error que este harness ya cometió una vez con los judges no
    parseables. Cada grupo se reporta por separado.
    """
    ans_rows = [r for r in out if not r.get("unanswerable")]
    un_rows = [r for r in out if r.get("unanswerable")]
    # Fallos de infraestructura fuera de las poblaciones que se promedian. Un 504
    # no es una respuesta mala del agente: meterlo en la media lo baja como si lo fuera.
    infra = [r for r in ans_rows if r.get("infra_error")]
    ans_rows = [r for r in ans_rows if not r.get("infra_error")]
    un_infra = [r for r in un_rows if r.get("infra_error")]
    un_rows = [r for r in un_rows if not r.get("infra_error")]
    na, nu = len(ans_rows), len(un_rows)

    def mean(xs):
        return round(sum(xs) / len(xs), 3) if xs else None

    # Las claves existen siempre,(None si no aplica): que un consumidor lea
    # judge_mean y se KeyError porque no había respondibles es una forma
    # innecesaria de romperse.
    agg = {"n": len(out), "n_answerable": na, "n_unanswerable": nu,
           "judge_model": JUDGE_MODEL, "turns": turns, "retries": retries,
           "judge_mean": None, "n_scored": 0, "n_judge_errors": 0,
           "n_infra": len(infra) + len(un_infra), "infra_error_ids": [r["id"] for r in infra + un_infra],
           "cite_precision_mean": None, "cite_coverage_mean": None,
           "answer_cite_rate": None, "by_difficulty": None,
           "abstain_rate": None, "n_abstain_decided": 0, "n_abstain_errors": 0,
           "n_fabricated": 0, "latency_median_s": None,
           "false_abstention_rate": None, "n_false_abstention": 0,
           "answer_rate_on_answerable": None, "false_abstention_ids": []}

    if na:
        scores = [0 if r["judge"] is None else r["judge"] for r in ans_rows]
        errs = sum(1 for r in ans_rows if r["judge"] is None)
        agg.update({
            "judge_mean": mean(scores),               # judge no parseable = 0
            "n_scored": na - errs, "n_judge_errors": errs,
            "cite_precision_mean": mean([r["cite_precision"] for r in ans_rows]),
            "cite_coverage_mean": mean([r["cite_coverage"] for r in ans_rows]),
            "answer_cite_rate": mean([1.0 if r["answer_has_cite"] else 0.0 for r in ans_rows]),
            "by_difficulty": {d: mean([0 if r["judge"] is None else r["judge"]
                                       for r in ans_rows if r["difficulty"] == d])
                              for d in ("facil", "media", "dificil")},
        })
    if nu:
        decided = [r for r in un_rows if r["abstained"] is not None]
        agg.update({
            "abstain_rate": mean([1.0 if r["abstained"] else 0.0 for r in decided]),
            "n_abstain_decided": len(decided), "n_abstain_errors": nu - len(decided),
            # is not None y no truthiness: una cifra inventada de 0 es tan
            # inventada como un 2.7. Contando por verdad, pg-b8 daba "0" y
            # pasaba por abstención limpia.
            "n_fabricated": sum(1 for r in un_rows if r.get("fabricated_value") is not None),
        })
    if na:
        # Abstención sobre preguntas respondibles: no es una virtud, es retrieval
        # fallido. Se mide aparte para no leer el abstain_rate como una skill.
        fa = [r for r in ans_rows if r.get("looks_abstained")]
        agg.update({
            "false_abstention_rate": round(len(fa) / na, 3),
            "n_false_abstention": len(fa),
            "answer_rate_on_answerable": round(1 - len(fa) / na, 3),
            "false_abstention_ids": [r["id"] for r in fa],
        })
    if out:
        # Si solo hay no respondibles, la mediana sale de esas filas y no de None.
        src = ans_rows or out
        agg["latency_median_s"] = sorted(r["latency_s"] for r in src)[len(src) // 2]
    agg.update({
        "truncated": sum(1 for r in out if r["truncated"]),
        "fallbacks": sum(1 for r in out if r["fallback"]),
        "agent_tokens_total": sum(r["agent_usage"].get("total_tokens", 0) for r in out),
        "agent_calls_total": sum(r["agent_usage"].get("calls", 0) for r in out),
        "agent_calls_tokens_unknown": sum(r["agent_usage"].get("calls_tokens_unknown", 0)
                                          for r in out),
        # Qué modelos respondieron de verdad. Si esto mezcla dos modelos, la run
        # está contaminada aunque la media parezca bien.
        "agent_models": sorted({m for r in out for m in r["agent_usage"].get("models", [])}),
        "judge_tokens_total": sum((r.get("judge_usage") or {}).get("total_tokens", 0) or 0
                                  for r in out),
    })
    return agg


def _wrap_generate(retries_default: int, gen):
    """Fija --retries y conserva cualquier otro kwarg, temperature incluida.

    El lambda original era `(p, max_tokens, retries)` y no aceptaba `temperature`:
    aunque main() la hubiera pasado, `generate(..., temperature=0.0)` reventaba con
    TypeError. Se tapaba con el otro bug (la rama paralela no pasaba temp_kw), que
    impedía que este llegara a ejecutarse nunca. Juntos, la consecuencia silenciosa
    fue que NINGUNA run del corpus llegó a fijar temperatura: todos los brazos
    corrieron a 0.2, el default del backend.
    """
    def _wrap(p, max_tokens=512, retries=None, **kw):
        return gen(p, max_tokens, retries_default if retries is None else retries, **kw)
    return _wrap


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--retries", type=int, default=1)
    ap.add_argument("--ids", default="", help="coma-separados, ej. wiki-1,tce-3 (para lotes)")
    ap.add_argument("--out", default="result_end2end.json")
    ap.add_argument("--golden", default="golden_qa.jsonl")
    ap.add_argument("--workers", type=int, default=1,
                    help="preguntas en paralelo (el sink de tokens es thread-local)")
    ap.add_argument("--run", default="", help="etiqueta de la run, va en el JSON")
    # Default 0.0, no None: medido. Con temperatura libre el agente fabrica en el
    # 51.6% de las no respondibles; a 0 baja al 33.9%. Pareado sobre los mismos 62
    # items, p exacto = 0.019, y no cuesta un token. El otro lado (24 respondibles)
    # no mostraba dano: 0 abstenciones falsas, 0 respuestas degeneradas, 0 truncados,
    # delta de judge -0.17 a 0.85 sigma.
    ap.add_argument("--temperature", type=float, default=0.0,
                    help="temperatura de sampling del agente. El default es 0 porque es "
                         "la unica palanca medida que funciona y es gratis. Con sampling "
                         "libre el ruido por item es sd 0.946 y la fabricacion de las no "
                         "respondibles sube del 33.9% al 51.6% (p=0.019).")
    ap.add_argument("--provider", default="",
                    help="fija proveedores (p.ej. nvidia). Sin esto el round-robin "
                         "reparte la run entre Nemotron y Gemini y se mezclan dos agentes")
    args = ap.parse_args()

    if args.provider:
        os.environ["LLM_PROVIDERS"] = args.provider

    # Un 504 transitorio en la NVIDIA no debe hacer que el resto de la run
    # conteste con Gemini: la media mezclaría dos modelos y seguiría pareciendo
    # válida. Con strict_fallback la pregunta queda como fallida y se ve.
    LOOP.STRICT_FALLBACK = True
    LOOP.generate = _wrap_generate(args.retries, LOOP.generate)

    rows = [json.loads(l) for l in (EVALS / args.golden).read_text().splitlines() if l.strip()]
    if args.ids:
        want = set(args.ids.split(","))
        rows = [q for q in rows if q["id"] in want]
    if args.limit:
        rows = rows[:args.limit]

    # Cada golden es una tarea de validación. Sin esto validation_tasks se
    # quedaba en 0 y Task-CoEvolve era código que nadie invocaba: task_stats()
    # no tenía nada de qué calcular p̄ y selector/estimator corrían sobre un
    # prior 0.5 vacío. Idempotente por golden_id, así que reanudar o repetir la
    # eval no duplica tareas ni reparte p̄ entre duplicados.
    task_ids: dict[str, int] = {}
    for q in rows:
        task_ids[q["id"]] = task_pool.get_or_add_task(
            q["question"], "qa", q.get("reference", ""), q["id"],
            json.dumps({"golden_id": q["id"], "difficulty": q.get("difficulty"),
                        "unanswerable": bool(q.get("unanswerable"))}, ensure_ascii=False))

    rp = EVALS / args.out
    out, done = [], set()
    if rp.exists():
        try:
            prev = json.loads(rp.read_text(encoding="utf-8"))
            out = prev.get("rows", [])
            # Las filas de infraestructura NO cuentan como terminadas: son ruido de
            # red, no mediciones. Si se dieran por buenas, reanudar las dejaria
            # para siempre y la media saldria con huecos que solo se ven en el
            # agregado. Reanudar es justamente el mecanismo para recuperar una run
            # a la que se le acabo el tier.
            out = [r for r in out if not r.get("infra_error")]
            done = {r["id"] for r in out}
        except ValueError:
            pass
    meta = {"golden": args.golden, "run": args.run, "judge_model": JUDGE_MODEL,
            "workers": args.workers, "providers": LLM._providers(),
            # El anclaje se lee del entorno, pero se graba aqui: una run sin
            # esta clave no se puede distinguir de una con anclaje al compararla.
            "anchor_grounding": LOOP.ANCHOR_GROUNDING,
            "temperature": args.temperature}

    # Ver run_one(): el kwarg solo viaja si se pidio una temperatura concreta.
    temp_kw = {} if args.temperature is None else {"temperature": args.temperature}
    todo = [q for q in rows if q["id"] not in done]
    results: dict[str, dict] = {}

    def emit(row):
        results[row["id"]] = row
        # Se persiste en orden del golden para que los ficheros sean comparables.
        # Las filas ya guardadas se conservan y las nuevas pisan por id: sin este
        # merge, reanudar una run interrumpida descarte las filas anteriores sin
        # avisar. Pasó de verdad: se perdieron 4 preguntas de la primera run.
        merged_map = {r["id"]: r for r in out}
        merged_map.update(results)
        merged = [merged_map[q["id"]] for q in rows if q["id"] in merged_map]
        save(merged, aggregate(merged, args.turns, args.retries), rp, meta)
        flag = ("abst=" + str(row["abstained"])) if row["unanswerable"] else f"judge={row['judge']}"
        print(f"{row['id']:8} prec={row['cite_precision']:.2f} {flag} "
              f"tok={row['agent_usage'].get('total_tokens', 0):6} "
              f"fb={row['fallback']} {row['latency_s']}s", flush=True)

    if args.workers > 1:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            # **temp_kw va AQUÍ y no solo en la rama serie: sin él, --temperature
            # se registraba en meta pero no se aplicaba nunca, y como todo se
            # ejecuta con --workers > 1, NINGUNA run del corpus llegó a fijar
            # temperatura. Medido: los dos brazos del contraste pareado corrieron
            # los dos a 0.2 (el default del backend), así que comparaban 0.2 con
            # 0.2 y la diferencia no era de temperatura.
            futs = {ex.submit(run_one, q, args.turns, task_id=task_ids[q["id"]],
                              **temp_kw): q for q in todo}
            for f in as_completed(futs):
                emit(f.result())
    else:
        for q in todo:
            emit(run_one(q, args.turns, task_id=task_ids[q["id"]], **temp_kw))

    merged_map = {r["id"]: r for r in out}
    merged_map.update(results)
    merged = [merged_map[q["id"]] for q in rows if q["id"] in merged_map]
    agg = aggregate(merged, args.turns, args.retries)
    save(merged, agg, rp, meta)
    print(f"\nn={agg['n']} (respondibles={agg['n_answerable']}, "
          f"no respondibles={agg['n_unanswerable']}) modelo_juez={JUDGE_MODEL}")
    if agg["n_answerable"]:
        print(f"judge={agg['judge_mean']} (n={agg['n_scored']}/{agg['n_answerable']}, "
              f"{agg['n_judge_errors']} errores)  por dificultad={agg['by_difficulty']}")
        print(f"cite_precision={agg['cite_precision_mean']} "
              f"cite_coverage={agg['cite_coverage_mean']} con_cita={agg['answer_cite_rate']}")
    if agg["n_answerable"]:
        print(f"abstencion_falsa={agg['false_abstention_rate']} "
              f"{agg['false_abstention_ids']} (respondidas={agg['answer_rate_on_answerable']})")
    if agg["n_unanswerable"]:
        print(f"abstain_rate={agg['abstain_rate']} "
              f"(decididas={agg['n_abstain_decided']}/{agg['n_unanswerable']}, "
              f"{agg['n_abstain_errors']} errores) inventadas={agg['n_fabricated']}")
    print(f"tokens_agente={agg['agent_tokens_total']} en {agg['agent_calls_total']} llamadas | "
          f"tokens_juez={agg['judge_tokens_total']} | latencia_mediana={agg['latency_median_s']}s")
    print(f"truncadas={agg['truncated']} fallbacks={agg['fallbacks']} -> {args.out}")


if __name__ == "__main__":
    main()