
"""
core_engine.py – PRAXIS Core Engine

Private multi-stage pipeline for the PRAXIS risk and reliability model.
This module is part of the proprietary `praxis_core` package and is NOT
included in the public GitHub repository.

Distribution and use are governed by the commercial license.
"""

from pathlib import Path

# Import your internal modules. These files should live in the same
# package folder as this file: praxis_core/
from . import risk_numeric
from . import risk_bayes
from . import pra_engine
from . import reliability_from_numeric


def run_engine(scenario_path: str):
    """
    Top-level entrypoint for the PRAXIS engine.

    scenario_path: path to a YAML/JSON scenario file.
    """

    scenario_path = Path(scenario_path).resolve()

    print("")
    print("=======================================")
    print("  PRAXIS – Private Core Engine")
    print("=======================================")
    print(f"Scenario file: {scenario_path}")
    print("")

    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario file not found: {scenario_path}")

    # 1) NUMERIC RISK LAYER
    print("[PRAXIS] Stage 1: Numeric risk analysis...")
    numeric_output = risk_numeric.run_numeric(scenario_path)
    print(f"[PRAXIS] Numeric risk output: {numeric_output}")
    print("")

    # 2) BAYESIAN UPDATE LAYER
    print("[PRAXIS] Stage 2: Bayesian update...")
    bayes_output = risk_bayes.run_bayes(numeric_output)
    print(f"[PRAXIS] Bayesian output: {bayes_output}")
    print("")

    # 3) PRA LAYER
    print("[PRAXIS] Stage 3: PRA propagation...")
    pra_output = pra_engine.run_pra(bayes_output)
    print(f"[PRAXIS] PRA output: {pra_output}")
    print("")

    # 4) LIFECYCLE / RELIABILITY LAYER
    print("[PRAXIS] Stage 4: Lifecycle / reliability computation...")
    reliability_output = reliability_from_numeric.run_reliability(
        numeric_output=numeric_output,
        pra_output=pra_output,
    )
    print(f"[PRAXIS] Reliability output: {reliability_output}")
    print("")

    print("[PRAXIS] Pipeline complete.")
    print("")

    return {
        "numeric": numeric_output,
        "bayes": bayes_output,
        "pra": pra_output,
        "reliability": reliability_output,
    }


if __name__ == "__main__":
    # Manual CLI test:
    #   py core_engine.py path\to\scenario.yaml
    import sys

    if len(sys.argv) < 2:
        print("Usage: py core_engine.py <scenario_file>")
        raise SystemExit(1)

    run_engine(sys.argv[1])
