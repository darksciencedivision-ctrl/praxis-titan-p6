from __future__ import annotations

from pathlib import Path
import textwrap
# import subprocess  # Optional: for auto-calling a local LLM

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE_DIR / "output" / "P6"

MASTER_REPORT_PATH = OUTPUT_DIR / "P6_master_report.txt"
TWIN_BRIEF_PATH = OUTPUT_DIR / "P6_twin_brief_for_chatbot.txt"


def read_text(path: Path) -> str:
    """
    Load text from a file, raising a clear error if missing.
    """
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path.read_text(encoding="utf-8")


def build_praxis_prompt() -> str:
    """
    Build a combined prompt for your local LLM, including:
      - The full P6 master report
      - The twin analysis brief
    and instructions to produce a one-page human brief.
    """
    master = read_text(MASTER_REPORT_PATH)
    twin_brief = read_text(TWIN_BRIEF_PATH)

    prompt = f"""
    You are Praxis-Chatbot, an infrastructure risk analyst using the PRAXIS P6 TITAN engine.

    You are given two structured texts:

    1) MASTER_REPORT: This is the full PRAXIS P6 TITAN master report for one scenario,
       including numeric, Bayesian, common-cause, cascade, fault-tree, and reliability
       layers, plus an embedded "ADVERSARIAL TWIN SUMMARY".

    2) TWIN_BRIEF: This is a compact twin analysis brief that describes the baseline
       top-event probability and reliability, the spread of adversarial twin runs
       (optimistic / chaotic / pessimistic), per-mode behavior, and the highest-sensitivity
       risks ("attention targets").

    -------------------- BEGIN MASTER_REPORT --------------------
    {master}
    --------------------- END MASTER_REPORT ---------------------

    --------------------- BEGIN TWIN_BRIEF ----------------------
    {twin_brief}
    ---------------------- END TWIN_BRIEF -----------------------

    TASK:

    Using ONLY the information above, write a single, clear, human-readable
    one-page brief (about 500–800 words) for a non-technical but serious
    decision-maker (e.g., national infrastructure planner, utility executive,
    emergency management director).

    The brief should:

    - State what scenario was analyzed and what PRAXIS P6 is doing.
    - Summarize the baseline risk level (top-event probability and approximate
      system reliability) in plain language.
    - Explain how robust this conclusion is given the adversarial twin spread
      (best-case, typical, worst-case bands).
    - Describe how each persona behaves:
        * Titan-Optimist (optimistic)
        * Titan-Chaos (chaotic)
        * Titan-Pessimist (pessimistic)
      and what each says about the risk picture.
    - Highlight the highest-sensitivity risks (attention targets) and explain,
      in plain language, why errors in those inputs would matter the most.
    - Close with 3–5 concise bullet recommendations:
        * What to investigate or validate next (data / priors / models)
        * Where to focus mitigation or hardening efforts
        * Any key "no-regrets" actions.

    Do NOT include raw JSON or code. Do NOT repeat the full reports. Synthesize.
    Focus on clarity, relevance, and actionability.
    """

    return textwrap.dedent(prompt).strip()


def main() -> None:
    """
    Default behavior: print a copy-paste-ready prompt for your local LLM.

    If you want to auto-call a local model (e.g., via Ollama), you can uncomment
    the subprocess block below and configure the model name.
    """
    prompt = build_praxis_prompt()

    print("=" * 70)
    print("PRAXIS P6 – CHATBOT PROMPT")
    print("Copy the text below into your local LLM (Dolphin/Qwen/etc.):")
    print("=" * 70)
    print()
    print(prompt)
    print()

    # Example for later: auto-call a local LLM via Ollama
    #
    # import subprocess
    # try:
    #     result = subprocess.run(
    #         ["ollama", "run", "dolphin-llama3"],
    #         input=prompt.encode("utf-8"),
    #         capture_output=True,
    #         check=True,
    #     )
    #     print("=" * 70)
    #     print("PRAXIS P6 – CHATBOT RESPONSE")
    #     print("=" * 70)
    #     print(result.stdout.decode("utf-8", errors="ignore"))
    # except FileNotFoundError:
    #     print("Ollama not found. Install it or adjust the subprocess call.")
    # except subprocess.CalledProcessError as e:
    #     print("Error running local LLM:", e)


if __name__ == "__main__":
    main()
