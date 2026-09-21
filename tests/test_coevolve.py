from bibliotecario.coevolve import estimator as EST
from bibliotecario.coevolve import selector as SEL
from bibliotecario.coevolve import task_pool as TP
from bibliotecario.coevolve import wiki as W
from bibliotecario.core import storage


def _mkpool(tmp_path, monkeypatch, specs):
    db = tmp_path / "co.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    ids = []
    for kind, outcomes in specs:
        tid = TP.add_task(f"tarea {kind}", kind)
        for ok in outcomes:
            TP.record_outcome(tid, ok)
        ids.append(tid)
    return ids


def test_variance_weights_prioriza_disputadas(tmp_path, monkeypatch):
    _mkpool(tmp_path, monkeypatch, [("qa", [True, False, True, False]), ("qa", [True] * 6), ("qa", [False] * 6)])
    stats = TP.task_stats()
    w = SEL.weights(stats)
    disputed = min(stats, key=lambda s: abs(s["pbar"] - 0.5))
    assert w[disputed["id"]] == max(w.values())


def test_unsolved_floor_y_exploracion(tmp_path, monkeypatch):
    _mkpool(tmp_path, monkeypatch, [("qa", [False, False]), ("qa", [True])])
    w = SEL.weights(task_stats := TP.task_stats())
    unsolved = next(s for s in task_stats if s["pbar"] == 0.0)
    assert w[unsolved["id"]] > 0  # piso ℓ, no queda excluida


def test_sample_subset_tamano(tmp_path, monkeypatch):
    _mkpool(tmp_path, monkeypatch, [("qa", [True, False])] * 10)
    sub = SEL.sample_subset(TP.task_stats(), rho=0.2, seed=1)
    assert len(sub) == 2 and len(set(sub)) == 2


def test_hajek_recupera_media_con_muestreo_uniforme():
    import math
    stats = [{"id": i, "pbar": 0.0, "n": 4} for i in range(6)]
    pi = {s["id"]: 0.5 for s in stats}
    sampled = {0: 1.0, 2: 1.0, 4: 0.0}
    est, which = EST.estimate_full(sampled, stats, pi)
    assert which == "hajek"
    assert math.isclose(est, (1 + 1 + 0) / 3, rel_tol=1e-9)


def test_anchored_al_medio():
    stats = [{"id": 0, "pbar": 0.5, "n": 10}, {"id": 1, "pbar": 0.6, "n": 10}]
    assert EST.choose_estimator(stats) == "anchored"
    pi = {0: 0.5, 1: 0.5}
    est, which = EST.estimate_full({0: 1.0}, stats, pi)
    assert which == "anchored"
    # base=(0.5+0.6)/2=0.55, adj=((1-0.5)/0.5)/2=0.5 → 1.05
    assert abs(est - 1.05) < 1e-9


def test_select_best_desempate_temprano():
    assert EST.select_best([(0.8, 3), (0.9, 2), (0.9, 1)]) == 1


def test_wiki_gating(tmp_path, monkeypatch):
    db = tmp_path / "wiki.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    ok = W.gate_skill("s1", "# S1", "para X", 0.8)
    assert ok["promoted"] and W.get_page("skill-s1")["kind"] == "skill"
    ko = W.gate_skill("s2", "# S2", "para Y", 0.2)
    assert not ko["promoted"] and W.get_page("skill-s2")["kind"] == "accumulated"


def test_stratified_traces():
    t = W.stratified_traces([f"f{i}" for i in range(9)], [f"s{i}" for i in range(9)])
    assert len(t["failed"]) == 5 and len(t["succeeded"]) == 3


def test_background_cycle_sin_llm(tmp_path, monkeypatch):
    import bibliotecario.background as BG
    db = tmp_path / "bg.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    rep = BG.run_cycle()
    assert rep["consolidate"]["forgotten"] == 0
    assert "refine" in rep
