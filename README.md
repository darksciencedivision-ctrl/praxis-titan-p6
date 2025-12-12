RAXIS TITAN Custom Research & Attribution License (PRCAL) v1.0

Copyright (c) 2025
Samuel Lawson
All rights reserved.

1. Purpose

This license governs the use, modification, and distribution of the PRAXIS TITAN software and associated materials (the “Software”).

The Software is released to support research, education, analysis, and non-commercial experimentation in probabilistic risk modeling and complex systems analysis.

This license is intentionally more restrictive than permissive open-source licenses in order to protect authorship, attribution, and downstream misuse.

2. Permissions Granted

Subject to the terms below, permission is hereby granted to any individual or organization to:

Use the Software for personal, academic, or internal research purposes

Study and inspect the source code

Modify the Software for non-commercial research or learning

Run analyses and generate outputs for private or academic use

Reference the Software in academic or technical publications, with attribution

3. Attribution Requirement

Any use, publication, presentation, or derivative work that includes or is based on this Software must clearly attribute:

“PRAXIS TITAN by Samuel Lawson”

Attribution must appear in:

README files

Academic papers

Presentations

Reports

Documentation

Public descriptions of derived tools

Removing, obscuring, or misrepresenting authorship is strictly prohibited.

4. Restrictions

You may NOT, without explicit written permission from the author:

Sell, license, sublicense, or commercially distribute the Software

Offer the Software as part of a paid product, service, SaaS, or consulting deliverable

Repackage the Software under a different name or brand

Claim authorship or co-authorship of the original Software

Use the Software for autonomous control of real-world systems

Deploy the Software in safety-critical, life-critical, or mission-critical operational environments

Train or fine-tune proprietary AI models using the Software or its outputs

5. Derivative Works

You may create derivative works only for non-commercial purposes, provided that:

This license is retained in full

Attribution to the original author is preserved

Derivative works are clearly marked as modified

You do not imply endorsement by the original author

Derivative works must not be relicensed under more permissive terms.

6. No Warranty

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO:

MERCHANTABILITY

FITNESS FOR A PARTICULAR PURPOSE

ACCURACY

COMPLETENESS

NON-INFRINGEMENT

The entire risk as to the quality and performance of the Software is with the user.

7. Limitation of Liability

IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM:

USE OF THE SOFTWARE

MISUSE OF THE SOFTWARE

INTERPRETATION OF RESULTS

DECISIONS MADE BASED ON OUTPUTS

This includes, but is not limited to, financial loss, system failure, personal injury, or downstream consequences.

8. Termination

Any violation of the terms of this license automatically terminates the permissions granted herein.

Upon termination, you must immediately cease all use, modification, and distribution of the Software.

9. Contact & Commercial Licensing

Commercial licensing, enterprise use, or special permissions may be available.

Contact:

Samuel Lawson
GitHub: https://github.com/darksciencedivision-ctrl

10. Acceptance

By using, copying, modifying, or distributing this Software, you acknowledge that you have read, understood, and agreed to the terms of this license.

End of License
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
