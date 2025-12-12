"""
PRAXIS P6.1 TITAN - Core Engine

This is a clean, self-contained orchestrator that connects:

    numeric → bayes → CCF → cascade → fault_tree (analytic)
    → fault_tree_mc (MC stub) → reliability
    → twin_analysis (adversarial twins)
    → sensitivity (one-at-a-time sweeps)

It is designed to be run as:

    cd C:\ai_control
    python -m src.praxis_core.engine

and expects the following files:

    config\scenario_example.json
    config\risk_priors_example.json
    config\adversarial_twin_config.json

Outputs are written under:

    output\P6\runs\<run_id>_ScenarioName\
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

# Package-local modules
from . import (
    numeric,
    bayes,
    ccf,
    cascade,
    fault_tree,
)

# Optional modules (may not exist)
try:
    from . import fault_tree_mc
    HAS_FT_MC = True
except ImportError:
    HAS_FT_MC = False

try:
    from . import reliability
    HAS_RELIABILITY = True
except ImportError:
    HAS_RELIABILITY = False

try:
    from . import twin_analysis
    HAS_TWINS = True
except ImportError:
    HAS_TWINS = False

try:
    from . import sensitivity
    HAS_SENSITIVITY = True
except ImportError:
    HAS_SENSITIVITY = False


# ---------------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> Dict[str, Any]:
    """Load JSON from path."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON with nice indentation, creating parent folders if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    """Write plain text / markdown to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def hash_object(obj: Any) -> str:
    """Return a short hash string for any JSON-serializable object."""
    as_bytes = json.dumps(obj, sort_keys=True).encode("utf-8")
    return hashlib.sha256(as_bytes).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Core pipeline for a single scenario (baseline)
# ---------------------------------------------------------------------------

def run_baseline_pipeline(
    scenario: Dict[str, Any],
    priors: Dict[str, Any],
    mc_iterations: int = 10_000,
) -> Dict[str, Any]:
    """
    Run the full baseline pipeline:

        numeric → bayes → CCF → cascade
        → fault_tree (analytic) → fault_tree_mc (MC stub)
        → reliability
    """
    # 1. Numeric layer - pass full scenario dict
    numeric_results = numeric.compute_numeric_risks(scenario)
    basic_probs = numeric_results.get("basic_probs", {})

    # 2. Bayes layer
    try:
        bayes_results = bayes.bayes_update(
            basic_probs=basic_probs,
            priors_cfg=priors,
            pseudo_n=5.0,
        )
    except TypeError:
        # Fallback API
        bayes_results = bayes.bayes_update(basic_probs, priors)

    posterior_probs = bayes_results.get("posterior_probs", basic_probs)

    # 3. CCF layer
    ccf_groups = scenario.get("ccf_groups", {})
    if ccf_groups:
        try:
            ccf_results = ccf.apply_ccf_groups(posterior_probs, ccf_groups)
            if isinstance(ccf_results, dict) and "probs" in ccf_results:
                ccf_probs = ccf_results["probs"]
            else:
                ccf_probs = ccf_results
        except Exception as e:
            print(f"WARNING: CCF failed: {e}")
            ccf_probs = posterior_probs
    else:
        ccf_probs = posterior_probs

    # 4. Cascade layer
    cascade_cfg = scenario.get("cascade", {})
    if cascade_cfg:
        try:
            cascade_results = cascade.run_cascade_engine(ccf_probs, cascade_cfg)
            if isinstance(cascade_results, dict):
                final_probs = cascade_results.get("effective_probs") or ccf_probs
            else:
                final_probs = ccf_probs
        except Exception as e:
            print(f"WARNING: Cascade failed: {e}")
            final_probs = ccf_probs
    else:
        final_probs = ccf_probs

    # 5. Fault-tree analytic
    ft_structure = scenario.get("fault_tree", {})
    ft_analytic = {}

    if ft_structure:
        try:
            top_event = ft_structure.get("top_event")
            gates = ft_structure.get("gates", {})
            p_top, gate_outputs = fault_tree.evaluate_fault_tree_analytic(
                top_event, gates, final_probs
            )
            ft_analytic = {
                "p_top": p_top if p_top >= 0 else "N/A",
                "gate_outputs": gate_outputs,
            }
        except Exception as e:
            print(f"WARNING: Fault tree analytic failed: {e}")
            ft_analytic = {"p_top": "N/A"}

    # 6. Fault-tree Monte Carlo (if available)
    ft_mc = {}
    if HAS_FT_MC and ft_structure:
        try:
            ft_mc = fault_tree_mc.run_mc(
                final_probs,
                ft_structure,
                iterations=mc_iterations,
            )
        except Exception as e:
            print(f"WARNING: Fault tree MC failed: {e}")

    # 7. Reliability
    rel = {}
    if HAS_RELIABILITY:
        try:
            p_top = ft_analytic.get("p_top")
            if isinstance(p_top, (int, float)):
                rel = reliability.compute_reliability(p_top)
        except Exception as e:
            print(f"WARNING: Reliability failed: {e}")

    return {
        "numeric": numeric_results,
        "bayes": bayes_results,
        "ccf": {"probs": ccf_probs},
        "cascade": {"final_probs": final_probs},
        "ft_analytic": ft_analytic,
        "ft_mc": ft_mc,
        "reliability": rel,
    }


# ---------------------------------------------------------------------------
# Scenario runner: baseline + twins + sensitivity
# ---------------------------------------------------------------------------

def run_scenario(
    scenario_path: Path,
    priors_path: Path,
    twin_config_path: Path,
    output_base_dir: Path,
    mc_iterations: int = 10_000,
) -> Dict[str, Any]:
    """
    Load configs, run baseline, twins, and sensitivity, and write outputs.

    Returns a dictionary with run metadata + summaries.
    """
    scenario = load_json(scenario_path)
    priors = load_json(priors_path)

    # Twin config is optional
    try:
        twin_cfg = load_json(twin_config_path)
    except Exception:
        twin_cfg = {}

    scenario_name = scenario.get("scenario_name", "Scenario")

    # --- baseline pipeline --------------------------------------------------
    baseline_pipeline = run_baseline_pipeline(
        scenario=scenario,
        priors=priors,
        mc_iterations=mc_iterations,
    )

    # --- adversarial twins --------------------------------------------------
    twin_results = {}
    if HAS_TWINS and twin_cfg:
        try:
            twin_results = twin_analysis.run_twin_engine(
                scenario=scenario,
                priors=priors,
                twin_config=twin_cfg,
                baseline_pipeline=baseline_pipeline,
                mc_iterations=mc_iterations,
            )
        except Exception as e:
            print(f"WARNING: Twin analysis failed: {e}")

    # --- sensitivity sweeps -------------------------------------------------
    sensitivity_results = {}
    if HAS_SENSITIVITY:
        try:
            sensitivity_results = sensitivity.run_sensitivity(
                scenario=scenario,
                priors=priors,
                baseline_pipeline=baseline_pipeline,
            )
        except Exception as e:
            print(f"WARNING: Sensitivity analysis failed: {e}")

    # --- run metadata + directory layout -----------------------------------
    base = output_base_dir
    base.mkdir(parents=True, exist_ok=True)

    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    run_id = hash_object(now)

    run_dir = base / "runs" / f"{run_id}_{scenario_name.replace(' ', '_')}"
    run_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "run_id": run_id,
        "timestamp_utc": now,
        "scenario_file": str(scenario_path),
        "priors_file": str(priors_path),
        "twin_config_file": str(twin_config_path),
        "scenario_name": scenario_name,
        "scenario_hash": hash_object(scenario),
        "priors_hash": hash_object(priors),
    }

    # --- write JSON summaries ----------------------------------------------
    write_json(run_dir / "run_meta.json", meta)
    write_json(run_dir / "baseline_summary.json", baseline_pipeline)

    if twin_results:
        write_json(run_dir / "twin_summary.json", twin_results)
    if sensitivity_results:
        write_json(run_dir / "sensitivity_summary.json", sensitivity_results)

    # --- simple text / markdown report -------------------------------------
    report_lines: List[str] = []

    report_lines.append(f"# PRAXIS P6.1 TITAN Run – {scenario_name}")
    report_lines.append("")
    report_lines.append(f"Run ID: {run_id}")
    report_lines.append(f"Timestamp (UTC): {now}")
    report_lines.append("")
    report_lines.append("## Baseline Top Event")

    ft_analytic = baseline_pipeline.get("ft_analytic", {})
    p_top = ft_analytic.get("p_top", None)
    report_lines.append(f"- p_top (analytic): {p_top!r}")

    rel = baseline_pipeline.get("reliability", {})
    report_lines.append(f"- Reliability: {rel.get('reliability', 'N/A')!r}")
    report_lines.append("")

    if twin_results:
        report_lines.append("## Twin Engine (Adversarial)")
        twins = twin_results.get("twins", [])
        report_lines.append(f"- Number of twins: {len(twins)}")
        if twins:
            for twin in twins[:3]:
                report_lines.append(
                    f"  - {twin.get('twin_id')} [{twin.get('mode')}]: "
                    f"p_top={twin.get('p_top')!r}, "
                    f"Δp_top={twin.get('delta_p_top')!r}"
                )
        report_lines.append("")

    if sensitivity_results:
        report_lines.append("## Sensitivity (Top Δp_top)")
        sens_risks = sensitivity_results.get("risks", [])
        sens_sorted = sorted(
            sens_risks,
            key=lambda r: abs(r.get("delta_p_top_max") or 0.0),
            reverse=True,
        )
        for r in sens_sorted[:5]:
            report_lines.append(
                f"- {r.get('id')} ({r.get('domain')} – {r.get('name')}): "
                f"max |Δp_top| ≈ {r.get('delta_p_top_max')!r}"
            )

    write_text(run_dir / "P6_master_report.md", "\n".join(report_lines))

    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "meta": meta,
        "baseline": baseline_pipeline,
        "twins": twin_results,
        "sensitivity": sensitivity_results,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """
    CLI entrypoint when run as a module:

        python -m src.praxis_core.engine
    """
    # engine.py is in: C:\ai_control\src\praxis_core
    # We want the project root: C:\ai_control
    project_root = Path(__file__).resolve().parents[2]

    config_dir = project_root / "config"
    output_base_dir = project_root / "output" / "P6"

    scenario_path = config_dir / "scenario_example.json"
    priors_path = config_dir / "risk_priors_example.json"
    twin_config_path = config_dir / "adversarial_twin_config.json"

    print(f"Loading configs from: {config_dir}")
    print(f"Output directory: {output_base_dir}")

    results = run_scenario(
        scenario_path=scenario_path,
        priors_path=priors_path,
        twin_config_path=twin_config_path,
        output_base_dir=output_base_dir,
        mc_iterations=10_000,
    )

    print(f"\nPRAXIS run complete. Run ID: {results['run_id']}")
    print(f"Run directory: {results['run_dir']}")


if __name__ == "__main__":
    main()
