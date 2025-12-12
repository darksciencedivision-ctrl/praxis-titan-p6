from pathlib import Path

def run_numeric(scenario_path: str | Path) -> Path:
    """
    Run the numeric risk layer.

    Returns:
        Path to the numeric risk output file.
    """
    scenario_path = Path(scenario_path).resolve()

    # TODO: Insert your real numeric risk code here.
    # For now, this placeholder writes a dummy output.

    numeric_output = scenario_path.parent / "numeric_risk_OUTPUT.txt"
    with numeric_output.open("w", encoding="utf-8") as f:
        f.write("Placeholder numeric risk results.\n")

    return numeric_output
