import pathlib
import glob
import datetime

BASE_DIR = pathlib.Path(r"C:\ai_control")
OUTPUT_DIR = BASE_DIR / "output"
PRIORS_PATH = BASE_DIR / "risk_priors.txt"

# FailureClass-dependent pseudo-sample sizes
# Tweak these as you like.
PSEUDO_N_BY_CLASS = {
    "SPF": 8.0,   # Single-point failures – more weight
    "CMF": 6.0,   # Common-mode failures
    "LF": 5.0,    # Latent / long-fuse
    "CF": 4.0,    # Cyber / control failures
}
PSEUDO_N_DEFAULT = 5.0  # fallback if FailureClass not in table


def find_latest_numeric_risk():
    pattern = str(OUTPUT_DIR / "numeric_risk_test_ANALYSIS_*.txt")
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError("No numeric_risk_test_ANALYSIS_*.txt files found in output.")
    files.sort()
    return pathlib.Path(files[-1])


def load_priors(path):
    priors = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "Alpha" in line and "Beta" in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 6:
                continue
            domain, risk, failure_class, alpha_str, beta_str, sev_str = parts
            key = (domain, risk, failure_class)
            priors[key] = {
                "Alpha": float(alpha_str),
                "Beta": float(beta_str),
                "Severity": float(sev_str),
            }
    return priors


def load_numeric_risk(path):
    rows = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "Domain" in line and "Likelihood" in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 6:
                continue
            if parts[0].startswith("---"):
                continue
            domain, risk, failure_class, lik_str, sev_str, rpn_str = parts
            key = (domain, risk, failure_class)
            rows[key] = {
                "Domain": domain,
                "Risk": risk,
                "FailureClass": failure_class,
                "Likelihood": float(lik_str),
                "Severity": float(sev_str),
            }
    return rows


def main():
    numeric_path = find_latest_numeric_risk()
    priors = load_priors(PRIORS_PATH)
    numeric_rows = load_numeric_risk(numeric_path)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path = OUTPUT_DIR / f"numeric_bayes_ANALYSIS_{timestamp}.txt"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("=== BAYESIAN RISK UPDATE (BETA-BINOMIAL) ===\n")
        f.write(f"Source: {numeric_path}\n")
        f.write(
            "Domain | Risk | FailureClass | AlphaPrior | BetaPrior | "
            "ObservedLikelihood | AlphaPost | BetaPost | PriorMean | "
            "PosteriorMean | Severity | PosteriorRPN\n"
        )

        for key, nrow in numeric_rows.items():
            domain = nrow["Domain"]
            risk = nrow["Risk"]
            failure_class = nrow["FailureClass"]
            likelihood = nrow["Likelihood"]
            severity = nrow["Severity"]

            prior = priors.get(key, {"Alpha": 1.0, "Beta": 1.0, "Severity": severity})
            alpha_prior = prior["Alpha"]
            beta_prior = prior["Beta"]

            # FailureClass-dependent pseudo-counts
            pseudo_n = PSEUDO_N_BY_CLASS.get(failure_class, PSEUDO_N_DEFAULT)

            # Beta-Binomial update with pseudo-counts
            k = likelihood * pseudo_n
            alpha_post = alpha_prior + k
            beta_post = beta_prior + (pseudo_n - k)

            prior_mean = alpha_prior / (alpha_prior + beta_prior)
            post_mean = alpha_post / (alpha_post + beta_post)
            post_rpn = post_mean * severity

            f.write(
                f"{domain} | {risk} | {failure_class} | "
                f"{alpha_prior:.6f} | {beta_prior:.6f} | {likelihood:.6f} | "
                f"{alpha_post:.6f} | {beta_post:.6f} | "
                f"{prior_mean:.6f} | {post_mean:.6f} | "
                f"{severity:.2f} | {post_rpn:.6f}\n"
            )

    print(f"Wrote Bayesian update to: {out_path}")


if __name__ == "__main__":
    main()
