import pathlib
import glob
import datetime

BASE_DIR = pathlib.Path(r"C:\ai_control")
OUTPUT_DIR = BASE_DIR / "output"


def find_latest_analysis():
    pattern = str(OUTPUT_DIR / "test_ANALYSIS_*.txt")
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError("No test_ANALYSIS_*.txt files found in output.")
    files.sort()
    return pathlib.Path(files[-1])


def extract_risk_section(lines):
    start_idx = None
    for i, line in enumerate(lines):
        if "2)" in line and "RISK ANALYSIS" in line.upper():
            start_idx = i
            break

    if start_idx is None:
        raise ValueError("Could not find '2) RISK ANALYSIS' section.")

    risk_lines = []
    for line in lines[start_idx + 1 :]:
        if line.strip().startswith("3)"):
            break
        risk_lines.append(line)

    return risk_lines


def parse_markdown_table(risk_lines):
    rows = []

    for line in risk_lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Remove pure separator rows like "--- | --- | ---"
        no_pipes = stripped.replace("|", "").strip()
        if no_pipes and set(no_pipes) <= {"-"}:
            continue

        # Must contain at least one |
        if "|" not in stripped:
            continue

        parts = [p.strip() for p in stripped.split("|")]

        # Remove empty edges caused by leading/trailing pipes
        if parts and parts[0] == "":
            parts = parts[1:]
        if parts and parts[-1] == "":
            parts = parts[:-1]

        # Require minimum data columns
        if len(parts) < 5:
            continue

        rows.append(parts)

    return rows


def main():
    analysis_path = find_latest_analysis()

    with open(analysis_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    try:
        risk_section = extract_risk_section(lines)
    except ValueError as e:
        print("[RISK] ERROR:", e)
        return

    table_rows = parse_markdown_table(risk_section)

    if not table_rows:
        print("[RISK] ERROR: Found '2) RISK ANALYSIS' but parsed 0 table rows.")
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path = OUTPUT_DIR / f"numeric_risk_test_ANALYSIS_{timestamp}.txt"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("Domain | Risk | FailureClass | Likelihood | Severity | RPN\n")

        for cols in table_rows:
            try:
                domain = cols[0]
                risk = cols[1]
                failure_class = cols[2]
                likelihood = float(cols[3])
                severity = float(cols[4])
                rpn = likelihood * severity

            except Exception as e:
                print("[RISK] Skipping malformed row:", cols)
                continue

            f.write(
                f"{domain} | {risk} | {failure_class} | "
                f"{likelihood:.6f} | {severity:.2f} | {rpn:.6f}\n"
            )

    print(f"[RISK] Using output directory: {OUTPUT_DIR}")
    print(f"[RISK] Using analysis file: {analysis_path}")
    print(f"[RISK] Saved numeric risk table to: {out_path}")


if __name__ == "__main__":
    main()
