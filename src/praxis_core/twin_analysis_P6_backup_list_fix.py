"""
PRAXIS P6.1 – Adversarial Twin Engine (Defensive Version)

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

For each mode we generate several "twins", run the full baseline
pipeline on the perturbed scenario, and record:

    twin_id, mode, p_top, reliability, delta_p_top

This version is extra defensive about types, so we never call .get()
on a list or other non-dict object.
"""

from __future__ import annotations

import copy
import random
from typing import Any, Dict, List, Tuple, Optional

from . import engine  # reuse run_baseline_pipeline from engine.py


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_dict(obj: Any) -> Dict[str, Any]:
    """Return obj if it's a dict; otherwise an empty dict."""
    return obj if isinstance(obj, dict) else {}


def _get_baseline_p_top(baseline_pipeline: Any) -> float:
    """Extract a numeric baseline p_top if possible."""
    bp = _ensure_dict(baseline_pipeline)

    ft_analytic = _ensure_dict(bp.get("ft_analytic"))
    p_top = ft_analytic.get("p_top")

    if isinstance(p_top, (int, float)):
        return float(p_top)

    # Fallback to MC if available
    ft_mc = _ensure_dict(bp.get("ft_mc"))
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


def _iter_mode_config(twin_config: Any) -> List[Tuple[str, int]]:
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
    cfg = _ensure_dict(twin_config)
    modes_cfg = _ensure_dict(cfg.get("modes"))

    out: List[Tuple[str, int]] = []
    for mode in ("optimistic", "pessimistic", "chaotic"):
        m_cfg = _ensure_dict(modes_cfg.get(mode))
        try:
            count = int(m_cfg.get("count", default_count))
        except Exception:
            count = default_count
        out.append((mode, count))

    return out


def _extract_reliability(twin_pipeline: Any) -> Optional[float]:
    """Get reliability value from a pipeline dict, if present."""
    tp = _ensure_dict(twin_pipeline)
    rel_block = _ensure_dict(tp.get("reliability"))
    val = rel_block.get("reliability")
    if isinstance(val, (int, float)):
        return float(val)
    return None


def _extract_p_top(twin_pipeline: Any) -> float:
    """Get p_top (analytic) from a pipeline dict, if present."""
    tp = _ensure_dict(twin_pipeline)
    ft_analytic = _ensure_dict(tp.get("ft_analytic"))
    p_top = ft_analytic.get("p_top")
    if isinstance(p_top, (int, float)):
        return float(p_top)
    return 0.0


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
               "p_top": float | None,
               "reliability": float | None,
               "delta_p_top": float | None,
               "error": str | optional
             },
             ...
          ]
        }
    """
    # Safety: if baseline_pipeline somehow isn't a dict, bail out cleanly
    if not isinstance(baseline_pipeline, dict):
        return {
            "baseline_p_top": 0.0,
            "twins": [],
        }

    # Make randomness deterministic-ish per run
    random.seed(1337)

    baseline_p_top = _get_baseline_p_top(baseline_pipeline)
    twins: List[Dict[str, Any]] = []

    mode_plan = _iter_mode_config(twin_config)

    # Pull the base risks list safely
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
                twins.append(
                    {
                        "twin_id": f"{mode}_{idx:02d}",
                        "mode": mode,
                        "p_top": None,
                        "reliability": None,
                        "delta_p_top": None,
                        "error": f"pipeline_error: {e}",
                    }
                )
                continue

            if not isinstance(twin_pipeline, dict):
                twins.append(
                    {
                        "twin_id": f"{mode}_{idx:02d}",
                        "mode": mode,
                        "p_top": None,
                        "reliability": None,
                        "delta_p_top": None,
                        "error": "twin_pipeline_not_dict",
                    }
                )
                continue

            p_top = _extract_p_top(twin_pipeline)
            rel_value = _extract_reliability(twin_pipeline)
            delta = p_top - baseline_p_top

            twins.append(
                {
                    "twin_id": f"{mode}_{idx:02d}",
                    "mode": mode,
                    "p_top": p_top,
                    "reliability": rel_value,
                    "delta_p_top": delta,
                }
            )

    return {
        "baseline_p_top": baseline_p_top,
        "twins": twins,
    }

