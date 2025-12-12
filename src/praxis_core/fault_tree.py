"""
PRAXIS P6.1 – Fault Tree Analytic Engine

Engine entrypoint used by engine.py and sensitivity.py:

    evaluate_fault_tree_analytic(
        top_event: str,
        gates: dict,
        basic_event_probs: dict[str, float],
    ) -> (float, dict[str, float])

Supported gate types (case-insensitive):

    "OR"   – P = 1 - ∏(1 - p_i)
    "AND"  – P = ∏ p_i
    "KOFN" – minimal K-of-N gate:
             gate["k"] = required successes (default 1 = OR)
"""

from __future__ import annotations

from math import prod
from typing import Any, Dict, Tuple


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _eval_kofn(inputs: list[float], k: int) -> float:
    """
    Simple exact K-of-N calculation via dynamic programming.
    inputs: list of probabilities p_1..p_n
    k: required number of successes
    """
    n = len(inputs)
    if n == 0:
        return 0.0
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0

    # dp[j] = probability of exactly j successes so far
    dp = [0.0] * (n + 1)
    dp[0] = 1.0

    for p in inputs:
        q = 1.0 - p
        new_dp = [0.0] * (n + 1)
        for j in range(0, n + 1):
            # failure branch
            new_dp[j] += dp[j] * q
            # success branch
            if j + 1 <= n:
                new_dp[j + 1] += dp[j] * p
        dp = new_dp

    return _clamp01(sum(dp[k:]))


def evaluate_fault_tree_analytic(
    top_event: str,
    gates: Dict[str, Any],
    basic_event_probs: Dict[str, float],
) -> Tuple[float, Dict[str, float]]:
    """
    Evaluate the fault tree analytically.

    Args:
        top_event: ID of the top event (string).
        gates: dict mapping gate_id -> { "type": "OR"/"AND"/"KOFN", "inputs": [...] }
        basic_event_probs: dict mapping basic_event_id -> probability in [0,1]

    Returns:
        (p_top, gate_outputs), where:
            p_top is the probability of the top event (float),
            gate_outputs maps gate_id -> probability.
    """
    if not isinstance(gates, dict):
        gates = {}

    # Cache of computed probabilities (gates + basic events)
    cache: Dict[str, float] = {}
    gate_outputs: Dict[str, float] = {}

    def eval_node(node_id: str) -> float:
        # Already computed?
        if node_id in cache:
            return cache[node_id]

        # Basic event
        if node_id in basic_event_probs:
            p = _clamp01(float(basic_event_probs[node_id]))
            cache[node_id] = p
            return p

        gate = gates.get(node_id)
        if not isinstance(gate, dict):
            # Unknown node → treat as probability 0
            cache[node_id] = 0.0
            return 0.0

        gate_type = str(gate.get("type", "OR")).upper()
        inputs = gate.get("inputs", [])
        if not isinstance(inputs, list):
            inputs = []

        # Recursively evaluate children
        child_probs = [eval_node(str(child_id)) for child_id in inputs]

        if not child_probs:
            p_gate = 0.0
        elif gate_type == "AND":
            p_gate = prod(child_probs)
        elif gate_type in ("KOFN", "K_OF_N", "K-OF-N"):
            try:
                k = int(gate.get("k", 1))
            except Exception:
                k = 1
            p_gate = _eval_kofn(child_probs, k)
        else:  # default OR
            p_gate = 1.0 - prod(1.0 - p for p in child_probs)

        p_gate = _clamp01(p_gate)
        cache[node_id] = p_gate
        gate_outputs[node_id] = p_gate
        return p_gate

    if not top_event:
        return 0.0, {}

    p_top = eval_node(str(top_event))
    return _clamp01(p_top), gate_outputs

