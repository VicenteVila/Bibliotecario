"""HITO16 §1.2 — juez multimodal B-2 sobre la rúbrica oculta ρ.

Scorer de Capa B-2 (GameCraft §3.2 / BENCHMARK_SPEC §5.2.1): los frames del
replay (2 fps, 1280×720) van al juez en orden cronológico; la rúbrica ρ va
SOLO en el prompt — el agente nunca la ve (hallazgo 13).

Congelados de HITO16 §3: modelo `gemini-3.1-flash-lite` (env Q1_*), temp 0,
plantilla PROMPT_B2 literal, JSON estricto por ítem, pesos 0.35/0.15/0.35,
fórmula Score = BUILD × (0.15·M_B1 + Score_B2).
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUBRICAS = HERE / "rubricas"

JUDGE_MODEL_B2 = os.environ.get("JUDGE_MODEL_B2", "gemini-3.1-flash-lite")
MAX_TOKENS = int(os.environ.get("B2_MAX_TOKENS", "2400"))
TEMPERATURE = 0.0
PESOS = {"D": 0.35, "V": 0.15, "A": 0.35}
SCORES_VALIDOS = (0.0, 0.5, 1.0)

PROMPT_B2 = """Eres un evaluador estricto de juegos 2D. Recibes los FRAMES de un replay \
(en orden cronológico, muestreo 2 fps, viewport 1280x720) y una RÚBRICA con ítems \
anclados. Evalúas SOLO lo observable en los frames: sin exploración, sin asumir \
lo que no se ve, sin puntuar intenciones ni código.

Reglas:
- Cada ítem se puntúa con EXACTAMENTE 0, 0.5 o 1 según sus anclajes.
- Respeta el tope indicado por ítem (nunca lo superes).
- Si algo no es observable en los frames, puntúa 0.
- Una justificación por ítem: una frase citando el frame/evidencia.

**Tu ÚNICA salida es el objeto JSON de abajo.** Sin prosa antes, sin prosa \
después, sin ```markdown. El razonamiento se come los tokens y el JSON se \
corta a mitad; eso ya ha pasado.

RÚBRICA (oculta para el agente):
%s

{"items": [{"id": "<id>", "score": <0|0.5|1>, "justificacion": "<frase>"}]}"""


def cargar_rubrica(tarea: str) -> dict:
    p = RUBRICAS / f"{tarea}.json"
    if not p.exists():
        raise SystemExit(f"rúbrica inexistente: {p}")
    doc = json.loads(p.read_text(encoding="utf-8"))
    errs = validar_rubrica(doc)
    if errs:
        raise SystemExit(f"rúbrica inválida ({p.name}): {errs}")
    return doc


def validar_rubrica(doc: dict) -> list[str]:
    errs: list[str] = []
    items = doc.get("items")
    if not isinstance(items, list) or not items:
        return ["sin items"]
    if len(items) > 24:
        errs.append(f"{len(items)} items > 24")
    pesos = doc.get("pesos") or {}
    if any(abs(float(pesos.get(c, 0)) - w) > 1e-9
           for c, w in PESOS.items()):
        errs.append(f"pesos {pesos} != {PESOS}")
    ids: set[str] = set()
    for it in items:
        iid = it.get("id", "")
        if not re.match(r"^B2-[DVA]-\d{2}$", iid):
            errs.append(f"id malformado ({iid!r})")
        if iid in ids:
            errs.append(f"id duplicado ({iid})")
        ids.add(iid)
        if it.get("categoria") not in PESOS:
            errs.append(f"{iid}: categoria {it.get('categoria')!r}")
        if it.get("aplica") not in ("max", "mean"):
            errs.append(f"{iid}: aplica {it.get('aplica')!r}")
        tope = it.get("tope")
        if not isinstance(tope, (int, float)) or tope not in (0.5, 1.0):
            errs.append(f"{iid}: tope {tope!r}")
        ancl = it.get("anclajes") or {}
        for a in ("0", "0.5", "1"):
            if not str(ancl.get(a, "")).strip():
                errs.append(f"{iid}: ancla {a} vacía")
    return errs


def montar_prompt(rubrica: dict, n_frames: int) -> str:
    """Plantilla congelada + ítems de ρ + aviso de orden de frames."""
    lineas = []
    for it in rubrica["items"]:
        tope = f" · tope {it['tope']}" if it.get("tope", 1.0) == 0.5 else ""
        lineas.append(
            f"- {it['id']} [{it['categoria']} · {it['aplica']}{tope}] "
            f"{it['texto']}\n    0 = {it['anclajes']['0']}\n"
            f"    0.5 = {it['anclajes']['0.5']}\n"
            f"    1 = {it['anclajes']['1']}")
    rub = "\n".join(lineas)
    return (PROMPT_B2 % rub
            + f"\n\nFRAMES: {n_frames} imágenes en orden cronológico t=0, "
              "0.5 s, 1 s, … (el primer frame es t=0).")


def _imagen_url(png: Path) -> str:
    b64 = base64.b64encode(png.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _endpoint() -> tuple[str, str]:
    base = os.environ.get("Q1_BASE_URL") or ""
    key = os.environ.get("Q1_API_KEY") or ""
    if not base or not key:
        raise SystemExit(
            "faltan Q1_BASE_URL/Q1_API_KEY (patrón declarado: "
            "export Q1_API_KEY=$(grep -m1 '^GEMINI_API_KEY=' .env | "
            "cut -d= -f2- | tr -d \"\\\"'\") && "
            "export Q1_BASE_URL=https://generativelanguage.googleapis.com/"
            "v1beta/openai/)")
    return base, key


def _llamar(prompt: str, frames: list[Path]) -> tuple[str, dict]:
    base, key = _endpoint()
    if not base.rstrip("/").endswith("openai"):
        base = base.rstrip("/") + "/v1beta/openai" if "v1beta" not in base \
            else base
    content: list[dict] = [{"type": "text", "text": prompt}]
    for f in frames:
        content.append({"type": "image_url",
                        "image_url": {"url": _imagen_url(f)}})
    payload = {"model": JUDGE_MODEL_B2, "temperature": TEMPERATURE,
               "max_tokens": MAX_TOKENS,
               "messages": [{"role": "user", "content": content}]}
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "User-Agent": "bibliotecario/1.0 (+https://github.com/"
                               "VicenteVila/Bibliotecario)"})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read().decode())
    choices = d.get("choices") or []
    msg = choices[0].get("message") if choices else None
    if not msg:
        raise RuntimeError(f"respuesta sin message: {str(d)[:300]}")
    return (msg.get("content") or ""), (d.get("usage") or {})


def parsear(raw: str, rubrica: dict) -> dict | None:
    """JSON estricto: ids exactos de ρ, scores en {0,0.5,1}, justif. no vacía."""
    if not raw:
        return None
    clean = re.sub(r"```(?:json)?|```", "", raw).strip()
    cand = clean if clean.startswith("{") else (
        clean[clean.find("{"):clean.rfind("}") + 1] if "{" in clean else "")
    if not cand:
        return None
    try:
        o = json.loads(cand)
    except (json.JSONDecodeError, ValueError):
        return None
    filas = o.get("items")
    if not isinstance(filas, list):
        return None
    esperados = [it["id"] for it in rubrica["items"]]
    vistos: list[str] = []
    out: dict[str, dict] = {}
    for f in filas:
        if not isinstance(f, dict):
            return None
        iid = str(f.get("id", ""))
        try:
            sc = float(f.get("score"))
        except (TypeError, ValueError):
            return None
        just = str(f.get("justificacion", "")).strip()
        if iid not in esperados or iid in out:
            return None
        if not any(abs(sc - s) < 1e-9 for s in SCORES_VALIDOS):
            return None
        if not just:
            return None
        out[iid] = {"score": sc, "justificacion": just[:400]}
        vistos.append(iid)
    if vistos != esperados:
        return None
    return {"items": out}


def evaluar(rubrica: dict, frames: list[Path],
            intentos: int = 2) -> dict:
    """U1: JSON estricto en ≤2 intentos. Devuelve items+usage o {'error'}."""
    prompt = montar_prompt(rubrica, len(frames))
    ult = ""
    usage: dict = {}
    for i in range(intentos):
        try:
            raw, usage_i = _llamar(prompt, frames)
        except Exception as e:  # red/endpoint: no es fallo de parseo
            ult = str(e)[:300]
            # HITO16 §4: reintento ≤2 por evaluación en 429/5xx/timeout.
            # Se mira e.code (urllib str() es "HTTP Error 503", que no
            # contiene "HTTP 5": con solo el string los 5xx no reintentaban).
            cod = getattr(e, "code", None)
            transitorio = ((isinstance(cod, int)
                            and (cod == 429 or 500 <= cod <= 599))
                           or "429" in ult or "HTTP 5" in ult
                           or "timed out" in ult)
            if transitorio:
                time.sleep(min(60, 5 * 2 ** i))
                continue
            return {"error": ult, "usage": usage, "intentos": i + 1}
        usage = usage_i or usage
        got = parsear(raw, rubrica)
        if got:
            got["usage"] = usage
            got["intentos"] = i + 1
            return got
        ult = f"no parseable: {(raw or '')[:200]}"
        time.sleep(2)
    # agotó intentos (5xx/parse en todos): reporta cuántos gastó para que
    # `llamadas` de U6 cuente los reintentos, no solo los éxitos.
    return {"error": ult, "usage": usage, "intentos": intentos}


def agregar(parsed: dict, rubrica: dict) -> dict:
    """tope por ítem → media por categoría (1 demo) → D/V/A → Score_B2.

    `aplica` (max/mean) es la regla de cruce ENTRE demos (§3, futuro
    multi-demo de GameCraft): con 1 demo colapsa y la categoría es la media
    simple de sus ítems ya topeados.
    """
    por_cat: dict[str, list[float]] = {c: [] for c in PESOS}
    for it in rubrica["items"]:
        sc = parsed["items"][it["id"]]["score"]
        sc = min(sc, float(it.get("tope", 1.0)))
        por_cat[it["categoria"]].append(sc)
    cats = {c: (sum(v) / len(v) if v else 0.0)
            for c, v in por_cat.items()}
    score_b2 = (PESOS["D"] * cats["D"] + PESOS["V"] * cats["V"]
                + PESOS["A"] * cats["A"])
    return {"D": round(cats["D"], 4), "V": round(cats["V"], 4),
            "A": round(cats["A"], 4),
            "Score_B2": round(score_b2, 4)}


def score_completo(build: float, m_b1: float, score_b2: float) -> float:
    """Score = BUILD × (0.15·M_B1 + Score_B2) — §5.2.1 congelado."""
    if not build:
        return 0.0
    return round(0.15 * m_b1 + score_b2, 4)
