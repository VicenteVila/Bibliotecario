"""Tests del piloto HITO19: Sens(x) puro, arnés con LLM falso, verificador,
fixtures y dictámen G0. Sin red: NINGÚN test llama al LLM real.
"""
from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from evals.sd_pilot import sens, tasks, verifier
from evals.sd_pilot.harness import (
    CANAL_CAP_PROMPT_TOKENS,
    FILE_BLOCK_RE,
    Cell,
    _safe_path,
    parse_action,
    parse_actions,
)
from evals.sd_pilot.run_pilot import (
    DIAG_MAX_TURNS,
    DIAG_TECHO_TOKENS,
    G0_TASKS,
    MARGEN_RECALIBRACION,
    PRESUPUESTO_BASE_16,
    TECHO_TOKENS,
    _veredicto_g0,
    estimar_tokens_celda,
    evaluar_diagnostico,
    evaluar_diagnostico_b,
    presupuesto_run,
    recalibrar_diagnostico_b,
)
from evals.sd_pilot.variants import VARIANT_NAMES, VARIANTS

REPO = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO / "evals" / "sd_pilot" / "skills_pack"


# ---------------------------------------------------------------- helpers --

class FakeLLM:
    """LLM falso: respuestas en secuencia (la última se repite)."""

    def __init__(self, *responses: str) -> None:
        self.responses = list(responses)
        self.i = 0
        self.prompts: list[str] = []

    def __call__(self, prompt: str, max_tokens: int) -> str:
        self.prompts.append(prompt)
        out = self.responses[min(self.i, len(self.responses) - 1)]
        self.i += 1
        return out


def mini_task(root: Path) -> Path:
    d = root / "mini"
    ws = d / "workspace"
    ws.mkdir(parents=True)
    (ws / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (ws / "pytest.ini").write_text(
        "[pytest]\npythonpath = .\ntestpaths = tests_public\n", encoding="utf-8")
    (ws / "tests_public").mkdir()
    (ws / "tests_public" / "test_calc.py").write_text(
        "from calc import add\n\n\ndef test_add_pos():\n    assert add(1, 1) == 2\n",
        encoding="utf-8")
    (d / "TASK.md").write_text("Haz que add sume de verdad.", encoding="utf-8")
    hid = d / "tests_hidden"
    hid.mkdir()
    (hid / "conftest.py").write_text(
        "import sys\nfrom pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parents[1]))\n",
        encoding="utf-8")
    (hid / "test_hidden.py").write_text(
        "from calc import add\n\n\ndef test_add_neg():\n    assert add(-2, -3) == -5\n"
        "\n\ndef test_add_cero():\n    assert add(0, 0) == 0\n", encoding="utf-8")
    ref = d / "reference"
    ref.mkdir()
    (ref / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    return d


def run_cell(variant_name: str, task_dir: Path, ws: Path, llm,
             with_skills: bool = False) -> tuple[Cell, object]:
    cell = Cell(VARIANTS[variant_name], task_dir.name, task_dir, ws, llm,
                skills_dir=SKILLS_DIR if with_skills else None, tracing=False)
    return cell, cell.run()


# ------------------------------------------------------------------ sens ---

def test_pearson_perfecto_inverso_y_nulo():
    assert sens.pearson([1, 2, 3], [2, 4, 6]) == 1.0
    assert sens.pearson([1, 2, 3], [6, 4, 2]) == -1.0
    assert sens.pearson([1, 1, 1], [1, 2, 3]) is None      # varianza nula en m
    assert sens.pearson([1, 2, 3], [5, 5, 5]) is None      # varianza nula en Q
    assert sens.pearson([1, 2], [1, 2]) is None            # n<3


def test_leave_one_out_excluye_la_tarea():
    m = {"A": {"t1": 10.0, "t2": 20.0, "t3": 30.0}}
    assert sens.leave_one_out(m, "t1") == {"A": 25.0}
    assert sens.leave_one_out(m, "t2") == {"A": 20.0}


def _matriz_ok(n_tasks: int = 12) -> dict[str, dict[str, float]]:
    """Matriz sintética donde TODOS los gates pasan (escalón por arnés)."""
    base = {"A1": 10.0, "A2": 20.0, "A3": 30.0, "A4": 40.0, "A5": 50.0}
    return {v: {f"t{i}": score for i in range(n_tasks)} for v, score in base.items()}


def test_compute_gates_ok_y_sens_unitario():
    r = sens.compute(_matriz_ok(), [f"t{i}" for i in range(12)], VARIANT_NAMES)
    assert r["todos_ok"], r["gates"]
    assert r["spread"] == 40.0
    assert all(v == 1.0 for v in r["sens"].values())
    assert r["n_finitos"] == 12 and r["n_positivos"] == 12
    assert r["q_h"]["A5"] == 50.0


def test_compute_sin_varianza_no_es_cero():
    # misma puntuación en todos los arneses y tareas -> Sens NO DEFINIBLE (None)
    m = {v: {f"t{i}": 50.0 for i in range(12)} for v in VARIANT_NAMES}
    r = sens.compute(m, [f"t{i}" for i in range(12)], VARIANT_NAMES)
    assert all(v is None for v in r["sens"].values())
    assert r["n_finitos"] == 0
    assert not r["gates"]["U4"]["ok"] and not r["gates"]["U5"]["ok"]
    assert not r["gates"]["U3"]["ok"]  # spread 0


def test_compute_u7_detecta_techo():
    m = {v: {f"t{i}": 95.0 for i in range(12)} for v in VARIANT_NAMES}
    r = sens.compute(m, [f"t{i}" for i in range(12)], VARIANT_NAMES)
    assert not r["gates"]["U7"]["ok"]
    v = r["gates"]["U7"]["valor"]
    assert v["media_global"] == 95.0 and v["media_A5"] == 95.0
    assert v["A5_lt_100"] == 12  # 95 < 100 en las 12: sin techo A5=100


def test_compute_u2_detecta_huecos():
    m = _matriz_ok()
    del m["A3"]["t7"]
    r = sens.compute(m, [f"t{i}" for i in range(12)], VARIANT_NAMES)
    assert not r["gates"]["U2"]["ok"]
    assert "A3/t7" in r["gates"]["U2"]["faltan"]
    assert not r["todos_ok"]


# ------------------------------------------------------------- parseo/FS ---

def test_parse_action_json_crudo_vallado_y_basura():
    assert parse_action('{"tool": "run_tests"}') == {"tool": "run_tests"}
    assert parse_action('Respuesta:\n```json\n{"final": "hecho"}\n```') == {"final": "hecho"}
    assert parse_action("habla normal y luego {\"tool\": \"read_file\", \"args\": {}}")["tool"] == "read_file"
    assert parse_action("no hay json aqui") is None
    assert parse_action("") is None


def test_file_block_re_multi_bloque():
    raw = ("texto previo\n###FILE: a.py###\nprint(1)\n"
           "###FILE: sub/b.py###\nprint(2)\nsin cierre")
    bloques = FILE_BLOCK_RE.findall(raw)
    assert [b[0] for b in bloques] == ["a.py", "sub/b.py"]
    assert bloques[0][1].strip() == "print(1)"


def test_safe_path_rechaza_fuera_del_workspace(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    with pytest.raises(ValueError):
        _safe_path(ws, "../evil.py")
    with pytest.raises(ValueError):
        _safe_path(ws, "/etc/passwd")
    assert _safe_path(ws, "pkg/mod.py") == (ws / "pkg" / "mod.py").resolve()


# ---------------------------------------------------------------- arnés ----

def test_a1_one_shot_escribe_bloques_file(tmp_path):
    d = mini_task(tmp_path)
    ws = tmp_path / "ws"
    llm = FakeLLM("Aquí van:\n###FILE: calc.py###\ndef add(a, b):\n    return a + b\n"
                  "###FILE: extra/util.py###\nX = 1")
    _, res = run_cell("A1", d, ws, llm)
    assert res.stopped_by == "one_shot" and res.turns == 1 and res.llm_calls == 1
    assert "return a + b" in (ws / "calc.py").read_text(encoding="utf-8")
    assert (ws / "extra" / "util.py").is_file()
    assert verifier.hidden_score(ws, d)["score"] == 100.0


def test_a1_one_shot_sin_bloques_lo_registra(tmp_path):
    d = mini_task(tmp_path)
    _, res = run_cell("A1", d, tmp_path / "ws", FakeLLM("se me olvido"))
    assert any("sin bloques" in e for e in res.errors)


def test_a1_one_shot_no_escapa_del_workspace(tmp_path):
    d = mini_task(tmp_path)
    ws = tmp_path / "ws"
    _, res = run_cell("A1", d, ws,
                      FakeLLM("###FILE: ../evil.py###\nMALO"))
    assert not (tmp_path / "evil.py").exists()
    assert any("fuera del workspace" in e for e in res.errors)


def test_a2_bucle_tools_final_y_puntuacion(tmp_path):
    d = mini_task(tmp_path)
    ws = tmp_path / "ws"
    llm = FakeLLM(
        '{"tool": "write_file", "args": {"path": "calc.py", "content": "def add(a, b):\\n    return a + b\\n"}}',
        '{"tool": "run_tests"}',
        '{"final": "arreglado"}',
    )
    _, res = run_cell("A2", d, ws, llm)
    assert res.stopped_by == "final" and res.tool_calls == 2
    assert res.llm_calls == 3 and res.invalid_actions == 0
    assert res.pf_fires == [] and res.regulation == []   # A2 sin subsistemas
    assert verifier.hidden_score(ws, d)["score"] == 100.0
    # la herramienta run_tests informó del estado público real
    assert llm.prompts[2].count("PÚBLICOS") >= 1 or "PÚBLICOS" in llm.prompts[2]


def test_a2_rechaza_escritura_fuera_del_workspace(tmp_path):
    d = mini_task(tmp_path)
    ws = tmp_path / "ws"
    llm = FakeLLM('{"tool": "write_file", "args": {"path": "../evil.py", "content": "x"}}',
                  '{"final": "nada"}')
    _, res = run_cell("A2", d, ws, llm)
    assert not (tmp_path / "evil.py").exists()
    assert any("fuera del workspace" in e for e in res.errors)


def test_a3_dispara_retry_y_validate_tras_errores(tmp_path):
    d = mini_task(tmp_path)
    llm = FakeLLM('{"tool": "frobnicate"}',   # herramienta inexistente -> error
                  '{"tool": "frobnicate"}',
                  '{"tool": "frobnicate"}',   # error_count=3 -> validate_before_act
                  '{"final": "me rindo"}')
    _, res = run_cell("A3", d, tmp_path / "ws", llm)
    assert res.pf_fires.count("retry_on_failure") >= 3
    assert "validate_before_act" in res.pf_fires
    # el consejo del PF entra en el prompt del turno siguiente
    assert any("[PF retry_on_failure]" in p for p in llm.prompts[1:])


def test_a4_inyecta_skills_en_el_prompt(tmp_path):
    d = mini_task(tmp_path)
    llm4 = FakeLLM('{"final": "x"}')
    run_cell("A4", d, tmp_path / "ws", llm4, with_skills=True)
    assert "=== SKILL: 01_leer_antes_de_escribir ===" in llm4.prompts[0]
    assert "=== SKILL: 04_casos_limite ===" in llm4.prompts[0]

    llm2 = FakeLLM('{"final": "x"}')
    run_cell("A2", d, tmp_path / "ws", llm2, with_skills=True)
    assert "=== SKILL:" not in llm2.prompts[0]   # A2 no tiene D7


def test_a5_digest_y_regulacion_por_estancamiento(tmp_path):
    d = mini_task(tmp_path)
    # estancamiento: la 1ª fija el hash; hacen falta 4 idénticas para llegar a 3
    llm = FakeLLM("no soy json", "tampoco", "otra vez", "sigue sin json",
                  '{"final": "ok"}')
    _, res = run_cell("A5", d, tmp_path / "ws", llm, with_skills=True)
    assert res.invalid_actions == 4
    assert any("Bucle de acciones repetidas" in m for m in res.regulation)
    assert res.stopped_by == "final"
    # D4: el digest de errores solo aparece en A5, a partir del turno 2
    assert "ERRORES RECIENTES" in llm.prompts[1]
    assert "ERRORES RECIENTES" not in llm.prompts[0]


def test_a4_no_tiene_digest_ni_regulacion(tmp_path):
    d = mini_task(tmp_path)
    llm = FakeLLM("no soy json", '{"final": "ok"}')
    _, res = run_cell("A4", d, tmp_path / "ws", llm, with_skills=True)
    assert res.regulation == []
    assert "ERRORES RECIENTES" not in llm.prompts[1]


def test_celdas_independientes_workspace_fresco(tmp_path):
    d = mini_task(tmp_path)
    ws1, ws2 = tmp_path / "ws1", tmp_path / "ws2"
    run_cell("A1", d, ws1, FakeLLM("###FILE: calc.py###\nbasura"))
    _, res2 = run_cell("A1", d, ws2, FakeLLM("###FILE: calc.py###\ndef add(a, b):\n    return a + b"))
    # la segunda celda parte de la fixture original, no de la primera
    assert "return a + b" in (ws2 / "calc.py").read_text(encoding="utf-8")
    assert res2.variant == "A1"


# ------------------------------------------------------------ verificador --

def test_verificador_ocultos_referencia_vs_vacio(tmp_path):
    d = mini_task(tmp_path)
    vacio = verifier.hidden_score(d / "workspace", d)
    assert vacio["score"] < 100.0 and vacio["failed"] >= 1
    shutil.copytree(d / "reference", d / "workspace", dirs_exist_ok=True)
    assert verifier.hidden_score(d / "workspace", d)["score"] == 100.0


def test_public_summary_informativo(tmp_path):
    d = mini_task(tmp_path)
    res = verifier.public_summary(d / "workspace")
    assert res["failed"] >= 1 and ".py:" in res["output"]


# ---------------------------------------------------------------- fixtures -

def test_lint_de_las_12_tareas_congeladas():
    assert len(tasks.TASK_IDS) == 12
    assert tasks.lint_tasks() == []


def test_skills_pack_presente_y_congelado():
    nombres = sorted(p.stem for p in SKILLS_DIR.glob("*.md"))
    assert nombres == ["01_leer_antes_de_escribir", "02_iterar_con_tests_publicos",
                       "03_contratos_estrictos", "04_casos_limite"]


# ------------------------------------------------------------- dictamen G0 -

def _cells(coste: int, a1: float = 50.0, a5: float = 90.0) -> dict:
    return {f"{v}_{t}": {"score": (a1 if v == "A1" else a5),
                         "usage": {"calls": 4, "prompt_tokens": coste // 2,
                                   "completion_tokens": coste - coste // 2,
                                   "total_tokens": coste}}
            for t in G0_TASKS for v in ("A1", "A5")}


def test_g0_ventana_ok_coste_barato():
    cells = _cells(10_000)
    m = {v: {t: cells[f"{v}_{t}"]["score"] for t in G0_TASKS}
         for v in ("A1", "A5")}
    ver = _veredicto_g0(m, cells)
    assert ver["ventana"] == "VENTANA_OK" and ver["coste"] == "COSTE_OK"
    assert ver["n_final"] == 12 and ver["arranca_oficial"]


def test_g0_techo_y_escalado():
    # A5 a 0 en ambos G0 -> suelo, escalar modelo
    cells = _cells(10_000, a5=0.0)
    m = {v: {t: (cells[f"{v}_{t}"]["score"]) for t in G0_TASKS}
         for v in ("A1", "A5")}
    assert _veredicto_g0(m, cells)["ventana"] == "ESCALAR_MODELO"

    # ambas al 100 -> sin techo, endurecer tarea en BUILD
    cells2 = _cells(10_000, a1=100.0, a5=100.0)
    m2 = {v: {t: (cells2[f"{v}_{t}"]["score"]) for t in G0_TASKS}
          for v in ("A1", "A5")}
    assert _veredicto_g0(m2, cells2)["ventana"] == "ENDURECER_TAREA"


def test_g0_presupuesto_reduce_n_o_no_arranca():
    m = {v: {t: (50.0 if v == "A1" else 90.0) for t in G0_TASKS}
         for v in ("A1", "A5")}
    # derivado del techo vigente: 1.2x el techo a 60 celdas, 0.8x a 40 celdas
    coste_reduccion = TECHO_TOKENS // 50
    ver = _veredicto_g0(m, _cells(coste_reduccion))
    assert ver["proyeccion_60"] > TECHO_TOKENS >= ver["proyeccion_40"]
    assert ver["coste"] == "REDUCIR_N_8" and ver["n_final"] == 8
    assert ver["arranca_oficial"]
    # 4/3 del techo incluso a 40 celdas -> no arranca
    coste_no_arranca = TECHO_TOKENS // 30
    ver2 = _veredicto_g0(m, _cells(coste_no_arranca))
    assert ver2["coste"] == "NO_ARRANCA" and not ver2["arranca_oficial"]
    assert ver2["proyeccion_40"] > TECHO_TOKENS


def test_variantas_congeladas():
    assert VARIANT_NAMES == ("A1", "A2", "A3", "A4", "A5")
    assert VARIANTS["A1"].one_shot and VARIANTS["A1"].max_tokens == 8192
    assert VARIANTS["A5"].use_pfs and VARIANTS["A5"].use_skills
    assert VARIANTS["A5"].use_regulation and VARIANTS["A5"].error_digest
    assert all(not VARIANTS[v].use_regulation for v in ("A1", "A2", "A3", "A4"))


# ------------------------------------------- diagnóstico HITO20 (§0.1) ---


def test_diag_reglas_declaradas():
    assert DIAG_MAX_TURNS == 32 and DIAG_TECHO_TOKENS == 450_000


def test_diag_d1_dos_celdas_sobre_0_9xa1():
    pares = [{"celda": "A2_plugin", "score16": 64.29, "score32": 78.0,
              "a1": 82.14},
             {"celda": "A5_repo", "score16": 41.67, "score32": 95.0,
              "a1": 100.0}]
    ver = evaluar_diagnostico(pares)
    assert ver["regla"] == "D1_CLARO_C1"
    assert all(d["cumple_09a1"] for d in ver["celdas"])


def test_diag_d2_el_doble_presupuesto_no_mueve():
    pares = [{"celda": "A2_plugin", "score16": 64.29, "score32": 68.0,
              "a1": 82.14},
             {"celda": "A5_repo", "score16": 41.67, "score32": 45.0,
              "a1": 100.0}]
    ver = evaluar_diagnostico(pares)
    assert ver["regla"] == "D2_NO_CLARO" and ver["media_delta"] < 10


def test_diag_d3_mejora_pero_sin_dos_sobre_0_9xa1():
    pares = [{"celda": "A2_plugin", "score16": 64.29, "score32": 80.0,
              "a1": 82.14},
             {"celda": "A5_repo", "score16": 41.67, "score32": 75.0,
              "a1": 100.0}]
    ver = evaluar_diagnostico(pares)
    assert ver["regla"] == "D3_AMBIGUO"


def test_diag_una_sola_celda_nunca_d1():
    ver = evaluar_diagnostico([{"celda": "A2_plugin", "score16": 64.29,
                                "score32": 45.0, "a1": 82.14}])
    assert ver["regla"] in ("D2_NO_CLARO", "D3_AMBIGUO")


# --------------------------------- presupuesto de antemano (dueño 2026-10-23) -


def test_presupuesto_modelo_cubico_calibrado():
    assert estimar_tokens_celda(114_467, 16) == 114_467
    # A5_repo real @30 = 752.118 tok; el modelo cúbico da ~0.3% de error
    est = estimar_tokens_celda(114_467, 30)
    assert abs(est - 752_118) <= 0.01 * 752_118


def test_presupuesto_a16_reproduce_la_corrida_oficial():
    p = presupuesto_run(16, 12, TECHO_TOKENS)
    # oficial H19: 5.123.036 tokens — la media por variante × 12 tareas la
    # reproduce (los promedios salen de esa misma corrida)
    assert abs(p["total"] - 5_123_036) <= 0.01 * 5_123_036
    assert p["cabe"] and p["veredicto"] == "COSTE_OK"
    assert p["llamadas_max"] == (1 + 4 * 16) * 12


def test_presupuesto_a1_no_escala_y_teche():
    p32 = presupuesto_run(32, 12, TECHO_TOKENS)
    assert p32["por_variante"]["A1"] == PRESUPUESTO_BASE_16["A1"]
    assert p32["por_variante"]["A2"] == estimar_tokens_celda(
        PRESUPUESTO_BASE_16["A2"], 32)
    # a 48 turnos la corrida se pasa con creces del techo de 7M
    p48 = presupuesto_run(48, 12, TECHO_TOKENS)
    assert not p48["cabe"] and p48["veredicto"] == "EXCEDE_TECHO"


# ------------------------------------------- canal b HITO20 §0.3 (BUILD) ----


def test_parse_actions_multiaccion():
    raw = ('{"tool": "read_file", "args": {"path": "a.py"}}\n'
           'pienso...\n'
           '{"tool": "write_file", "args": {"path": "b.py", "content": "x"}}\n'
           '{"final": "listo"}')
    accs = parse_actions(raw)
    assert [a.get("tool") for a in accs] == ["read_file", "write_file", None]
    assert "final" in accs[-1]  # el objeto {"final"} viaja como acción
    assert parse_action(raw) == accs[0]  # el oficial sigue con la primera


def test_canal_b_preserva_entrada_inicial_bajo_poda(tmp_path):
    """Puerta de BUILD exigida por el dueño (§0.3): la entrada inicial del
    historial NUNCA se elimina con el cap por turno, por grande que sea el
    resto del historial."""
    d = mini_task(tmp_path)
    cell = Cell(VARIANTS["A2"], d.name, d, tmp_path / "ws", FakeLLM(),
                canal="b")
    inicial = "TAREA INICIAL MUY IMPORTANTE — no me elimines"
    cell.history = [inicial] + [f"ENTRADA {i} " + "x" * 4000 for i in range(20)]
    prompt = cell._render()
    assert inicial in prompt                      # inicial preservada
    assert "omitidas por cap de turno" in prompt  # la poda ocurrió
    assert "ENTRADA 19" in prompt                 # las recientes quedan
    assert "ENTRADA 0 " not in prompt             # las antiguas se podan
    # el prompt cabe en el cap salvo la inicial (que se conserva pase lo que pase)
    coste_resto = sum(len(p) for p in prompt.split("\n\n") if p != inicial) // 4
    assert coste_resto <= CANAL_CAP_PROMPT_TOKENS


def test_canal_b_lecturas_completas_vs_oficial(tmp_path):
    d = mini_task(tmp_path)
    grande = "contenido " * 400  # 3.600 chars > _MAX_TOOL_OUT (2.500)
    (d / "workspace" / "grande.txt").write_text(grande, encoding="utf-8")
    for canal, exigido in (("b", len(grande)), ("oficial", 2500)):
        cell = Cell(VARIANTS["A2"], d.name, d, tmp_path / f"ws_{canal}",
                    FakeLLM('{"tool": "read_file", "args": {"path": "grande.txt"}}',
                            '{"final": "ok"}'),
                    canal=canal)
        cell.run()
        resultado = next(h for h in cell.history if h.startswith("RESULTADO de read_file"))
        if canal == "b":
            assert len(resultado) >= exigido  # lectura íntegra (hasta _MAX_READ)
        else:
            assert len(resultado) <= exigido + 40  # canal oficial: cortado


def test_canal_b_multiaccion_un_turno(tmp_path):
    d = mini_task(tmp_path)
    var = replace(VARIANTS["A2"], max_turns=1)
    raw = ('{"tool": "write_file", "args": {"path": "uno.py", "content": "1"}},\n'
           '{"tool": "write_file", "args": {"path": "dos.py", "content": "2"}}')
    cell = Cell(var, d.name, d, tmp_path / "ws", FakeLLM(raw), canal="b")
    res = cell.run()
    assert res.tool_calls == 2 and res.writes == 2
    assert (cell.workspace / "uno.py").is_file()
    assert (cell.workspace / "dos.py").is_file()


def test_canal_b_mid_cell_cap(tmp_path, monkeypatch):
    d = mini_task(tmp_path)
    var = replace(VARIANTS["A2"], max_turns=16)
    cell = Cell(var, d.name, d, tmp_path / "ws",
                FakeLLM('{"tool": "run_tests"}'), canal="b",
                cell_token_cap=1000)
    monkeypatch.setattr(Cell, "_usage", staticmethod(lambda: (800, 300)))
    res = cell.run()
    assert res.stopped_by == "presupuesto"  # tope duro por celda, mid-cell


def test_canal_b_snapshots_turnos_8_y_12(tmp_path):
    d = mini_task(tmp_path)
    var = replace(VARIANTS["A2"], max_turns=8)
    cell = Cell(var, d.name, d, tmp_path / "ws", FakeLLM("sin json"), canal="b")
    res = cell.run()
    assert "score@8" in res.snapshots
    assert isinstance(res.snapshots["score@8"], float)
    # el workspace sigue intacto (snapshot en copia, 0 interferencia)
    assert (cell.workspace / "calc.py").is_file()


# --------------------------------- E1/E2/E3 + recalibración (§0.3, puras) ---


def _par_b(delta: float, writes: int, infra: bool = False, cortada: bool = False,
           pendiente: bool = True) -> dict:
    tp = [1000] * 5 + ([200] * 5 if pendiente else [9000] * 5)
    return {"celda": f"c{delta}{writes}", "score16": 40.0,
            "score17": 40.0 + delta, "writes": writes, "tokens16": 100_000,
            "tokens17": 200_000, "tokens_por_turno": tp,
            "cortada": cortada, "infra_error": infra}


def test_evaluar_b_e1_aclara():
    pares = [_par_b(12, 2), _par_b(11, 1), _par_b(0, 0)]
    ver = evaluar_diagnostico_b(pares, informes_ok=True)
    assert ver["regla"] == "E1_ACLARA"
    assert ver["n_validas"] == 3


def test_evaluar_b_e2_no_aclara_por_delta():
    ver = evaluar_diagnostico_b([_par_b(0, 1), _par_b(0, 2), _par_b(0, 0)])
    assert ver["regla"] == "E2_NO_ACLARA"


def test_evaluar_b_e2_no_aclara_sin_writes():
    ver = evaluar_diagnostico_b([_par_b(20, 0), _par_b(15, 0), _par_b(12, 0)])
    assert ver["regla"] == "E2_NO_ACLARA"


def test_evaluar_b_e3_ambiguo():
    ver = evaluar_diagnostico_b([_par_b(12, 1), _par_b(0, 0), _par_b(0, 0)])
    assert ver["regla"] == "E3_AMBIGUO"


def test_evaluar_b_infra_error_excluye_y_e3():
    pares = [_par_b(12, 2, infra=True), _par_b(11, 1), _par_b(0, 0)]
    ver = evaluar_diagnostico_b(pares, informes_ok=True)
    assert ver["n_validas"] == 2 and ver["n_infra"] == 1
    assert ver["regla"] in ("E1_ACLARA", "E3_AMBIGUO", "E2_NO_ACLARA")
    # dos infra → <2 válidas → E3 por infraestructura
    ver2 = evaluar_diagnostico_b(
        [_par_b(12, 2, infra=True), _par_b(11, 1, infra=True), _par_b(0, 0)])
    assert ver2["regla"] == "E3_INFRA"


def test_evaluar_b_sin_informes_no_es_e1():
    ver = evaluar_diagnostico_b([_par_b(12, 2), _par_b(11, 1), _par_b(0, 0)],
                                informes_ok=False)
    assert ver["regla"] != "E1_ACLARA"


def test_recalibrar_margen_30_y_excede():
    assert MARGEN_RECALIBRACION == 0.30
    # factor 1.0 (el canal b costara exacto lo que el oficial) + 30% cabe
    r = recalibrar_diagnostico_b({"A2_plugin-registry": 1.0,
                                  "A5_repo-cache-layer": 1.0,
                                  "A5_workflow-statemachine": 1.0})
    por_tarea = sum(PRESUPUESTO_BASE_16.values())
    assert r["proyeccion"] == round(por_tarea * 12 * 1.30)
    assert r["veredicto"] == "COSTE_OK" and r["cabe"]
    r_bad = recalibrar_diagnostico_b({"A2_plugin-registry": 2.0})
    assert r_bad["veredicto"] == "EXCEDE_CONSULTAR" and not r_bad["cabe"]


def test_urllerror_dns_es_retryable_c1():
    import urllib.error

    from bibliotecario.core import llm as BLLM
    e = urllib.error.URLError(
        "<urlopen error [Errno -3] Temporary failure in name resolution>")
    assert BLLM._classify(e) == "retryable"
    assert BLLM._classify(RuntimeError("connection refused")) == "retryable"
