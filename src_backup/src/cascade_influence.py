import pathlib
import glob
import datetime
import re

BASE_DIR = pathlib.Path(r"C:\ai_control")
OUTPUT_DIR = BASE_DIR / "output"
CASCADE_PATH = BASE_DIR / "cascade_matrix.txt"


def normalize(text: str) -> str:
    """
    Turn (Domain, Risk, FailureClass) text into a tolerant key so
    small formatting/Unicode differences don't break matching.
    """
    text = text.lower().strip()
    # replace common unicode stuff
    text = text.replace("°", "")
    text = text.replace("–", "-").replace("—", "-")
    text = text.replace("≥", ">=")
    # collapse whitespace
    text = re.sub(r"\s+", " ", text)
    # normalize patterns around hyphens (carrington- level -> carrington-level)
    text = text.replace("- ", "-").replace(" -", "-")
    # keep only simple characters
    text = re.sub(r"[^a-z0-9 >=+\-]", "", text)
    return text


def find_latest_pra():
    pattern = str(OUTPUT_DIR / "pra_ANALYSIS_*.txt")
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError("No pra_ANALYSIS_*.txt files found.")
    files.sort()
    return pathlib.Path(files[-1])


def load_pra(path):
    """
    Load PRA rows keyed by normalized (domain, risk, failure_class).
    Uses PosteriorMean_CCF as base probability.
    """
    rows = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "|" not in line or line.startswith("="):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 9:
                continue
            domain, risk, failure_class = parts[0], parts[1], parts[2]
            try:
                p_ccf = float(parts[7])
            except ValueError:
                continue

            key_norm = (
                normalize(domain),
                normalize(risk),
                normalize(failure_class),
            )
            rows[key_norm] = {
                "domain": domain,
                "risk": risk,
                "failure_class": failure_class,
                "p_base": p_ccf,
            }
    return rows


def load_cascade_config(path):
    """
    Load cascade EVENTS and CASCADE edges.
    EVENTS: EID | Domain | Risk | FailureClass
    CASCADE: FromID | ToID | InfluenceProb
    """
    events = {}
    edges = []
    section = None

    if not path.exists():
        return events, edges

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.upper() == "[EVENTS]":
                section = "EVENTS"
                continue
            if line.upper() == "[CASCADE]":
                section = "CASCADE"
                continue

            parts = [p.strip() for p in line.split("|")]

            if section == "EVENTS" and len(parts) >= 4:
                eid, domain, risk, failure_class = parts[:4]
                events[eid] = {
                    "domain": domain,
                    "risk": risk,
                    "failure_class": failure_class,
                    "key_norm": (
                        normalize(domain),
                        normalize(risk),
                        normalize(failure_class),
                    ),
                }

            elif section == "CASCADE" and len(parts) >= 3:
                src, dst, w_str = parts[:3]
                try:
                    w = float(w_str)
                except ValueError:
                    continue
                edges.append((src, dst, w))

    return events, edges


def main():
    pra_path = find_latest_pra()
    pra_rows = load_pra(pra_path)
    events, edges = load_cascade_config(CASCADE_PATH)

    # Map event IDs to PRA probabilities where possible
    resolved = {}  # eid -> dict with base p and keys
    skipped = []   # list of (domain, risk, fc) that truly don't match

    for eid, info in events.items():
        key_norm = info["key_norm"]
        if key_norm in pra_rows:
            pr = pra_rows[key_norm]
            resolved[eid] = {
                "domain": pr["domain"],
                "risk": pr["risk"],
                "failure_class": pr["failure_class"],
                "key_norm": key_norm,
                "p_base": pr["p_base"],
            }
        else:
            skipped.append(
                (info["domain"], info["risk"], info["failure_class"])
            )

    # Single-step static cascade:
    # p_eff(i) = min(1, p_base(i) + sum_j p_base(j) * w_j->i)
    influence_sum = {}  # key_norm -> added probability

    for src, dst, w in edges:
        if src not in resolved or dst not in resolved:
            continue
        src_key = resolved[src]["key_norm"]
        dst_key = resolved[dst]["key_norm"]
        p_src = resolved[src]["p_base"]
        influence_sum[dst_key] = influence_sum.get(dst_key, 0.0) + p_src * w

    results = []
    for eid, info in resolved.items():
        key_norm = info["key_norm"]
        p_base = info["p_base"]
        add = influence_sum.get(key_norm, 0.0)
        p_eff = min(1.0, p_base + add)
        results.append(
            (
                info["domain"],
                info["risk"],
                info["failure_class"],
                p_base,
                p_eff,
            )
        )

    # Sort by effective probability descending
    results.sort(key=lambda r: r[4], reverse=True)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path = OUTPUT_DIR / f"cascade_ANALYSIS_{timestamp}.txt"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("=== PRAxis CASCADE / INFLUENCE RESULTS ===\n")
        f.write(f"PRA source: {pra_path}\n")
        f.write(f"Cascade config: {CASCADE_PATH}\n\n")

        f.write("Domain | Risk | FailureClass | p_base | p_effective\n")
        for domain, risk, fc, p_base, p_eff in results:
            f.write(
                f"{domain} | {risk} | {fc} | "
                f"{p_base:.6f} | {p_eff:.6f}\n"
            )

        if skipped:
            f.write("\n=== SKIPPED EVENTS (not found in PRA after normalization) ===\n")
            for d, r, fc in skipped:
                f.write(f"{d} | {r} | {fc}\n")

    print(f"Wrote cascade output to: {out_path}")
    if skipped:
        print("Skipped events (not found in PRA after normalization):")
        for d, r, fc in skipped:
            print("  ", (d, r, fc))


if __name__ == "__main__":
    main()
  