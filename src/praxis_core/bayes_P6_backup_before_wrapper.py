from __future__ import annotations

import math
from typing import Dict, Any, Tuple
from pathlib import Path

from . import output_manager
from ..utils.io import read_json

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"


def load_priors(path: Path | None = None) -> Dict[str, Dict[str, float]]:
    """Load and standardize prior definitions from the config file."""
    if path is None:
        path = CONFIG_DIR / "risk_priors_example.json"

    try:
        cfg = read_json(path)
    except FileNotFoundError:
        print(f"WARNING: Priors file not found at {path}. Using defaults.")
        return {}

    priors_map: Dict[str, Dict[str, float]] = {}

    # Defaults from config, or hardcoded safe fallback
    default_alpha = float(cfg.get("default_alpha", 1.0))
    default_beta = float(cfg.get("default_beta", 1.0))
    pseudo_n_scale = float(cfg.get("pseudo_n", 10.0))

    for item in cfg.get("priors", []):
        priors_map[item["id"]] = {
            "alpha_prior": float(item.get("alpha_prior", default_alpha)),
            "beta_prior": float(item.get("beta_prior", default_beta)),
            "pseudo_n": float(item.get("n_obs", pseudo_n_scale)),
        }

    # Global fallback priors
    priors_map["__GLOBAL__"] = {
        "alpha_prior": default_alpha,
        "beta_prior": default_beta,
        "pseudo_n": pseudo_n_scale,
    }

    return priors_map


def bayes_update_risk(
    p_base: float,
    alpha_prior: float,
    beta_prior: float,
    pseudo_n: float,
) -> Tuple[float, float, float]:
    """
    Beta-Binomial Bayesian update using pseudo-counts.

    p_base acts as the probability of "success" for pseudo_n pseudo trials.

    Returns:
        (p_effective, alpha_post, beta_post)
    """
    # Pseudo successes/failures
    pseudo_successes = pseudo_n * p_base
    pseudo_failures = pseudo_n * (1.0 - p_base)

    # Posterior hyperparameters
    alpha_post = alpha_prior + pseudo_successes
    beta_post = beta_prior + pseudo_failures

    # Posterior mean
    p_effective = alpha_post / (alpha_post + beta_post)

    return p_effective, alpha_post, beta_post


def run_bayes_layer(numeric_result: Dict[str, Any]) -> Dict[str, Any]:
    numeric_rows = numeric_result.get("numeric_output", {})
    priors_map = load_priors()
    global_priors = priors_map.get("__GLOBAL__", {})

    bayes_output: Dict[str, Any] = {}

    for rid, row in numeric_rows.items():
        p_base = float(row.get("p_base", 0.0))

        # Choose priors for this risk
        risk_priors = priors_map.get(rid, global_priors)

        alpha_prior = float(risk_priors.get("alpha_prior", 1.0))
        beta_prior = float(risk_priors.get("beta_prior", 1.0))
        pseudo_n = float(risk_priors.get("pseudo_n", 10.0))

        # Bayesian update
        p_effective, alpha_post, beta_post = bayes_update_risk(
            p_base, alpha_prior, beta_prior, pseudo_n
        )

        bayes_output[rid] = {
            "id": rid,
            "domain": row.get("domain", ""),
            "risk": row.get("risk", ""),
            "p_base": p_base,
            "p_effective": p_effective,
            "alpha_prior": alpha_prior,
            "beta_prior": beta_prior,
            "alpha_post": alpha_post,
            "beta_post": beta_post,
            "pseudo_n_used": pseudo_n,
        }

    # Human summary
    lines = ["Bayes Layer (Beta-Binomial Update) – Top 5 P_effective:"]
    sorted_rows = sorted(
        bayes_output.values(), key=lambda x: x["p_effective"], reverse=True
    )
    for row in sorted_rows[:5]:
        lines.append(
            f"- {row['domain']} | {row['risk']} | P_eff={row['p_effective']:.4f} "
            f"(P_base={row['p_base']:.4f})"
        )
    summary_text = "\n".join(lines)
    output_manager.append_section("BAYES LAYER", summary_text)

    out = {
        "bayes_output": bayes_output,
        "diagnostics": {
            "priors_source": str(CONFIG_DIR / "risk_priors_example.json"),
            "input_count": len(bayes_output),
            "warnings": [],
        },
    }
    output_manager.write_P6_json_block("bayes_summary", out)
    return out



