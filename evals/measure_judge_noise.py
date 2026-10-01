"""Fase 1: cuanto de la varianza de las notas es del juez y cuanto del agente.

El agente responde de forma distinta en cada run, asi que la sd dentro de una
pregunta (0.709 sobre las 35 respondibles) mezcla dos cosas: que el agente
conteste distinto, y que el juez valore distinto lo mismo. Aqui se separa.

Metodo: se re-juzga la MISMA respuesta varias veces. Todo lo que varye entre
repeticiones de una misma respuesta es ruido del juez, por construccion. Y se
compara con la sd total observada en las runs.

No hace falta ni una llamada al agente: el juez solo recibe
(question, reference, answer), los dos primeros estan en el golden y el tercero
en la fila del resultado. Re-juzgar desde disco es identico a la llamada
original, byte a byte.

Uso:
    python evals/measure_judge_noise.py --reps 3
    python evals/measure_judge_noise.py --reps 3 --arms 0.2,0.0
Salida: evals/result_judge_noise.json
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

EVALS = Path(__file__).parent
sys.path.insert(0, str(EVALS.parent))

from evals.judge import judge

OUT = EVALS / "result_judge_noise.json"


def _load_runs(runs: list[int]) -> tuple[dict, dict]:
    golden = {json.loads(l)["id"]: json.loads(l) for l in
              (EVALS / "golden_blind_qa.jsonl").read_text().splitlines() if l.strip()}
    rows: dict[tuple[int, str], dict] = {}
    for r in runs:
        f = EVALS / f"result_blind_r{r}.json"
        if not f.exists():
            print(f"aviso: falta {f.name}, la run {r} se omite", file=sys.stderr)
            continue
        for row in json.loads(f.read_text())["rows"]:
            rows[(r, row["id"])] = row
    return golden, rows


def pick_sample(rows: dict, runs: list[int], n: int) -> list[dict]:
    """Muestra estratificada a proposito, no aleatoria.

    Se eligen categorias porque cada una responde a una pregunta distinta:
      - las caidas (respuesta vacia): el juez deberia dar 0 siempre. Si no, el
        juez es erratico y todo lo demas hay que mirarlo con recelo.
      - las deterministas (misma nota en las 3 runs): el juez es coherente
        cuando la respuesta coincide. Es el control positivo.
      - las inestables (nota distinta entre runs): es donde se concentra el
        sigma y donde hay que medirlo.
      - las estables: el otro extremo, por si el juez solo falla en lo dificil.
    """
    avail = sorted({(r, i) for (r, i) in rows if runs and r in runs})
    per_q: dict[str, list] = {}
    for (r, i) in avail:
        per_q.setdefault(i, []).append((r, rows[(r, i)]))

    buckets: dict[str, list[tuple[str, int, dict]]] = {
        "caida": [], "determinista_mala": [], "determinista_buena": [],
        "inestable": [], "estable": []}

    for i in sorted(per_q):
        trips = per_q[i]
        if trips[-1][1].get("unanswerable"):
            continue  # las no respondibles las juzga judge_abstention, no judge
        empty = [(r, row) for r, row in trips if not (row.get("answer") or "").strip()]
        if empty:
            # La caida se busca en CUALQUIER run, no en la ultima: pg-b4 y
            # tce-b6 se rompieron solo en la r2 y en la r3 contestaron bien, asi
            # que mirando la ultima no hay caida que ver. Y se detecta por el
            # texto vacio, no por la nota: el juez da 0 a una cadena vacia con
            # razon, asi que por nota caia en "estable".
            r, row = empty[0]
            buckets["caida"].append((i, r, row))
            continue
        sc = [row["judge"] for _, row in trips if row["judge"] is not None]
        if len(sc) < 2:
            continue
        sd = st.stdev(sc)
        r, row = trips[-1]
        if sd < 0.5:
            # Las deterministas que fallan son el control con mas poder
            # discriminante: si el juez es estable, wiki-b1=2 tiene que dar 2
            # las tres veces. Las que aciertan (5,5,5) casi no info.
            cat = "determinista_mala" if st.mean(sc) < 5 else "determinista_buena"
            buckets[cat].append((i, r, row))
        elif sd >= 1.0:
            buckets["inestable"].append((i, r, row))
        else:
            buckets["estable"].append((i, r, row))

    quota = {"caida": 2, "determinista_mala": 3, "determinista_buena": 2,
             "inestable": 10, "estable": 3}
    sample: list[dict] = []
    for cat, want in quota.items():
        for i, r, row in buckets[cat][:want]:
            sample.append({"key": f"{i}@r{r}", "id": i, "run": r, "categoria": cat,
                           "judge_original": row["judge"], "answer": row.get("answer") or ""})
    return sample[:n] if n else sample


def analyse(sample: list[dict], obs: list[dict], arms: list[float]) -> dict:
    by_arm: dict[float, dict] = {}
    for t in arms:
        calls = [o for o in obs if o["temperature"] == t]
        per_item: dict[str, list] = {}
        for c in calls:
            if c["score"] is not None:
                per_item.setdefault(c["key"], []).append(c["score"])
        # Varianza intra-item: todo lo que varye al repetir el juez sobre la MISMA
        # respuesta es ruido del juez, por construccion.
        sds = [st.stdev(v) for v in per_item.values() if len(v) >= 2]
        flat = [v for vs in per_item.values() for v in vs]
        agree = [len(set(vs)) == 1 for vs in per_item.values() if len(vs) >= 2]
        by_arm[t] = {
            "n_items": len(per_item),
            "n_calls": len([c for c in calls if c["score"] is not None]),
            "n_parse_errors": len([c for c in calls if c["score"] is None]),
            "judge_sd": round(st.mean(sds), 3) if sds else None,
            "judge_sd_max": round(max(sds), 3) if sds else None,
            "items_con_discrepancia": sum(1 for a in agree if not a),
            "frac_items_coherentes": round(sum(agree) / len(agree), 3) if agree else None,
            "media_notas": round(st.mean(flat), 3) if flat else None,
            "tokens": sum(c["usage"].get("total_tokens", 0) or 0 for c in calls),
        }
        if t == arms[0]:
            disagreements = [{"key": k, "notas": v} for k, v in per_item.items()
                             if len(set(v)) > 1]
            by_arm[t]["detalle_discrepancias"] = disagreements

    out = {"por_brazo": by_arm,
           "tokens_total": sum(a["tokens"] for a in by_arm.values())}
    return out


def main() -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3, help="repeticiones por respuesta")
    ap.add_argument("--arms", default="0.2,0.0", help="temperaturas a comparar")
    ap.add_argument("--n", type=int, default=20, help="tamaño de la muestra")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--runs", default="1,2,3")
    args = ap.parse_args()
    runs = [int(x) for x in args.runs.split(",") if x.strip()]
    arms = [float(x) for x in args.arms.split(",") if x.strip()]

    golden, rows = _load_runs(runs)
    sample = pick_sample(rows, runs, args.n)
    print(f"muestra: {len(sample)} respuestas x {args.reps} repeticiones x {len(arms)} brazos "
          f"= {len(sample) * args.reps * len(arms)} llamadas al juez")
    for c in ("caida", "determinista_mala", "determinista_buena", "inestable", "estable"):
        ids = [s["id"] for s in sample if s["categoria"] == c]
        print(f"  {c:15} {len(ids):2}  {', '.join(ids)}")

    obs: list[dict] = []
    if OUT.exists():  # reanudar: no volver a pagar lo ya pagado
        prev = json.loads(OUT.read_text())
        done = {(o["key"], o["temperature"], o["rep"]) for o in prev.get("observaciones", [])}
        obs = [o for o in prev.get("observaciones", []) if (o["key"], o["temperature"], o["rep"]) in done]
        print(f"reanudando: {len(obs)} observaciones ya existen")

    jobs = [(s, t, rep) for s in sample for t in arms for rep in range(args.reps)
            if (s["key"], t, rep) not in {(o["key"], o["temperature"], o["rep"]) for o in obs}]
    print(f"llamadas pendientes: {len(jobs)}")

    def one(job):
        s, t, rep = job
        g = golden[s["id"]]
        t0 = time.time()
        r = judge(g["question"], g["reference"], s["answer"], temperature=t)
        return {"key": s["key"], "id": s["id"], "run": s["run"], "categoria": s["categoria"],
                "temperature": t, "rep": rep, "score": r["score"], "verdict": r["verdict"],
                "error": r["error"], "judge_original": s["judge_original"],
                "usage": r.get("usage") or {}, "latency_s": round(time.time() - t0, 1)}

    if jobs:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            for k, o in enumerate(ex.map(one, jobs), 1):
                obs.append(o)
                OUT.write_text(json.dumps({"observaciones": obs}, indent=1, ensure_ascii=False))
                if k % 10 == 0 or k == len(jobs):
                    sc = [x["score"] for x in obs if x["score"] is not None]
                    print(f"  {k}/{len(jobs)} llamadas | notas hasta ahora: media "
                          f"{st.mean(sc):.2f}, min {min(sc)}, max {max(sc)}", flush=True)

    res = analyse(sample, obs, arms)
    res["muestra"] = [{k: v for k, v in s.items() if k != "answer"} for s in sample]
    res["reps"] = args.reps
    # Las observaciones crudas se conservan: sin ellas no se puede recalcular el
    # sd por item ni refinar el analisis sin volver a pagar las llamadas.
    res["observaciones"] = obs
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False))

    print("\n=== ruido del juez por brazo ===")
    for t, a in res["por_brazo"].items():
        print(f"  T={t}: sd={a['judge_sd']} (max {a['judge_sd_max']}) "
              f"coherentes={a['frac_items_coherentes']} "
              f"discrepancias={a['items_con_discrepancia']}/{a['n_items']} "
              f"parse_errors={a['n_parse_errors']} tokens={a['tokens']}")
    print(f"\ntokens totales: {res['tokens_total']}  ->  {OUT}")
    return res


if __name__ == "__main__":
    main()