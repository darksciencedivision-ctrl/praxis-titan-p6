import pathlib
import glob
import datetime
import random
import math

BASE_DIR = pathlib.Path(r"C:\ai_control")
OUTPUT_DIR = BASE_DIR / "output"
FT_CONFIG_PATH = BASE_DIR / "fault_tree_config.txt"


def find_latest_pra():
    pattern = str(OUTPUT_DIR / "pra_ANALYSIS_*.txt")
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError("No pra_ANALYSIS_*.txt files found in output.")
    files.sort()
    return pathlib.Path(files[-1])


def find_latest_reliability():
    pattern = str(OUTPUT_DIR / "reliability_from_numeric_ANALYSIS_*.txt")
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError("No reliability_from_numeric_ANALYSIS_*.txt files found in output.")
    files.sort()
    return pathlib.Path(files[-1])


def load_pra(pra_path):
    """Load PRA rows and return dict keyed by (Domain, Risk, FailureClass)
       with PosteriorMean_CCF as probability."""
    rows = {}
    with open(pra_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "PosteriorMean_CCF" in line and "Domain" in line:
                # header line
                continue
            if line.startswith("===") or line.startswith("Numeric source"):
                continue
            if "CCFGroup" in line and "BetaFactor" in line:
                # header line
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 10:
                continue

            domain = parts[0]
            risk = parts[1]
            failure_class = parts[2]
            # Likelihood = parts[3], Severity = parts[4]
            # PriorMean = parts[5], PosteriorMean = parts[6]
            try:
                p_ccf = float(parts[7])
            except ValueError:
                continue

            key = (domain, risk, failure_class)
            rows[key] = p_ccf
    return rows


def load_reliability(rel_path):
    """Load reliability outputs and return override probs for transformer events."""
    overrides = {}
    with open(rel_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("===") or "Numeric source" in line:
                continue
            if "IsTransformer" in line and "P_fail_heat_72h" in line:
                # header
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 10:
                continue

            domain = parts[0]
            risk = parts[1]
            failure_class = parts[2]
            is_transformer = parts[3]
            p_fail_heat_str = parts[7]

            try:
                is_tx = int(is_transformer)
            except ValueError:
                continue

            if is_tx != 1:
                continue

            try:
                p_heat = float(p_fail_heat_str)
            except ValueError:
                continue

            key = (domain, risk, failure_class)
            overrides[key] = p_heat
    return overrides


def load_fault_tree_config(path):
    basic_events = {}  # BE_ID -> (Domain, Risk, FailureClass)
    top_events = {}    # TE_ID -> {gate, k, inputs}

    section = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.upper() == "[BASIC_EVENTS]":
                section = "BASIC"
                continue
            if line.upper() == "[TOP_EVENTS]":
                section = "TOP"
                continue

            parts = [p.strip() for p in line.split("|")]
            if section == "BASIC":
                if len(parts) < 4:
                    continue
                be_id, domain, risk, failure_class = parts[:4]
                basic_events[be_id] = (domain, risk, failure_class)
            elif section == "TOP":
                if len(parts) < 4:
                    continue
                te_id, gate_type, k_str, inputs_str = parts[:4]
                inputs = [x.strip() for x in inputs_str.split(",") if x.strip()]
                k = None
                if gate_type.upper() == "KOFN":
                    try:
                        k = int(k_str)
                    except ValueError:
                        k = 1
                top_events[te_id] = {
                    "gate": gate_type.upper(),
                    "k": k,
                    "inputs": inputs,
                }

    return basic_events, top_events


def simulate_fault_tree(be_probs, top_events, n_sims=100000):
    """Monte Carlo simulation. Returns dict of TE_ID -> stats dict."""
    te_hits = {te_id: 0 for te_id in top_events}
    # no need to store BE states across runs
    be_ids = list(be_probs.keys())

    for _ in range(n_sims):
        be_state = {}
        for be_id in be_ids:
            p = be_probs[be_id]
            be_state[be_id] = (random.random() < p)

        for te_id, cfg in top_events.items():
            gate = cfg["gate"]
            inputs = cfg["inputs"]
            k = cfg["k"]

            vals = [be_state.get(bid, False) for bid in inputs]

            if gate == "OR":
                te_true = any(vals)
            elif gate == "AND":
                te_true = all(vals)
            elif gate == "KOFN":
                k = k or 1
                te_true = sum(1 for v in vals if v) >= k
            else:
                # default OR
                te_true = any(vals)

            if te_true:
                te_hits[te_id] += 1

    results = {}
    for te_id, hits in te_hits.items():
        p_hat = hits / n_sims
        # Binomial standard error (guard against p=0 or 1)
        se = math.sqrt(p_hat * (1.0 - p_hat) / n_sims) if 0.0 < p_hat < 1.0 else 0.0

        # 95% CI (normal approximation), clipped to [0,1]
        z = 1.96
        ci_low = max(0.0, p_hat - z * se)
        ci_high = min(1.0, p_hat + z * se)

        results[te_id] = {
            "p_hat": p_hat,
            "se": se,
            "ci_low": ci_low,
            "ci_high": ci_high,
        }
    return results


def main():
    pra_path = find_latest_pra()
    rel_path = find_latest_reliability()
    basic_events, top_events = load_fault_tree_config(FT_CONFIG_PATH)

    pra_probs = load_pra(pra_path)
    rel_overrides = load_reliability(rel_path)

    # Build BE probability map using PRA, overridden by Arrhenius transformers
    be_probs = {}
    for be_id, key in basic_events.items():
        domain, risk, failure_class = key
        k = (domain, risk, failure_class)

        if k in rel_overrides:
            p = rel_overrides[k]
        else:
            p = pra_probs.get(k, 0.0)
        be_probs[be_id] = p

    n_sims = 100000
    te_results = simulate_fault_tree(be_probs, top_events, n_sims=n_sims)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path = OUTPUT_DIR / f"fault_tree_ANALYSIS_{timestamp}.txt"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("=== PRAxis FAULT-TREE MONTE CARLO ===\n")
        f.write(f"PRA source: {pra_path}\n")
        f.write(f"Reliability source: {rel_path}\n")
        f.write(f"Fault-tree config: {FT_CONFIG_PATH}\n")
        f.write(f"Simulations: {n_sims}\n\n")

        f.write("=== BASIC EVENTS (BE probabilities after overrides) ===\n")
        f.write("BE_ID | Domain | Risk | FailureClass | Probability\n")
        for be_id, key in basic_events.items():
            domain, risk, failure_class = key
            p = be_probs.get(be_id, 0.0)
            f.write(f"{be_id} | {domain} | {risk} | {failure_class} | {p:.6f}\n")

        f.write("\n=== TOP EVENTS (Monte Carlo results, 95% CI) ===\n")
        f.write("TE_ID | GateType | K | p_hat | StdErr | CI_low_95 | CI_high_95\n")
        for te_id, cfg in top_events.items():
            gate = cfg["gate"]
            k = cfg["k"]
            k_str = "-" if gate in ("AND", "OR") else str(k or 1)
            stats = te_results[te_id]
            f.write(
                f"{te_id} | {gate} | {k_str} | "
                f"{stats['p_hat']:.6f} | {stats['se']:.6f} | "
                f"{stats['ci_low']:.6f} | {stats['ci_high']:.6f}\n"
            )

    print(f"Wrote fault-tree Monte Carlo results to: {out_path}")


if __name__ == "__main__":
    main()
