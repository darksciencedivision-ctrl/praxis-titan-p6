PRAXIS TITAN P6.1

Offline Probabilistic Risk Analysis Engine for Complex Systems

Author: Samuel Lawson
License: Custom Research & Attribution License (see LICENSE)
Status: Public Research Release (Second Published Model)

Overview

PRAXIS TITAN P6.1 is an offline, file-driven probabilistic risk analysis engine designed to model complex, interdependent systems under uncertainty.

It combines deterministic scoring with Bayesian updating, cascading effects, fault-tree analysis, adversarial scenario exploration, and sensitivity analysis — all without requiring cloud access, APIs, or external services.

This release represents the second public evolution of the PRAXIS engine family and introduces:

A unified baseline pipeline

Adversarial twin modeling

Monte Carlo fault-tree estimation

One-at-a-time sensitivity sweeps

Fully reproducible, inspectable outputs

PRAXIS TITAN is intended for research, analysis, and decision-support, not automated control.

Design Philosophy

PRAXIS is built around four core principles:

Offline First
Runs entirely locally. No cloud dependencies. No external APIs.

Explainability Over Black Boxes
Every stage produces intermediate artifacts you can inspect.

Composable Risk Layers
Each analytical layer can be swapped, bypassed, or extended.

Adversarial Awareness
The model does not assume “average conditions” — it actively explores how assumptions break.

Core Pipeline

The baseline pipeline executed by TITAN P6.1 is:

Scenario JSON
   ↓
Numeric Risk Scoring
   ↓
Bayesian Updating (Beta-Binomial)
   ↓
Common Cause Failure (optional)
   ↓
Cascade Effects (optional)
   ↓
Fault Tree (Analytic)
   ↓
Fault Tree (Monte Carlo)
   ↓
Reliability Estimation (optional)


On top of the baseline, TITAN can run:

Adversarial Twin Scenarios (optimistic / pessimistic / chaotic)

Sensitivity Analysis (one-at-a-time parameter sweeps)

What “Adversarial Twins” Mean Here

Adversarial twins are systematically distorted versions of the baseline scenario that answer:

“If my assumptions are wrong, how wrong could the outcome be?”

Each twin modifies risk probabilities according to a defined mode:

Optimistic – assumptions consistently understate risk

Pessimistic – assumptions consistently overstate stress

Chaotic – mixed perturbations within bounded ranges

The engine reports how each twin shifts the top event probability (Δp_top).

This is not AI hallucination — it is controlled, repeatable perturbation.

Sensitivity Analysis

TITAN performs one-at-a-time sensitivity sweeps to identify:

Which individual risks most influence the final outcome

The relative leverage of each risk on the top event probability

Outputs include:

Baseline top-event probability

Max absolute Δp_top per risk

Ranked sensitivity drivers

This allows targeted mitigation instead of broad guesswork.

Directory Structure
praxis-titan-p6/
│
├─ config/                  # Scenario, priors, twin configs
├─ src/praxis_core/         # Core engine modules
├─ output/P6/               # Run outputs (JSON + reports)
├─ reports/                 # Human-readable summaries
├─ logs/                    # Execution logs
├─ memory/                  # Persistent priors / state (optional)
│
├─ engine.py                # Main orchestrator
├─ pyproject.toml
├─ P6_master_report.md
└─ README.md

Running the Engine

From the project root:

cd C:\ai_control
python -m src.praxis_core.engine


The engine expects the following files:

config/scenario_example.json
config/risk_priors_example.json
config/adversarial_twin_config.json


Outputs are written to:

output/P6/runs/<run_id>_<scenario_name>/

Outputs Generated Per Run

Each run produces:

run_meta.json – run metadata and hashes

baseline_summary.json – full baseline pipeline output

twin_summary.json – adversarial twin results

sensitivity_summary.json – sensitivity analysis

P6_master_report.md – human-readable report

All outputs are deterministic given the same inputs.

Current Capabilities (P6.1)

✔ Numeric risk scoring
✔ Bayesian updating with effective sample size
✔ Common cause failure grouping
✔ Cascading probability propagation
✔ Analytic fault-tree evaluation
✔ Monte Carlo fault-tree estimation
✔ Adversarial twin modeling
✔ Sensitivity analysis
✔ Full run traceability

Known Limitations (Intentional)

Reliability modeling is currently stubbed / optional

Fault-tree structures must be explicitly defined

No GUI (command-line and file driven by design)

Not optimized for massive Monte Carlo scale (yet)

These are design choices, not oversights.

Intended Use Cases

Infrastructure risk analysis

Human-machine system modeling

Engineering decision support

Scenario stress testing

Research & academic exploration

Offline contingency analysis

Not intended for:

Autonomous control

Real-time operational decision making

Financial trading automation

License

This project is released under a Custom Research & Attribution License.

You may:

Study the code

Run the engine

Modify it for personal or academic use

You may not:

Repackage it commercially

Remove attribution

Represent derivative work as the original

See LICENSE for full terms.

Author Statement

PRAXIS TITAN is developed and maintained by Samuel Lawson as part of an ongoing research effort into probabilistic risk modeling, adversarial analysis, and complex system resilience.

This repository represents a real, functioning analytical engine, not a demo or mockup.
