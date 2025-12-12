from pathlib import Path
import subprocess
import sys

# Base directories
BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
OUTPUT_DIR = BASE_DIR / "output"


def run_step(label: str, script_name: str) -> bool:
    """Run one pipeline step and report success/failure."""
    print(f"\n=== {label} ===")
    script_path = SRC_DIR / script_name

    if not script_path.exists():
        print(f"[ERROR] Script not found: {script_path}")
        return False

    print(f"[RUN] {script_path}")
    result = subprocess.run([sys.executable, str(script_path)])

    if result.returncode != 0:
        print(f"[ERROR] {script_name} exited with code {result.returncode}")
        return False

    print(f"[OK] {label} finished.")
    return True


def newest(pattern: str) -> Path | None:
    """Return newest file in output/ matching the glob pattern."""
    files = list(OUTPUT_DIR.glob(pattern))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def main() -> None:
    print("=== PRAXIS RISK PIPELINE: FULL CYCLE ===")
    print(f"[INFO] Base dir   : {BASE_DIR}")
    print(f"[INFO] Output dir : {OUTPUT_DIR}")

    steps = [
        ("STEP 1: Core scenario analysis", "core_engine.py"),
        ("STEP 2: Extract numeric risk table", "risk_numeric.py"),
        ("STEP 3: Bayesian risk update", "risk_bayes.py"),
        ("STEP 4: Update risk priors from latest run", "update_priors_from_bayes.py"),
        ("STEP 5: First-order PRA", "pra_engine.py"),
        ("STEP 6: Lifecycle reliability from numeric risk", "reliability_from_numeric.py"),
    ]

    for label, script in steps:
        if not run_step(label, script):
            print("\n[ABORT] Stopping pipeline due to error in previous step.")
            return

    # Show the latest outputs from each stage
    print("\n=== SUMMARY OF LATEST OUTPUT FILES ===")
    patterns = {
        "Core analysis"     : "test_ANALYSIS_*.txt",
        "Numeric risk"      : "numeric_risk_test_ANALYSIS_*.txt",
        "Bayesian update"   : "numeric_bayes_test_ANALYSIS_*.txt",
        "PRA report"        : "pra_ANALYSIS_*.txt",
        "Reliability report": "reliability_from_numeric_ANALYSIS_*.txt",
    }

    for label, pattern in patterns.items():
        f = newest(pattern)
        if f:
            print(f"- {label}: {f.name}")
        else:
            print(f"- {label}: (no matching files found)")

    print("\n[DONE] Full cycle complete.")
    print("Open the files above from C:\\ai_control\\output in Notepad to inspect results.")


if __name__ == "__main__":
    main()
