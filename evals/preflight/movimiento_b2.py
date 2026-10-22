"""HITO18 §1 — métrica determinista de movimiento (M_mov) y trampas U7b.

Definición congelada (HITO18_PLAN.md §1): frames → escala de grises
(Pillow `convert("L")`, luma ITU-R 601-2) → `Δ_i = media(|I_{i+1} − I_i|)`
→ `M_mov = media(Δ_i)`, en unidades de nivel de gris (0-255). Sin RNG,
sin red, sin umbral de luminancia. `S_mov = clamp(M_mov / M_MOV_REF, 0, 1)`.

Umbrales ratificados 2026-10-22 (H18 §2): U4′ (0.20 / Δ 0.15 / idle 0.15)
y U7b (mov ≥ 0.20, estática ≤ 0.05).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

M_MOV_REF = 0.50
U4_MOV_MIN = 0.20
U4_DELTA_MIN = 0.15
U4_IDLE_MAX = 0.15
U7B_MOV_MIN = 0.20
U7B_ESTATICO_MAX = 0.05


def m_mov(frames: list[Path]) -> float:
    """M_mov: Δ media (0-255) entre frames consecutivos en grises."""
    if len(frames) < 2:
        return 0.0
    grises = [np.asarray(Image.open(f).convert("L"), dtype=np.int16)
              for f in frames]
    deltas = [float(np.abs(grises[i + 1] - grises[i]).mean())
              for i in range(len(grises) - 1)]
    return round(float(np.mean(deltas)), 4)


def s_mov(m: float, ref: float = M_MOV_REF) -> float:
    """S_mov = clamp(M_mov / M_MOV_REF, 0, 1) — nota de movimiento."""
    return round(min(1.0, max(0.0, m / ref)), 4)


def score_b2_hibrido(s: float, v: float, a: float) -> float:
    """Score_B2 = 0.50·S_mov + 0.25·V + 0.25·A (H18 §1, ratificado)."""
    return round(0.50 * s + 0.25 * v + 0.25 * a, 4)


def gate_u4p(m_default: float | None, m_idle: float | None
             ) -> tuple[bool, str]:
    """U4′: default ≥ 0.20, Δ(default−idle) ≥ 0.15, idle ≤ 0.15."""
    if m_default is None or m_idle is None:
        return False, "falta M_mov(default) o M_mov(idle)"
    delta = round(m_default - m_idle, 4)
    ok = (m_default >= U4_MOV_MIN and delta >= U4_DELTA_MIN
          and m_idle <= U4_IDLE_MAX)
    return ok, (f"M_mov(default)={m_default} (≥{U4_MOV_MIN}) · "
                f"Δ(default−idle)={delta} (≥{U4_DELTA_MIN}) · "
                f"M_mov(idle)={m_idle} (≤{U4_IDLE_MAX})")


def gate_u7b(m_mov_seq: float | None, m_estatico: float | None
             ) -> tuple[bool, str]:
    """U7b: la secuencia con sprite en movimiento separa de la estática."""
    if m_mov_seq is None or m_estatico is None:
        return False, "falta M_mov de la trampa"
    ok = m_mov_seq >= U7B_MOV_MIN and m_estatico <= U7B_ESTATICO_MAX
    return ok, (f"trampa mov={m_mov_seq} (≥{U7B_MOV_MIN}) · "
                f"estática={m_estatico} (≤{U7B_ESTATICO_MAX})")


def trampas_mov(destino: Path) -> tuple[list[Path], list[Path]]:
    """U7b: secuencia determinista con sprite moviéndose vs su gemela estática.

    Fondo plano (32,32,64) 1280×720; sprite amarillo de 64×64 que avanza
    40 px por frame durante 8 frames; la gemela estática lo deja fijo.
    Sin RNG: ambas secuencias son funciones puras del índice de frame.
    """
    destino.mkdir(parents=True, exist_ok=True)
    mov_dir = destino / "mov"
    est_dir = destino / "estatica"
    mov_dir.mkdir(exist_ok=True)
    est_dir.mkdir(exist_ok=True)
    fondo = (32, 32, 64)
    sprite = (250, 208, 44)
    for i in range(8):
        for modo, x in (("mov", 100 + i * 40), ("estatica", 100)):
            im = Image.new("RGB", (1280, 720), fondo)
            ImageDraw.Draw(im).ellipse(
                [x, 328, x + 64, 392], fill=sprite)
            im.save(destino / modo / f"step_{i:03d}.png")
    return (sorted(mov_dir.glob("step_*.png")),
            sorted(est_dir.glob("step_*.png")))
