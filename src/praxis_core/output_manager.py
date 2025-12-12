"""
PRAXIS P6.1 TITAN - Output Manager

This module standardizes all output and reporting for a single PRAXIS run.

It is designed so that:
- Each run gets its own directory under:  output/P6/runs/<run_id>/
- A compact run_meta.json summarizes the run.
- Master / twin / sensitivity reports are written as Markdown.
- JSON summaries are machine-readable for later analysis.

This is a scaffolding module: you can safely extend or adjust field names
to match your engine.py structures.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..utils import io  # expects io.load_json / io.write_json / io.write_text


# ---------------------------------------------------------------------------
# Run ID & Directory Management
# ---------------------------------------------------------------------------

def generate_run_id(scenario_name: Optional[str] = None) -> str:
    """
    Generate a human-readable run ID based on UTC timestamp and scenario name.

    Example: 20251211T083012Z_Black_Swan_Saturday
    """
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    if scenario_name:
        safe = "".join(c if c.isalnum() else "_" for c in scenario_name)
        safe = safe.strip("_")[:32] or "Scenario"
        return f"{ts}_{safe}"
    return ts


def create_run_directory(base_output_dir: str, run_id: str) -> Path:
    """
    Create the directory for this run:

        <base_output_dir>/P6/runs/<run_id>/

    Also updates:

        <base_output_dir>/P6/latest/LATEST_RUN.txt
    """
    base = Path(base_output_dir)
    runs_root = base / "P6" / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)

    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Update latest pointer (simple text file)
    latest_dir = base / "P6" / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    io.write_text(latest_dir / "LATEST_RUN.txt", run_id + "\n")

    return run_dir


# ---------------------------------------------------------------------------
# Run Metadata
# ---------------------------------------------------------------------------

def write_run_meta(run_dir: Path, meta: Dict[str, Any]) -> None:
    """
    Write run_meta.json into the run directory.

    'meta' is expected to be a dictionary with keys such as:
      - run_id
      - praxis_version
      - scenario_file
      - scenario_name
      - timestamp_utc
      - iterations_mc
      - twin_clones
      - sensitivity_factors
      - hashes
      - performance
      - top_event
      - most_sensitive_risks
    """
    io.write_json(run_dir / "run_meta.json", meta)


# ---------------------------------------------------------------------------
# Master Report (Markdown)
# ---------------------------------------------------------------------------

def render_master_report(ctx: Dict[str, Any]) -> str:
    """
    Render the main PRAXIS P6.1 master run report as Markdown.

    'ctx' should contain at least:
      - run_id
      - scenario_name
      - scenario_description
      - praxis_version
      - n_risks
      - domains
      - p_top_analytic
      - p_top_mc_mean
      - p_top_mc_ci_95
      - reliability
      - most_sensitive_risks  (list of dicts)
      - risk_table            (list of dicts for |ID|Domain|...|)
      - ft_structure_summary  (string description of gates)
      - mc_iterations
      - mc_notes
    """
    # Helper to pull values safely
    def g(key: str, default: Any = "N/A") -> Any:
        return ctx.get(key, default)

    run_id = g("run_id")
    scenario_name = g("scenario_name")
    scenario_description = g("scenario_description")
    praxis_version = g("praxis_version", "P6.1-TITAN")

    n_risks = g("n_risks")
    domains = ", ".join(g("domains", []))

    p_top_analytic = g("p_top_analytic")
    p_top_mc_mean = g("p_top_mc_mean")
    p_top_mc_ci = g("p_top_mc_ci_95", [None, None])
    reliability = g("reliability")

    most_sensitive = g("most_sensitive_risks", [])
    risk_table = g("risk_table", [])
    ft_struct = g("ft_structure_summary", "Not specified.")
    mc_iterations = g("mc_iterations", "N/A")
    mc_notes = g("mc_notes", "N/A")

    # Build sensitivity bullet list
    sens_lines: List[str] = []
    for item in most_sensitive:
        rid = item.get("id", "UNKNOWN")
        dpt = item.get("delta_p_top_max", "N/A")
        dom = item.get("domain", "")
        sens_lines.append(f"- {rid} ({dom}) – Δp_top_max ≈ {dpt}")
    sens_block = "\n".join(sens_lines) if sens_lines else "No sensitivity data available."

    # Build risk table section
    risk_table_lines: List[str] = []
    if risk_table:
        risk_table_lines.append(
            "| ID | Domain | Risk | p_base | p_effective | p_ccf | p_final |"
        )
        risk_table_lines.append(
            "|----|--------|------|--------|-------------|-------|---------|"
        )
        for r in risk_table:
            risk_id = r.get("id", "")
            domain = r.get("domain", "")
            desc = r.get("risk", "")
            p_base = r.get("p_base", "")
            p_eff = r.get("p_effective", "")
            p_ccf = r.get("p_ccf", "")
            p_final = r.get("p_final", "")
            risk_table_lines.append(
                f"| {risk_id} | {domain} | {desc} | {p_base} | {p_eff} | {p_ccf} | {p_final} |"
            )
    else:
        risk_table_lines.append("_No risk table available in context._")

    risk_table_block = "\n".join(risk_table_lines)

    # Monte Carlo CI
    ci_low = p_top_mc_ci[0]
    ci_high = p_top_mc_ci[1]

    text = f"""# PRAXIS P6.1 TITAN – MASTER RUN REPORT
**Run ID:** {run_id}  
**Scenario:** {scenario_name}  
**Version:** {praxis_version}  

---

## 1. Scenario Overview
- Scenario name: {scenario_name}
- Description: {scenario_description}
- Number of risks: {n_risks}
- Domains: {domains}

---

## 2. Key Results (Executive Summary)
- Top event (analytic) p_top ≈ {p_top_analytic}
- Top event (Monte Carlo) p_top ≈ {p_top_mc_mean}
- Monte Carlo 95% CI: [{ci_low}, {ci_high}]
- System reliability ≈ {reliability}

Most sensitive risks (by Δp_top_max):
{sens_block}

---

## 3. Risk Table (Final Probabilities)

{risk_table_block}

---

## 4. Fault Tree Results
- Fault-tree structure:
{ft_struct}

- Analytic top-event probability:
  - p_top_analytic ≈ {p_top_analytic}

---

## 5. Monte Carlo Validation
- Iterations: {mc_iterations}
- p_top_mean ≈ {p_top_mc_mean}
- 95% CI: [{ci_low}, {ci_high}]
- Notes: {mc_notes}

---

## 6. Model Integrity & Diagnostics
- Run ID: {run_id}
- Engine version: {praxis_version}
"""

    return text


def write_master_report(run_dir: Path, context: Dict[str, Any]) -> None:
    """
    Render and write master_report.md in the run directory.
    """
    report_text = render_master_report(context)
    io.write_text(run_dir / "master_report.md", report_text)


# ---------------------------------------------------------------------------
# Twin Report (Markdown + optional JSON summary)
# ---------------------------------------------------------------------------

def render_twin_report(ctx: Dict[str, Any]) -> str:
    """
    Render the adversarial twin report as Markdown.

    'ctx' is expected to contain:
      - run_id
      - baseline_p_top
      - baseline_reliability
      - twins (list of dicts with twin_id, mode, p_top, reliability, delta_p_top)
      - p_top_min
      - p_top_max
      - reliability_min
      - reliability_max
    """
    def g(key: str, default: Any = "N/A") -> Any:
        return ctx.get(key, default)

    run_id = g("run_id")
    baseline_p = g("baseline_p_top")
    baseline_rel = g("baseline_reliability")
    twins = g("twins", [])

    p_top_min = g("p_top_min")
    p_top_max = g("p_top_max")
    rel_min = g("reliability_min")
    rel_max = g("reliability_max")

    # Build table
    lines: List[str] = []
    if twins:
        lines.append(
            "| Twin ID | Mode | p_top | Reliability | Δp_top vs baseline |"
        )
        lines.append(
            "|---------|------|-------|-------------|--------------------|"
        )
        for t in twins:
            twin_id = t.get("twin_id", "")
            mode = t.get("mode", "")
            p_top = t.get("p_top", "")
            rel = t.get("reliability", "")
            dp = t.get("delta_p_top", "")
            lines.append(
                f"| {twin_id} | {mode} | {p_top} | {rel} | {dp} |"
            )
    else:
        lines.append("_No twin results provided in context._")

    table_block = "\n".join(lines)

    text = f"""# PRAXIS P6.1 – ADVERSARIAL TWIN REPORT
**Run ID:** {run_id}  

---

## 1. Overview
- Baseline top-event probability: {baseline_p}
- Baseline system reliability: {baseline_rel}
- Total twins: {len(twins)}
- Observed p_top range across twins: [{p_top_min}, {p_top_max}]
- Observed reliability range across twins: [{rel_min}, {rel_max}]

---

## 2. Twin Summary Table

{table_block}
"""

    return text


def write_twin_report(run_dir: Path, twin_ctx: Dict[str, Any]) -> None:
    """
    Write twin_report.md and twin_summary.json into the run directory.

    twin_ctx should match the expectations of render_twin_report plus
    be valid JSON-friendly data.
    """
    report_text = render_twin_report(twin_ctx)
    io.write_text(run_dir / "twin_report.md", report_text)

    # Also write a JSON summary for machine consumption
    io.write_json(run_dir / "twin_summary.json", twin_ctx)


# ---------------------------------------------------------------------------
# Sensitivity Reports
# ---------------------------------------------------------------------------

def render_sensitivity_report(ctx: Dict[str, Any]) -> str:
    """
    Render the sensitivity analysis report as Markdown.

    'ctx' should contain:
      - run_id
      - factors (list[float])
      - risks (list of dicts with id, domain, delta_p_top_max, etc.)
      - detailed (optional dict mapping risk_id -> list of factor sweeps)
    """
    def g(key: str, default: Any = "N/A") -> Any:
        return ctx.get(key, default)

    run_id = g("run_id")
    factors = g("factors", [])
    risks = g("risks", [])
    detailed = g("detailed", {})

    # High-level table
    lines: List[str] = []
    if risks:
        lines.append(
            "| Rank | Risk ID | Domain | Δp_top_max |"
        )
        lines.append(
            "|------|---------|--------|------------|"
        )
        sorted_risks = sorted(
            risks,
            key=lambda r: r.get("delta_p_top_max", 0.0),
            reverse=True
        )
        for idx, r in enumerate(sorted_risks, start=1):
            rid = r.get("id", "")
            dom = r.get("domain", "")
            dpt = r.get("delta_p_top_max", "")
            lines.append(
                f"| {idx} | {rid} | {dom} | {dpt} |"
            )
    else:
        lines.append("_No sensitivity data provided in context._")

    table_block = "\n".join(lines)

    # Optional detailed sweeps
    detailed_blocks: List[str] = []
    for rid, sweeps in detailed.items():
        detailed_blocks.append(f"### Detailed sweeps for {rid}")
        detailed_blocks.append(
            "| Factor | p_top | Δp_top vs baseline |"
        )
        detailed_blocks.append(
            "|--------|-------|--------------------|"
        )
        for s in sweeps:
            f = s.get("factor", "")
            p_top = s.get("p_top", "")
            dp = s.get("delta_p_top", "")
            detailed_blocks.append(
                f"| {f} | {p_top} | {dp} |"
            )
        detailed_blocks.append("")  # blank line

    detailed_block = "\n".join(detailed_blocks) if detailed_blocks else "_No detailed sweep data recorded._"

    text = f"""# PRAXIS P6.1 – SENSITIVITY REPORT
**Run ID:** {run_id}  

---

## 1. Method
- Per-risk multiplicative sweep of likelihood.
- Factors used: {factors}

---

## 2. High-Leverage Risks

{table_block}

---

## 3. Detailed Sweeps

{detailed_block}
"""

    return text


def write_sensitivity_reports(run_dir: Path, sens_ctx: Dict[str, Any]) -> None:
    """
    Write sensitivity_report.md and sensitivity_summary.json into the run directory.
    """
    report_text = render_sensitivity_report(sens_ctx)
    io.write_text(run_dir / "sensitivity_report.md", report_text)
    io.write_json(run_dir / "sensitivity_summary.json", sens_ctx)

