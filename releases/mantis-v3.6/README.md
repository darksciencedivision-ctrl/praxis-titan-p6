\# PRAXIS MANTIS v3.6  

\## Governed Policy Runtime \& Explainability Layer for PRAXIS TITAN



PRAXIS MANTIS v3.6 is a governed policy runtime designed to operate alongside PRAXIS TITAN as an explainable, fail-closed decision-support layer. It evaluates candidate mitigation policies, enforces immutable constraints (including budget authority), and emits structured, auditable outputs suitable for engineering review.



MANTIS is intentionally not an autonomous agent. It does not self-execute actions, does not self-modify, and does not escalate privileges. It produces bounded, inspectable recommendations and refuses unsafe or unauthorized execution.



---



\## 1. System Overview



MANTIS provides three core capabilities:



1\) Governed Policy Evaluation  

Evaluate and rank mitigation policies against an objective function and explicit constraints (including cost / budget authority).



2\) Fail-Closed Enforcement  

If a policy violates constraints (e.g., cost exceeds remaining budget), MANTIS halts/refuses rather than improvising.



3\) Explainability Output  

Emit structured artifacts showing why a policy was selected or refused, enabling review and replay without hidden state.



MANTIS follows the PRAXIS engineering posture:

\- Offline-first

\- Artifact-driven (file contracts)

\- Deterministic + auditable execution

\- Human-in-the-loop authority retained



---



\## 2. What MANTIS Is / Is Not



MANTIS is:

\- A policy runtime (evaluate, rank, refuse)

\- A constraint enforcement layer (fail-closed governance)

\- An explainability layer (structured rationale + diagnostics)

\- A decision-support system (advisory, not self-executing)



MANTIS is not:

\- An autonomous agent

\- A tool runner that executes system actions

\- A self-modifying system

\- A cloud service

\- A chatbot replacement for engineering analysis



---



\## 3. Design Principles



Determinism over Emergence  

Policy evaluation is contract-driven and reproducible; constraints are explicit.



Fail-Closed Governance  

If a policy cannot be executed within constraints, MANTIS refuses and explains why.



Artifact Contracts  

Inputs and outputs are explicit JSON/text artifacts to support review, replay, and audit.



Human Root Authority  

MANTIS does not commit changes or enact actions without operator authorization in the surrounding workflow.



---



\## 4. Core Concepts



\### 4.1 Policy

A policy is a bounded mitigation definition containing:

\- Cost (ISC or equivalent)

\- Target risk driver(s)

\- Preconditions / required artifacts

\- Expected outputs

\- Verification checks



\### 4.2 Budget Authority (ISC)

MANTIS enforces an execution budget. If:



policy\_cost > available\_budget



then MANTIS emits a refusal/halt result and does not proceed.



\### 4.3 Explainability

MANTIS emits structured diagnostics such as:

\- Why a policy ranks highest

\- Why a policy is refused

\- Which constraints bind (budget, eligibility, missing artifacts)

\- What evidence/artifacts were used

\- What must change to proceed (without auto-escalation)



---



\## 5. Runtime Posture



Operational Mode: Offline / local  

Control Model: Human-in-the-loop  

Autonomy Level: Decision-support only



MANTIS can:

\- Read artifacts

\- Evaluate policy candidates

\- Emit ranked outputs and refusals

\- Produce explainability traces



MANTIS cannot:

\- Self-execute external actions

\- Spawn uncontrolled processes

\- Modify itself

\- Override budget authority

\- Substitute missing artifacts with guesswork



---



\## 6. Functional Architecture



High-level pipeline:



Inputs (Artifacts) → Validate → Assemble Candidates → Score/Rank → Enforce Constraints → Emit Outputs



Typical phases:



1\) Artifact Ingestion  

Load current run artifacts/state and validate required schemas/fields.



2\) Policy Candidate Assembly  

Enumerate candidates from the policy registry and attach metadata (cost, targets, prerequisites).



3\) Scoring \& Ranking  

Apply objective function (risk reduction / feasibility / cost) and produce ranked candidates with rationale.



4\) Governance Gate  

Enforce budget authority and hard constraints; refuse non-compliant actions with explicit reasons.



5\) Output Emission  

Write decision and explainability artifacts and include a verification checklist for the operator.



---



\## 7. Output Artifacts



MANTIS emits machine- and human-readable artifacts such as:

\- mantis\_decision.json — ranked candidates, selected option (if any), refusals, binding constraints

\- mantis\_explain.json — explainability trace: reasons, evidence, checks

\- mantis\_verification.json — verification checklist to confirm expected impact

\- mantis\_log.txt — human-readable runtime summary



Exact filenames may vary by repo layout; the contract is structured, auditable, and replayable.



---



\## 8. Failure Modes (By Design)



MANTIS refuses rather than improvises when:

\- Budget authority is insufficient

\- Required artifacts are missing or invalid

\- Preconditions are not met

\- Policy registry is empty or inconsistent



Refusal outputs include:

\- Which constraint failed

\- Required vs available values

\- What must change to proceed (without auto-escalation)



---



\## 9. Quick Start



This release is designed to run within the PRAXIS ecosystem. Typical use pattern:



1\) Run PRAXIS TITAN to generate stable run artifacts.

2\) Point MANTIS at the run directory / state file.

3\) Execute the MANTIS runtime entrypoint.

4\) Review outputs:

&nbsp;  - ranked policies

&nbsp;  - refusal conditions (if any)

&nbsp;  - verification checklist



---



\## 10. Validation Philosophy



MANTIS is validated through:

\- Deterministic replay on identical artifacts

\- Schema checks for inputs/outputs

\- Constraint enforcement tests (budget refusal cases)

\- Regression prompts / canned scenarios (optional)



MANTIS is considered correct when:

\- It never violates constraints

\- Refusals are explicit and reproducible

\- Rankings are stable under identical inputs

\- Explainability artifacts match evaluated evidence



---



\## 11. Roadmap



Planned improvements:

\- Stronger artifact schema validators

\- Expanded explainability (rank-by-rank comparisons)

\- Bounded multi-step planning outputs (still fail-closed)

\- QA harness for required-section compliance

\- Optional integrity signing for artifacts



---



\## 12. License



Use the same license posture as your other PRAXIS releases (recommended: consistent dual-license across the suite).



---



\## 13. Disclaimer



PRAXIS MANTIS provides decision-support output only. It does not execute actions. Operators remain responsible for verification and for consulting primary sources and qualified professionals in high-stakes domains.



