from __future__ import annotations

import random
from pathlib import Path
from typing import Dict, Any, List, Tuple

from . import engine
from . import output_manager
from ..utils.io import read_json, write_json

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"
TWIN_OUTPUT_DIR = BASE_DIR / "output" / "P6" / "twin_scenarios"
TWIN_REPORT_PATH = BASE_DIR / "output" / "P6" / "P6_twin_report.txt"
TWIN_LLM_BRIEF_PATH = BASE_DIR / "output" / "P6" / "P6_twin_brief_for_chatbot.txt"


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_twin_config(path: Path | None = None) -> Dict[str, Any]:
    """
    Load adversarial twin configuration.
    """
    if path is None:
        path = CONFIG_DIR / "adversarial_twin_config.json"
    cfg = read_json(path)
    return cfg


# ---------------------------------------------------------------------------
# Perturbation logic with bias modes (personas)
# ---------------------------------------------------------------------------

def get_mode_ranges(
    cfg: Dict[str, Any],
    mode: str,
) -> Tuple[float, float, float, float]:
    """
    Given the global config and a bias mode, return:
        (likelihood_min, likelihood_max, severity_shift_min, severity_shift_max)

    Modes:
      - "chaotic": use config ranges as-is
      - "optimistic": push toward lower likelihoods and lower severities
      - "pessimistic": push toward higher likelihoods and higher severities
    """
    base_l_cfg = cfg.get("likelihood_scale", {})
    base_s_cfg = cfg.get("severity_shift", {})

    base_l_min = float(base_l_cfg.get("min", 1.0))
    base_l_max = float(base_l_cfg.get("max", 1.0))
    base_s_min = float(base_s_cfg.get("min", 0.0))
    base_s_max = float(base_s_cfg.get("max", 0.0))

    mode = (mode or "chaotic").lower()

    if mode == "optimistic":
        # Strong bias to lower likelihoods and lower severities
        l_min = min(base_l_min, 0.3)
        l_max = min(base_l_max, 0.9)
        s_min = min(base_s_min, -2.0)
        s_max = min(base_s_max, 0.0)
    elif mode == "pessimistic":
        # Strong bias to higher likelihoods and higher severities
        l_min = max(base_l_min, 1.0)
        l_max = max(base_l_max, 1.8)
        s_min = max(base_s_min, 0.0)
        s_max = max(base_s_max, 2.0)
    else:
        # chaotic (default): use global ranges
        l_min = base_l_min
        l_max = base_l_max
        s_min = base_s_min
        s_max = base_s_max

    return (l_min, l_max, s_min, s_max)


def perturb_scenario(
    scenario: Dict[str, Any],
    cfg: Dict[str, Any],
    run_index: int,
    mode: str,
) -> Dict[str, Any]:
    """
    Create an adversarially perturbed copy of the scenario under a given bias mode.
    """
    l_min, l_max, s_min, s_max = get_mode_ranges(cfg, mode)

    l_floor = float(cfg.get("likelihood_floor", 0.00001))
    l_ceil = float(cfg.get("likelihood_ceiling", 0.99999))
    sev_min = float(cfg.get("severity_min", 1.0))
    sev_max = float(cfg.get("severity_max", 10.0))

    new_scenario = {
        k: v for k, v in scenario.items() if k != "risks"
    }
    new_scenario["scenario_name"] = (
        scenario.get("scenario_name", "Scenario")
        + f" - TwinRun_{run_index} ({mode})"
    )

    new_risks: List[Dict[str, Any]] = []
    for r in scenario.get("risks", []):
        r_copy = dict(r)

        base_l = float(r_copy.get("likelihood", 0.0))
        base_s = float(r_copy.get("severity", 1.0))

        # Random multiplicative distortion of likelihood
        scale = random.uniform(l_min, l_max)
        new_l = base_l * scale
        new_l = max(l_floor, min(l_ceil, new_l))

        # Random additive distortion of severity
        shift = random.uniform(s_min, s_max)
        new_s = base_s + shift
        new_s = max(sev_min, min(sev_max, new_s))

        r_copy["likelihood"] = new_l
        r_copy["severity"] = new_s
        r_copy["twin_info"] = {
            "mode": mode,
            "base_likelihood": base_l,
            "scale_applied": scale,
            "base_severity": base_s,
            "shift_applied": shift,
        }

        new_risks.append(r_copy)

    new_scenario["risks"] = new_risks
    return new_scenario


# ---------------------------------------------------------------------------
# Core metrics helpers
# ---------------------------------------------------------------------------

def extract_top_and_reliability(run: Dict[str, Any]) -> Tuple[float, float]:
    """
    From a full-cycle run dict, return (top_event_probability, system_reliability).
    """
    ft_block = run.get("fault_tree", {})
    top_p = float(ft_block.get("top_event_probability", 0.0))

    rel_block = run.get("reliability", {})
    rel_info = rel_block.get("reliability", {})
    system_reliability = float(rel_info.get("system_reliability", 0.0))

    return top_p, system_reliability


# ---------------------------------------------------------------------------
# Sensitivity sweep (per-risk, likelihood factors)
# ---------------------------------------------------------------------------

def run_sensitivity_sweep(
    base_scenario: Dict[str, Any],
    cfg: Dict[str, Any],
    base_top: float,
    base_rel: float,
) -> Dict[str, Any]:
    """
    For each risk, vary its likelihood with others fixed and measure impact
    on top-event probability and reliability.

    This version is tuned for your 2-risk Titan test, but general.
    """
    factors = [0.5, 0.75, 1.0, 1.25, 1.5]

    l_floor = float(cfg.get("likelihood_floor", 0.00001))
    l_ceil = float(cfg.get("likelihood_ceiling", 0.99999))

    risk_results: List[Dict[str, Any]] = []

    risks = base_scenario.get("risks", [])
    for idx, r in enumerate(risks):
        rid = r.get("id", f"RISK_{idx}")
        name = f"{r.get('domain', '')} | {r.get('risk', '')}".strip()

        base_l = float(r.get("likelihood", 0.0))

        points: List[Dict[str, Any]] = []
        max_abs_dt = 0.0
        max_abs_dr = 0.0

        for f in factors:
            # Build new scenario with only this risk's likelihood changed
            new_scenario = {k: v for k, v in base_scenario.items() if k != "risks"}
            new_risks: List[Dict[str, Any]] = []
            for j, rj in enumerate(risks):
                r_copy = dict(rj)
                if j == idx:
                    new_l = base_l * f
                    new_l = max(l_floor, min(l_ceil, new_l))
                    r_copy["likelihood"] = new_l
                new_risks.append(r_copy)
            new_scenario["risks"] = new_risks

            # Save scenario JSON (for inspection)
            filename = f"scenario_sensitivity_{rid}_f{int(f * 100):03d}.json"
            sens_path = TWIN_OUTPUT_DIR / filename
            write_json(sens_path, new_scenario)

            # Run Titan
            run = engine.run_full_cycle(sens_path)
            t_top, t_rel = extract_top_and_reliability(run)

            dt = t_top - base_top
            dr = t_rel - base_rel
            max_abs_dt = max(max_abs_dt, abs(dt))
            max_abs_dr = max(max_abs_dr, abs(dr))

            points.append(
                {
                    "factor": f,
                    "scenario_path": str(sens_path),
                    "top_event": t_top,
                    "reliability": t_rel,
                    "delta_top_event": dt,
                    "delta_reliability": dr,
                }
            )

        risk_results.append(
            {
                "id": rid,
                "name": name,
                "max_abs_delta_top_event": max_abs_dt,
                "max_abs_delta_reliability": max_abs_dr,
                "points": points,
            }
        )

    return {
        "factors": factors,
        "risks": risk_results,
    }


# ---------------------------------------------------------------------------
# Attention targets (rank risks by sensitivity)
# ---------------------------------------------------------------------------

def compute_attention_targets(sensitivity: Dict[str, Any], top_n: int = 5) -> Dict[str, Any]:
    """
    Rank risks by max_abs_delta_top_event and return top N as 'attention targets'.
    """
    risks = sensitivity.get("risks", [])
    if not risks:
        return {"targets": []}

    ranked = sorted(
        risks,
        key=lambda r: r.get("max_abs_delta_top_event", 0.0),
        reverse=True,
    )
    top = ranked[:top_n]

    return {
        "targets": [
            {
                "id": r.get("id"),
                "name": r.get("name", ""),
                "max_abs_delta_top_event": r.get("max_abs_delta_top_event", 0.0),
                "max_abs_delta_reliability": r.get("max_abs_delta_reliability", 0.0),
            }
            for r in top
        ]
    }


# ---------------------------------------------------------------------------
# Per-mode (persona) aggregates
# ---------------------------------------------------------------------------

def compute_per_mode_aggregates(
    twins: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Compute separate aggregates for each mode/persona (optimistic/pessimistic/chaotic).
    """
    by_mode: Dict[str, List[Dict[str, Any]]] = {}
    for t in twins:
        m = str(t.get("mode", "chaotic")).lower()
        by_mode.setdefault(m, []).append(t)

    result: Dict[str, Any] = {}
    for mode, items in by_mode.items():
        if not items:
            continue
        tops = [float(x.get("top_event_probability", 0.0)) for x in items]
        rels = [float(x.get("system_reliability", 0.0)) for x in items]

        top_min = min(tops)
        top_max = max(tops)
        top_mean = sum(tops) / len(tops)

        rel_min = min(rels)
        rel_max = max(rels)
        rel_mean = sum(rels) / len(rels)

        result[mode] = {
            "count": len(items),
            "top_event_min": top_min,
            "top_event_max": top_max,
            "top_event_mean": top_mean,
            "reliability_min": rel_min,
            "reliability_max": rel_max,
            "reliability_mean": rel_mean,
        }

    return result


# ---------------------------------------------------------------------------
# LLM brief generator
# ---------------------------------------------------------------------------

def build_llm_brief(summary: Dict[str, Any]) -> str:
    """
    Build a compact, LLM-friendly text brief explaining baseline, twin spread,
    per-mode behavior, and key attention targets. Chatbot Praxis can ingest this.
    """
    base = summary.get("baseline", {})
    agg = summary.get("aggregate", {})
    per_mode = summary.get("per_mode", {})
    attention = summary.get("attention", {})

    lines: List[str] = []
    lines.append("PRAXIS P6 TWIN BRIEF (FOR CHATBOT ANALYSIS)")
    lines.append("")
    lines.append("Baseline:")
    lines.append(
        f"- Scenario: {base.get('scenario_name', 'UNKNOWN')}"
    )
    lines.append(
        f"- Baseline top-event probability: {base.get('top_event_probability', 0.0):.6f}"
    )
    lines.append(
        f"- Baseline system reliability:   {base.get('system_reliability', 0.0):.6f}"
    )
    lines.append("")
    lines.append("Twin spread (all modes combined):")
    lines.append(
        f"- Top-event p range: "
        f"{agg.get('top_event_min', 0.0):.6f} to "
        f"{agg.get('top_event_max', 0.0):.6f} "
        f"(mean {agg.get('top_event_mean', 0.0):.6f})"
    )
    lines.append(
        f"- Reliability range: "
        f"{agg.get('reliability_min', 0.0):.6f} to "
        f"{agg.get('reliability_max', 0.0):.6f} "
        f"(mean {agg.get('reliability_mean', 0.0):.6f})"
    )
    lines.append("")

    if per_mode:
        lines.append("Per-mode behavior (personas):")
        for mode, stats in per_mode.items():
            label = {
                "optimistic": "Titan-Optimist",
                "pessimistic": "Titan-Pessimist",
                "chaotic": "Titan-Chaos",
            }.get(mode, mode)
            lines.append(f"- {label} (mode={mode}):")
            lines.append(
                f"    top-event p range: {stats['top_event_min']:.6f} "
                f"to {stats['top_event_max']:.6f} "
                f"(mean {stats['top_event_mean']:.6f})"
            )
            lines.append(
                f"    reliability range: {stats['reliability_min']:.6f} "
                f"to {stats['reliability_max']:.6f} "
                f"(mean {stats['reliability_mean']:.6f})"
            )
        lines.append("")

    targets = attention.get("targets", [])
    if targets:
        lines.append("Highest-sensitivity risks (attention targets):")
        for t in targets:
            lines.append(
                f"- {t.get('id')} :: {t.get('name', '')} | "
                f"max |Δ top-event p| ≈ {t.get('max_abs_delta_top_event', 0.0):.6f}, "
                f"max |Δ reliability| ≈ {t.get('max_abs_delta_reliability', 0.0):.6f}"
            )
        lines.append("")

    lines.append(
        "Instruction for chatbot: Explain how robust the baseline conclusion is "
        "given the twin spread, how each persona (optimistic/pessimistic/chaotic) "
        "changes the risk picture, and why the listed attention-target risks matter most."
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def write_twin_report(summary: Dict[str, Any]) -> None:
    """
    Write human-readable twin report.
    """
    base = summary.get("baseline", {})
    twins = summary.get("twins", [])
    agg = summary.get("aggregate", {})
    sens = summary.get("sensitivity", {})
    per_mode = summary.get("per_mode", {})
    attention = summary.get("attention", {})

    lines: List[str] = []
    lines.append("==============================")
    lines.append("PRAXIS P6 ADVERSARIAL TWIN REPORT")
    lines.append("==============================")
    lines.append("")
    lines.append(f"Base scenario: {base.get('scenario_name', 'UNKNOWN')}")
    lines.append(
        f"Baseline top event p ≈ {base.get('top_event_probability', 0.0):.6f}, "
        f"reliability ≈ {base.get('system_reliability', 0.0):.6f}"
    )
    lines.append("")

    # Twins (worst reliability first)
    lines.append("Twin runs (sorted by worst reliability first):")
    sorted_twins = sorted(
        twins, key=lambda t: t.get("system_reliability", 1.0)
    )
    for t in sorted_twins:
        lines.append(f"- {t.get('twin_name', 'Twin')}")
        lines.append(f"  Mode: {t.get('mode', 'chaotic')}")
        lines.append(f"  Scenario path: {t.get('scenario_path', '')}")
        lines.append(
            f"  Top event p: {t.get('top_event_probability', 0.0):.6f} "
            f"(Δ vs base: {t.get('delta_top_event', 0.0):+.6f})"
        )
        lines.append(
            f"  Reliability: {t.get('system_reliability', 0.0):.6f} "
            f"(Δ vs base: {t.get('delta_reliability', 0.0):+.6f})"
        )
        lines.append(f"  Hash: {t.get('hash', '')}")
        lines.append("")

    # Aggregate statistics
    lines.append("Aggregate twin statistics (all modes):")
    lines.append(
        f"  Top event p: min={agg.get('top_event_min', 0.0):.6f}, "
        f"max={agg.get('top_event_max', 0.0):.6f}, "
        f"mean={agg.get('top_event_mean', 0.0):.6f}"
    )
    lines.append(
        f"  Reliability: min={agg.get('reliability_min', 0.0):.6f}, "
        f"max={agg.get('reliability_max', 0.0):.6f}, "
        f"mean={agg.get('reliability_mean', 0.0):.6f}"
    )
    lines.append("")

    # Per-mode aggregates
    if per_mode:
        lines.append("Per-mode aggregates:")
        for mode, stats in per_mode.items():
            label = {
                "optimistic": "Titan-Optimist",
                "pessimistic": "Titan-Pessimist",
                "chaotic": "Titan-Chaos",
            }.get(mode, mode)
            lines.append(f"- {label} (mode={mode}):")
            lines.append(
                f"    top-event p: min={stats['top_event_min']:.6f}, "
                f"max={stats['top_event_max']:.6f}, "
                f"mean={stats['top_event_mean']:.6f}"
            )
            lines.append(
                f"    reliability: min={stats['reliability_min']:.6f}, "
                f"max={stats['reliability_max']:.6f}, "
                f"mean={stats['reliability_mean']:.6f}"
            )
        lines.append("")

    # Sensitivity section
    if sens:
        lines.append("Risk sensitivity (per-risk, likelihood sweeps):")
        for r in sens.get("risks", []):
            lines.append(
                f"- {r.get('id')} :: {r.get('name', '')} | "
                f"max |Δ p_top| ≈ {r.get('max_abs_delta_top_event', 0.0):.6f}, "
                f"max |Δ reliability| ≈ {r.get('max_abs_delta_reliability', 0.0):.6f}"
            )
        lines.append("")

    # Attention targets
    targets = attention.get("targets", [])
    if targets:
        lines.append("Attention targets (highest sensitivity):")
        for t in targets:
            lines.append(
                f"- {t.get('id')} :: {t.get('name', '')} | "
                f"max |Δ p_top| ≈ {t.get('max_abs_delta_top_event', 0.0):.6f}, "
                f"max |Δ reliability| ≈ {t.get('max_abs_delta_reliability', 0.0):.6f}"
            )
        lines.append("")

    text = "\n".join(lines)
    TWIN_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    TWIN_REPORT_PATH.write_text(text, encoding="utf-8")


def append_twin_summary_to_master(summary: Dict[str, Any]) -> None:
    """
    Append a compact twin summary block into the main P6 master report.
    """
    base = summary.get("baseline", {})
    agg = summary.get("aggregate", {})
    attention = summary.get("attention", {})

    lines: List[str] = []
    lines.append("Baseline:")
    lines.append(
        f"- p_top ≈ {base.get('top_event_probability', 0.0):.4f}, "
        f"reliability ≈ {base.get('system_reliability', 0.0):.4f}"
    )
    lines.append("Twins (aggregate):")
    lines.append(
        f"- p_top range ≈ "
        f"[{agg.get('top_event_min', 0.0):.4f}, "
        f"{agg.get('top_event_max', 0.0):.4f}] "
        f"(mean ≈ {agg.get('top_event_mean', 0.0):.4f})"
    )
    lines.append(
        f"- reliability range ≈ "
        f"[{agg.get('reliability_min', 0.0):.4f}, "
        f"{agg.get('reliability_max', 0.0):.4f}] "
        f"(mean ≈ {agg.get('reliability_mean', 0.0):.4f})"
    )

    # Top 1 attention target
    targets = attention.get("targets", [])
    if targets:
        top = targets[0]
        lines.append(
            "Most sensitive risk: "
            f"{top.get('id')} with max |Δ p_top| "
            f"≈ {top.get('max_abs_delta_top_event', 0.0):.4f}"
        )

    body = "\n".join(lines)
    output_manager.append_section("ADVERSARIAL TWIN SUMMARY", body)


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def run_adversarial_twin(
    twin_cfg_path: Path | None = None,
) -> Dict[str, Any]:
    """
    Run baseline scenario + N adversarially perturbed twins through Titan.

    Supports bias modes: optimistic / pessimistic / chaotic.

    Returns a summary dict and writes:
      - twin_summary.json
      - twin_attention_targets.json
      - P6_twin_report.txt
      - P6_twin_brief_for_chatbot.txt
      - and appends an ADVERSARIAL TWIN SUMMARY section to P6_master_report.txt
    """
    cfg = load_twin_config(twin_cfg_path)
    base_scenario_rel = cfg.get("base_scenario", "config/scenario_example.json")
    base_scenario_path = (BASE_DIR / base_scenario_rel).resolve()

    runs = int(cfg.get("runs", 8))
    modes_cfg = cfg.get("modes", ["chaotic"])
    if not modes_cfg:
        modes_cfg = ["chaotic"]

    seed = cfg.get("random_seed", None)
    if seed is not None:
        random.seed(seed)

    # Ensure output dir exists
    TWIN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Baseline run
    baseline_run = engine.run_full_cycle(base_scenario_path)
    base_top, base_rel = extract_top_and_reliability(baseline_run)

    baseline_summary = {
        "scenario_name": baseline_run.get("scenario_name", str(base_scenario_path)),
        "scenario_path": str(base_scenario_path),
        "top_event_probability": base_top,
        "system_reliability": base_rel,
        "hash": baseline_run.get("hash"),
    }

    # Load base scenario JSON for perturbations and sensitivity
    base_scenario_dict = read_json(base_scenario_path)

    # Prepare mode sequence (cycle modes until we fill 'runs')
    mode_sequence: List[str] = []
    while len(mode_sequence) < runs:
        mode_sequence.extend(modes_cfg)
    mode_sequence = mode_sequence[:runs]

    twin_results: List[Dict[str, Any]] = []
    top_vals: List[float] = []
    rel_vals: List[float] = []

    for i in range(1, runs + 1):
        mode = mode_sequence[i - 1]
        twin_scenario = perturb_scenario(base_scenario_dict, cfg, i, mode)
        twin_filename = f"scenario_twin_{i:02d}_{mode}.json"
        twin_path = TWIN_OUTPUT_DIR / twin_filename
        write_json(twin_path, twin_scenario)

        twin_run = engine.run_full_cycle(twin_path)
        t_top, t_rel = extract_top_and_reliability(twin_run)

        top_vals.append(t_top)
        rel_vals.append(t_rel)

        twin_results.append(
            {
                "twin_index": i,
                "mode": mode,
                "twin_name": twin_scenario.get(
                    "scenario_name", f"TwinRun_{i} ({mode})"
                ),
                "scenario_path": str(twin_path),
                "top_event_probability": t_top,
                "system_reliability": t_rel,
                "delta_top_event": t_top - base_top,
                "delta_reliability": t_rel - base_rel,
                "hash": twin_run.get("hash"),
            }
        )

    # Aggregate stats (all modes)
    if top_vals:
        top_min = min(top_vals)
        top_max = max(top_vals)
        top_mean = sum(top_vals) / len(top_vals)
    else:
        top_min = top_max = top_mean = 0.0

    if rel_vals:
        rel_min = min(rel_vals)
        rel_max = max(rel_vals)
        rel_mean = sum(rel_vals) / len(rel_vals)
    else:
        rel_min = rel_max = rel_mean = 0.0

    aggregate = {
        "top_event_min": top_min,
        "top_event_max": top_max,
        "top_event_mean": top_mean,
        "reliability_min": rel_min,
        "reliability_max": rel_max,
        "reliability_mean": rel_mean,
    }

    # Sensitivity sweep
    sensitivity = run_sensitivity_sweep(
        base_scenario_dict, cfg, base_top, base_rel
    )

    # Attention targets
    attention = compute_attention_targets(sensitivity, top_n=5)

    # Per-mode aggregates
    per_mode = compute_per_mode_aggregates(twin_results)

    summary = {
        "baseline": baseline_summary,
        "twins": twin_results,
        "aggregate": aggregate,
        "sensitivity": sensitivity,
        "attention": attention,
        "per_mode": per_mode,
    }

    # Machine-readable JSON blocks
    output_manager.write_P6_json_block("twin_summary", summary)
    output_manager.write_P6_json_block("twin_attention_targets", attention)

    # Human-readable report
    write_twin_report(summary)

    # Append compact summary into the current P6 master report
    append_twin_summary_to_master(summary)

    # LLM brief file
    brief_text = build_llm_brief(summary)
    TWIN_LLM_BRIEF_PATH.parent.mkdir(parents=True, exist_ok=True)
    TWIN_LLM_BRIEF_PATH.write_text(brief_text, encoding="utf-8")

    return summary

