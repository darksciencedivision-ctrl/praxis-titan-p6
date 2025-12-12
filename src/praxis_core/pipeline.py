"""
pipeline.py

PRAXIS v1.1 Titan – main orchestration pipeline.

Flow:
  Scenario JSON
    -> numeric.compute_numeric_risks
    -> bayes.bayes_update
    -> ccf.apply_ccf_groups
    -> cascade.run_cascade_engine
    -> fault_tree (analytic + Monte Carlo)

Always returns a dict with keys:
  - numeric
  - bayes
  - ccf
  - cascade
  - fault_tree
  - reliability
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from . import numeric
from . import bayes
from . import ccf
from . import cascade
from . import fault_tree


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Optional[str], default: Any) -> Any:
    """
    Load JSON from 'path' if it exists, otherwise return 'default'.
    """
    if not path:
        return default

    p = Path(path)
    if not p.is_file():
        print(f"WARNING: Config file not found: {path}")
        return default

    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"WARNING: Failed to load JSON from {path}: {e}")
        return default


def _write_summary(out_dir_path: Path, result: Dict[str, Any]) -> None:
    summary_path = out_dir_path / "praxis_output_summary.json"
    try:
        with summary_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Wrote output summary to: {summary_path}")
    except Exception as e:
        print(f"WARNING: Failed to write summary JSON: {e}")


# ---------------------------------------------------------------------------
# Main orchestration function
# ---------------------------------------------------------------------------

def run_scenario(
    *,
    scenario_config_path: str,
    priors_path: Optional[str] = None,
    ccf_groups_path: Optional[str] = None,
    fault_tree_config_path: Optional[str] = None,
    cascade_config_path: Optional[str] = None,
    out_dir: Optional[str] = None,
    pseudo_n: float = 5.0,
    write_report: bool = True,  # kept for compatibility; not used here
) -> Dict[str, Any]:
    """
    Run a full PRAXIS scenario and return a result dictionary.
    """

    # Ensure output directory exists
    out_dir_path = Path(out_dir or ".").resolve()
    out_dir_path.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1) Load scenario
    # ------------------------------------------------------------------
    scenario_cfg = _load_json(scenario_config_path, default={"risks": []})
    if not isinstance(scenario_cfg, dict) or not scenario_cfg.get("risks"):
        print("ERROR: No valid scenario configuration loaded. Aborting.")
        empty = {"numeric": {}, "bayes": {}, "ccf": {}, "cascade": {},
                 "fault_tree": {}, "reliability": {}}
        _write_summary(out_dir_path, empty)
        return empty

    # ------------------------------------------------------------------
    # 2) Numeric layer
    # ------------------------------------------------------------------
    try:
        numeric_result: Dict[str, Any] = numeric.compute_numeric_risks(scenario_cfg)
        basic_probs_numeric: Dict[str, float] = numeric_result.get("basic_probs", {})
    except Exception as e:
        print(f"ERROR: Numeric layer failed: {e}")
        numeric_result = {"error": str(e)}
        basic_probs_numeric = {}

    # ------------------------------------------------------------------
    # 3) Bayes layer
    # ------------------------------------------------------------------
    try:
        bayes_result: Dict[str, Any] = bayes.bayes_update(
            basic_probs=basic_probs_numeric,
            priors_path=priors_path,
            pseudo_n=pseudo_n,
        )
    except TypeError:
        # Fallback for older API that takes priors_cfg
        try:
            priors_cfg = _load_json(priors_path, default=None)
            bayes_result = bayes.bayes_update(
                basic_probs=basic_probs_numeric,
                priors_cfg=priors_cfg,
                pseudo_n=pseudo_n,
            )
        except Exception as e:
            print(f"ERROR: Bayes layer failed: {e}")
            bayes_result = {"error": str(e)}
    except Exception as e:
        print(f"ERROR: Bayes layer failed: {e}")
        bayes_result = {"error": str(e)}

    posterior_probs: Dict[str, float] = bayes_result.get(
        "posterior_probs", basic_probs_numeric
    )

    # ------------------------------------------------------------------
    # 4) CCF layer
    # ------------------------------------------------------------------
    ccf_groups_cfg: Dict[str, Any] = _load_json(ccf_groups_path, default={})

    try:
        if ccf_groups_cfg:
            ccf_result = ccf.apply_ccf_groups(
                probs=posterior_probs,
                ccf_groups_cfg=ccf_groups_cfg,
            )
            if isinstance(ccf_result, dict) and "probs" in ccf_result:
                ccf_probs = ccf_result["probs"]
            elif isinstance(ccf_result, dict):
                ccf_probs = ccf_result
            else:
                ccf_probs = posterior_probs
        else:
            ccf_probs = posterior_probs
    except Exception as e:
        print(f"WARNING: CCF layer failed: {e}")
        ccf_probs = posterior_probs

    # ------------------------------------------------------------------
    # 5) Cascade layer
    # ------------------------------------------------------------------
    cascade_cfg: Dict[str, Any] = _load_json(cascade_config_path, default={})

    cascade_results: Optional[Dict[str, Any]] = None
    final_probs: Dict[str, float] = dict(ccf_probs)

    if cascade_cfg:
        try:
            cascade_results = cascade.run_cascade_engine(
                base_probs=ccf_probs,
                cascade_cfg=cascade_cfg,
            )
            if isinstance(cascade_results, dict):
                eff = cascade_results.get("effective_probs")
                if isinstance(eff, dict):
                    final_probs = {k: float(v) for k, v in eff.items()}
        except Exception as e:
            print(f"WARNING: Cascade engine failed: {e}")
            cascade_results = {"error": str(e)}
            final_probs = dict(ccf_probs)

    # ------------------------------------------------------------------
    # Base output structure
    # ------------------------------------------------------------------
    praxis_output: Dict[str, Any] = {
        "numeric": numeric_result,
        "bayes": bayes_result,
        "ccf": {"probs": ccf_probs, "cfg": ccf_groups_cfg},
        "cascade": {
            "results": cascade_results,
            "final_probs": final_probs,
            "cfg": cascade_cfg,
        },
    }

    # ------------------------------------------------------------------
    # 6) Fault Tree (analytic + Monte Carlo)
    # ------------------------------------------------------------------
    fault_tree_output: Dict[str, Any] = {}

    if fault_tree_config_path:
        ft_cfg = _load_json(fault_tree_config_path, default=None)

        if isinstance(ft_cfg, dict):
            top_event = ft_cfg.get("top_event") or ft_cfg.get("top_event_id")
            gates_cfg = ft_cfg.get("gates", {})

            mc_samples = int(
                ft_cfg.get("mc_samples")
                or ft_cfg.get("monte_carlo", {}).get("n_samples", 100_000)
            )

            # Build a clean mapping from scenario risks
            basic_event_probs: Dict[str, float] = {}
            for row in scenario_cfg.get("risks", []):
                rid = (
                    row.get("id")
                    or row.get("risk_id")
                    or f"{row.get('domain', '')}_{row.get('risk', '')}_{row.get('failure_class', '')}".strip("_")
                )
                if rid:
                    basic_event_probs[rid] = float(row.get("likelihood", 0.0))

            # Overlay any updated probs from upstream chain
            for k, v in final_probs.items():
                basic_event_probs[k] = float(v)

            fault_tree_output["top_event"] = top_event
            fault_tree_output["basic_event_probs"] = basic_event_probs
            fault_tree_output["mc_samples"] = mc_samples

            # Analytic
            try:
                p_top_analytic, gate_outputs = fault_tree.evaluate_fault_tree_analytic(
                    top_event,
                    gates_cfg,
                    basic_event_probs,
                )
                if isinstance(p_top_analytic, (int, float)) and p_top_analytic < 0.0:
                    fault_tree_output["p_top_analytic"] = "N/A"
                else:
                    fault_tree_output["p_top_analytic"] = p_top_analytic
                fault_tree_output["gate_outputs"] = gate_outputs
            except Exception as e:
                print(f"WARNING: Analytic fault-tree evaluation failed: {e}")
                fault_tree_output["p_top_analytic"] = "N/A"

            # Monte Carlo
            try:
                mc_result = fault_tree.run_fault_tree_monte_carlo(
                    top_event,
                    gates_cfg,
                    basic_event_probs,
                    n_samples=mc_samples,
                )
                if isinstance(mc_result, dict):
                    fault_tree_output["p_top_mc"] = mc_result.get("p_top_mc")
                    fault_tree_output["mc"] = mc_result
                else:
                    fault_tree_output["p_top_mc"] = mc_result
            except Exception as e:
                print(f"WARNING: Monte Carlo fault-tree simulation failed: {e}")
                fault_tree_output["p_top_mc"] = "N/A"
        else:
            print("WARNING: Fault tree config could not be loaded or was not a dict.")

    praxis_output["fault_tree"] = fault_tree_output

    # ------------------------------------------------------------------
    # 7) Reliability placeholder
    # ------------------------------------------------------------------
    praxis_output["reliability"] = {}

    # ------------------------------------------------------------------
    # 8) Write summary JSON
    # ------------------------------------------------------------------
    _write_summary(out_dir_path, praxis_output)
    return praxis_output




