\# PRAXIS TITAN — Roadmap \& Versioning



\## Current Version (This Repo)



\*\*P6.1 — Implemented Public Research Release\*\*



This repository contains the functioning baseline engine:

\- Offline, file-driven execution

\- Probabilistic pipeline (numeric → Bayes → cascade → fault tree)

\- Adversarial twin modeling

\- Sensitivity analysis

\- Inspectable run artifacts



---



\## Next Architecture Evolution



\*\*P6.3 — Governance-Layer Hardening (Planned / In-Progress)\*\*



P6.3 is an architectural evolution built on top of the P6.1 compute core, focusing on:

\- Read-only Oracle interface (artifact-only inspection)

\- Explicit message schemas and validators

\- Allowed-actions registry (no hidden behavior)

\- Strong artifact contracts (baseline\_summary, twin\_summary, etc.)

\- Improved report formatting and output structure



---



\## What Will NOT Be Added (By Design)



To preserve governance and auditability, PRAXIS TITAN will not become:

\- An autonomous agent

\- A self-modifying system

\- A cloud-first dependency

\- A real-time operational controller



---



\## Suggested Repo Split (Future)



When P6.3 stabilizes, a clean separation may be used:

\- `praxis-titan-core` (compute baseline)

\- `praxis-titan-oracle` (read-only interface + schemas)

\- `praxis-titan-reports` (formatters / templates)



