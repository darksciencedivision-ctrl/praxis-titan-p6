import os
import datetime
import requests

# === PATH CONFIG ==========================================================
BASE_DIR = r"C:\ai_control"
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
MEMORY_FILE = os.path.join(BASE_DIR, "praxis_memory.txt")

# Name of your local Ollama model
MODEL_NAME = "dolphin-llama3"

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


# === HELPERS ==============================================================

def load_memory() -> str:
    """
    Load persistent PRAXIS behavior rules from praxis_memory.txt.
    If not found, fall back to a minimal neutral system profile.
    """
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            memory = f.read().strip()
        if not memory:
            raise ValueError("Empty memory file.")
        print(f"[CORE] Loaded persistent memory from: {MEMORY_FILE}")
        return memory
    except Exception as e:
        print(f"[CORE] WARNING: Could not load praxis_memory.txt ({e}). Using fallback profile.")
        return (
            "PERSISTENT PROFILE (FALLBACK):\n"
            "- Neutral, non-ideological analytical AI.\n"
            "- Only physics, engineering, mechanisms, probabilities.\n"
            "- Must output:\n"
            "  1) SYSTEM BREAKDOWN table\n"
            "  2) RISK ANALYSIS table with numeric RPN\n"
            "  3) RESEARCH QUESTIONS list (numbered)\n"
        )


def load_input_text() -> str:
    """
    For now, always read from input\\test.txt.
    This keeps behavior predictable while you are training.
    """
    input_file = os.path.join(INPUT_DIR, "test.txt")
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read().strip()
    if not text:
        raise ValueError(f"Input file is empty: {input_file}")
    print(f"[CORE] Loaded input scenario from: {input_file}")
    return text


def build_prompt(memory: str, scenario: str) -> str:
    """
    Combine persistent memory + user scenario into a single strict prompt
    that enforces the 3-section analytical format.
    """
    return f"""
{memory}

=====================================================
RUNTIME INSTRUCTIONS (NON-OVERRIDABLE)
=====================================================
You are running as a local analysis engine for power / infrastructure risk.

You must ALWAYS respond in EXACTLY this structure:

1) SYSTEM BREAKDOWN
- Output a MARKDOWN TABLE with columns:
  Component | Function | Physical / Technical Principles | Notes

2) RISK ANALYSIS
- Output a MARKDOWN TABLE with columns:
  Domain | Risk | FailureClass | Likelihood | Severity | RPN | Mechanism | Consequence | Mitigation
- Likelihood must be a number between 0.0 and 1.0
- Severity must be an integer from 1 to 5
- RPN = Likelihood * Severity (numeric, not text)
- FailureClass must be one of:
  SPF (Single-Point Failure), CMF (Common-Mode Failure),
  CF (Cyber Failure), LF (Load Failure), EF (Environmental Failure)

3) RESEARCH QUESTIONS
- Output a NUMBERED LIST (1., 2., 3., …)
- All questions must be technical, about physics, engineering,
  grid dynamics, cyber-risk, or system behavior.
- No ethics, no politics, no moral language.

You must NOT use words like: fair, equitable, justice, moral, ethical, good, bad.
Use only neutral engineering language: criticality, priority class, severity, load, threshold, etc.

=====================================================
SCENARIO TO ANALYZE
=====================================================
{scenario}
""".strip()


def call_ollama(prompt: str) -> str:
    """
    Send the composed prompt to the local Ollama model and return the full text response.
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
    }

    print(f"[CORE] Calling Ollama model: {MODEL_NAME}")
    resp = requests.post(OLLAMA_URL, json=payload, timeout=600)
    resp.raise_for_status()
    data = resp.json()

    if "response" not in data:
        raise KeyError(f"Ollama response missing 'response' field: {data}")

    return data["response"]


def write_output(text: str) -> str:
    """
    Write the analysis to output\\<name>_ANALYSIS_YYYY-MM-DD_HH-MM-SS.txt
    using the prefix 'test' for now.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"test_ANALYSIS_{ts}.txt"
    full_path = os.path.join(OUTPUT_DIR, filename)

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"[CORE] Saved analysis to: {full_path}")
    return full_path


# === MAIN =================================================================

def main():
    print("[CORE] === PRAXIS CORE ENGINE START ===")
    memory = load_memory()
    scenario = load_input_text()
    prompt = build_prompt(memory, scenario)
    analysis = call_ollama(prompt)
    output_path = write_output(analysis)
    print("[CORE] === ENGINE COMPLETE ===")
    print(f"[CORE] Output file: {output_path}")


if __name__ == "__main__":
    main()
