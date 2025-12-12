import pathlib
import glob

BASE_DIR = pathlib.Path(r"C:\ai_control")
OUTPUT_DIR = BASE_DIR / "output"
PRIORS_PATH = BASE_DIR / "risk_priors.txt"


def find_latest_bayes():
    """
    Find newest numeric_bayes_ANALYSIS_*.txt in output/.
    """
    pattern = str(OUTPUT_DIR / "numeric_bayes_ANALYSIS_*.txt")
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError("No numeric_bayes_ANALYSIS_*.txt files found in output.")
    files.sort()
    return pathlib.Path(files[-1])


def load_bayes(path):
    """
    Load posterior alpha/beta from numeric_bayes_ANALYSIS_*.txt.
    Skips metadata and header lines.
    Format of data lines:
    Domain | Risk | FailureClass | AlphaPrior | BetaPrior |
            ObservedLikelihood | AlphaPost | BetaPost |
            PriorMean | PosteriorMean | Severity | PosteriorRPN
    """
    rows = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Skip metadata and header
            if line.startswith("===") or line.startswith("Source:"):
                continue
            if "AlphaPost" in line and "BetaPost" in line:
                # header row
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 12:
                continue

            (domain, risk, failure_class,
             alpha_prior_str, beta_prior_str,
             obs_lik_str, alpha_post_str, beta_post_str,
             prior_mean_str, post_mean_str,
             sev_str, post_rpn_str) = parts

            key = (domain, risk, failure_class)
            rows[key] = {
                "alpha_post": float(alpha_post_str),
                "beta_post": float(beta_post_str),
                "severity": float(sev_str),
            }
    return rows


def load_priors(path):
    """
    Load existing priors file (if any).
    Format:
    Domain | Risk | FailureClass | Alpha | Beta | Severity
    """
    priors = {}
    if not path.exists():
        return priors

    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            if i == 0:
                # header
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 6:
                continue
            domain, risk, failure_class, alpha_str, beta_str, sev_str = parts
            priors[(domain, risk, failure_class)] = {
                "alpha": float(alpha_str),
                "beta": float(beta_str),
                "severity": float(sev_str),
            }
    return priors


def save_priors(path, priors):
    """
    Write priors back out in Alpha/Beta form.
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write("Domain | Risk | FailureClass | Alpha | Beta | Severity\n")
        for (domain, risk, failure_class), vals in priors.items():
            f.write(
                f"{domain} | {risk} | {failure_class} | "
                f"{vals['alpha']:.6f} | {vals['beta']:.6f} | {vals['severity']:.2f}\n"
            )


def main():
    bayes_path = find_latest_ba_
