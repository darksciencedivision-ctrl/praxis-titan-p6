"""
cli.py

Command-line interface for PRAXIS v1.1 Titan.

This version is defensive:
- Calls pipeline.run_scenario(...) with explicit keyword args.
- Never crashes if parts of the result dict are missing.
- Always prints a fault-tree / reliability summary, using "N/A"
  when an analytic value is not available.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

from .pipeline import run_scenario


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="praxis_core.cli",
        description="PRAXIS Risk Engine v1.1 Titan CLI",
    )

    parser.add_argument(
        "--scenario-config",
        required=True,
        help="Path to scenario JSON (risks, metadata).",
    )

    parser.add_argument(
        "--priors",
        required=False,
        help="Path to Bayesian priors JSON (risk_priors).",
    )

    parser.add_argument(
        "--ccf-groups",
        required=False,
        help="Path to CCF groups JSON (beta-factor groups).",
    )

    parser.add_argument(
        "--fault-tree",
        required=False,
        help="Path to fault tree JSON configuration.",
    )

    parser.add_argument(
        "--cascade",
        required=False,
        help="Path to cascade influence JSON configuration.",
    )

    parser.add_argument(
        "--out-dir",
        required=True,
        help="Output directory for PRAXIS results.",
    )

    parser.add_argument(
        "--no-report",
        action="store_true",
        help="If set, do not write the Markdown report.",
    )

    return parser


def _print_summary(result: Dict[str, Any]) -> None:
    """
    Print a short human-readable summary.

    This function is deliberately tolerant:
    - Missing sections become empty dicts.
    - Missing keys like 'p_top_analytic' are shown as 'N/A'.
    """

    if result is None:
        print("No in-memory result returned from pipeline (report only mode?).")
        return

    ft_results: Dict[str, Any] = result.get("fault_tree") or {}
    rel_results: Dict[str, Any] = result.get("reliability") or {}

    # ----- Fault tree summary -----
    print("\n=== FAULT TREE SUMMARY ===")

    top_event = ft_results.get("top_event") or ft_results.get("top_events")
    if isinstance(top_event, list) and top_event:
        top_event = top_event[0]

    if top_event is None:
        print("Top event: N/A (no fault tree results present in output dict).")
    else:
        print(f"Top event: {top_event}")

    p_top_analytic = ft_results.get("p_top_analytic", "N/A")
    p_top_mc = ft_results.get("p_top_mc", ft_results.get("p_top_mc_mean", "N/A"))

    print(f"  Top event (analytic): {p_top_analytic}")
    print(f"  Top event (Monte Carlo): {p_top_mc}")

    # ----- Reliability summary (very light-touch) -----
    print("\n=== RELIABILITY SUMMARY (if available) ===")

    if not rel_results:
        print("No reliability rows present in result dict.")
        return

    # Try to show a couple of sample rows if the structure matches
    rows = rel_results.get("rows") or rel_results.get("reliability_rows")
    if isinstance(rows, list) and rows:
        sample = rows[:3]
        print(f"Showing up to 3 reliability rows (of {len(rows)} total):")
        for row in sample:
            rid = row.get("id") or row.get("risk_id") or "UNKNOWN_ID"
            r1 = row.get("R_1yr") or row.get("R(1.0)") or row.get("R_1")
            print(f"  - {rid}: R(1yr) = {r1}")
    else:
        print("Reliability structure present but not in expected 'rows' list format.")


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    scenario_path = args.scenario_config
    priors_path = args.priors
    ccf_groups_path = args.ccf_groups
    fault_tree_path = args.fault_tree
    cascade_path = args.cascade
    out_dir = args.out_dir
    write_report = not args.no_report

    # Ensure output directory exists
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # Call the pipeline with explicit keyword args that match its signature.
    result = run_scenario(
        scenario_config_path=scenario_path,
        priors_path=priors_path,
        ccf_groups_path=ccf_groups_path,
        fault_tree_config_path=fault_tree_path,
        cascade_config_path=cascade_path,
        out_dir=out_dir,
        write_report=write_report,
    )

    print(f"PRAXIS run complete. Output directory: {Path(out_dir).resolve()}")

    _print_summary(result)


if __name__ == "__main__":
    main()

