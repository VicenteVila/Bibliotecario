"""Dimensión D (§2.D, dec. 13) — el agente generado no escribe su propio estado.

El fallo que estos tests impiden: `instantiate_agent_template` generaba un
`run()` con el literal `"todo"` dentro del fichero, así que el resultado se
sabía antes de correrlo y 0 de 20 pasos se ejecutaban (§8.6). Si alguien
vuelve a escribir el estado en la plantilla, **D2** y **D3** fallan aquí.
"""

from __future__ import annotations

import importlib.util
import py_compile
from pathlib import Path

PROCS = ["paso uno", "paso dos"]
PASOS_TOOL = ("deep_sweep", "search_papers", "retrieve_evidence", "get_subgraph")


def _herramientas_controladas(monkeypatch, fn):
    """Sustituye las 4 tools de rotación de la plantilla (Fase 2) por `fn`.

    La plantilla nueva llama a `TOOLS[nombre]["fn"]` (la referencia vive en el
    dict TOOLS, no en el atributo del módulo), así que hay que parchear el
    dict. El schema se copia del original: `validate_call` necesita que la
    herramienta siga "existiendo" para la capa de validación.
    """
    from bibliotecario.agent import tools as T

    for name in ("deep_sweep", "search_papers", "retrieve_evidence", "get_subgraph"):
        entry = dict(T.TOOLS[name])
        entry["fn"] = fn
        monkeypatch.setitem(T.TOOLS, name, entry)


def _resultado(score: float):
    return {"hits": [{"score": score, "doc_id": 0, "chunk": 0,
                      "title": "x", "text": "t"}]}


def _generar(tmp_path, monkeypatch, score: float):
    """Genera el agente con herramientas controladas y lo carga."""
    from bibliotecario.agent import loop as LOOP
    from bibliotecario.agent import tools as T

    monkeypatch.setattr(T, "data_dir", lambda: tmp_path)
    # Hito 3, Fase 1: la plantilla pasa por `build_blueprint_p4`, que entra
    # por `loop.run_blueprint` (4 turnos de loop + blueprint). Se corta ahí
    # la entrada — sin LLM en tests — con el mismo bp stub que antes daba
    # `build_blueprint`.
    monkeypatch.setattr(LOOP, "run_blueprint",
                        lambda t, g, **k: {"technique": t, "goal": g,
                                           "procedures": PROCS,
                                           "blueprint": "bp"})
    # Fase 2: la plantilla rota entre 4 herramientas del loop; todas se
    # controlan con el mismo score, que es lo que miden los tests D.
    _herramientas_controladas(monkeypatch, lambda **k: _resultado(score))

    res = T.instantiate_agent_template("TecnicaDePrueba", "objetivo")
    src = Path(res["dir"]) / "agent_template.py"
    spec = importlib.util.spec_from_file_location("agente_prueba", src)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return src, mod


def test_d1_compila_y_run_no_lanza(tmp_path, monkeypatch):
    src, mod = _generar(tmp_path, monkeypatch, score=0.9)
    py_compile.compile(str(src), doraise=True)
    out = mod.run({"objetivo": "cualquiera"})
    assert out["trace"], "run() tiene que devolver traza"


def test_d2_el_estado_no_esta_escrito_en_el_fichero(tmp_path, monkeypatch):
    src, _mod = _generar(tmp_path, monkeypatch, score=0.9)
    cuerpo = src.read_text(encoding="utf-8").split("def run(", 1)[-1]
    assert '"todo"' not in cuerpo and "'todo'" not in cuerpo, (
        "el literal 'todo' vuelve a estar en la plantilla: el resultado se "
        "saber antes de correrla, que es el fallo de 8.6"
    )


def _pasos_tool(trace):
    return [s for s in trace if s["tool"] in PASOS_TOOL]


def test_d3_alcanza_done_con_evidencia(tmp_path, monkeypatch):
    _src, mod = _generar(tmp_path, monkeypatch, score=0.9)
    trace = mod.run({"objetivo": "x"})["trace"]
    assert len(_pasos_tool(trace)) == len(PROCS)
    assert all(s["status"] == "done" for s in _pasos_tool(trace)), trace
    # la plantilla nueva añade el paso de validación contra el blueprint
    assert any(s["step"] == "validacion_blueprint" for s in trace)


def test_d3_el_umbral_030_separa(tmp_path, monkeypatch):
    """Sin score suficiente no hay 'done' — las tools de retrieval devuelven
    resultados para cualquier cadena, asi que 'hay documentos' no discrimina
    (2a enmienda)."""
    _src, mod = _generar(tmp_path, monkeypatch, score=0.05)
    trace = mod.run({"objetivo": "x"})["trace"]
    assert all(s["status"] == "empty" for s in _pasos_tool(trace)), trace
    # y lo dice con el numero delante
    assert "0.05" in trace[0]["detalle"]


def test_d3_un_paso_que_falla_no_tumba_la_traza(tmp_path, monkeypatch):
    src, mod = _generar(tmp_path, monkeypatch, score=0.9)

    def _revienta(**k):
        raise RuntimeError("boom")

    _herramientas_controladas(monkeypatch, _revienta)
    trace = mod.run({"objetivo": "x"})["trace"]
    assert [s["status"] for s in _pasos_tool(trace)] == ["error", "error"]
    assert any(s["step"] == "validacion_blueprint" for s in trace)
    assert src.exists()


def test_d2_responde_al_contexto(tmp_path, monkeypatch):
    _src, mod = _generar(tmp_path, monkeypatch, score=0.9)

    def _por_consulta(question=None, query=None, **k):
        texto = f"{question or ''} {query or ''}"
        return _resultado(0.9 if "alpha" in texto else 0.05)

    _herramientas_controladas(monkeypatch, _por_consulta)
    a = mod.run({"objetivo": "alpha"})["trace"]
    b = mod.run({"objetivo": "beta"})["trace"]
    assert [s["status"] for s in _pasos_tool(a)] != [s["status"] for s in _pasos_tool(b)], (
        "run() ignora su entrada: salida identica con contextos distintos"
    )
