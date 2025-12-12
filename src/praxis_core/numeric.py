from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List

from . import output_manager
from ..utils.io import read_json

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"


def load_numeric_config() -> Dict[str, Any]:
    """
    Load numeric weighting config.

    Structure:
    {
      "severity_max": 5.0,
      "weights": {
        "likelihood": 0.5,
        "severity": 0.3,
        "failure_class": 0.2
      },
      "failure_class_weights": {
        "CMF": 1.25,
        "SPF": 1.00,
        "LF": 0.90,
        "ENV": 0.80,
        "CYBER": 1.15,
        "DEFAULT": 1.00
      }
    }
    """
    path = CONFIG_DIR / "numeric_weights.json"
    try:
        cfg = read_json(path)
    except FileNotFoundError:
        print(f"WARNING: numeric_weights.json not found at {path}, using defaults.")
        cfg = {
            "severity_max": 5.0,
            "weights": {
                "likelihood": 0.5,
                "severity": 0.3,
                "failure_class": 0.2,
            },
            "failure_class_weights": {
                "DEFAULT": 1.0,
            },
        }
    return cfg


def get_failure_class_weight(fc: str, fc_weights: Dict[str, float]) -> float:
    fc = (fc or "").upper()
    if fc in fc_weights:
        return float(fc_weights[fc])
    return float(fc_weights.get("DEFAULT", 1.0))


def compute_numeric_risks(scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Titan+ Numeric Layer:

    - p_base: bounded [1e-5, 0.99999] from scenario likelihood
    - severity_norm: severity / severity_max (clamped)
    - fc_weight: from failure_class_weights
    - risk_score: weighted combination of (p_base, severity_norm, fc_weight)
    """
    cfg = load_numeric_config()
    sev_max = float(cfg.get("severity_max", 5.0))
    w_cfg = cfg.get("weights", {})
    w_like = float(w_cfg.get("likelihood", 0.5))
    w_sev = float(w_cfg.get("severity", 0.3))
    w_fc = float(w_cfg.get("failure_class", 0.2))

    fc_weights = {
        k.upper(): float(v)
        for k, v in cfg.get("failure_class_weights", {}).items()
    }

    risks = scenario.get("risks", [])
    numeric_rows: List[Dict[str, Any]] = []

    for r in risks:
        p_raw = float(r.get("likelihood", 0.0))
        p_base = max(0.00001, min(0.99999, p_raw))

        severity = float(r.get("severity", 1.0))
        if sev_max <= 0:
            severity_norm = 0.0
        else:
            severity_norm = max(0.0, min(1.0, severity / sev_max))

        fc = r.get("failure_class", "")
        fc_weight = get_failure_class_weight(fc, fc_weights)

        # Composite risk score (dimensionless, ~0-1.5 typical range)
        risk_score = (
            w_like * p_base
            + w_sev * severity_norm
            + w_fc * (fc_weight / max(1.0, fc_weights.get("DEFAULT", 1.0)))
        )

        # Keep original simple RPN for continuity
        rpn = p_base * severity

        numeric_rows.append(
            {
                "id": r.get("id", ""),
                "domain": r.get("domain", ""),
                "risk": r.get("risk", ""),
                "failure_class": fc,
                "p_base": p_base,
                "severity": severity,
                "severity_norm": severity_norm,
                "failure_class_weight": fc_weight,
                "rpn": rpn,
                "risk_score": risk_score,
            }
        )

    return numeric_rows


def run_numeric_layer(scenario: Dict[str, Any]) -> Dict[str, Any]:
    numeric_rows = compute_numeric_risks(scenario)

    # Human summary
    lines = ["Top Numeric Risks (by risk_score):"]
    sorted_rows = sorted(numeric_rows, key=lambda x: x["risk_score"], reverse=True)
    for row in sorted_rows[:5]:
        lines.append(
            f"- {row['domain']} | {row['risk']} | "
            f"p_base={row['p_base']:.4f}, "
            f"sev={row['severity']:.1f}, "
            f"score={row['risk_score']:.4f}"
        )
    summary_text = "\n".join(lines)

    output_manager.append_section("NUMERIC LAYER", summary_text)

    # Machine-readable JSON block
    numeric_dict = {
        "numeric_output": {row["id"]: row for row in numeric_rows},
        "diagnostics": {
            "input_count": len(numeric_rows),
            "zero_values": sum(
                1 for r in numeric_rows if r["p_base"] <= 0.00001
            ),
            "warnings": [],
        },
    }
    output_manager.write_P6_json_block("numeric_summary", numeric_dict)
    return numeric_dict


