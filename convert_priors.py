import pathlib

# Base directory where your PRAxis stack lives
BASE = pathlib.Path(r"C:\ai_control")

# Old priors file (from your previous system)
OLD_PATH = BASE / "risk_priors_old.txt"
# New priors file (Beta prior form)
NEW_PATH = BASE / "risk_priors.txt"

# How "strong" the initial priors are (pseudo-sample size)
# N0 = 10 means your initial PriorMean is treated like 10 Bernoulli trials.
N0 = 10.0

def main():
    with OLD_PATH.open("r", encoding="utf-8") as f_in, \
         NEW_PATH.open("w", encoding="utf-8") as f_out:

        for i, line in enumerate(f_in):
            line = line.strip()
            if not line:
                continue

            # First line is assumed to be header
            if i == 0:
                # Old header: Domain | Risk | FailureClass | PriorMean | Severity
                # New header:
                f_out.write("Domain | Risk | FailureClass | Alpha | Beta | Severity\n")
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 5:
                continue

            domain, risk, failure_class, prior_mean_str, severity = parts

            m = float(prior_mean_str)
            alpha = m * N0
            beta = (1.0 - m) * N0

            f_out.write(
                f"{domain} | {risk} | {failure_class} | "
                f"{alpha:.6f} | {beta:.6f} | {severity}\n"
            )

if __name__ == "__main__":
    main()
