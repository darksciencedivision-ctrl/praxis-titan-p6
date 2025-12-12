"""
engine.py

PRAXIS Core Orchestration Engine - v1.1 (Titan Core)

High-level pipeline:

    1) Load scenario + config
    2) Compute numeric baseline probabilities
    3) Apply Bayesian updates (priors → posteriors)
    4) Apply CCF grouping (β-factor type model)
    5) Run cascade engine (iterative) to get p_effective
    6) Evaluate fault tree using p_effective
    7) Compute reliability metrics
    8) Write outputs

This version is designed to be run either:

    - As a script:
        py engine.py <scenario.json> <config.json> <output_dir>

    - Or imported from other Python code:
        from engine import run_scenario
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Local sibling modules (same folder)
import risk_numeric
import risk_bayes
import ccf
import cascade
import fault_tree
import reliability
import version
import io_utils


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def run_scenario(
    scenario_path: str,
    config_path: str,
    output_dir: str,
) -> Dict[str, Any]:
    """
    Main entry point for a full PRAXIS v1.1 run.
    """
    scenario_file = Path(scenario_path)
    config_file = Path(config_path)
    out_dir = Path(output_dir)

    scenario_data = load_json(scenario_file)
    config_data = load_json(config_file)

    # 1) Numeric layer
    numeric_result = risk_numeric.compute_numeric_risks(scenario_data)
    # Expect numeric_result["basic_probs"] = {event_id: p_base, ...}

    basic_probs: Dict[str, float] = numeric_result["basic_probs"]

    # 2) Bayesian updates
    bayes_result = risk_bayes.compute_bayes_updates(
        basic_probs=basic_probs,
        priors_path=config_data.get("priors_path"),
        pseudo_n=config_data.get("pseudo_n", 10),
    )
    # Expect bayes_result["posterior_probs"] = {event_id: p_bayes, ...}

    posterior_probs: Dict[str, float] = bayes_result["posterior_probs"]

    # 3) CCF grouping
    ccf_config = config_data.get("ccf_groups", [])
    ccf_probs = ccf.apply_ccf_groups(
        probs=posterior_probs,
        ccf_groups=ccf_config,
    )

    # 4) Cascade engine (ITERATIVE by default)
    cascade_edges: List[cascade.CascadeEdge] = config_data.get("cascade_edges", [])
    effective_probs = cascade.run_cascade_engine(
        base_probs=ccf_probs,
        edges=cascade_edges,
        mode=config_data.get("cascade_mode", "iterative"),
        max_iterations=config_data.get("cascade_max_iterations", 20),
        epsilon=config_data.get("cascade_epsilon", 1e-6),
    )

    # 5) Fault tree - MUST use p_effective
    ft_config = config_data.get("fault_tree", {})
    top_event_id = ft_config.get("top_event")
    gates = ft_config.get("gates", {})

    if top_event_id:
        p_top_analytic, all_gate_outputs = fault_tree.evaluate_fault_tree_analytic(
            top_event=top_event_id,
            gates=gates,
            basic_probs=effective_probs,
        )

        ft_mc_stats = fault_tree.simulate_fault_tree_monte_carlo(
            top_event=top_event_id,
            gates=gates,
            basic_probs=effective_probs,
            num_samples=config_data.get("ft_mc_samples", 50_000),
            rng_seed=config_data.get("ft_mc_seed"),
        )
    else:
        p_top_analytic = 0.0
        all_gate_outputs = {}
        ft_mc_stats = {
            "p_mc": 0.0,
            "ci_95_low": 0.0,
            "ci_95_high": 0.0,
            "samples": 0,
        }

    # 6) Reliability metrics from top-event probability
    time_horizons = config_data.get("reliability_horizons", [1.0, 5.0, 10.0])
    rel_curves = {}
    for horizon in time_horizons:
        rel_curves[horizon] = reliability.reliability_curve(
            p=p_top_analytic,
            time_points=[0.0, horizon / 4, horizon / 2, 3 * horizon / 4, horizon],
        )

    result: Dict[str, Any] = {
        "version": version.get_version(),
        "numeric": numeric_result,
        "bayes": bayes_result,
        "ccf_probs": ccf_probs,
        "effective_probs": effective_probs,
        "fault_tree": {
            "top_event": top_event_id,
            "p_top_analytic": p_top_analytic,
            "gate_outputs": all_gate_outputs,
            "monte_carlo": ft_mc_stats,
        },
        "reliability": {
            "time_horizons": time_horizons,
            "curves": rel_curves,
        },
    }

    # 7) Persist outputs
    save_json(out_dir / "praxis_v1_1_result.json", result)

    # Optionally write a Markdown / text report
    try:
        io_utils.write_markdown_report(out_dir / "praxis_v1_1_report.md", result)
    except Exception:
        # Don't let a reporting failure kill the core engine
        pass

    return result


if __name__ == "__main__":
    # CLI entry point:
    #   py engine.py <scenario.json> <config.json> <output_dir>
    if len(sys.argv) != 4:
        print(
            "Usage:\n"
            "  py engine.py <scenario.json> <config.json> <output_dir>\n"
            "Example:\n"
            "  py engine.py ..\\data\\scenario_example.json "
            "..\\data\\config_example.json ..\\out_v1_1"
        )
        sys.exit(1)

    scenario_arg = sys.argv[1]
    config_arg = sys.argv[2]
    outdir_arg = sys.argv[3]

    run_scenario(scenario_arg, config_arg, outdir_arg)
