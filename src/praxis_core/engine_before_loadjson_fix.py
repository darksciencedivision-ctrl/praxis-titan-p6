"""
PRAXIS P6.1 TITAN - Core Engine

This module orchestrates the full PRAXIS pipeline:

    scenario.json
        → NUMERIC LAYER
        → BAYES LAYER
        → CCF LAYER
        → CASCADE LAYER
        → FAULT TREE (analytic)
        → FAULT TREE (Monte Carlo)
        → RELIABILITY
        → ADVERSARIAL TWIN ENGINE
        → SENSITIVITY ENGINE
        → OUTPUT MANAGER (run directory + reports)

It is written to be:
- Deterministic
- File-driven
- Easy to debug
- Easy to extend for future P7+ upgrades
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..utils import io, hashing
from . import (
    numeric,
    bayes,
    ccf,
    cascade,
    fault_tree,
    fault_tree_mc,
    reliability,
    twin_analysis,
    sensitivity,
    output_manager,
)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def load_json(path: str | Path) -> Dict[str, Any]:
    """Thin wrapper around utils.io.load_json."""
    return io.load_json(Path(path))


def hash_or_none(path: Optional[str]) -> Optional[str]:
    """Return a stable hash for a file path, or None if path is falsy."""
    if not path:
        return None
    return hashing.hash_file(Path(path))


# ---------------------------------------------------------------------------
# Core pipeline (single baseline run)
# ---------------------------------------------------------------------------

def run_baseline_pipeline(
    scenario: Dict[str, Any],
    priors: Dict[str, Any],
    mc_iterations: int = 10_000,
) -> Dict[str, Any]:
    """
    Run the full pipeline for a single baseline scenario:
    numeric → bayes → CCF → cascade → fault-tree analytic + MC → reliability.

    Returns a dictionary with all intermediate and final results.
    """

    risks: List[Dict[str, Any]] = scenario.get("risks", [])

    # 1. Numeric layer
    numeric_results = numeric.compute_numeric_risks(risks)

    # 2. Bayesian update layer
    bayes_results = bayes.bayes_update(numeric_results, priors)

    # 3. Common-cause failure layer
    ccf_results = ccf.apply_ccf(bayes_results)

    # 4. Cascade layer (you can switch between linear / iterative inside cascade.py)
    cascade_results = cascade.propagate(ccf_results)

    # 5. Fault-tree analytic
    ft_structure = scenario.get("fault_tree", {})
    ft_analytic = fault_tree.evaluate_fault_tree(cascade_results, ft_structure)

    # 6. Fault-tree Monte Carlo
    ft_mc = fault_tree_mc.run_mc(
        cascade_results,
        ft_structure,
        iterations=mc_iterations,
    )

    # 7. Reliability layer
    rel_result = reliability.compute_reliability(
        p_top_event=ft_analytic.get("p_top")
    )

    return {
        "numeric": numeric_results,
        "bayes": bayes_results,
        "ccf": ccf_results,
        "cascade": cascade_results,
        "ft_analytic": ft_analytic,
        "ft_mc": ft_mc,
        "reliability": rel_result,
    }


# ---------------------------------------------------------------------------
# Twin + Sensitivity engines
# ---------------------------------------------------------------------------

def run_twin_engine(
    scenario: Dict[str, Any],
    priors: Dict[str, Any],
    twin_config: Dict[str, Any],
    baseline_pipeline: Dict[str, Any],
    mc_iterations: int = 10_000,
) -> Dict[str, Any]:
    """
    Invoke the adversarial twin engine.

    This function assumes twin_analysis.py exposes a function like:

        run_twin_engine(
            scenario, priors, twin_config,
            mc_iterations=...,  # optional
        ) -> dict

    If your existing twin module uses a different function name or signature,
    you can adjust the call here.
    """
    return twin_analysis.run_twin_engine(
        scenario=scenario,
        priors=priors,
        twin_config=twin_config,
        mc_iterations=mc_iterations,
        baseline_pipeline=baseline_pipeline,
    )


def run_sensitivity_engine(
    scenario: Dict[str, Any],
    priors: Dict[str, Any],
    baseline_pipeline: Dict[str, Any],
    factors: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Invoke the sensitivity engine.

    Assumes sensitivity.py exposes a function like:

        run_sensitivity(
            scenario, priors, baseline_pipeline, factors=None
        ) -> dict
    """
    return sensitivity.run_sensitivity(
        scenario=scenario,
        priors=priors,
        baseline_pipeline=baseline_pipeline,
        factors=factors,
    )


# ---------------------------------------------------------------------------
# Output context builders for output_manager.py
# ---------------------------------------------------------------------------

def build_run_meta(
    run_id: str,
    praxis_version: str,
    scenario_path: str,
    scenario: Dict[str, Any],
    mc_iterations: int,
    baseline_pipeline: Dict[str, Any],
    twin_results: Dict[str, Any],
    sensitivity_results: Dict[str, Any],
    priors_path: Optional[str] = None,
    twin_config_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build the run_meta.json structure for this run.
    """

    scenario_name = scenario.get("scenario_name", "Unknown Scenario")
    description = scenario.get("description", "")
    risks = scenario.get("risks", [])

    ft_analytic = baseline_pipeline.get("ft_analytic", {}) or {}
    ft_mc = baseline_pipeline.get("ft_mc", {}) or {}
    rel = baseline_pipeline.get("reliability", {}) or {}

    # sensitivity_results is expected to have "risks" list with delta_p_top_max
    most_sensitive_risks = sensitivity_results.get("risks", [])

    meta: Dict[str, Any] = {
        "run_id": run_id,
        "praxis_version": praxis_version,
        "scenario_file": scenario_path,
        "scenario_name": scenario_name,
        "timestamp_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "iterations_mc": mc_iterations,
        "twin_clones": len(twin_results.get("twins", [])),
        "sensitivity_factors": sensitivity_results.get("factors", []),
        "hashes": {
            "scenario": hash_or_none(scenario_path),
            "priors": hash_or_none(priors_path),
            "twin_config": hash_or_none(twin_config_path),
        },
        "performance": {
            # You can fill this with real timing metrics later if you want.
            "total_runtime_sec": None,
            "mc_runtime_sec": None,
            "n_risks": len(risks),
        },
        "top_event": {
            "id": ft_analytic.get("top_event_id", "TOP_EVENT"),
            "p_top_analytic": ft_analytic.get("p_top"),
            "p_top_mc_mean": ft_mc.get("p_top_mean"),
            "p_top_mc_ci_95": ft_mc.get("CI_95"),
            "reliability": rel.get("reliability"),
        },
        "most_sensitive_risks": most_sensitive_risks,
    }

    return meta


def build_master_context(
    run_id: str,
    praxis_version: str,
    scenario: Dict[str, Any],
    baseline_pipeline: Dict[str, Any],
    sensitivity_results: Dict[str, Any],
    mc_iterations: int,
) -> Dict[str, Any]:
    """
    Build the context dictionary for master_report.md.
    """

    scenario_name = scenario.get("scenario_name", "Unknown Scenario")
    description = scenario.get("description", "")
    risks = scenario.get("risks", [])
    domains = sorted({r.get("domain", "UNKNOWN") for r in risks})

    ft_analytic = baseline_pipeline.get("ft_analytic", {}) or {}
    ft_mc = baseline_pipeline.get("ft_mc", {}) or {}
    rel = baseline_pipeline.get("reliability", {}) or {}

    most_sensitive_risks = sensitivity_results.get("risks", [])

    ctx: Dict[str, Any] = {
        "run_id": run_id,
        "scenario_name": scenario_name,
        "scenario_description": description,
        "praxis_version": praxis_version,
        "n_risks": len(risks),
        "domains": domains,
        "p_top_analytic": ft_analytic.get("p_top"),
        "p_top_mc_mean": ft_mc.get("p_top_mean"),
        "p_top_mc_ci_95": ft_mc.get("CI_95"),
        "reliability": rel.get("reliability"),
        "most_sensitive_risks": most_sensitive_risks,
        # risk_table: you can fill this with merged numeric/bayes/ccf/cascade
        # later. For now we leave it empty; the report will show a placeholder.
        "risk_table": sensitivity_results.get("risk_table", []),
        "ft_structure_summary": ft_analytic.get(
            "structure_summary",
            "Fault-tree structure not described."
        ),
        "mc_iterations": mc_iterations,
        "mc_notes": ft_mc.get("notes", ""),
    }

    return ctx


def build_twin_context(
    run_id: str,
    baseline_pipeline: Dict[str, Any],
    twin_results: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build context for twin_report.md and twin_summary.json.

    Expects twin_results to contain a list under "twins",
    each with: twin_id, mode, p_top, reliability, delta_p_top.
    """

    ft_analytic = baseline_pipeline.get("ft_analytic", {}) or {}
    rel = baseline_pipeline.get("reliability", {}) or {}

    twins: List[Dict[str, Any]] = twin_results.get("twins", [])

    # Compute ranges if we have data
    p_values = [t.get("p_top") for t in twins if t.get("p_top") is not None]
    r_values = [t.get("reliability") for t in twins if t.get("reliability") is not None]

    p_min = min(p_values) if p_values else None
    p_max = max(p_values) if p_values else None
    r_min = min(r_values) if r_values else None
    r_max = max(r_values) if r_values else None

    ctx: Dict[str, Any] = {
        "run_id": run_id,
        "baseline_p_top": ft_analytic.get("p_top"),
        "baseline_reliability": rel.get("reliability"),
        "twins": twins,
        "p_top_min": p_min,
        "p_top_max": p_max,
        "reliability_min": r_min,
        "reliability_max": r_max,
    }

    return ctx


def build_sensitivity_context(
    run_id: str,
    sensitivity_results: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build context for sensitivity_report.md and sensitivity_summary.json.

    Expects sensitivity_results to already be shaped like:
      {
        "factors": [...],
        "risks": [...],
        "detailed": { risk_id: [ {factor, p_top, delta_p_top}, ... ] }
      }
    """

    ctx: Dict[str, Any] = {
        "run_id": run_id,
        "factors": sensitivity_results.get("factors", []),
        "risks": sensitivity_results.get("risks", []),
        "detailed": sensitivity_results.get("detailed", {}),
    }
    return ctx


# ---------------------------------------------------------------------------
# Public API: run_scenario
# ---------------------------------------------------------------------------

def run_scenario(
    scenario_path: str,
    priors_path: str,
    twin_config_path: str,
    output_base_dir: str = "output",
    praxis_version: str = "P6.1-TITAN",
    mc_iterations: int = 10_000,
    sensitivity_factors: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    High-level orchestration function for a full PRAXIS run.

    1) Loads scenario, priors, twin config.
    2) Runs baseline pipeline.
    3) Runs adversarial twin engine.
    4) Runs sensitivity analysis.
    5) Constructs output contexts.
    6) Writes run_meta.json + Markdown reports via output_manager.
    7) Returns a dictionary with key results and paths.
    """

    scenario = load_json(scenario_path)
    priors = load_json(priors_path)
    twin_config = load_json(twin_config_path)

    # ------------------------------------------------------------------
    # Baseline pipeline
    # ------------------------------------------------------------------
    baseline_pipeline = run_baseline_pipeline(
        scenario=scenario,
        priors=priors,
        mc_iterations=mc_iterations,
    )

    # ------------------------------------------------------------------
    # Twin engine
    # ------------------------------------------------------------------
    twin_results = run_twin_engine(
        scenario=scenario,
        priors=priors,
        twin_config=twin_config,
        baseline_pipeline=baseline_pipeline,
        mc_iterations=mc_iterations,
    )

    # ------------------------------------------------------------------
    # Sensitivity engine
    # ------------------------------------------------------------------
    sensitivity_results = run_sensitivity_engine(
        scenario=scenario,
        priors=priors,
        baseline_pipeline=baseline_pipeline,
        factors=sensitivity_factors,
    )

    # ------------------------------------------------------------------
    # Build output contexts
    # ------------------------------------------------------------------
    scenario_name = scenario.get("scenario_name", "Scenario")
    run_id = output_manager.generate_run_id(scenario_name=scenario_name)
    run_dir = output_manager.create_run_directory(output_base_dir, run_id)

    meta = build_run_meta(
        run_id=run_id,
        praxis_version=praxis_version,
        scenario_path=scenario_path,
        scenario=scenario,
        mc_iterations=mc_iterations,
        baseline_pipeline=baseline_pipeline,
        twin_results=twin_results,
        sensitivity_results=sensitivity_results,
        priors_path=priors_path,
        twin_config_path=twin_config_path,
    )

    master_ctx = build_master_context(
        run_id=run_id,
        praxis_version=praxis_version,
        scenario=scenario,
        baseline_pipeline=baseline_pipeline,
        sensitivity_results=sensitivity_results,
        mc_iterations=mc_iterations,
    )

    twin_ctx = build_twin_context(
        run_id=run_id,
        baseline_pipeline=baseline_pipeline,
        twin_results=twin_results,
    )

    sens_ctx = build_sensitivity_context(
        run_id=run_id,
        sensitivity_results=sensitivity_results,
    )

    # ------------------------------------------------------------------
    # Write outputs
    # ------------------------------------------------------------------
    output_manager.write_run_meta(run_dir, meta)
    output_manager.write_master_report(run_dir, master_ctx)
    output_manager.write_twin_report(run_dir, twin_ctx)
    output_manager.write_sensitivity_reports(run_dir, sens_ctx)

    # Return a high-level result structure
    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "meta": meta,
        "baseline": baseline_pipeline,
        "twin": twin_results,
        "sensitivity": sensitivity_results,
    }


# ---------------------------------------------------------------------------
# CLI entry point (optional)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    """
    Simple CLI usage example:

        py -m praxis_core.engine

    You can customize this block to parse arguments if you wish.
    For now, it uses the default example config paths.
    """
    base = Path(__file__).resolve().parents[2]  # C:\ai_control
    config_dir = base / "config"

    scenario_path = str(config_dir / "scenario_example.json")
    priors_path = str(config_dir / "risk_priors_example.json")
    twin_config_path = str(config_dir / "adversarial_twin_config.json")

    results = run_scenario(
        scenario_path=scenario_path,
        priors_path=priors_path,
        twin_config_path=twin_config_path,
        output_base_dir=str(base / "output"),
    )

    print(f"PRAXIS run complete. Run ID: {results['run_id']}")
    print(f"Run directory: {results['run_dir']}")
