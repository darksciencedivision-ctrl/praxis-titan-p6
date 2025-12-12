from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Dict, Any, List

from . import output_manager
from ..utils.io import read_json

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"


def load_fault_tree(path: Path | None = None) -> Dict[str, Any]:
    if path is None:
        path = CONFIG_DIR / "fault_tree_k_of_n.json"
    try:
        return read_json(path)
    except FileNotFoundError:
        print(f"WARNING: Fault tree config not found at {path}. Monte Carlo fallback.")
        return {"basic_events": [], "gates": [], "top_event": None}


def evaluate_event_bool(
    event_id: str,
    basic_sample: Dict[str, bool],
    gate_defs: Dict[str, Dict[str, Any]],
    cache: Dict[str, bool],
) -> bool:
    """
    Evaluate the event as a boolean given sampled basic events.
    """
    if event_id in cache:
        return cache[event_id]

    if event_id in basic_sample and event_id not in gate_defs:
        val = basic_sample[event_id]
        cache[event_id] = val
        return val

    gate = gate_defs.get(event_id)
    if gate is None:
        cache[event_id] = False
        return False

    gate_type = str(gate.get("type", "OR")).upper()
    inputs = list(gate.get("inputs", []))

    child_vals = [evaluate_event_bool(i, basic_sample, gate_defs, cache) for i in inputs]

    if gate_type == "AND":
        val = all(child_vals)
    elif gate_type == "OR":
        val = any(child_vals)
    elif gate_type in ("K_OF_N", "KOFN", "KOFN_GATE"):
        k = int(gate.get("k", len(child_vals)))
        val = sum(1 for v in child_vals if v) >= k
    else:
        # Unknown gate type: treat as OR
        val = any(child_vals)

    cache[event_id] = val
    return val


def run_fault_tree_mc_layer(
    ft_result: Dict[str, Any],
    iterations: int = 10000,
) -> Dict[str, Any]:
    """
    Monte Carlo simulation of the top event.

    - Uses p_final from Cascade as Bernoulli parameters for basic events.
    - Evaluates the same gate structure as the analytic layer.
    """
    from . import fault_tree as ft_analytic  # local import to avoid circular

    # Read cascade output via analytic layer's expectations
    # The analytic layer already ran, so ft_result is available, but we still
    # need cascade probabilities from the last run. For simplicity, we
    # re-load them from the written JSON is an option, but here we assume
    # the caller passes cascade probabilities externally via engine.
    # In this design, we only need the basic event IDs and use their
    # probabilities from ft_result's context when available.

    # For now, Monte Carlo will re-derive basic probabilities from analytic's
    # top-event surroundings is too complex; instead we read them from the
    # last cascade_summary.json for consistency.
    cascade_path = BASE_DIR / "output" / "P6" / "cascade_summary.json"
    try:
        cascade_data = read_json(cascade_path)
        cascade_output = cascade_data.get("cascade_output", {})
    except FileNotFoundError:
        cascade_output = {}

    basic_probs: Dict[str, float] = {
        rid: float(row.get("p_final", 0.0)) for rid, row in cascade_output.items()
    }

    ft_cfg = load_fault_tree()
    top_event_id = ft_cfg.get("top_event")
    gates = ft_cfg.get("gates", [])
    gate_defs: Dict[str, Dict[str, Any]] = {g["id"]: g for g in gates if "id" in g}

    warnings: List[str] = []

    if not top_event_id:
        warnings.append("No top_event defined in fault tree config (MC).")

    if not basic_probs:
        warnings.append("No cascade_output found; Monte Carlo is trivial.")
        p_mean = 0.0
        ci_low = 0.0
        ci_high = 0.0
    else:
        if not top_event_id or (
            top_event_id not in gate_defs and top_event_id not in basic_probs
        ):
            # Fallback: treat top event as OR over all basic events
            warnings.append(
                "Top event not found in FT config for MC; using OR of all basic events."
            )
            # Fake gate
            gate_defs["__OR_ALL__"] = {
                "id": "__OR_ALL__",
                "type": "OR",
                "inputs": list(basic_probs.keys()),
            }
            top_event_id = "__OR_ALL__"

        # Run MC
        successes = 0
        for _ in range(iterations):
            # Sample basic events
            basic_sample = {
                rid: (random.random() < p)
                for rid, p in basic_probs.items()
            }
            cache_bool: Dict[str, bool] = {}
            if evaluate_event_bool(top_event_id, basic_sample, gate_defs, cache_bool):
                successes += 1

        p_mean = successes / float(iterations)

        # Normal-approx CI
        if iterations > 0:
            stderr = math.sqrt(max(p_mean * (1.0 - p_mean), 1e-12) / iterations)
            ci_low = max(0.0, p_mean - 1.96 * stderr)
            ci_high = min(1.0, p_mean + 1.96 * stderr)
        else:
            ci_low = ci_high = p_mean

    summary_text = (
        "Fault Tree (Monte Carlo, Titan)\n"
        f"Top event: {top_event_id}\n"
        f"p_mean ≈ {p_mean:.4f}, 95% CI ≈ [{ci_low:.4f}, {ci_high:.4f}] "
        f"(iterations={iterations})"
    )
    output_manager.append_section("FAULT TREE (MONTE CARLO)", summary_text)

    out = {
        "monte_carlo": {
            "top_event_id": top_event_id,
            "p_mean": p_mean,
            "ci_95_low": ci_low,
            "ci_95_high": ci_high,
            "iterations": iterations,
        },
        "diagnostics": {
            "warnings": warnings,
        },
    }
    output_manager.write_P6_json_block("faulttree_montecarlo", out)
    return out
