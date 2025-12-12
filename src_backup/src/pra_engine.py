import pathlib
import glob
import datetime

BASE_DIR = pathlib.Path(r"C:\ai_control")
OUTPUT_DIR = BASE_DIR / "output"
CCF_CONFIG_PATH = BASE_DIR / "ccf_groups.txt"


def find_latest_numeric_risk():
    pattern = str(OUTPUT_DIR / "numeric_risk_test_ANALYSIS_*.txt")
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError("No numeric_risk_test_ANALYSIS_*.txt files found in output.")
    files.sort()
    return pathlib.Path(files[-1])


def find_latest_bayes():
    pattern = str(OUTPUT_DIR / "numeric_bayes_ANALYSIS_*.txt")
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError("No numeric_bayes_ANALYSIS_*.txt files found in output.")
    files.sort()
    return pathlib.Path(files[-1])


def load_numeric_risk(path):
    """
    Domain | Risk | FailureClass | Likelihood | Severity | (optional RPN column)
    """
    rows = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "Domain" in line and "Likelihood" in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 5:
                continue
            if parts[0].startswith("---"):
                continue

            domain, risk, failure_class, lik_str, sev_str = parts[:5]

            likelihood = float(lik_str)
            severity = float(sev_str)

            key = (domain, risk, failure_class)
            rows[key] = {
                "Domain": domain,
                "Risk": risk,
                "FailureClass": failure_class,
                "Likelihood": likelihood,
                "Severity": severity,
            }
    return rows


def load_bayes(path):
    """
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
            if line.startswith("===") or line.startswith("Source:"):
                continue
            if "AlphaPost" in line and "PosteriorMean" in line:
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
                "Domain": domain,
                "Risk": risk,
                "FailureClass": failure_class,
                "PriorMean": float(prior_mean_str),
                "PosteriorMean": float(post_mean_str),
                "Severity": float(sev_str),
            }
    return rows


def load_ccf_config(path):
    """
    Config format:
    Domain | Risk | FailureClass | CCFGroup | BetaFactor
    """
    ccf_by_key = {}
    if not path.exists():
        return ccf_by_key

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "CCFGroup" in line:
                # header
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 5:
                continue
            domain, risk, failure_class, group, beta_str = parts
            key = (domain, risk, failure_class)
            ccf_by_key[key] = {
                "group": group,
                "beta": float(beta_str),
            }
    return ccf_by_key


def apply_ccf_correction(joined_rows, ccf_by_key):
    """
    Simple beta-factor model on probabilities only:
      For each CCF group g with beta:
        p_eff_i = (1 - beta) * p_i + beta * max_j( p_j in group g )
    """
    # Group rows by CCF group
    groups = {}
    for key, row in joined_rows.items():
        if key not in ccf_by_key:
            continue
        group_name = ccf_by_key[key]["group"]
        groups.setdefault(group_name, []).append(key)

    # For each group, compute max posterior mean in that group
    max_posterior_by_group = {}
    for group_name, keys in groups.items():
        max_p = 0.0
        for key in keys:
            p = joined_rows[key]["PosteriorMean"]
            if p > max_p:
                max_p = p
        max_posterior_by_group[group_name] = max_p

    # Apply correction
    for key, row in joined_rows.items():
        if key not in ccf_by_key:
            # No CCF group: effective = original
            row["CCFGroup"] = ""
            row["BetaFactor"] = 0.0
            row["PosteriorMean_CCF"] = row["PosteriorMean"]
            continue

        info = ccf_by_key[key]
        group_name = info["group"]
        beta = info["beta"]
        base_p = row["PosteriorMean"]
        group_p = max_posterior_by_group.get(group_name, base_p)

        p_eff = (1.0 - beta) * base_p + beta * group_p

        row["CCFGroup"] = group_name
        row["BetaFactor"] = beta
        row["PosteriorMean_CCF"] = p_eff

    return joined_rows


def main():
    numeric_path = find_latest_numeric_risk()
    bayes_path = find_latest_bayes()

    numeric_rows = load_numeric_risk(numeric_path)
    bayes_rows = load_bayes(bayes_path)
    ccf_by_key = load_ccf_config(CCF_CONFIG_PATH)

    # Join numeric + bayes
    joined = {}
    for key, nrow in numeric_rows.items():
        if key not in bayes_rows:
            continue
        brow = bayes_rows[key]
        row = {
            "Domain": nrow["Domain"],
            "Risk": nrow["Risk"],
            "FailureClass": nrow["FailureClass"],
            "Likelihood": nrow["Likelihood"],
            "Severity": nrow["Severity"],
            "PriorMean": brow["PriorMean"],
            "PosteriorMean": brow["PosteriorMean"],
        }
        joined[key] = row

    # Apply common-cause correction
    joined = apply_ccf_correction(joined, ccf_by_key)

    # Write PRA output (no RPN columns)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path = OUTPUT_DIR / f"pra_ANALYSIS_{timestamp}.txt"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("=== FIRST-ORDER PROBABILISTIC RISK ASSESSMENT (PRA) WITH CCF, NO RPN ===\n")
        f.write(f"Numeric source: {numeric_path}\n")
        f.write(f"Bayes source:   {bayes_path}\n")
        if CCF_CONFIG_PATH.exists():
            f.write(f"CCF config:     {CCF_CONFIG_PATH}\n")
        else:
            f.write("CCF config:     <none>\n")
        f.write(
            "Domain | Risk | FailureClass | Likelihood | Severity | "
            "PriorMean | PosteriorMean | PosteriorMean_CCF | "
            "CCFGroup | BetaFactor\n"
        )

        # Sort rows by probability (CCF-corrected), highest first
        sorted_rows = sorted(
            joined.values(),
            key=lambda r: r["PosteriorMean_CCF"],
            reverse=True,
        )

        for r in sorted_rows:
            f.write(
                f"{r['Domain']} | {r['Risk']} | {r['FailureClass']} | "
                f"{r['Likelihood']:.6f} | {r['Severity']:.2f} | "
                f"{r['PriorMean']:.6f} | {r['PosteriorMean']:.6f} | "
                f"{r['PosteriorMean_CCF']:.6f} | "
                f"{r['CCFGroup']} | {r['BetaFactor']:.2f}\n"
            )

    print(f"Wrote PRA output (no RPN) to: {out_path}")


if __name__ == "__main__":
    main()
