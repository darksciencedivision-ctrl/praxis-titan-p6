from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


def generate_text_report(praxis_output: Dict[str, Any], out_path: str | Path) -> None:
    """
    Generate a simple markdown report summarizing top risks and top events.
    """
    scenario_id = praxis_output.get("scenario_id", "UNKNOWN")
    pra_rows: List[Dict[str, Any]] = praxis_output.get("pra", [])
    fault_tree = praxis_output.get("fault_tree", {})
    top_events = fault_tree.get("top_events", [])

    pra_sorted = sorted(
        pra_rows,
        key=lambda r: r.get("posterior_mean_ccf", r.get("posterior_mean", 0.0)),
        reverse=True,
    )
    top_risks = pra_sorted[:10]

    lines: List[str] = []
    lines.append(f"# PRAXIS Scenario Report – {scenario_id}")
    lines.append("")
    lines.append("## Top Risk Drivers")
    lines.append("")

    if not top_risks:
        lines.append("_No PRA rows available._")
    else:
        for r in top_risks:
            dom = r["domain"]
            risk = r["risk"]
            p = r.get("posterior_mean_ccf", r.get("posterior_mean", 0.0))
            lines.append(f"- **{dom}** – {risk} (p ≈ {p:.3f})")

    lines.append("")
    lines.append("## Top Events (Fault Tree)")
    lines.append("")

    if not top_events:
        lines.append("_No fault tree results available._")
    else:
        for te in top_events:
            lines.append(
                f"- **{te['top_event_id']}**: p ≈ {te['probability']:.3f} "
                f"(95% CI [{te['ci_95_low']:.3f}, {te['ci_95_high']:.3f}])"
            )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
