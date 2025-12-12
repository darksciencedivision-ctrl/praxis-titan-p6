import pathlib
import glob
import datetime
import math

BASE_DIR = pathlib.Path(r"C:\ai_control")
OUTPUT_DIR = BASE_DIR / "output"

# ==============================
# PERFECT STORM 2032 SETTINGS
# ==============================

SCENARIO_AMBIENT_C = 52.0        # 125 °F heat dome
REFERENCE_AMBIENT_C = 25.0
MTTF_YEARS_BASE = 40.0           # Transformer baseline life at 110 °C hotspot
HOURS_PER_YEAR = 8760.0
MISSION_HOURS = 120.0            # 5 days per scenario spec

# ==============================
# FILE DISCOVERY
# ==============================

def find_latest_numeric_risk():
    pattern = str(OUTPUT_DIR / "numeric_risk_test_ANALYSIS_*.txt")
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError("No numeric_risk_test_ANALYSIS_*.txt files found in output.")
    files.sort()
    return pathlib.Path(files[-1])

# ==============================
# MAIN COMPUTATION
# ==============================

def main():
    numeric_path = find_latest_numeric_risk()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path = OUTPUT_DIR / f"reliability_from_numeric_ANALYSIS_{timestamp}.txt"

    lambda_base = 1.0 / (MTTF_YEARS_BASE * HOURS_PER_YEAR)

    # Arrhenius 2x per 10K acceleration
    delta_T = SCENARIO_AMBIENT_C - REFERENCE_AMBIENT_C
    accel = 2.0 ** (delta_T / 10.0)

    with open(numeric_path, "r", encoding="utf-8") as fin, open(out_path, "w", encoding="utf-8") as fout:
        fout.write("=== RELIABILITY AND AGING FROM NUMERIC RISK ===\n")
        fout.write(f"Numeric source: {numeric_path}\n")
        fout.write(f"Scenario ambient (C): {SCENARIO_AMBIENT_C}\n")
        fout.write(f"Mission window (hours): {MISSION_HOURS}\n")
        fout.write(
            "Domain | Risk | FailureClass | IsTransformer | "
            "MTTF_base_yrs | MTTF_heat_yrs | "
            "P_fail_base_mission | P_fail_heat_mission | "
            "Scenario_L | Implied_MTTF_yrs_nontransformer\n"
        )

        for line in fin:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "Domain" in line and "Likelihood" in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 6:
                continue

            domain, risk, failure_class, lik_str, sev_str, rpn_str = parts
            L = float(lik_str)

            is_transformer = "transformer" in risk.lower()

            if is_transformer:
                lambda_use = lambda_base * accel

                p_fail_base = 1.0 - math.exp(-lambda_base * MISSION_HOURS)
                p_fail_heat = 1.0 - math.exp(-lambda_use * MISSION_HOURS)

                mttf_base_yrs = MTTF_YEARS_BASE
                mttf_heat_yrs = 1.0 / (lambda_use * HOURS_PER_YEAR)

                implied_mttf_non_tx = 0.0
            else:
                if L >= 1.0:
                    L = 0.999999
                if L <= 0.0:
                    L = 1e-9

                lam = -math.log(1.0 - L) / MISSION_HOURS
                implied_mttf_hours = 1.0 / lam
                implied_mttf_non_tx = implied_mttf_hours / HOURS_PER_YEAR

                p_fail_base = L
                p_fail_heat = L
                mttf_base_yrs = implied_mttf_non_tx
                mttf_heat_yrs = implied_mttf_non_tx

            fout.write(
                f"{domain} | {risk} | {failure_class} | "
                f"{int(is_transformer)} | "
                f"{mttf_base_yrs:.6f} | {mttf_heat_yrs:.6f} | "
                f"{p_fail_base:.6f} | {p_fail_heat:.6f} | "
                f"{L:.6f} | {implied_mttf_non_tx:.6f}\n"
            )

    print(f"Wrote reliability/aging output to: {out_path}")

# ==============================
# ENTRY POINT
# ==============================

if __name__ == "__main__":
    main()
