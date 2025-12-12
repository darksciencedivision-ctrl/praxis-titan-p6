
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, List, Tuple, DefaultDict

from . import output_manager
from ..utils.io import read_json

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"


def load_cascade_map(path: Path | None = None) -> Dict[str, Any]:
    """
    Load cascade influence definitions.

    Expected structure:
    {
      "edges": [
        { "from": "R_GAS", "to": "R_GRID", "weight": 0.25 },
        { "from": "R_GRID", "to": "R_GAS", "weight": 0.10 }
      ],
      "mode": "iterative" | "single_pass",
      "max_iterations": 8,
      "damping": 0.80,
      "tolerance": 0.0001
    }
    """
    if path is None:
        path = CONFIG_DIR / "cascade_map.json"

    try:
        data = read_json(path)
    except FileNotFoundError:
        print(f"WARNING: Cascade map file not found at {path}. Using no propagation.")
        return {
            "edges": [],
            "mode": "single_pass",
            "max_iterations": 1,
            "damping": 0.0,
            "tolerance": 1e-4,
        }

    return data


def build_influence_index(
    edges: List[Dict[str, Any]]
) -> DefaultDict[str, List[Tuple[str, float]]]:
    """
    Build an index mapping each 'to' risk to a list of (from, weight) pairs.
    """
    index: DefaultDict[str, List[Tuple[str, float]]] = defaultdict(list)
    for e in edges:
        src = e.get("from")
        dst = e.get("to")
        w = float(e.get("weight", 0.0))
        if src is None or dst is None:
            continue
        index[dst].append((src, w))
    return index


def run_cascade_layer(ccf_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Titan Cascade Layer (advanced).

    Modes:
      - single_pass: p_final(A) = p_ccf(A) + sum_B p_ccf(B) * w_{B->A}
      - iterative:   start p^(0) = p_ccf, then iterate

        p^(t+1)(A) = p_ccf(A) + damping * sum_B p^(t)(B) * w_{B->A}

      until max |p^(t+1) - p^(t)| < tolerance or max_iterations reached.
    """
    ccf_output: Dict[str, Dict[str, Any]] = ccf_result.get("ccf_output", {})
    cascade_cfg = load_cascade_map()
    edges = cascade_cfg.get("edges", [])
    mode = str(cascade_cfg.get("mode", "single_pass")).lower()
    max_iters = int(cascade_cfg.get("max_iterations", 1))
    damping = float(cascade_cfg.get("damping", 0.0))
    tolerance = float(cascade_cfg.get("tolerance", 1e-4))

    influence_index = build_influence_index(edges)

    cascade_output: Dict[str, Dict[str, Any]] = {}

    if not edges:
        # No propagation at all: p_final = p_ccf
        for rid, row in ccf_output.items():
            p_ccf = float(row.get("p_effective_ccf", 0.0))
            cascade_output[rid] = {
                "id": rid,
                "domain": row.get("domain", ""),
                "risk": row.get("risk", ""),
                "failure_class": row.get("failure_class", ""),
                "p_ccf": p_ccf,
                "p_final": p_ccf,
            }

        summary_text = (
            "Cascade Layer – no edges defined; p_final = p_ccf for all risks."
        )
        output_manager.append_section("CASCADE LAYER", summary_text)

        out = {
            "cascade_output": cascade_output,
            "diagnostics": {
                "edges_count": 0,
                "input_count": len(cascade_output),
                "mode": mode,
                "iterations_used": 0,
                "warnings": [],
            },
        }
        output_manager.write_P6_json_block("cascade_summary", out)
        return out

    # Initialize with p_ccf
    current: Dict[str, float] = {
        rid: float(row.get("p_effective_ccf", 0.0)) for rid, row in ccf_output.items()
    }
    base: Dict[str, float] = current.copy()

    iterations_used = 1
    if mode == "iterative":
        for it in range(max_iters):
            new_vals: Dict[str, float] = {}
            max_delta = 0.0

            for rid, row in ccf_output.items():
                p_ccf = base[rid]
                extra = 0.0
                for src_id, weight in influence_index.get(rid, []):
                    p_src = current.get(src_id, base.get(src_id, 0.0))
                    extra += p_src * float(weight)

                p_new = p_ccf + damping * extra
                p_new = max(0.0, min(0.99999, p_new))

                new_vals[rid] = p_new
                max_delta = max(max_delta, abs(p_new - current[rid]))

            current = new_vals
            iterations_used = it + 1
            if max_delta < tolerance:
                break
    else:
        # single_pass mode
        new_vals: Dict[str, float] = {}
        for rid, row in ccf_output.items():
            p_ccf = base[rid]
            extra = 0.0
            for src_id, weight in influence_index.get(rid, []):
                p_src = base.get(src_id, 0.0)
                extra += p_src * float(weight)
            p_new = p_ccf + extra
            p_new = max(0.0, min(0.99999, p_new))
            new_vals[rid] = p_new
        current = new_vals
        iterations_used = 1

    # Build cascade_output from final values
    for rid, row in ccf_output.items():
        p_ccf = base[rid]
        p_final = current[rid]
        cascade_output[rid] = {
            "id": rid,
            "domain": row.get("domain", ""),
            "risk": row.get("risk", ""),
            "failure_class": row.get("failure_class", ""),
            "p_ccf": p_ccf,
            "p_final": p_final,
        }

    # Human summary
    lines: List[str] = []
    lines.append(
        f"Cascade Layer – mode={mode}, iterations_used={iterations_used}, "
        f"damping={damping:.2f}"
    )
    for e in edges:
        lines.append(
            f"Edge {e.get('from')} -> {e.get('to')} "
            f"(w={float(e.get('weight', 0.0)):.2f})"
        )

    sorted_rows = sorted(
        cascade_output.values(), key=lambda x: x["p_final"], reverse=True
    )
    for row in sorted_rows[:5]:
        lines.append(
            f"- {row['domain']} | {row['risk']} | "
            f"p_final={row['p_final']:.4f} (p_ccf={row['p_ccf']:.4f})"
        )

    summary_text = "\n".join(lines)
    output_manager.append_section("CASCADE LAYER", summary_text)

    out = {
        "cascade_output": cascade_output,
        "diagnostics": {
            "edges_count": len(edges),
            "input_count": len(cascade_output),
            "mode": mode,
            "iterations_used": iterations_used,
            "warnings": [],
        },
    }
    output_manager.write_P6_json_block("cascade_summary", out)
    return out
