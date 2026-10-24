"""Arnés mínimo del piloto HITO19 (§1.1-§1.2): bucle observe-reason-act con
subsistemas conmutables A1-A5.

Reutiliza SIN MODIFICAR los subsistemas del arnés real del proyecto:
  D5 validación  -> bibliotecario.harness.pfs (RetryPF, ValidateBeforeActPF)
  regulación     -> bibliotecario.harness.layers.TrajectoryRegulationLayer
  D7 skills      -> skills_pack/ congelado (§1.B)
  D4 memoria     -> digest estructurado de errores (A5)

`llm_fn(prompt, max_tokens) -> str` es inyectable: los tests usan un LLM
falso; el corredor oficial usa `bibliotecario.core.llm.generate` con
LLM_PROVIDERS=nvidia (§1.5).
"""
from __future__ import annotations

import json
import re
import shutil
from collections import deque
from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bibliotecario.harness.layers import TrajectoryRegulationLayer
from bibliotecario.harness.pfs import RetryPF, SkillProgramRegistry, ValidateBeforeActPF
from evals.sd_pilot import verifier
from evals.sd_pilot.variants import Variant

LLMFn = Callable[[str, int], str]

FILE_BLOCK_RE = re.compile(r"###FILE:\s*([^\s#]+?)\s*###\s*\n(.*?)(?=\n###FILE:|\Z)", re.DOTALL)
_MAX_READ = 8000
_MAX_TOOL_OUT = 2500
_MAX_INLINE = 6000
_MAX_RAW_IN_HISTORY = 4000

# Canal b HITO20 §0.3 (ratificado 2026-10-23): cap de input por llamada,
# snapshots de score y multi-acción. El canal "oficial" de H19 NO usa nada
# de esto (default intacto).
CANAL_CAP_PROMPT_TOKENS = 18_000
CANAL_SNAP_TURNS = (8, 12)

# Version del canal b (HITO20 §1). Subir a "b2" + enmienda ratificada si
# cambia cualquiera de los elementos congelados: TOOLS_JSON, REPROMPT_FORZADO,
# CANAL_CAP_PROMPT_TOKENS o _MAX_READ (tests dorados en test_sens_sd_pilot).
CANAL_B_VERSION = "b1"

# Brazo forzado HITO20 §1 (Enmienda 2, pre-registrado 2026-10-23): texto
# exacto del reprompt inyectado en cada turno tras `final`.
REPROMPT_FORZADO = (
    "Turno {n}/{total}. Revisa el estado, identifica una mejora concreta "
    "pendiente y ejecútala; si no hay ninguna, escribe SIN_MEJORA y explica "
    "por qué.")


def parse_actions(raw: str) -> list[dict]:
    """Extrae TODAS las acciones JSON (tool/final) del turno (canal b)."""
    acciones: list[dict] = []
    if not raw:
        return acciones
    dec = json.JSONDecoder()
    i = 0
    while True:
        j = raw.find("{", i)
        if j == -1:
            break
        try:
            obj, end = dec.raw_decode(raw[j:])
        except ValueError:
            i = j + 1
            continue
        if isinstance(obj, dict) and ("tool" in obj or "final" in obj):
            acciones.append(obj)
        i = j + end
    return acciones

TOOLS_JSON = (
    'Responde SOLO con un objeto JSON de una de estas formas:\n'
    '{"tool": "read_file", "args": {"path": "ruta/relativa.py"}}\n'
    '{"tool": "write_file", "args": {"path": "ruta/relativa.py", "content": "codigo completo"}}\n'
    '{"tool": "run_tests"}\n'
    '{"final": "resumen corto de lo hecho"}\n'
    "No escribas nada fuera de un JSON. Al terminar, run_tests debe dar 0 fallos "
    "y solo entonces emite final."
)


def parse_action(raw: str) -> dict | None:
    """Extrae el primer objeto JSON con `tool` o `final` de la respuesta."""
    if not raw:
        return None
    for m in re.finditer(r"\{", raw):
        try:
            obj, _ = json.JSONDecoder().raw_decode(raw[m.start():])
        except ValueError:
            continue
        if isinstance(obj, dict) and ("tool" in obj or "final" in obj):
            return obj
    return None


def _safe_path(workspace: Path, path: str) -> Path:
    ws = workspace.resolve()
    p = (workspace / path).resolve()
    if p == ws or not str(p).startswith(str(ws) + "/"):
        raise ValueError(f"ruta fuera del workspace: {path}")
    return p


class _NoopSpan:
    """Span neutro: los tests (sin traza) usan la misma superficie."""

    def set_input(self, value: Any) -> None:
        pass

    def set_output(self, value: Any) -> None:
        pass

    def set_error(self, error: str) -> None:
        pass

    def set_tokens(self, inp: int, outp: int) -> None:
        pass

    def add_metadata(self, **kwargs: Any) -> None:
        pass


@dataclass
class CellResult:
    variant: str
    task: str
    turns: int = 0
    llm_calls: int = 0
    tool_calls: int = 0
    invalid_actions: int = 0
    pf_fires: list[str] = field(default_factory=list)
    regulation: list[str] = field(default_factory=list)
    final: str = ""
    stopped_by: str = ""
    llm_error: str = ""
    errors: list[str] = field(default_factory=list)
    writes: int = 0
    tokens_por_turno: list[int] = field(default_factory=list)
    snapshots: dict[str, float] = field(default_factory=dict)
    # Brazo forzado §1 (Enmienda 2): ledger por turno forzado + veredicto.
    forced_turns: int = 0
    forced_writes: int = 0
    forced_sin_mejora: int = 0
    convergencia_real: bool = False


class Cell:
    """Una celda del piloto: un arnés (variante) corriendo una tarea."""

    def __init__(self, variant: Variant, task_id: str, task_dir: Path,
                 workspace: Path, llm_fn: LLMFn, skills_dir: Path | None = None,
                 tracing: bool = False, canal: str = "oficial",
                 cell_token_cap: int = 0, force_full_turns: bool = False,
                 snap_turns: tuple[int, ...] | None = None,
                 ceiling_watch: tuple[int, int, int] | None = None) -> None:
        self.variant = variant
        self.task_id = task_id
        self.task_dir = task_dir
        self.workspace = workspace
        self.llm_fn = llm_fn
        self.tracing = tracing
        self.canal = canal  # "oficial" (H19, intacto) | "b" (§0.3 HITO20)
        self.cell_token_cap = cell_token_cap
        self.force_full_turns = force_full_turns  # brazo forzado §1
        self._reprompt_activo = False  # True tras el primer `final` forzado
        self.snap_turns = tuple(snap_turns or CANAL_SNAP_TURNS)
        # (tokens_otros, proy_celda, techo_global): corte mid-cell al techo
        # con la regla del 80 % (§1 Enmienda 2, E2-Crítico 2).
        self.ceiling_watch = ceiling_watch
        self.result = CellResult(variant=variant.name, task=task_id)

        if workspace.exists():
            shutil.rmtree(workspace)
        shutil.copytree(task_dir / "workspace", workspace)

        self.history: list[str] = []
        self.errors_recent: deque[str] = deque(maxlen=5)
        self.registry: SkillProgramRegistry | None = None
        if variant.use_pfs:
            self.registry = SkillProgramRegistry()
            self.registry.register(RetryPF())
            self.registry.register(ValidateBeforeActPF())
        self.state_pf: dict[str, Any] = {
            "last_action.status": "ok", "error_count": 0,
            "attempt_count": 0, "max_attempts": 3,
        }
        self.regulation: TrajectoryRegulationLayer | None = None
        if variant.use_regulation:
            self.regulation = TrajectoryRegulationLayer(
                max_stagnation=3, max_retries=5, max_actions=40, max_duration=1800.0)
        self.skills_text = self._load_skills(skills_dir) if variant.use_skills else ""

    # ---------- trazas (esquema congelado §1.B) ----------

    def _span(self, agent: str, metadata: dict | None = None):
        if not self.tracing:
            return nullcontext(_NoopSpan())
        import traceforge
        return traceforge.span(agent=agent, metadata=metadata or {})

    @staticmethod
    def _usage() -> tuple[int, int]:
        from bibliotecario.core import llm as BLLM
        tot = BLLM.usage_totals()
        return int(tot.get("prompt_tokens") or 0), int(tot.get("completion_tokens") or 0)

    # ---------- observación (Iobs/C) ----------

    def _load_skills(self, skills_dir: Path | None) -> str:
        if not skills_dir or not skills_dir.is_dir():
            return ""
        parts = []
        for f in sorted(skills_dir.glob("*.md")):
            parts.append(f"=== SKILL: {f.stem} ===\n{f.read_text(encoding='utf-8').strip()}")
        return "\n\n".join(parts)

    def _header(self) -> str:
        task_md = (self.task_dir / "TASK.md").read_text(encoding="utf-8")
        return f"TAREA:\n{task_md}"

    @staticmethod
    def _tree(workspace: Path) -> str:
        lines = []
        for f in sorted(workspace.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts and ".pytest_cache" not in f.parts:
                lines.append(str(f.relative_to(workspace)))
        return "\n".join(lines)

    def _files_inline(self) -> str:
        parts = []
        for f in sorted(self.workspace.rglob("*")):
            if not f.is_file() or "__pycache__" in f.parts or ".pytest_cache" in f.parts:
                continue
            rel = f.relative_to(self.workspace)
            content = f.read_text(encoding="utf-8", errors="replace")[:_MAX_INLINE]
            parts.append(f"=== {rel} ===\n{content}")
        return "\n\n".join(parts)

    def _render(self) -> str:
        entries = list(self.history)
        marcador = ""
        if self.canal == "b":
            # Cap por turno (§0.3): se poda por antigüedad desde la segunda
            # entrada; la inicial (TAREA/herramientas) NUNCA se elimina.
            n_drop = 0
            chars_drop = 0

            def _coste(text: str) -> int:
                return len(text) // 4 + 1

            while (len(entries) > 1
                   and _coste(marcador)
                   + sum(_coste(e) for e in entries) > CANAL_CAP_PROMPT_TOKENS):
                drop = entries.pop(1)
                n_drop += 1
                chars_drop += len(drop)
            if n_drop:
                marcador = (f"[{n_drop} entradas antiguas omitidas por cap de "
                            f"turno ({chars_drop} chars)]")
        prompt = "\n\n".join(([marcador] if marcador else []) + entries)
        if self.variant.error_digest and self.errors_recent:
            digest = "ERRORES RECIENTES (no los repitas):\n" + "\n".join(
                f"- {e}" for e in self.errors_recent)
            prompt = digest + "\n\n" + prompt
        return prompt

    # ---------- acción (Iact) ----------

    def _exec_tool(self, action: dict) -> tuple[str, bool]:
        name = str(action.get("tool", ""))
        args = action.get("args") or {}
        try:
            if name == "read_file":
                p = _safe_path(self.workspace, str(args.get("path", "")))
                if not p.is_file():
                    return f"ERROR: no existe {args.get('path')}", False
                content = p.read_text(encoding="utf-8", errors="replace")[:_MAX_READ]
                return f"CONTENIDO de {args.get('path')}:\n{content}", True
            if name == "write_file":
                p = _safe_path(self.workspace, str(args.get("path", "")))
                content = args.get("content")
                if not isinstance(content, str):
                    return "ERROR: content debe ser string", False
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
                self.result.writes += 1
                return f"OK escrito {args.get('path')} ({len(content)} chars)", True
            if name == "run_tests":
                res = verifier.public_summary(self.workspace)
                out = res["output"]
                lines = [ln for ln in out.splitlines()
                         if ".py:" in ln or "Error" in ln or "error" in ln][:25]
                detail = "\n".join(lines)[:_MAX_TOOL_OUT]
                return (f"PÚBLICOS: {res['passed']} pasan, {res['failed']} fallan, "
                        f"{res['errors']} errores\n{detail}"), res["failed"] + res["errors"] == 0
            return f"ERROR: herramienta desconocida {name}", False
        except ValueError as e:
            return f"ERROR: {e}", False
        except OSError as e:
            return f"ERROR de escritura: {e}", False

    # ---------- bucle (L) ----------

    def _record_action(self, action: dict, result: str, ok: bool) -> None:
        self.state_pf["attempt_count"] += 1
        if ok:
            self.state_pf["last_action.status"] = "ok"
            self.state_pf["error_count"] = 0
        else:
            self.state_pf["last_action.status"] = "error"
            self.state_pf["error_count"] += 1
            self.errors_recent.append(result[:160])
            self.result.errors.append(result[:160])
        if self.registry is not None:
            for fire in self.registry.execute_matching(self.state_pf):
                msg = fire.get("message", "")
                self.result.pf_fires.append(str(fire.get("pf", "")))
                self.history.append(f"[PF {fire.get('pf')}] {msg}")
        if self.regulation is not None:
            st = self.regulation.state("cell")
            st.record_action({"tool": action.get("tool"),
                              "args": json.dumps(action.get("args") or {},
                                                 sort_keys=True, default=str)})
            for msg in self.regulation.check_all("cell"):
                self.result.regulation.append(msg)
                self.history.append(msg)

    def _llm(self, prompt: str) -> str:
        self.result.llm_calls += 1
        with self._span("llm", {"turn": self.result.turns}) as sp:
            sp.set_input(prompt[:_MAX_RAW_IN_HISTORY])
            before = self._usage()
            out = self.llm_fn(prompt, self.variant.max_tokens)
            after = self._usage()
            sp.set_tokens(after[0] - before[0], after[1] - before[1])
            if self.canal == "b":
                self.result.tokens_por_turno.append(
                    (after[0] - before[0]) + (after[1] - before[1]))
            sp.set_output((out or "")[:_MAX_RAW_IN_HISTORY])
        return out

    def _cap_excedido(self) -> bool:
        """Tope duro por celda (§0.3): corte mid-cell documentado."""
        if not self.cell_token_cap:
            return False
        p, c = self._usage()
        return (p + c) >= self.cell_token_cap

    def _techo_alcanzado(self) -> bool:
        """Regla del 80 % (§1 E2-Crítico 2): al cruzar el techo global,
        la celda en curso se corta SOLO si ya gastó ≥80 % de su
        proyección; si no, se completa (overshoot documentado)."""
        if self.ceiling_watch is None:
            return False
        otros, proy, techo = self.ceiling_watch
        p, c = self._usage()
        cell = p + c
        if otros + cell < techo:
            return False
        return proy <= 0 or cell >= 0.8 * proy

    def _clasificar_turno_forzado(self, raw: str, writes_antes: int) -> None:
        """§1 E2-Crítico 3: write | sin_mejora (SIN_MEJORA o solo-final) | otro."""
        self.result.forced_turns += 1
        if self.result.writes > writes_antes:
            self.result.forced_writes += 1
            return
        acciones = parse_actions(raw)
        solo_final = bool(acciones) and all("final" in a for a in acciones)
        if "sin_mejora" in (raw or "").lower() or solo_final:
            self.result.forced_sin_mejora += 1

    def _snapshot(self, turn: int) -> None:
        from evals.sd_pilot import verifier
        snap = verifier.hidden_score(self.workspace, self.task_dir)
        self.result.snapshots[f"score@{turn}"] = snap["score"]

    def _run_one_shot(self) -> None:
        with self._span("turn", {"turn": 1}) as tsp:
            prompt = (self._header()
                      + "\n\nFICHEROS DEL PROYECTO:\n" + self._files_inline()
                      + "\n\nDEVUELVE SOLO bloques con el contenido COMPLETO de cada fichero "
                        "que quieras crear o modificar, en este formato exacto:\n"
                        "###FILE: ruta/relativa.py###\n<contenido>\n"
                        "Sin nada más antes ni después.")
            tsp.set_input(prompt[:_MAX_RAW_IN_HISTORY])
            raw = self._llm(prompt)
            tsp.set_output((raw or "")[:_MAX_RAW_IN_HISTORY])
        self.result.turns = 1
        written = 0
        for rel, content in FILE_BLOCK_RE.findall(raw or ""):
            try:
                p = _safe_path(self.workspace, rel)
            except ValueError as e:
                self.result.errors.append(str(e))
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content.rstrip("\n") + "\n", encoding="utf-8")
            written += 1
        if written == 0:
            self.result.errors.append("one-shot sin bloques ###FILE parseables")
        self.result.stopped_by = "one_shot"

    def _pasar_acciones_b(self, raw: str) -> bool:
        """Canal b (§0.3): ejecuta todas las acciones del turno; True = final."""
        acciones = parse_actions(raw)
        if not acciones:
            self.result.invalid_actions += 1
            self.history.append(f"MODELO: {raw[:_MAX_RAW_IN_HISTORY]}")
            self.history.append("AVISO: respuesta no es un JSON válido con tool/final. "
                                "Responde SOLO con el JSON.")
            self._record_action({"tool": "_invalid"}, "JSON invalido", False)
            return False
        self.history.append(f"MODELO: {raw[:_MAX_RAW_IN_HISTORY]}")
        for action in acciones:
            if "final" in action:
                self.result.final = str(action.get("final", ""))[:1000]
                self.result.stopped_by = "final"
                return True
            with self._span("tool", {"tool_name": action.get("tool")}) as spt:
                spt.set_input(json.dumps(action.get("args") or {}, sort_keys=True,
                                         default=str)[:2000])
                result, ok = self._exec_tool(action)
                spt.set_output(result[:2000])
                if not ok:
                    spt.set_error(result[:500])
            self.result.tool_calls += 1
            if action.get("tool") == "read_file":
                # lecturas completas (§0.3): el contenido entra íntegro
                # (hasta _MAX_READ), sin cortar a _MAX_TOOL_OUT
                self.history.append(f"RESULTADO de read_file:\n{result}")
            else:
                self.history.append(
                    f"RESULTADO de {action.get('tool')}:\n{result[:_MAX_TOOL_OUT]}")
            self._record_action(action, result, ok)
        return False

    def _run_loop(self) -> None:
        initial = (self._header()
                   + "\n\nFICHEROS DEL PROYECTO (árbol; usa read_file para ver su contenido):\n"
                   + self._tree(self.workspace)
                   + "\n\n" + TOOLS_JSON)
        if self.skills_text:
            initial += "\n\n" + self.skills_text
        self.history = [initial]

        for turn in range(1, self.variant.max_turns + 1):
            self.result.turns = turn
            with self._span("turn", {"turn": turn}) as tsp:
                prompt = self._render()
                tsp.set_input(prompt[:_MAX_RAW_IN_HISTORY])
                raw = self._llm(prompt)
                tsp.set_output((raw or "")[:_MAX_RAW_IN_HISTORY])

            if self.canal == "b":
                writes_antes = self.result.writes
                final_found = self._pasar_acciones_b(raw)
                if self.force_full_turns and self._reprompt_activo:
                    # todo turno POST-final cuenta en el ledger (E2-Crítico 3)
                    self._clasificar_turno_forzado(raw, writes_antes)
                if final_found:
                    if not self.force_full_turns:
                        return
                    # Brazo forzado §1: se ignora `final` y se inyecta el
                    # reprompt pre-registrado (desde el primer `final`).
                    self._reprompt_activo = True
                    if turn < self.variant.max_turns:
                        self.history.append(REPROMPT_FORZADO.format(
                            n=turn + 1, total=self.variant.max_turns))
                if self._cap_excedido():
                    self.result.stopped_by = "presupuesto"
                    return
                if self._techo_alcanzado():
                    self.result.stopped_by = "truncated_by_ceiling"
                    return
                if (self.regulation is not None
                        and self.regulation.state("cell").budget_exhausted):
                    self.result.stopped_by = "presupuesto"
                    return
                if turn in self.snap_turns:
                    self._snapshot(turn)
                continue

            action = parse_action(raw)

            if action is None:
                self.result.invalid_actions += 1
                self.history.append(f"MODELO: {raw[:_MAX_RAW_IN_HISTORY]}")
                self.history.append("AVISO: respuesta no es un JSON válido con tool/final. "
                                    "Responde SOLO con el JSON.")
                self._record_action({"tool": "_invalid"}, "JSON invalido", False)
                continue

            if "final" in action:
                self.result.final = str(action.get("final", ""))[:1000]
                self.result.stopped_by = "final"
                return

            with self._span("tool", {"tool_name": action.get("tool")}) as spt:
                spt.set_input(json.dumps(action.get("args") or {}, sort_keys=True,
                                         default=str)[:2000])
                result, ok = self._exec_tool(action)
                spt.set_output(result[:2000])
                if not ok:
                    spt.set_error(result[:500])
            self.result.tool_calls += 1
            self.history.append(f"MODELO: {raw[:_MAX_RAW_IN_HISTORY]}")
            self.history.append(f"RESULTADO de {action.get('tool')}:\n{result[:_MAX_TOOL_OUT]}")
            self._record_action(action, result, ok)

            if self.regulation is not None and self.regulation.state("cell").budget_exhausted:
                self.result.stopped_by = "presupuesto"
                return

        self.result.stopped_by = ("max_turns_forzado" if self.force_full_turns
                                  else "max_turns")

    def run(self) -> CellResult:
        if self.tracing:
            import traceforge
            meta = {"variant": self.variant.name, "task": self.task_id,
                    "max_turns": self.variant.max_turns,
                    "subsystems": self.variant.subsystems}
            with traceforge.span(agent="sens_pilot", metadata=meta) as root:
                root.set_input(self._header()[:4000])
                self._dispatch()
                root.set_output(self.result.final or self.result.stopped_by)
            return self.result
        self._dispatch()
        return self.result

    def _dispatch(self) -> None:
        try:
            if self.variant.one_shot:
                self._run_one_shot()
            else:
                self._run_loop()
        except Exception as e:  # fallo de proveedor/infra: la celda queda documentada
            self.result.llm_error = f"{type(e).__name__}: {e}"
            if not self.result.stopped_by:
                self.result.stopped_by = "error_llm"
        # §1 E2-Crítico 3: ≥80 % de turnos forzados sin mejora => la
        # convergencia es real (el agente no tenía nada que hacer).
        if (self.result.forced_turns
                and self.result.forced_sin_mejora >= 0.8 * self.result.forced_turns):
            self.result.convergencia_real = True
