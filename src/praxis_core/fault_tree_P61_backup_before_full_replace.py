
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List

from . import output_manager
from ..utils.io import read_json

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"


def load_fault_tree(path: Path | None = None) -> Dict[str, Any]:
    """
    Load fault tree definition from JSON.
    """
    if path is None:
        path = CONFIG_DIR / "fault_tree_k_of_n.json"

    try:
        cfg = read_json(path)
    except FileNotFoundError:
        print(f"WARNING: Fault tree config not found at {path}. Using fallback.")
        return {"basic_events": [], "gates": [], "top_event": None}

    return cfg


def compute_k_of_n_probability(probs: List[float], k: int) -> float:
    """
    Compute P(at least k of N independent events occur) via Poisson-binomial DP.
    """
    n = len(probs)
    k = max(0, min(k, n))

    dp = [0.0] * (n + 1)
    dp[0] = 1.0

    for p in probs:
        new_dp = [0.0] * (n + 1)
        for j in range(0, n + 1):
            new_dp[j] += dp[j] * (1.0 - p)
            if j > 0:
                new_dp[j] += dp[j - 1] * p
        dp = new_dp

    return sum(dp[j] for j in range(k, n + 1))


def evaluate_event(
    event_id: str,
    basic_probs: Dict[str, float],
    gate_defs: Dict[str, Dict[str, Any]],
    cache: Dict[str, float],
) -> float:
    """
    Recursively evaluate the probability of an event (basic or gate).
    """
    if event_id in cache:
        return cache[event_id]

    if event_id in basic_probs and event_id not in gate_defs:
        p = basic_probs[event_id]
        cache[event_id] = p
        return p

    gate = gate_defs.get(event_id)
    if gate is None:
        cache[event_id] = 0.0
        return 0.0

    gate_type = str(gate.get("type", "OR")).upper()
    inputs = list(gate.get("inputs", []))

    child_probs = [evaluate_event(i, basic_probs, gate_defs, cache) for i in inputs]

    if gate_type == "AND":
        p_gate = 1.0
        for p in child_probs:
            p_gate *= p
    elif gate_type == "OR":
        p_not = 1.0
        for p in child_probs:
            p_not *= (1.0 - p)
        p_gate = 1.0 - p_not
    elif gate_type in ("K_OF_N", "KOFN", "KOFN_GATE"):
        k = int(gate.get("k", len(child_probs)))
        p_gate = compute_k_of_n_probability(child_probs, k)
    elif gate_type == "NOT":
        # Single-input NOT gate
        if not child_probs:
            p_gate = 0.0
        else:
            p_gate = 1.0 - child_probs[0]
    else:
        # Unknown gate type; treat as OR
        p_not = 1.0
        for p in child_probs:
            p_not *= (1.0 - p)
        p_gate = 1.0 - p_not

    cache[event_id] = p_gate
    return p_gate


def run_fault_tree_layer(cascade_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Titan Analytic Fault Tree layer (extended).
    """
    cascade_output: Dict[str, Dict[str, Any]] = cascade_result.get("cascade_output", {})
    ft_cfg = load_fault_tree()
    top_event_id = ft_cfg.get("top_event")
    gates = ft_cfg.get("gates", [])
    basic_events = ft_cfg.get("basic_events", [])

    # Map basic IDs -> probabilities from cascade layer
    basic_probs: Dict[str, float] = {}
    for rid, row in cascade_output.items():
        basic_probs[rid] = float(row.get("p_final", 0.0))

    gate_defs: Dict[str, Dict[str, Any]] = {g["id"]: g for g in gates if "id" in g}

    warnings: List[str] = []
    if not top_event_id:
        warnings.append("No top_event defined in fault tree config.")
    if not gates:
        warnings.append("No gates defined in fault tree config.")

    node_probs: Dict[str, float] = {}

    if not basic_probs:
        warnings.append("No cascade_output found; fault tree evaluation is trivial.")
        top_prob = 0.0
    else:
        cache: Dict[str, float] = {}
        if not top_event_id or (
            top_event_id not in gate_defs and top_event_id not in basic_probs
        ):
            top_event_id = "FALLBACK_MAX_P"
            top_prob = max(basic_probs.values())
            warnings.append(
                "Top event not found; using max basic probability as fallback."
            )
        else:
            top_prob = evaluate_event(top_event_id, basic_probs, gate_defs, cache)

        # Cache now contains probabilities for all visited nodes
        node_probs.update(cache)

        # Make sure all gate IDs have a probability
        for g_id in gate_defs.keys():
            if g_id not in node_probs:
                node_probs[g_id] = evaluate_event(g_id, basic_probs, gate_defs, cache)

        # Ensure all basic events have an entry
        for b_id, p in basic_probs.items():
            node_probs.setdefault(b_id, p)

    # Human summary
    lines: List[str] = []
    lines.append("Fault Tree (analytic, Titan+)")
    lines.append(f"Top event: {top_event_id}  p ≈ {top_prob:.4f}")
    if gates:
        lines.append("Gates (with probabilities):")
        for g in gates:
            g_id = g.get("id", "UNKNOWN")
            g_type = g.get("type", "OR")
            inputs = ", ".join(g.get("inputs", []))
            p_gate = node_probs.get(g_id, 0.0)
            lines.append(
                f"  - {g_id} [{g_type}] = f({inputs})  p≈{p_gate:.4f}"
            )

    summary_text = "\n".join(lines)
    output_manager.append_section("FAULT TREE (ANALYTIC)", summary_text)

    out = {
        "top_event_id": top_event_id,
        "top_event_probability": top_prob,
        "node_probabilities": node_probs,
        "diagnostics": {
            "gates_count": len(gates),
            "basic_event_count": len(basic_probs),
            "warnings": warnings,
        },
    }
    output_manager.write_P6_json_block("faulttree_summary", out)
    return out

