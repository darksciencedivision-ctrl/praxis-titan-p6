# PRAXIS P6.1 TITAN Run – Builder Under Constraint

Run ID: 22d1813e98e8
Timestamp (UTC): 2025-12-12T05:04:46Z

## Baseline Top Event
- p_top (analytic): 0.9736047480216576
- Reliability: 'N/A'

## Twin Engine (Adversarial)
- Number of twins: 18
  - optimistic_01 [optimistic]: p_top=0.9621223820121555, Δp_top=-0.011482366009502143
  - optimistic_02 [optimistic]: p_top=0.9622917194626507, Δp_top=-0.011313028559006955
  - optimistic_03 [optimistic]: p_top=0.9566456258240943, Δp_top=-0.016959122197563348

## Sensitivity (Top Δp_top)
- R_HW_LIMIT (Computational – Insufficient workstation capability): max |Δp_top| ≈ 0.017596834652228277
- R_CERT_GAP (Training – Lack of required professional certifications): max |Δp_top| ≈ 0.015228029987505165
- R_SUPPORT_FAIL (Operational – Lack of external support causing throughput degradation): max |Δp_top| ≈ 0.015228029987505165
- R_SOC_COMM (Communication – Critical system information not reaching key engineer (father)): max |Δp_top| ≈ 0.01319762598917118
- R_ENG_OUTPUT (Performance – Human subsystem producing output exceeding observer expectations): max |Δp_top| ≈ 0.009898219491878413