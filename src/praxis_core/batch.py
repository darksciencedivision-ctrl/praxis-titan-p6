
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List

from . import engine
from . import output_manager
from ..utils.io import read_json

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"
BATCH_REPORT_PATH = BASE_DIR / "output" / "P6" / "P6_batch_report.txt"


def load_batch_list(path: Path | None = None) -> List[str]:
    """
    Load list of scenario paths (relative to BASE_DIR) from JSON.

    {
      "scenarios": [
        "config/scenario_example.json",
        "config/scenario_example_alt.json"
      ]
    }
    """
    if path is None:
        path = CONFIG_DIR / "scenario_batch_list.json"

    cfg = read_json(path)
    return list(cfg.get("scenarios", []))


def write_batch_report(summary: Dict[str, Any]) -> None:
    """
    Write a human-readable batch report to P6_batch_report.txt.
    """
    scenarios = summary.get("scenarios", [])
    lines: List[str] = []

    lines.append("==============================")
    lines.append("PRAXIS P6 BATCH REPORT")
    lines.append("==============================")
    lines.append("")
    lines.append(f"Batch size: {summary.get('batch_size', len(scenarios))}")
    lines.append("")

    # Sort by system reliability ascending (worst first)
    sorted_scenarios = sorted(
        scenarios,
        key=lambda s: s.get("system_reliability", 1.0),
    )

    lines.append("Scenarios (worst reliability first):")
    for s in sorted_scenarios:
        name = s.get("scenario_name", "UNKNOWN")
        path = s.get("scenario_path", "")
        top_id = s.get("top_event_id", "")
        p_top = s.get("top_event_probability", None)
        rel = s.get("system_reliability", None)
        hash_val = s.get("hash", "")

        lines.append(f"- {name}")
        lines.append(f"  Path: {path}")
        lines.append(f"  Top event: {top_id}")
        if p_top is not None:
            lines.append(f"  Top event probability: {p_top:.6f}")
        if rel is not None:
            lines.append(f"  System reliability:    {rel:.6f}")
        lines.append(f"  Hash: {hash_val}")
        lines.append("")

    text = "\n".join(lines)
    BATCH_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    BATCH_REPORT_PATH.write_text(text, encoding="utf-8")


def run_batch(batch_path: Path | None = None) -> Dict[str, Any]:
    """
    Run P6 full cycle for each scenario listed in scenario_batch_list.json.

    NOTE: Each run overwrites the standard P6 single-scenario outputs on disk,
    but this function returns a combined summary and also writes:
      - batch_summary.json (machine-readable)
      - P6_batch_report.txt (human-readable)
    """
    if batch_path is None:
        batch_path = CONFIG_DIR / "scenario_batch_list.json"

    scenario_paths = load_batch_list(batch_path)
    results: List[Dict[str, Any]] = []

    for rel_path in scenario_paths:
        scenario_file = (BASE_DIR / rel_path).resolve()
        run = engine.run_full_cycle(scenario_file)

        scenario_name = run.get("scenario_name", str(scenario_file))
        reliability_block = run.get("reliability", {})
        reliability_info = reliability_block.get("reliability", {})
        system_reliability = reliability_info.get("system_reliability", None)

        ft_block = run.get("fault_tree", {})
        top_p = ft_block.get("top_event_probability", None)
        top_id = ft_block.get("top_event_id", None)

        results.append(
            {
                "scenario_name": scenario_name,
                "scenario_path": str(scenario_file),
                "top_event_id": top_id,
                "top_event_probability": top_p,
                "system_reliability": system_reliability,
                "hash": run.get("hash"),
            }
        )

    summary = {
        "batch_size": len(results),
        "scenarios": results,
    }

    # JSON summary via standard P6 JSON writer
    output_manager.write_P6_json_block("batch_summary", summary)

    # Human-readable text report
    write_batch_report(summary)

    return summary
