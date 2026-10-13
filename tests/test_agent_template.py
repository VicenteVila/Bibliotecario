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


def _generar(tmp_path, monkeypatch, score: float):
    """Genera el agente con un `deep_sweep` controlado y lo carga."""
    from bibliotecario.agent import tools as T

    monkeypatch.setattr(T, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(T, "build_blueprint",
                        lambda t, g, extra_source="": {"technique": t, "goal": g,
                                                       "procedures": PROCS,
                                                       "blueprint": "bp"})
    # deep_sweep se importa dentro de run(), asi que se parchea en su modulo
    from bibliotecario.agent import tools
    monkeypatch.setattr(tools, "deep_sweep",
                        lambda q, **k: {"docs": [{"title": "x", "chunks": [
                            {"chunk": 0, "score": score, "text": "t"}]}]})

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


def test_d3_alcanza_done_con_evidencia(tmp_path, monkeypatch):
    _src, mod = _generar(tmp_path, monkeypatch, score=0.9)
    trace = mod.run({"objetivo": "x"})["trace"]
    assert len(trace) == len(PROCS)
    assert all(s["status"] == "done" for s in trace), trace


def test_d3_el_umbral_030_separa(tmp_path, monkeypatch):
    """Sin score suficiente no hay 'done' — deep_sweep devuelve docs para
    cualquier cadena, asi que 'hay documentos' no discrimina (2a enmienda)."""
    _src, mod = _generar(tmp_path, monkeypatch, score=0.05)
    trace = mod.run({"objetivo": "x"})["trace"]
    assert all(s["status"] == "empty" for s in trace), trace
    # y lo dice con el numero delante
    assert "0.05" in trace[0]["detalle"]


def test_d3_un_paso_que_falla_no_tumba_la_traza(tmp_path, monkeypatch):
    from bibliotecario.agent import tools

    src, mod = _generar(tmp_path, monkeypatch, score=0.9)

    def _revienta(q, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(tools, "deep_sweep", _revienta)
    trace = mod.run({"objetivo": "x"})["trace"]
    assert [s["status"] for s in trace] == ["error", "error"]
    assert len(trace) == len(PROCS)
    assert src.exists()


def test_d2_responde_al_contexto(tmp_path, monkeypatch):
    from bibliotecario.agent import tools

    _src, mod = _generar(tmp_path, monkeypatch, score=0.9)

    def _por_consulta(q, **k):
        score = 0.9 if "alpha" in q else 0.05
        return {"docs": [{"title": "x", "chunks": [
            {"chunk": 0, "score": score, "text": "t"}]}]}

    monkeypatch.setattr(tools, "deep_sweep", _por_consulta)
    a = mod.run({"objetivo": "alpha"})["trace"]
    b = mod.run({"objetivo": "beta"})["trace"]
    assert [s["status"] for s in a] != [s["status"] for s in b], (
        "run() ignora su entrada: salida identica con contextos distintos"
    )
