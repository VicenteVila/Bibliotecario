"""HITO16 — tests puros del juez B-2 (sin red, sin motor).

Rúbrica ρ real, parse estricto, agregación con tope, fórmula congelada,
prompt, búsqueda de ids para U5 y los gates U1-U4 del runner.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "evals" / "preflight"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PREFLIGHT) not in sys.path:
    sys.path.insert(0, str(PREFLIGHT))

import juez_b2
import pi_schema
import run_fase2_b2 as runner

RUB = juez_b2.cargar_rubrica("platformer-juego")


def _raw(items: list[dict]) -> str:
    return json.dumps({"items": items}, ensure_ascii=False)


def _filas(score=1.0, just="visible en frame", omite=None, extra=None,
           score_override=None) -> list[dict]:
    filas = []
    for it in RUB["items"]:
        if omite and it["id"] == omite:
            continue
        filas.append({
            "id": it["id"],
            "score": score_override.get(it["id"], score)
            if score_override else score,
            "justificacion": just,
        })
    if extra:
        filas.append({"id": extra, "score": 1, "justificacion": "x"})
    return filas


# ---------------------------------------------------------------- rubrica

def test_rubrica_real_valida_y_congelada():
    errs = juez_b2.validar_rubrica(RUB)
    assert errs == []
    assert len(RUB["items"]) <= 24
    assert len(RUB["items"]) >= 15
    assert RUB["pesos"] == juez_b2.PESOS == {"D": 0.35, "V": 0.15, "A": 0.35}
    ids = [i["id"] for i in RUB["items"]]
    assert len(ids) == len(set(ids))
    for c in ("D", "V", "A"):
        assert any(i["categoria"] == c for i in RUB["items"])


def test_rubrica_d_tiene_sensibles_a_movimiento():
    # base del gate U4: ≥3 ítems D/A que caen sin input (idle)
    sensibles = [i for i in RUB["items"]
                 if i["id"] in ("B2-D-01", "B2-D-02", "B2-D-04",
                                "B2-A-03", "B2-A-04")]
    assert len(sensibles) >= 3


def test_validar_rubrica_rechaza_id_malformado():
    doc = json.loads(json.dumps(RUB))
    doc["items"][0]["id"] = "x"
    assert any("malformado" in e for e in juez_b2.validar_rubrica(doc))


def test_validar_rubrica_rechaza_muchos_items():
    doc = json.loads(json.dumps(RUB))
    extra = json.loads(json.dumps(doc["items"][0]))
    while len(doc["items"]) < 25:
        extra["id"] = f"B2-D-{len(doc['items']):02d}"
        doc["items"].append(json.loads(json.dumps(extra)))
    assert any("> 24" in e for e in juez_b2.validar_rubrica(doc))


# ---------------------------------------------------------------- parse

def test_parsear_bueno():
    got = juez_b2.parsear(_raw(_filas()), RUB)
    assert got is not None
    assert len(got["items"]) == len(RUB["items"])
    assert all(v["score"] == 1.0 for v in got["items"].values())


def test_parsear_con_prosa_y_fences():
    raw = ("razono un poco\n```json\n" + _raw(_filas()) + "\n```\ny listo")
    assert juez_b2.parsear(raw, RUB) is not None


def test_parsear_rechaza_id_faltante():
    assert juez_b2.parsear(_raw(_filas(omite="B2-D-03")), RUB) is None


def test_parsear_rechaza_id_extra():
    assert juez_b2.parsear(_raw(_filas(extra="B2-X-99")), RUB) is None


def test_parsear_rechaza_score_fuera_de_anclaje():
    assert juez_b2.parsear(
        _raw(_filas(score_override={"B2-D-01": 0.7})), RUB) is None


def test_parsear_rechaza_justificacion_vacia():
    assert juez_b2.parsear(_raw(_filas(just="   ")), RUB) is None


def test_parsear_rechaza_json_roto():
    assert juez_b2.parsear("{\"items\": [", RUB) is None


# ---------------------------------------------------------------- agregar

def test_agregar_todos_unos():
    parsed = juez_b2.parsear(_raw(_filas()), RUB)
    cats = juez_b2.agregar(parsed, RUB)
    assert cats["D"] == 1.0
    assert cats["V"] < 1.0  # V-01 y V-05 tope 0.5
    assert cats["Score_B2"] == round(
        0.35 * cats["D"] + 0.15 * cats["V"] + 0.35 * cats["A"], 4)


def test_agregar_aplica_tope_por_item():
    # V-01 tope 0.5: score 1 del juez cuenta 0.5
    parsed = juez_b2.parsear(_raw(_filas()), RUB)
    cats = juez_b2.agregar(parsed, RUB)
    v_items = [it for it in RUB["items"] if it["categoria"] == "V"]
    esperado = sum(min(1.0, float(it.get("tope", 1.0)))
                   for it in v_items) / len(v_items)
    assert abs(cats["V"] - esperado) < 1e-9


def test_agregar_cero_total():
    parsed = juez_b2.parsear(_raw(_filas(score=0)), RUB)
    cats = juez_b2.agregar(parsed, RUB)
    assert cats == {"D": 0.0, "V": 0.0, "A": 0.0, "Score_B2": 0.0}


# ---------------------------------------------------------------- formula

def test_score_completo_build_cero_da_cero():
    assert juez_b2.score_completo(0.0, 1.0, 0.9) == 0.0


def test_score_completo_fórmula_congelada():
    # BUILD × (0.15·M_B1 + Score_B2)
    assert juez_b2.score_completo(1.0, 1.0, 0.5) == 0.65
    assert juez_b2.score_completo(1.0, 0.0, 0.4) == 0.4
    assert juez_b2.score_completo(1.0, 0.8, 0.5) == 0.62


# ---------------------------------------------------------------- prompt

def test_montar_prompt_contiene_todo():
    p = juez_b2.montar_prompt(RUB, 14)
    for it in RUB["items"]:
        assert it["id"] in p
        assert it["texto"] in p
    assert "FRAMES: 14 imágenes" in p
    assert "Tu ÚNICA salida" in p
    assert "0.5" in p


def test_prompt_no_expone_ruzbrica_al_workspace():
    # la ρ vive bajo evals/, nunca bajo EG (U5)
    ruta = str(juez_b2.RUBRICAS.resolve())
    assert "EG" not in ruta.replace(str(ROOT.resolve()), "")


# ---------------------------------------------------------------- U5 / Π

def test_buscar_ids_detecta_y_no_falsa(tmp_path):
    (tmp_path / "a.gd").write_text("var x = 1 # B2-D-01\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("nada raro aqui\n", encoding="utf-8")
    hits = runner.buscar_ids(tmp_path)
    assert len(hits) == 1 and "B2-D-" in hits[0]
    assert runner.buscar_ids(tmp_path / "vacio") == [] or not (
        tmp_path / "vacio").exists()


def test_duracion_ms_con_eventos_vacios():
    assert pi_schema.duracion_ms({"version": 1, "fps": 60,
                                  "events": []}) == 0


# ---------------------------------------------------------------- gates

def _eval_todo(score=1.0, sb2=0.9, intentos=1) -> dict:
    parsed = juez_b2.parsear(_raw(_filas(score=score)), RUB)
    cats = juez_b2.agregar(parsed, RUB)
    return {"items": {k: v["score"] for k, v in parsed["items"].items()},
            "justificaciones": {k: v["justificacion"]
                                for k, v in parsed["items"].items()},
            "intentos": intentos,
            **({"Score_B2": cats["Score_B2"], "D": cats["D"],
                "V": cats["V"], "A": cats["A"]} if sb2 is None
               else {"Score_B2": sb2, "D": score, "V": score, "A": score})}


def test_gate_u1_ok_y_falla():
    ok, _ = runner.gate_u1(_eval_todo(intentos=1), len(RUB["items"]))
    assert ok
    ok, _ = runner.gate_u1(_eval_todo(intentos=3), len(RUB["items"]))
    assert not ok
    ok, _ = runner.gate_u1({"error": "x"}, len(RUB["items"]))
    assert not ok


def test_gate_u2_negro_puro_pasa_negro_malo_falla():
    pres = {it["id"]: 0 for it in RUB["items"] if it.get("presencia")}
    otros = {it["id"]: 0 for it in RUB["items"]
             if not it.get("presencia")}
    e_ok = {"items": {**pres, **otros}, "Score_B2": 0.05}
    ok, _ = runner.gate_u2(e_ok, RUB)
    assert ok
    # un ítem de presencia con 1 (juez caucho) → falla
    e_caucho = {"items": {**pres, **otros, "B2-V-02": 1}, "Score_B2": 0.05}
    ok, _ = runner.gate_u2(e_caucho, RUB)
    assert not ok
    # Score_B2 del negro demasiado alto → falla
    e_alto = {"items": {**pres, **otros}, "Score_B2": 0.31}
    ok, _ = runner.gate_u2(e_alto, RUB)
    assert not ok


def test_gate_u3_estabilidad():
    base = _eval_todo(sb2=0.50)
    cerca = _eval_todo(sb2=0.55)
    lejos = _eval_todo(sb2=0.65)
    ok, _ = runner.gate_u3(base, cerca)
    assert ok
    ok, _ = runner.gate_u3(base, lejos)
    assert not ok
    # delta de categoría > 0.15 aunque el score total esté cerca
    cat_lejos = dict(cerca)
    cat_lejos["D"] = base["D"] - 0.20
    cat_lejos["Score_B2"] = base["Score_B2"]
    ok, _ = runner.gate_u3(base, cat_lejos)
    assert not ok


def test_gate_u4_orden_default_sobre_idle():
    d = _eval_todo(sb2=0.55)
    i = _eval_todo(score=0.0, sb2=0.10)
    ok, _ = runner.gate_u4(d, i)
    assert ok
    ok, _ = runner.gate_u4(i, d)
    assert not ok
    # diferencia insuficiente
    i2 = _eval_todo(score=0.0, sb2=0.50)
    ok, _ = runner.gate_u4(d, i2)
    assert not ok


# ---------------------------------------------------------------- evaluar

def test_evaluar_reintenta_5xx_y_reporta_intentos(monkeypatch):
    # HITO16 §4: reintento ≤2 en 5xx; str(HTTPError) no contiene "HTTP 5"
    import urllib.error
    llamadas = []

    def _503(prompt, frames):
        llamadas.append(1)
        raise urllib.error.HTTPError("https://x", 503, "Unavailable",
                                     {}, None)

    monkeypatch.setattr(juez_b2, "_llamar", _503)
    monkeypatch.setattr(juez_b2.time, "sleep", lambda _s: None)
    r = juez_b2.evaluar(RUB, [])
    assert "error" in r and r["intentos"] == 2
    assert len(llamadas) == 2


def test_evaluar_error_no_reintentable_una_llamada(monkeypatch):
    import urllib.error
    llamadas = []

    def _400(prompt, frames):
        llamadas.append(1)
        raise urllib.error.HTTPError("https://x", 400, "Bad Request",
                                     {}, None)

    monkeypatch.setattr(juez_b2, "_llamar", _400)
    monkeypatch.setattr(juez_b2.time, "sleep", lambda _s: None)
    r = juez_b2.evaluar(RUB, [])
    assert "error" in r and r["intentos"] == 1
    assert len(llamadas) == 1
