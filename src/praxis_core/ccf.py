
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Set

from . import output_manager
from ..utils.io import read_json

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"


def load_ccf_groups(path: Path | None = None) -> Dict[str, Any]:
    """
    Load CCF group definitions from JSON.

    Expected structure:
    {
      "groups": [
        {
          "group_id": "CCF_POWER_GAS",
          "description": "...",
          "beta_factor": 0.30,
          "members": ["R_GRID", "R_GAS"]
        }
      ],
      "default_beta": 0.0
    }
    """
    if path is None:
        path = CONFIG_DIR / "CCF_groups.json"

    try:
        data = read_json(path)
    except FileNotFoundError:
        print(f"WARNING: CCF groups file not found at {path}. Using no CCF.")
        return {"groups": [], "default_beta": 0.0}

    return data


def apply_beta_factor_to_group(
    bayes_output: Dict[str, Dict[str, Any]],
    members: List[str],
    beta: float,
) -> Dict[str, float]:
    """
    Given a set of risk IDs (members) and a beta factor, compute adjusted
    probabilities p_ccf for each member using a simple beta-factor model:

        p_ccf = (1 - beta) * p_eff + beta * p_common

    where p_common is the max p_eff over the group (conservative).
    """
    # Collect effective probabilities for the group
    p_values = []
    for rid in members:
        row = bayes_output.get(rid)
        if row is None:
            continue
        p_values.append(float(row.get("p_effective", 0.0)))

    if not p_values:
        return {}

    p_common = max(p_values)
    beta = max(0.0, min(1.0, beta))

    adjusted: Dict[str, float] = {}
    for rid in members:
        row = bayes_output.get(rid)
        if row is None:
            continue
        p_eff = float(row.get("p_effective", 0.0))
        p_ccf = (1.0 - beta) * p_eff + beta * p_common
        adjusted[rid] = p_ccf

    return adjusted


def run_ccf_layer(bayes_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Titan CCF layer (beta-factor approximation).

    - Loads CCF groups from config.
    - For each group, computes a shared 'common-cause' component.
    - Produces p_effective_ccf for each risk.
    """
    bayes_output: Dict[str, Dict[str, Any]] = bayes_result.get("bayes_output", {})
    ccf_config = load_ccf_groups()
    groups = ccf_config.get("groups", [])
    default_beta = float(ccf_config.get("default_beta", 0.0))

    ccf_output: Dict[str, Dict[str, Any]] = {}
    seen_members: Set[str] = set()
    group_summaries: List[str] = []

    # Apply group-specific beta factors
    for g in groups:
        group_id = g.get("group_id", "UNNAMED_GROUP")
        beta = float(g.get("beta_factor", default_beta))
        members = list(g.get("members", []))

        # Compute adjusted probabilities for this group
        adjusted = apply_beta_factor_to_group(bayes_output, members, beta)
        if not adjusted:
            continue

        # Build summary line for report
        member_str = ", ".join(members)
        group_summaries.append(
            f"Group {group_id} (beta={beta:.2f}) members: {member_str}"
        )

        for rid, p_ccf in adjusted.items():
            row = bayes_output[rid]
            ccf_output[rid] = {
                "id": rid,
                "domain": row.get("domain", ""),
                "risk": row.get("risk", ""),
                "failure_class": row.get("failure_class", ""),
                "p_effective": float(row.get("p_effective", 0.0)),
                "p_effective_ccf": p_ccf,
                "beta_factor": beta,
                "group_id": group_id,
            }
            seen_members.add(rid)

    # Any risks not in a group: p_ccf = p_effective (beta=0)
    for rid, row in bayes_output.items():
        if rid in seen_members:
            continue
        p_eff = float(row.get("p_effective", 0.0))
        ccf_output[rid] = {
            "id": rid,
            "domain": row.get("domain", ""),
            "risk": row.get("risk", ""),
            "failure_class": row.get("failure_class", ""),
            "p_effective": p_eff,
            "p_effective_ccf": p_eff,
            "beta_factor": 0.0,
            "group_id": None,
        }

    # Human summary
    lines: List[str] = []
    if group_summaries:
        lines.append("Common-Cause Layer (beta-factor applied):")
        lines.extend(group_summaries)
    else:
        lines.append("Common-Cause Layer – no CCF groups defined; p_ccf = p_effective.")

    # Show top by p_effective_ccf
    sorted_rows = sorted(
        ccf_output.values(), key=lambda x: x["p_effective_ccf"], reverse=True
    )
    for row in sorted_rows[:5]:
        lines.append(
            f"- {row['domain']} | {row['risk']} | p_ccf={row['p_effective_ccf']:.4f} "
            f"(p_eff={row['p_effective']:.4f}, beta={row['beta_factor']:.2f})"
        )

    summary_text = "\n".join(lines)
    output_manager.append_section("COMMON-CAUSE LAYER", summary_text)

    out = {
        "ccf_output": ccf_output,
        "diagnostics": {
            "groups_count": len(groups),
            "input_count": len(ccf_output),
            "warnings": [],
        },
    }
    output_manager.write_P6_json_block("ccf_summary", out)
    return out


