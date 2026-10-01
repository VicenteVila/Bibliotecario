"""Pre-flight del juez: ¿el juez discrimina una respuesta buena de una mala?

Por qué esto va antes que todo lo demás (F0.7 del plan): si el juez no separa
casos que nosotros ya sabemos etiquetados, ninguna media que produzca significa
nada, y no tiene sentido gastar 3 runs × 40 preguntas en producir un número sin
señal.

Los casos son de preguntas que ya están en el golden set viejo. No son un
eval del agente: la etiqueta (buena/mala) la pusimos a mano leyendo la
referencia, así que el juez no tiene forma de "ganarse" la nota.

Uso:  python evals/judge_smoke.py
"""
from __future__ import annotations

import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals.judge import judge

# --- Preguntas y referencias (compartidas por el par bueno/malo de cada caso) ---

Q_WIKI = ("How many execution traces does WikiSkill sample per iteration, "
          "and how are they split?")
REF_WIKI = (
    "At each iteration the Wiki Maintainer applies stratified sampling of up to 8 traces: "
    "at most 5 failing traces (for root-cause analysis) and up to 3 passing traces (to "
    "identify effective strategies). Each execution log is capped at 15,000 characters "
    "prior to injection into the prompt.")

Q_TCE = ("When several harness candidates tie on the best estimated score, "
         "which one does Task-CoEvolve return?")
REF_TCE = (
    "Task-CoEvolve returns the earliest candidate that reaches the best score under the "
    "S-hat-max rule, following Lee et al. (2026): the first candidate reaching the best score "
    "is returned. Selecting the latest instead drops Naive from 45.2 to 41.8 at 7% sampling.")

Q_REAS = "What is the name of the file ReASearch uses to persist lessons across runs?"
REF_REAS = (
    "The agent maintains a persistent lessons.md file and is periodically prompted to read "
    "from or update it.")

Q_REAS_ACROSS = "How does ReASearch persist what it learns across runs?"
REF_REAS_ACROSS = (
    "The agent maintains a persistent lessons.md file and is periodically prompted to read "
    "from or update it. Lessons accumulate during a run and are reused in later runs, and "
    "the paper tests transferring them by seeding a new run with a lessons.md from a previous run.")

# --- Respuestas: las buenas repiten el dato; las malas lo contradicen ---

ANS_WIKI_OK = (
    "The Wiki Maintainer samples up to 8 execution traces per iteration, stratified into a "
    "maximum of 5 failing traces (used for root-cause analysis) and up to 3 passing traces. "
    "Each execution log is capped at 15,000 characters before injection into the prompt. [5:57]")

ANS_WIKI_BAD = (
    "WikiSkill samples 10 execution traces per iteration, split into 5 successful and 5 failed "
    "traces, selected randomly from the training set. [5:14]")

ANS_TCE_OK = (
    "It returns the candidate from the earliest iteration, literally the first candidate that "
    "reaches the best score, following the implementation of Lee et al. (2026). This is "
    "deliberately generous to the baselines: picking the latest would drop Naive from 45.2 to "
    "41.8 at 7% sampling. [3:39]")

ANS_TCE_BAD = (
    "It returns the harness candidate with the highest variance in task outcomes when "
    "candidates tie, since higher variance means more discriminative power among the tasks.")

ANS_REAS_OK = (
    "ReASearch keeps a persistent lessons.md file that the agent is periodically prompted to "
    "read from and update. Lessons accumulate during a run and are carried into later runs, "
    "and the paper even tests transferring them by seeding a new run with the lessons.md of a "
    "previous NanoGPT run. [4:10]")

ANS_REAS_BAD = (
    "ReASearch stores its learnings in a persistent JSON database called lessons.json, which "
    "is rewritten after each evaluation batch.")

# (nombre, etiqueta, (min,max) esperado, pregunta, referencia, respuesta)
CASES = [
    ("buena-1", "buena", (4, 5), Q_WIKI, REF_WIKI, ANS_WIKI_OK),
    ("buena-2", "buena", (4, 5), Q_TCE, REF_TCE, ANS_TCE_OK),
    ("buena-3", "buena", (4, 5), Q_REAS_ACROSS, REF_REAS_ACROSS, ANS_REAS_OK),
    ("mala-1", "mala", (1, 2), Q_WIKI, REF_WIKI, ANS_WIKI_BAD),
    ("mala-2", "mala", (1, 3), Q_TCE, REF_TCE, ANS_TCE_BAD),
    ("mala-3", "mala", (1, 2), Q_REAS, REF_REAS, ANS_REAS_BAD),
]


def main() -> int:
    rows = []
    for name, label, bounds, q, ref, ans in CASES:
        lo, hi = bounds
        j = judge(q, ref, ans)
        score = j["score"]
        ok = score is not None and lo <= score <= hi
        rows.append({"name": name, "label": label, "expected": [lo, hi], "score": score,
                     "ok": ok, "error": j["error"], "verdict": j["verdict"], "model": j["model"]})
        flag = "OK  " if ok else "MAL "
        err = f" err={str(j['error'])[:50]}" if j["error"] else ""
        print(f"{flag}{name:8} [{lo}-{hi}] score={score}{err}")
        print(f"     {j['verdict'][:110]}")

    good = [r["score"] for r in rows if r["label"] == "buena" and r["score"]]
    bad = [r["score"] for r in rows if r["label"] == "mala" and r["score"]]
    sep = (st.mean(good) - st.mean(bad)) if good and bad else None
    failures = [r["name"] for r in rows if not r["ok"]]

    print("\n--- Separacion ---")
    if good:
        print(f"buenas: media={st.mean(good):.2f} (n={len(good)})")
    if bad:
        print(f"malas:  media={st.mean(bad):.2f} (n={len(bad)})")
    if sep is not None:
        print(f"separacion = {sep:.2f}")
    print(f"modelo: {rows[0]['model']}")
    print(f"casos fuera de rango: {failures or 'ninguno'}")

    # Veredicto: el juez tiene que separar con holgura (>=3), no solo "no fallar".
    if failures:
        print("\nRESULTADO: INSUFICIENTE (el juez no respeta sus propios casos)")
        return 1
    if sep is None or sep < 3:
        print("\nRESULTADO: INSUFICIENTE (separa, pero por debajo de 3 puntos)")
        return 1
    print("\nRESULTADO: OK (el juez discrimina; se puede seguir con la eval)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())