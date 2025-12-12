"""
PRAXIS P6.1 TITAN - Fault Tree Monte Carlo (Stub Implementation)

This module provides a minimal stub for the Monte Carlo fault-tree
engine so that imports of `fault_tree_mc` succeed and the engine runs
end-to-end.

For now, it simply:
  - Calls the analytic fault-tree evaluator to get p_top.
  - Reports that value as the Monte Carlo mean.
  - Uses [p_top, p_top] as a degenerate 95% CI.
  - Records the requested iteration count for bookkeeping.

You can later replace this with a full Monte Carlo implementation
without changing the public interface.
"""

from __future__ import annotations

from typing import Any, Dict, List

from . import fault_tree


def run_mc(
    cascade_results: List[Dict[str, Any]],
    ft_structure: Dict[str, Any],
    iterations: int = 10_000,
) -> Dict[str, Any]:
    """
    Minimal "Monte Carlo" stub.

    Parameters
    ----------
    cascade_results : list[dict]
        List of risk dicts with at least:
            - "id"
            - "p_final"

        This matches what engine.run_baseline_pipeline() passes in.

    ft_structure : dict
        Fault-tree definition (gates, top event ID, etc.).
        Passed through to fault_tree.evaluate_fault_tree.

    iterations : int
        Number of Monte Carlo iterations requested.
        Recorded in the output but not used for sampling in this stub.

    Returns
    -------
    dict
        {
          "p_top_mean": float | None,
          "CI_95": [low, high],
          "iterations": int,
          "notes": str,
        }
    """
    if not ft_structure:
        return {
            "p_top_mean": None,
            "CI_95": [None, None],
            "iterations": 0,
            "notes": "MC stub: no fault-tree structure provided.",
        }

    # Use the analytic engine as a stand-in for Monte Carlo.
    ft_analytic = fault_tree.evaluate_fault_tree(cascade_results, ft_structure)
    p_top = ft_analytic.get("p_top", None)

    if p_top is None:
        ci = [None, None]
    else:
        # Degenerate CI: no sampling yet, just echo p_top as both bounds.
        ci = [p_top, p_top]

    return {
        "p_top_mean": p_top,
        "CI_95": ci,
        "iterations": iterations,
        "notes": "MC stub: using analytic p_top as Monte Carlo mean.",
    }
