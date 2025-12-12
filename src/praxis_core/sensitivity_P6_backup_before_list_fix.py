"""
PRAXIS P6.1 TITAN - Sensitivity Analysis Engine (Analytic-Only)

This module computes simple one-at-a-time sensitivity of the top
fault-tree event to multiplicative changes in each risk's likelihood.

Pipeline per perturbed scenario:

    numeric → bayes → CCF → cascade → fault_tree (analytic) → reliability

No Monte Carlo is used here to avoid heavy runtime and circular imports.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from . import (
    numeric,
    bayes,
    ccf,
    cascade,
    fault_tree,
    reliability,
)


# ---------------------------------------------------------------------------
# Internal analytic pipeline for a single scenario
# ---------------------------------------------------------------------------

def _run_pipeline_for_scenario(
    scenario: Dict[str, Any],
    priors: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Run the analytic pipeline (no MC) for a given scenario.
    """
    risks: List[Dict[str, Any]] = scenario.get("risks", [])

    # 1. Numeric
    numeric_results = numeric.compute_numeric_risks(risks)

    # 2. Bayesian
    bayes_results = bayes.bayes_update(numeric_results, priors)

    # 3. CCF
    ccf_results = ccf.apply_ccf(bayes_results)

    # 4. Cascade
    cascade_results = cascade.propagate(ccf_results)

    # 5. Fault-tree analytic
    ft_structure = scenario.get("fault_tree", {})
    ft_analytic = fault_tree.evaluate_fault_tree(cascade_results, ft_structure)

    # 6. Reliability
    rel_result = reliability.compute_reliability(
        p_top_event=ft_analytic.get("p_top")
    )

    return {
        "numeric": numeric_results,
        "bayes": bayes_results,
        "ccf": ccf_results,
        "cascade": cascade_results,
        "ft_analytic": ft_analytic,
        "reliability": rel_result,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_sensitivity(
    scenario: Dict[str, Any],
    priors: Dict[str, Any],
    baseline_pipeline: Dict[str, Any],
    factors: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Compute one-at-a-time sensitivity of the top-event probability
    to multiplicative changes in each risk's likelihood.

    Parameters
    ----------
    scenario : dict
        Baseline scenario used in the main run.
    priors : dict
        Bayesian priors.
    baseline_pipeline : dict
        Output of the baseline pipeline; used to get baseline p_top.
    factors : list[float] | None
        Multiplicative factors to apply to each risk's likelihood.
        Default: [0.5, 0.75, 1.0, 1.25, 1.5]

    Returns
    -------
    dict
        {
          "factors": [...],
          "risks": [
            {
              "id": str,
              "domain": str,
              "name": str,
              "delta_p_top_max": float | None
            },
            ...
          ],
          "detailed": {
            risk_id: [
              {
                "factor": float,
                "p_top": float | None,
                "delta_p_top": float | None
              },
              ...
            ]
          }
        }
    """
    if factors is None:
        factors = [0.5, 0.75, 1.0, 1.25, 1.5]

    # Baseline top-event probability
    baseline_ft = baseline_pipeline.get("ft_analytic", {}) or {}
    baseline_p_top = baseline_ft.get("p_top", None)

    base_risks: List[Dict[str, Any]] = scenario.get("risks", [])

    detailed: Dict[str, List[Dict[str, Any]]] = {}
    risk_summaries: List[Dict[str, Any]] = []

    for risk in base_risks:
        rid = str(risk.get("id", "UNKNOWN_ID"))
        domain = risk.get("domain", "UNKNOWN_DOMAIN")
        name = risk.get("risk", "UNKNOWN_RISK")

        detailed[rid] = []
        max_delta_abs: Optional[float] = None

        for f in factors:
            # Build a perturbed scenario where ONLY this risk's likelihood
            # is scaled by factor f (clamped to (0, 1)).
            perturbed_scn = copy.deepcopy(scenario)
            for r2 in perturbed_scn.get("risks", []):
                if str(r2.get("id", "")) == rid:
                    base_like = float(r2.get("likelihood", 0.5))
                    new_like = base_like * float(f)
                    new_like = max(0.00001, min(0.99999, new_like))
                    r2["likelihood"] = new_like
                    break

            pipe = _run_pipeline_for_scenario(
                scenario=perturbed_scn,
                priors=priors,
            )

            ft_analytic = pipe.get("ft_analytic", {}) or {}
            p_top = ft_analytic.get("p_top", None)

            if baseline_p_top is not None and p_top is not None:
                delta = p_top - baseline_p_top
                delta_abs = abs(delta)
            else:
                delta = None
                delta_abs = None

            if delta_abs is not None:
                if max_delta_abs is None or delta_abs > max_delta_abs:
                    max_delta_abs = delta_abs

            detailed[rid].append(
                {
                    "factor": f,
                    "p_top": p_top,
                    "delta_p_top": delta,
                }
            )

        risk_summaries.append(
            {
                "id": rid,
                "domain": domain,
                "name": name,
                "delta_p_top_max": max_delta_abs,
            }
        )

    return {
        "factors": factors,
        "risks": risk_summaries,
        "detailed": detailed,
    }
