from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_json(path: str | Path) -> Dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_scenario_config(path: str | Path) -> Dict[str, Any]:
    cfg = load_json(path)
    if "scenario_id" not in cfg:
        raise ValueError("scenario_config must contain 'scenario_id'")
    if "risks" not in cfg or not isinstance(cfg["risks"], list):
        raise ValueError("scenario_config must contain a 'risks' list")
    return cfg


def load_priors(path: str | Path) -> List[Dict[str, Any]]:
    data = load_json(path)
    priors = data.get("priors", [])
    if not isinstance(priors, list):
        raise ValueError("priors JSON must contain a 'priors' list")
    return priors


def load_ccf_groups(path: str | Path) -> List[Dict[str, Any]]:
    data = load_json(path)
    groups = data.get("ccf_groups", [])
    if not isinstance(groups, list):
        raise ValueError("ccf_groups JSON must contain a 'ccf_groups' list")
    return groups


def compute_numeric_risks(scenario_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    numeric_risks: List[Dict[str, Any]] = []

    for row in scenario_cfg.get("risks", []):
        domain = row["domain"]
        risk_name = row["risk"]
        failure_class = row["failure_class"]
        likelihood = float(row["likelihood_scenario"])
        severity = float(row["severity"])

        if not (0.0 <= likelihood <= 1.0):
            raise ValueError(f"Likelihood out of range for risk {risk_name}: {likelihood}")

        rpn = likelihood * severity

        numeric_risks.append(
            {
                "domain": domain,
                "risk": risk_name,
                "failure_class": failure_class,
                "likelihood": likelihood,
                "severity": severity,
                "rpn": rpn,
            }
        )

    return numeric_risks


def _make_prior_map(priors: List[Dict[str, Any]]) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    prior_map: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for p in priors:
        key = (p["domain"], p["risk"], p["failure_class"])
        prior_map[key] = p
    return prior_map


def bayes_update(
    numeric_risks: List[Dict[str, Any]],
    priors: List[Dict[str, Any]],
    pseudo_n: float = 5.0,
) -> List[Dict[str, Any]]:
    prior_map = _make_prior_map(priors)
    out: List[Dict[str, Any]] = []

    for row in numeric_risks:
        key = (row["domain"], row["risk"], row["failure_class"])
        prior = prior_map.get(key)

        if prior is None:
            alpha_prior = 1.0
            beta_prior = 1.0
            severity = float(row["severity"])
        else:
            alpha_prior = float(prior["alpha"])
            beta_prior = float(prior["beta"])
            severity = float(prior.get("severity", row["severity"]))

        likelihood = float(row["likelihood"])
        k = likelihood * pseudo_n
        n = pseudo_n

        alpha_post = alpha_prior + k
        beta_post = beta_prior + (n - k)

        prior_mean = alpha_prior / (alpha_prior + beta_prior)
        post_mean = alpha_post / (alpha_post + beta_post)

        posterior_rpn = post_mean * severity

        out.append(
            {
                **row,
                "alpha_prior": alpha_prior,
                "beta_prior": beta_prior,
                "alpha_post": alpha_post,
                "beta_post": beta_post,
                "prior_mean": prior_mean,
                "posterior_mean": post_mean,
                "posterior_rpn": posterior_rpn,
                "severity": severity,
            }
        )

    return out


def update_priors_from_posterior(
    bayes_rows: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    new_priors: List[Dict[str, Any]] = []

    for row in bayes_rows:
        new_priors.append(
            {
                "domain": row["domain"],
                "risk": row["risk"],
                "failure_class": row["failure_class"],
                "alpha": row["alpha_post"],
                "beta": row["beta_post"],
                "severity": row["severity"],
            }
        )

    return new_priors


def apply_ccf_beta_factor(
    bayes_rows: List[Dict[str, Any]],
    ccf_groups: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    ccf_map: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for g in ccf_groups:
        key = (g["domain"], g["risk"], g["failure_class"])
        ccf_map[key] = g

    groups: Dict[str, List[Dict[str, Any]]] = {}
    for row in bayes_rows:
        key = (row["domain"], row["risk"], row["failure_class"])
        cfg = ccf_map.get(key)
        if cfg is None:
            group_id = f"__self_{row['domain']}_{row['risk']}"
            beta_factor = 0.0
        else:
            group_id = str(cfg["ccf_group"])
            beta_factor = float(cfg["beta_factor"])

        row_copy = dict(row)
        row_copy["_ccf_group"] = group_id
        row_copy["_beta_factor"] = beta_factor
        groups.setdefault(group_id, []).append(row_copy)

    out: List[Dict[str, Any]] = []
    for _, rows in groups.items():
        max_p = max(r["posterior_mean"] for r in rows)
        for r in rows:
            beta = r["_beta_factor"]
            p_i = r["posterior_mean"]
            p_ccf = (1.0 - beta) * p_i + beta * max_p

            r_out = dict(r)
            r_out["posterior_mean_ccf"] = p_ccf
            r_out.pop("_ccf_group", None)
            r_out.pop("_beta_factor", None)
            out.append(r_out)

    return out


def attach_reliability(
    pra_rows: List[Dict[str, Any]],
    config: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """
    Attach an approximate 1-year reliability and effective failure rate.

    We treat p as the 1-year failure probability, so:
      lambda_effective = -ln(1 - p)   (for 0 < p < 1)
      reliability_1y  = exp(-lambda)  = 1 - p
    """
    out: List[Dict[str, Any]] = []

    for row in pra_rows:
        p = float(row.get("posterior_mean_ccf", row.get("posterior_mean", 0.0)))
        p = min(max(p, 0.0), 1.0)

        if p <= 0.0:
            lambda_eff = 0.0
            reliability_1y = 1.0
        elif p >= 1.0:
            lambda_eff = float("inf")
            reliability_1y = 0.0
        else:
            lambda_eff = -math.log(1.0 - p)
            reliability_1y = math.exp(-lambda_eff)  # == 1 - p

        row_out = dict(row)
        row_out["lambda_effective"] = lambda_eff
        row_out["reliability_1y"] = reliability_1y
        out.append(row_out)

    return out


def _make_pra_map(pra_rows: List[Dict[str, Any]]) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    m: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for r in pra_rows:
        key = (r["domain"], r["risk"], r["failure_class"])
        m[key] = r
    return m


def get_pra_key(row: dict) -> Tuple[str, str, str]:
    """
    Return (domain, risk, failure_class) tuple for tying rows to PRA records.

    If 'pra_key' exists and is a 3-element list/tuple or a string, use it.
    Otherwise fall back to row['domain'], row['risk'], row['failure_class'].
    """
    if "pra_key" in row and row["pra_key"]:
        key = row["pra_key"]

        # Case 1: Already a list or tuple of length 3
        if isinstance(key, (list, tuple)) and len(key) == 3:
            return key[0], key[1], key[2]

        # Case 2: It's a string "Domain | Risk | FailureClass"
        if isinstance(key, str):
            parts = key.split("|")
            parts = [p.strip() for p in parts]
            if len(parts) == 3:
                return parts[0], parts[1], parts[2]

    # Fallback
    return (
        row.get("domain", "UNKNOWN_DOMAIN"),
        row.get("risk", "UNKNOWN_RISK"),
        row.get("failure_class", "UNKNOWN_CLASS"),
    )


def simulate_fault_tree(
    pra_rows: List[Dict[str, Any]],
    fault_tree_cfg: Dict[str, Any],
    n_samples: int = 50000,
) -> Dict[str, Any]:
    """
    Monte Carlo evaluation of top events in a fault tree.

    Patched to use get_pra_key() so flexible 'pra_key' values in basic_events
    will NOT crash the engine.

    A basic event in fault_tree_cfg['basic_events'] may specify:
      - 'pra_key': [domain, risk, failure_class]
      - or 'pra_key': "Domain | Risk | FailureClass"
      - or explicit 'domain', 'risk', 'failure_class' fields.

    If no matching PRA row is found, the basic event probability is treated as 0.
    """
    pra_map = _make_pra_map(pra_rows)

    # Map fault tree basic event IDs to probabilities from PRA rows
    be_probs: Dict[str, float] = {}
    for be in fault_tree_cfg.get("basic_events", []):
        be_id = be["id"]

        # Safe key resolution: this will not throw if 'pra_key' is missing
        domain, risk, failure_class = get_pra_key(be)
        key = (domain, risk, failure_class)

        row = pra_map.get(key)
        if row is None:
            be_probs[be_id] = 0.0
        else:
            be_probs[be_id] = float(
                row.get("posterior_mean_ccf", row.get("posterior_mean", 0.0))
            )

    top_results: List[Dict[str, Any]] = []

    for te in fault_tree_cfg.get("top_events", []):
        te_id = te["id"]
        gate = te["gate"].upper()
        inputs = te["inputs"]

        n_fail = 0
        for _ in range(n_samples):
            # Sample each basic event in this top event
            sample = {
                be_id: (random.random() < be_probs.get(be_id, 0.0))
                for be_id in inputs
            }

            if gate == "AND":
                fail = all(sample[be_id] for be_id in inputs)
            elif gate == "OR":
                fail = any(sample[be_id] for be_id in inputs)
            else:
                raise ValueError(f"Unsupported gate type: {gate}")

            if fail:
                n_fail += 1

        p_hat = n_fail / n_samples if n_samples > 0 else 0.0
        if n_samples > 0:
            se = math.sqrt(max(p_hat * (1 - p_hat), 0.0) / n_samples)
            ci_low = max(0.0, p_hat - 1.96 * se)
            ci_high = min(1.0, p_hat + 1.96 * se)
        else:
            ci_low = 0.0
            ci_high = 0.0

        top_results.append(
            {
                "top_event_id": te_id,
                "gate": gate,
                "inputs": inputs,
                "probability": p_hat,
                "ci_95_low": ci_low,
                "ci_95_high": ci_high,
                "n_samples": n_samples,
            }
        )

    return {
        "top_events": top_results,
        "basic_event_probs": be_probs,
        "n_samples": n_samples,
    }


def apply_cascade_influence(
    pra_rows: List[Dict[str, Any]],
    cascade_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    pra_map: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for r in pra_rows:
        key = (r["domain"], r["risk"], r["failure_class"])
        pra_map[key] = r

    p_eff: Dict[Tuple[str, str, str], float] = {}
    for key, r in pra_map.items():
        p_eff[key] = float(r.get("posterior_mean_ccf", r.get("posterior_mean", 0.0)))

    for link in cascade_cfg.get("links", []):
        s_domain, s_risk, s_fc = link["source"]
        t_domain, t_risk, t_fc = link["target"]
        influence = float(link["influence"])

        s_key = (s_domain, s_risk, s_fc)
        t_key = (t_domain, t_risk, t_fc)

        p_source = p_eff.get(s_key, 0.0)
        p_target = p_eff.get(t_key, 0.0)

        # Prob(target fails | source influence)
        p_target_eff = 1.0 - (1.0 - p_target) * (1.0 - influence * p_source)
        p_eff[t_key] = min(1.0, max(0.0, p_target_eff))

    events_out: List[Dict[str, Any]] = []
    for key, p in p_eff.items():
        domain, risk, fc = key
        events_out.append(
            {
                "domain": domain,
                "risk": risk,
                "failure_class": fc,
                "p_effective": p,
            }
        )

    return {
        "events": events_out,
    }


def generate_text_report(praxis_output: Dict[str, Any], out_path: str | Path) -> None:
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


def run_scenario(
    scenario_config_path: str | Path,
    priors_path: str | Path,
    ccf_groups_path: str | Path,
    fault_tree_path: str | Path,
    cascade_path: str | Path,
    out_dir: str | Path,
    pseudo_n: float = 5.0,
    write_report: bool = True,
) -> Dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    scenario_cfg = load_scenario_config(scenario_config_path)
    priors_list = load_priors(priors_path)
    ccf_groups = load_ccf_groups(ccf_groups_path)
    fault_tree_cfg = load_json(fault_tree_path)
    cascade_cfg = load_json(cascade_path)

    numeric_risks = compute_numeric_risks(scenario_cfg)
    bayes_rows = bayes_update(numeric_risks, priors_list, pseudo_n=pseudo_n)
    new_priors = update_priors_from_posterior(bayes_rows)
    pra_rows = apply_ccf_beta_factor(bayes_rows, ccf_groups)
    rel_rows = attach_reliability(pra_rows, config=None)
    fault_tree_results = simulate_fault_tree(rel_rows, fault_tree_cfg)
    cascade_results = apply_cascade_influence(rel_rows, cascade_cfg)

    praxis_output: Dict[str, Any] = {
        "schema_version": "1.0",
        "scenario_id": scenario_cfg["scenario_id"],
        "numeric_risks": numeric_risks,
        "bayes": bayes_rows,
        "priors_updated": new_priors,
        "pra": pra_rows,
        "reliability": rel_rows,
        "fault_tree": fault_tree_results,
        "cascades": cascade_results,
        "metadata": {
            "praxis_core_version": "1.0.0",
            "pseudo_n": pseudo_n,
        },
    }

    out_json_path = out_dir / f"{scenario_cfg['scenario_id']}_praxis_output.json"
    save_json(praxis_output, out_json_path)

    new_priors_path = out_dir / "risk_priors_updated.json"
    save_json({"schema_version": "1.0", "priors": new_priors}, new_priors_path)

    if write_report:
        report_path = out_dir / f"{scenario_cfg['scenario_id']}_report.md"
        generate_text_report(praxis_output, report_path)

    return praxis_output
