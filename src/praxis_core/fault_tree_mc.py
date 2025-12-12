"""
PRAXIS P6.1 – Fault Tree Monte Carlo Engine

Entry point used by engine.py:

    run_mc(
        final_probs: dict[str, float],
        fault_tree_struct: dict,
        iterations: int = 10_000,
    ) -> dict

We sample each basic event as a Bernoulli(p) and evaluate the same
gate structure as in the analytic engine, but with booleans.
"""

from __future__ import annotations

import random
from typing import Any, Dict, Tuple


def _eval_gate_bool(
    node_id: str,
    basic_state: Dict[str, bool],
    gates: Dict[str, Any],
    cache: Dict[str, bool],
) -> bool:
    if node_id in cache:
        return cache[node_id]

    if node_id in basic_state:
        val = bool(basic_state[node_id])
        cache[node_id] = val
        return val

    gate = gates.get(node_id)
    if not isinstance(gate, dict):
        cache[node_id] = False
        return False

    gate_type = str(gate.get("type", "OR")).upper()
    inputs = gate.get("inputs", [])
    if not isinstance(inputs, list):
        inputs = []

    child_vals = [_eval_gate_bool(str(ch), basic_state, gates, cache) for ch in inputs]

    if not child_vals:
        val = False
    elif gate_type == "AND":
        val = all(child_vals)
    elif gate_type in ("KOFN", "K_OF_N", "K-OF-N"):
        try:
            k = int(gate.get("k", 1))
        except Exception:
            k = 1
        val = sum(1 for v in child_vals if v) >= k
    else:  # OR
        val = any(child_vals)

    cache[node_id] = val
    return val


def run_mc(
    final_probs: Dict[str, float],
    fault_tree_struct: Dict[str, Any],
    iterations: int = 10_000,
) -> Dict[str, Any]:
    """
    Monte Carlo fault tree evaluation.

    final_probs: dict of basic_event_id -> probability
    fault_tree_struct: {"top_event": "...", "gates": {...}}
    """
    top_event = str(fault_tree_struct.get("top_event", ""))
    gates = fault_tree_struct.get("gates", {}) or {}

    if not top_event:
        return {
            "iterations": iterations,
            "p_top_mean": 0.0,
        }

    top_count = 0

    basic_ids = list(final_probs.keys())

    for _ in range(iterations):
        # Sample basic events
        basic_state: Dict[str, bool] = {}
        for rid in basic_ids:
            p = float(final_probs.get(rid, 0.0))
            basic_state[rid] = random.random() < p

        cache_bool: Dict[str, bool] = {}
        if _eval_gate_bool(top_event, basic_state, gates, cache_bool):
            top_count += 1

    p_mean = float(top_count) / float(iterations) if iterations > 0 else 0.0

    return {
        "iterations": iterations,
        "p_top_mean": p_mean,
    }

