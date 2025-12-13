\# PRAXIS TITAN — Architecture (P6.1 Baseline)



\## 1. System Identity



PRAXIS TITAN is an offline, file-driven probabilistic risk analysis engine for complex systems.  

This document describes the \*\*implemented P6.1 architecture\*\* as reflected in this repository.



Key properties:

\- Offline-first (no cloud dependencies)

\- Artifact-driven (files are the system of record)

\- Deterministic given same inputs (Monte Carlo uses controlled seeding/structure)

\- Human-in-the-loop by design



---



\## 2. Core Pipeline



Baseline pipeline executed by TITAN P6.1:


Each stage writes artifacts that can be inspected independently.

---

## 3. Data Contracts (Inputs)

Expected input types (typical):
- Scenario JSON: risks, likelihoods, severities, metadata
- Risk priors: Beta-Binomial priors per risk
- Common-cause groups (optional): shared failure group definitions
- Cascade matrix (optional): dependency / influence graph
- Fault tree config: gates / k-of-n structures / top-event mapping
- Adversarial twin config: perturbation mode + bounds

---

## 4. Artifact Contracts (Outputs)

Outputs are written under:


Typical run artifacts:
- `run_meta.json` — run metadata and integrity hashes (if enabled)
- `baseline_summary.json` — baseline pipeline summary
- `twin_summary.json` — adversarial twin results (if enabled)
- `sensitivity_summary.json` — ranked sensitivity drivers
- `P6_master_report.md` — human-readable report output

Design intent: **every result is traceable to input artifacts**.

---

## 5. Adversarial Twin Modeling

Adversarial twins are controlled perturbations of the baseline scenario designed to explore assumption fragility:

> “If my assumptions are wrong, how wrong could the outcome be?”

Twin modes:
- Optimistic: systematically understates risk
- Pessimistic: systematically overstates stress
- Chaotic: bounded mixed perturbations

This is not “AI hallucination.” It is repeatable, parameterized distortion.

---

## 6. Sensitivity Analysis

TITAN performs one-at-a-time sweeps to identify:
- Which risks most influence top-event probability (p_top)
- Relative leverage per input parameter

Outputs include:
- Baseline top-event probability
- Max absolute Δp_top per risk
- Ranked sensitivity drivers

This enables targeted mitigation planning.

---

## 7. Module Layout (Conceptual)

Implementation modules typically map to:
- `numeric.py` — numeric scoring
- `bayes.py` — Bayesian update
- `ccf.py` — common cause failure grouping
- `cascade.py` — propagation
- `fault_tree.py` — analytic + Monte Carlo evaluation
- `reliability.py` — optional reliability estimation
- `reporting.py` — report outputs
- `pipeline.py` — orchestration
- `engine.py` — entrypoint

---

## 8. Notes on P6.3 Evolution

P6.3 refers to governance-layer hardening, including:
- Read-only Oracle interface (artifact-only inspection)
- Stronger schema validation and response contracts
- Explicit “allowed actions” registry
- Separation of compute core vs interpretive interface

P6.3 builds on the P6.1 baseline; it does not replace the computational core.


