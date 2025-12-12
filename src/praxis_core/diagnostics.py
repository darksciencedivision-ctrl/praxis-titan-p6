from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List

from ..utils.timing import now, elapsed


@dataclass
class LayerDiagnostics:
    name: str
    run_time_sec: float
    warnings: List[str]


def time_layer(name: str):
    """
    Usage:
        t_num = time_layer("numeric")
        ... run numeric ...
        diag_obj = stop_layer(t_num)
    """
    return name, now()


def stop_layer(timer_tuple) -> LayerDiagnostics:
    name, start = timer_tuple
    dt = elapsed(start)
    return LayerDiagnostics(name=name, run_time_sec=dt, warnings=[])


def diagnostics_summary(layers: Dict[str, LayerDiagnostics]) -> str:
    lines = []
    for key, diag in layers.items():
        lines.append(
            f"{key}: {diag.run_time_sec:.4f} s, warnings={len(diag.warnings)}"
        )
    return "\n".join(lines)


def diagnostics_to_dict(layers: Dict[str, LayerDiagnostics]) -> Dict[str, Dict]:
    return {k: asdict(v) for k, v in layers.items()}
