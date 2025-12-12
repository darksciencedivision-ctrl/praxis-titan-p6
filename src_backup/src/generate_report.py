import pathlib
import glob
import hashlib
import datetime

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

BASE_DIR = pathlib.Path(r"C:\ai_control")
SRC_DIR = BASE_DIR / "src"
OUTPUT_DIR = BASE_DIR / "output"
REPORT_DIR = BASE_DIR / "reports"


def find_latest(pattern):
    files = glob.glob(str(OUTPUT_DIR / pattern))
    if not files:
        return None
    files.sort()
    return pathlib.Path(files[-1])


def compute_version_hash():
    hasher = hashlib.sha256()
    candidates = [
        "core_engine.py",
        "risk_numeric.py",
        "risk_bayes.py",
        "update_priors_from_bayes.py",
        "pra_engine.py",
        "reliability_from_numeric.py",
        "fault_tree_montecarlo.py",
        "cascade_influence.py",
        "run_full_cycle.py",
        "fault_tree_config.txt",
        "ccf_groups.txt",
        "cascade_matrix.txt",
        "risk_priors.txt",
    ]

    for name in candidates:
        p1 = SRC_DIR / name
        p2 = BASE_DIR / name
        path = p1 if p1.exists() else p2 if p2.exists() else None
        if path is None:
            continue
        with open(path, "rb") as f:
            hasher.update(path.name.encode())
            hasher.update(b"\0")
            hasher.update(f.read())

    return hasher.hexdigest()


def parse_top_pra_events(pra_path, top_n=3):
    rows = []
    if not pra_path:
        return rows

    with open(pra_path, "r", encoding="utf-8") as f:
        for line in f:
            if "|" not in line or line.startswith("="):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 8:
                continue
            try:
                p_ccf = float(parts[7])
            except:
                continue
            rows.append((parts[0], parts[1], parts[2], p_ccf))

    rows.sort(key=lambda r: r[3], reverse=True)
    return rows[:top_n]


def parse_top_te_events(ft_path, top_n=3):
    rows = []
    if not ft_path:
        return rows

    in_section = False
    with open(ft_path, "r", encoding="utf-8") as f:
        for line in f:
            if "=== TOP EVENTS" in line:
                in_section = True
                continue
            if not in_section or "|" not in line:
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 7:
                continue
            try:
                p_hat = float(parts[3])
                ci_low = float(parts[5])
                ci_high = float(parts[6])
            except:
                continue

            rows.append((parts[0], parts[1], parts[2], p_hat, ci_low, ci_high))

    rows.sort(key=lambda r: r[3], reverse=True)
    return rows[:top_n]


def main():
    REPORT_DIR.mkdir(exist_ok=True)

    analysis_path = find_latest("test_ANALYSIS_*.txt")
    pra_path = find_latest("pra_ANALYSIS_*.txt")
    ft_path = find_latest("fault_tree_ANALYSIS_*.txt")
    cascade_path = find_latest("cascade_ANALYSIS_*.txt")
    reliability_path = find_latest("reliability_from_numeric_ANALYSIS_*.txt")

    version_hash = compute_version_hash()[:12]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    top_pra = parse_top_pra_events(pra_path)
    top_te = parse_top_te_events(ft_path)

    ts_file = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pdf_path = REPORT_DIR / f"praxis_report_{ts_file}.pdf"

    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter
    y = height - 50

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, "PRAxis Risk Engine — One Page Report")
    y -= 30

    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Timestamp: {timestamp}")
    y -= 15
    c.drawString(50, y, f"Version Hash: {version_hash}")
    y -= 15
    if analysis_path:
        c.drawString(50, y, f"Scenario File: {analysis_path.name}")
        y -= 15

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Top PRA Events:")
    y -= 18

    c.setFont("Helvetica", 10)
    for row in top_pra:
        c.drawString(60, y, f"{row[0]} | {row[1]} | p={row[3]:.4f}")
        y -= 14

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Top Fault Tree Events (95% CI):")
    y -= 18

    c.setFont("Helvetica", 10)
    for row in top_te:
        c.drawString(60, y, f"{row[0]} | p={row[3]:.4f} | [{row[4]:.4f}, {row[5]:.4f}]")
        y -= 14

    c.showPage()
    c.save()
    print(f"PDF report created: {pdf_path}")


if __name__ == "__main__":
    main()
