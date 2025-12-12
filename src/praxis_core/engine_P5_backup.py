
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from ..utils.io import read_json
from ..utils.hashing import sha256_of_strings
from . import output_manager
from . import diagnostics as diag
from . import numeric
from . import bayes
from . import ccf
from . import cascade
from . import fault_tree
from . import fault_tree_montecarlo
from . import reliability


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"


def load_scenario(path: str | Path | None = None) -> Dict[str, Any]:
    """
    Load scenario JSON from config. Default: scenario_example.json
    """
    if path is None:
        path = CONFIG_DIR / "scenario_example.json"
    return read_json(path)


def run_full_cycle(scenario_path: str | Path | None = None) -> Dict[str, Any]:
    """
    Main P6 entrypoint.

    Pipeline:
        Scenario → L1 numeric → L2 Bayes → L3 CCF → L4 Cascade →
        L5 Analytic FT → L6 MC FT → Reliability → P6 ReportPack
    """
    scenario = load_scenario(scenario_path)
    scenario_name = scenario.get("scenario_name", "Unnamed Scenario")

    # Initialize master report + metadata
    output_manager.init_master_report(scenario_name)

    layer_times: Dict[str, diag.LayerDiagnostics] = {}

    # L1: Numeric
    t_num = diag.time_layer("numeric")
    numeric_result = numeric.run_numeric_layer(scenario)
    layer_times["numeric"] = diag.stop_layer(t_num)

    # L2: Bayes
    t_bayes = diag.time_layer("bayes")
    bayes_result = bayes.run_bayes_layer(numeric_result)
    layer_times["bayes"] = diag.stop_layer(t_bayes)

    # L3: Common Cause
    t_ccf = diag.time_layer("ccf")
    ccf_result = ccf.run_ccf_layer(bayes_result)
    layer_times["ccf"] = diag.stop_layer(t_ccf)

    # L4: Cascade
    t_cascade = diag.time_layer("cascade")
    cascade_result = cascade.run_cascade_layer(ccf_result)
    layer_times["cascade"] = diag.stop_layer(t_cascade)

    # L5: Fault Tree (analytic)
    t_ft = diag.time_layer("fault_tree")
    ft_result = fault_tree.run_fault_tree_layer(cascade_result)
    layer_times["fault_tree"] = diag.stop_layer(t_ft)

    # L6: Fault Tree (Monte Carlo)
    t_mc = diag.time_layer("fault_tree_montecarlo")
    mc_result = fault_tree_montecarlo.run_fault_tree_mc_layer(ft_result)
    layer_times["fault_tree_montecarlo"] = diag.stop_layer(t_mc)

    # Reliability (based on analytic fault tree)
    t_rel = diag.time_layer("reliability")
    reliability_result = reliability.run_reliability_layer(ft_result)
    layer_times["reliability"] = diag.stop_layer(t_rel)

    # Diagnostics & hash
    diag_text = diag.diagnostics_summary(layer_times)
    output_manager.append_diagnostics_block(diag_text)

    # Build cross-module hash from layer summaries
    hash_chunks = [
        str(numeric_result),
        str(bayes_result),
        str(ccf_result),
        str(cascade_result),
        str(ft_result),
        str(mc_result),
        str(reliability_result),
    ]
    hash_hex = sha256_of_strings(hash_chunks)
    output_manager.append_hash_block(hash_hex)

    # Return a machine-usable summary of the run
    return {
        "scenario_name": scenario_name,
        "numeric": numeric_result,
        "bayes": bayes_result,
        "ccf": ccf_result,
        "cascade": cascade_result,
        "fault_tree": ft_result,
        "fault_tree_montecarlo": mc_result,
        "reliability": reliability_result,
        "diagnostics": diag.diagnostics_to_dict(layer_times),
        "hash": hash_hex,
    }
