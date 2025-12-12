"""
PRAXIS P6.1 – Adversarial Twin Engine

This module provides a single entrypoint used by engine.py:

    run_twin_engine(
        scenario: dict,
        priors: dict,
        twin_config: dict,
        baseline_pipeline: dict,
        mc_iterations: int = 10_000,
    ) -> dict

It implements three modes:

    optimistic:   likelihood *= U(0.8, 1.0); severity += U(-1, 0)
    pessimistic:  likelihood *= U(1.0, 1.5); severity += U(0, 1)
    chaotic:      likelihood *= U(0.8, 1.5); severity += U(-1, 1)

For each mode we generate several "twins" (default 6 each = 18 total),
run the full baseline pipeline on the perturbed scenario, and record:

    twin_id, mode, p_top, reliability, delta_p_top
"""

from __future__ import annotations

import copy
import random
from typing import Any, Dict, List, Tuple

from . import engine  # to reuse run_baseline_pipeline from engine.py


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_baseline_p_top(baseline_pipeline: Dict[str, Any]) -> float:
    """Extract a numeric baseline p_top if possible."""
    ft_analytic = baseline_pipeline.get("ft_analytic", {}) or {}
    p_top = ft_analytic.get("p_top")

    if isinstance(p_top, (int, float)):
        return float(p_top)

    # Fallback to MC if available
    ft_mc = baseline_pipeline.get("ft_mc", {}) or {}
    p_mc = ft_mc.get("p_top_mean")
    if isinstance(p_mc, (int, float)):
        return float(p_mc)

    return 0.0


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _apply_mode_to_risk(risk: Dict[str, Any], mode: str) -> None:
    """
    In-place modification of a single risk according to the desired mode.
    Expects keys: 'likelihood' and 'severity' if available.
    """
    p = risk.get("likelihood")
    sev = risk.get("severity")

    try:
        p = float(p)
    except Exception:
        p = 0.0

    try:
        sev = float(sev)
    except Exception:
        sev = 0.0

    if mode == "optimistic":
        mult = random.uniform(0.8, 1.0)
        sev_delta = random.uniform(-1.0, 0.0)
    elif mode == "pessimistic":
        mult = random.uniform(1.0, 1.5)
        sev_delta = random.uniform(0.0, 1.0)
    else:  # "chaotic"
        mult = random.uniform(0.8, 1.5)
        sev_delta = random.uniform(-1.0, 1.0)

    p_new = _clamp01(p * mult)
    sev_new = sev + sev_delta

    risk["likelihood"] = p_new
    risk["severity"] = sev_new


def _iter_mode_config(twin_config: Dict[str, Any]) -> List[Tuple[str, int]]:
    """
    Determine how many twins to generate per mode.

    twin_config may look like:

        {
          "modes": {
             "optimistic": {"count": 6},
             "pessimistic": {"count": 6},
             "chaotic": {"count": 6}
          }
        }

    If not provided, defaults to 6 per mode.
    """
    default_count = 6
    modes_cfg = (twin_config or {}).get("modes", {})

    out: List[Tuple[str, int]] = []
    for mode in ("optimistic", "pessimistic", "chaotic"):
        cfg = modes_cfg.get(mode, {})
        try:
            count = int(cfg.get("count", default_count))
        except Exception:
            count = default_count
        out.append((mode, count))

    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_twin_engine(
    scenario: Dict[str, Any],
    priors: Dict[str, Any],
    twin_config: Dict[str, Any],
    baseline_pipeline: Dict[str, Any],
    mc_iterations: int = 10_000,
) -> Dict[str, Any]:
    """
    Generate adversarial twins, run the full pipeline on each, and return results.

    Returns:
        {
          "baseline_p_top": float,
          "twins": [
             {
               "twin_id": "optimistic_01",
               "mode": "optimistic",
               "p_top": float,
               "reliability": float | None,
               "delta_p_top": float,
             },
             ...
          ]
        }
    """
    # Make randomness deterministic-ish per run
    random.seed(1337)

    baseline_p_top = _get_baseline_p_top(baseline_pipeline)
    twins: List[Dict[str, Any]] = []

    mode_plan = _iter_mode_config(twin_config)

    # Pre-extract base scenario risks list
    base_risks = scenario.get("risks", [])
    if not isinstance(base_risks, list):
        base_risks = []

    for mode, count in mode_plan:
        for idx in range(1, count + 1):
            # Clone the scenario so we can safely mutate
            twin_scenario = copy.deepcopy(scenario)

            twin_risks = twin_scenario.get("risks", [])
            if not isinstance(twin_risks, list):
                twin_risks = []

            # Apply mode perturbations to each risk
            for r in twin_risks:
                if isinstance(r, dict):
                    _apply_mode_to_risk(r, mode)

            # Run full baseline pipeline on perturbed scenario
            try:
                twin_pipeline = engine.run_baseline_pipeline(
                    scenario=twin_scenario,
                    priors=priors,
                    mc_iterations=mc_iterations,
                )
            except Exception as e:
                # If something goes wrong, record a stub and continue
                twins.append(
                    {
                        "twin_id": f"{mode}_{idx:02d}",
                        "mode": mode,
                        "p_top": None,
                        "reliability": None,
                        "delta_p_top": None,
                        "error": str(e),
                    }
                )
                continue

            ft_analytic = twin_pipeline.get("ft_analytic", {}) or {}
            p_top = ft_analytic.get("p_top")
            if not isinstance(p_top, (int, float)):
                p_top = 0.0
            p_top = float(p_top)

            rel_block = twin_pipeline.get("reliability", {}) or {}
            reliability_value = rel_block.get("reliability")
            if isinstance(reliability_value, (int, float)):
                reliability_value = float(reliability_value)
            else:
                reliability_value = None

            delta = p_top - baseline_p_top

            twins.append(
                {
                    "twin_id": f"{mode}_{idx:02d}",
                    "mode": mode,
                    "p_top": p_top,
                    "reliability": reliability_value,
                    "delta_p_top": delta,
                }
            )

    return {
        "baseline_p_top": baseline_p_top,
        "twins": twins,
    }

