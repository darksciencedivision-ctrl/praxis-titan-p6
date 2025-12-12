"""
PRAXIS P6.1 – One-at-a-Time Sensitivity Engine

Engine entrypoint (called from engine.py):

    run_sensitivity(
        scenario: dict,
        priors: dict,
        baseline_pipeline: dict,
    ) -> dict

We take the baseline final probabilities from the pipeline, then for each
risk in scenario["risks"] we sweep multiplicative factors:

    FACTORS = [0.5, 0.75, 1.0, 1.25, 1.5]

For each factor we:

    - clone the baseline final_probs
    - multiply that risk's probability by the factor (clamped to [0,1])
    - recompute the fault tree analytically
    - record Δp_top relative to baseline p_top

The output is:

    {
      "factors": FACTORS,
      "baseline_p_top": float,
      "risks": [
        {
          "id": "R_GAS",
          "domain": "Gas",
          "name": "Compressor backbone trip",
          "delta_p_top_max": 0.0359,
        },
        ...
      ]
    }
"""

from __future__ import annotations

from typing import Any, Dict, List

from . import fault_tree


FACTORS = [0.5, 0.75, 1.0, 1.25, 1.5]


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _get_baseline_final_probs(baseline_pipeline: Dict[str, Any]) -> Dict[str, float]:
    """
    Try multiple places in the baseline pipeline to find a mapping
    of risk_id -> probability.
    """
    # Preferred: cascade final_probs
    cascade_block = baseline_pipeline.get("cascade")
    if isinstance(cascade_block, dict):
        probs = cascade_block.get("final_probs")
        if isinstance(probs, dict):
            return {str(k): float(v) for k, v in probs.items()}

    # Fallback: CCF probs
    ccf_block = baseline_pipeline.get("ccf")
    if isinstance(ccf_block, dict):
        probs = ccf_block.get("probs")
        if isinstance(probs, dict):
            return {str(k): float(v) for k, v in probs.items()}

    # Fallback: Bayes posterior_probs
    bayes_block = baseline_pipeline.get("bayes")
    if isinstance(bayes_block, dict):
        probs = bayes_block.get("posterior_probs")
        if isinstance(probs, dict):
            return {str(k): float(v) for k, v in probs.items()}

    # Last resort: treat numeric results as a list of rows
    numeric_block = baseline_pipeline.get("numeric")
    if isinstance(numeric_block, list):
        out: Dict[str, float] = {}
        for row in numeric_block:
            if not isinstance(row, dict):
                continue
            rid = row.get("id") or row.get("risk_id")
            if not rid:
                continue
            p = (
                row.get("p_base")
                or row.get("likelihood")
                or row.get("p")
                or 0.0
            )
            out[str(rid)] = float(p)
        return out

    return {}


def _get_baseline_p_top(baseline_pipeline: Dict[str, Any]) -> float:
    ft_analytic = baseline_pipeline.get("ft_analytic", {}) or {}
    p_top = ft_analytic.get("p_top")
    if isinstance(p_top, (int, float)):
        return float(p_top)
    return 0.0


def run_sensitivity(
    scenario: Dict[str, Any],
    priors: Dict[str, Any],   # unused for now, kept for future extensions
    baseline_pipeline: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Perform one-at-a-time sensitivity sweeps on each risk.

    Returns:
        {
          "factors": FACTORS,
          "baseline_p_top": float,
          "risks": [
            {
              "id": ...,
              "domain": ...,
              "name": ...,
              "delta_p_top_max": float,
            },
            ...
          ]
        }
    """
    final_probs = _get_baseline_final_probs(baseline_pipeline)
    baseline_p_top = _get_baseline_p_top(baseline_pipeline)

    ft_struct = scenario.get("fault_tree", {}) or {}
    top_event = ft_struct.get("top_event")
    gates = ft_struct.get("gates", {}) or {}

    risks_cfg = scenario.get("risks", [])
    if not isinstance(risks_cfg, list):
        risks_cfg = []

    out_risks: List[Dict[str, Any]] = []

    for row in risks_cfg:
        if not isinstance(row, dict):
            continue

        rid = row.get("id") or row.get("risk_id")
        if not rid:
            continue
        rid = str(rid)

        domain = row.get("domain", "")
        name = row.get("risk", row.get("name", ""))

        base_p = final_probs.get(rid, 0.0)

        max_abs_delta = 0.0

        for f in FACTORS:
            # Build new probability map
            new_probs = dict(final_probs)
            new_probs[rid] = _clamp01(base_p * float(f))

            try:
                p_top, _gate_outputs = fault_tree.evaluate_fault_tree_analytic(
                    top_event, gates, new_probs
                )
            except Exception:
                # If the fault tree blows up for this factor, skip it
                continue

            if not isinstance(p_top, (int, float)):
                continue

            delta = float(p_top) - baseline_p_top
            if abs(delta) > max_abs_delta:
                max_abs_delta = abs(delta)

        out_risks.append(
            {
                "id": rid,
                "domain": domain,
                "name": name,
                "delta_p_top_max": max_abs_delta,
            }
        )

    return {
        "factors": list(FACTORS),
        "baseline_p_top": baseline_p_top,
        "risks": out_risks,
    }

