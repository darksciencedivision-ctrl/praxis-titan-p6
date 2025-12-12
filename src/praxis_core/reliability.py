
from __future__ import annotations

from typing import Dict, Any

from . import output_manager


def run_reliability_layer(ft_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Titan Reliability Layer.

    For now, we model 'system reliability' as 1 - P(top event),
    where top_event_probability comes from the analytic fault tree.
    """
    p_top = float(ft_result.get("top_event_probability", 0.0))
    reliability_val = max(0.0, 1.0 - p_top)

    summary_text = (
        "Reliability Layer (Titan)\n"
        f"Approx system reliability ≈ {reliability_val:.4f} "
        f"(based on top event probability {p_top:.4f})"
    )
    output_manager.append_section("RELIABILITY ANALYSIS", summary_text)

    out = {
        "reliability": {
            "system_reliability": reliability_val,
            "top_event_probability": p_top,
        },
        "diagnostics": {
            "warnings": [],
        },
    }
    output_manager.write_P6_json_block("reliability", out)
    return out
