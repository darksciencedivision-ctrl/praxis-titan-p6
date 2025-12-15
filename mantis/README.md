\# P# PRAXIS MANTIS  

\## Governed Policy Runtime \& Explainability Layer for PRAXIS TITAN



\*\*PRAXIS MANTIS\*\* is a \*\*governed policy runtime\*\* designed to operate alongside \*\*PRAXIS TITAN\*\* as an \*\*explainable, fail-closed decision-support layer\*\*. It evaluates candidate mitigation policies, enforces immutable constraints (including budget authority), and emits \*\*structured, auditable outputs\*\* suitable for engineering review.



MANTIS is intentionally \*\*not\*\* an autonomous agent. It does not self-execute actions, does not self-modify, and does not escalate privileges. It produces bounded, inspectable recommendations and refuses unsafe or unauthorized execution.



---



\## System Overview



MANTIS provides three core capabilities:



1\) \*\*Governed Policy Evaluation\*\*  

&nbsp;  Evaluate and rank mitigation policies against an objective function and explicit constraints (including cost/budget authority).



2\) \*\*Fail-Closed Enforcement\*\*  

&nbsp;  If a policy violates constraints (e.g., cost exceeds remaining budget), MANTIS halts/refuses rather than improvising.



3\) \*\*Explainability Output\*\*  

&nbsp;  Emit structured artifacts that show \*why\* a policy was selected or refused, enabling review and replay without hidden state.



MANTIS follows the PRAXIS engineering posture:

\- Offline-first  

\- Artifact-driven (file contracts)  

\- Deterministic + auditable execution  

\- Human-in-the-loop authority retained  



---



\## What MANTIS Is



MANTIS is:

\- A \*\*policy runtime\*\* (evaluate, rank, refuse)

\- A \*\*constraint enforcement layer\*\* (fail-closed governance)

\- An \*\*explainability layer\*\* (structured rationale + diagnostics)

\- A \*\*decision-support system\*\* (advisory, not self-executing)



MANTIS is not:

\- An autonomous agent  

\- A tool runner that executes system actions  

\- A self-modifying system  

\- A cloud service  

\- A “chatbot replacement” for engineering analysis  



---



\## Design Principles



\*\*Determinism over Emergence\*\*  

Policy evaluation is contract-driven; constraints are explicit.



\*\*Fail-Closed Governance\*\*  

If a policy cannot be executed within constraints, MANTIS refuses and explains why.



\*\*Artifact Contracts\*\*  

Inputs/outputs are explicit JSON/text artifacts for review, replay, and audit.



\*\*Human Root Authority\*\*  

MANTIS does not commit changes or enact actions without operator authorization in the surrounding workflow.



---



\## Core Concepts



\### Policy

A policy is a bounded mitigation definition containing:

\- Cost (ISC or equivalent)

\- Target risk driver(s) or constraint(s)

\- Preconditions / required artifacts

\- Expected outputs

\- Verification checks



\### Budget Authority (ISC)

MANTIS enforces an execution budget. If:



`policy\_cost > available\_budget`



Then MANTIS emits a refusal/halt result and does not proceed.



\### Explainability

MANTIS emits structured diagnostics such as:

\- Why a policy ranks highest

\- Why a policy is refused

\- Which constraints bind (budget, eligibility, missing artifacts)

\- What evidence/artifacts were used

\- What would be required to proceed (without auto-escalation)



---



\## Runtime Posture



\*\*Operational Mode:\*\* Offline / local  

\*\*Control Model:\*\* Human-in-the-loop  

\*\*Autonomy Level:\*\* Decision-support only



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



\## Functional Architecture



High-level pipeline:



RAXIS MANTIS  

\## Governed Policy Runtime \& Explainability Layer for PRAXIS TITAN



\*\*PRAXIS MANTIS\*\* is a \*\*governed policy runtime\*\* designed to operate alongside \*\*PRAXIS TITAN\*\* as an \*\*explainable, fail-closed decision-support layer\*\*. It evaluates candidate mitigation policies, enforces immutable constraints (including budget authority), and emits \*\*structured, auditable outputs\*\* suitable for engineering review.



MANTIS is intentionally \*\*not\*\* an autonomous agent. It does not self-execute actions, does not self-modify, and does not escalate privileges. It produces bounded, inspectable recommendations and refuses unsafe or unauthorized execution.



---



\## System Overview



MANTIS provides three core capabilities:



1\) \*\*Governed Policy Evaluation\*\*  

&nbsp;  Evaluate and rank mitigation policies against an objective function and explicit constraints (including cost/budget authority).



2\) \*\*Fail-Closed Enforcement\*\*  

&nbsp;  If a policy violates constraints (e.g., cost exceeds remaining budget), MANTIS halts/refuses rather than improvising.



3\) \*\*Explainability Output\*\*  

&nbsp;  Emit structured artifacts that show \*why\* a policy was selected or refused, enabling review and replay without hidden state.



MANTIS follows the PRAXIS engineering posture:

\- Offline-first  

\- Artifact-driven (file contracts)  

\- Deterministic + auditable execution  

\- Human-in-the-loop authority retained  



---



\## What MANTIS Is



MANTIS is:

\- A \*\*policy runtime\*\* (evaluate, rank, refuse)

\- A \*\*constraint enforcement layer\*\* (fail-closed governance)

\- An \*\*explainability layer\*\* (structured rationale + diagnostics)

\- A \*\*decision-support system\*\* (advisory, not self-executing)



MANTIS is not:

\- An autonomous agent  

\- A tool runner that executes system actions  

\- A self-modifying system  

\- A cloud service  

\- A “chatbot replacement” for engineering analysis  



---



\## Design Principles



\*\*Determinism over Emergence\*\*  

Policy evaluation is contract-driven; constraints are explicit.



\*\*Fail-Closed Governance\*\*  

If a policy cannot be executed within constraints, MANTIS refuses and explains why.



\*\*Artifact Contracts\*\*  

Inputs/outputs are explicit JSON/text artifacts for review, replay, and audit.



\*\*Human Root Authority\*\*  

MANTIS does not commit changes or enact actions without operator authorization in the surrounding workflow.



---



\## Core Concepts



\### Policy

A policy is a bounded mitigation definition containing:

\- Cost (ISC or equivalent)

\- Target risk driver(s) or constraint(s)

\- Preconditions / required artifacts

\- Expected outputs

\- Verification checks



\### Budget Authority (ISC)

MANTIS enforces an execution budget. If:



`policy\_cost > available\_budget`



Then MANTIS emits a refusal/halt result and does not proceed.



\### Explainability

MANTIS emits structured diagnostics such as:

\- Why a policy ranks highest

\- Why a policy is refused

\- Which constraints bind (budget, eligibility, missing artifacts)

\- What evidence/artifacts were used

\- What would be required to proceed (without auto-escalation)



---



\## Runtime Posture



\*\*Operational Mode:\*\* Offline / local  

\*\*Control Model:\*\* Human-in-the-loop  

\*\*Autonomy Level:\*\* Decision-support only



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



\## Functional Architecture



High-level pipeline:





