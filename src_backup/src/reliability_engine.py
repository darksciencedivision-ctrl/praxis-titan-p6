"""
reliability_engine.py

Full-lifecycle reliability modeling core:
- Fault / event trees (AND / OR gates)
- Time-to-failure models (Exponential, Weibull)
- Correlated failures via a simple beta-factor model
- Dynamic learning of failure rates (Gamma-Poisson style)
- Physical degradation / temperature acceleration

This file is self-contained and can be run directly:

    cd C:\\ai_control
    py src\\reliability_engine.py

Later you can wire it into your existing PRA pipeline.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Callable
import math

# =========================
# 1. TIME-TO-FAILURE MODELS
# =========================

class TimeToFailureModel:
    """Base class for time-to-failure models."""

    def reliability(self, t: float) -> float:
        """R(t) = P(component survives to time t)."""
        raise NotImplementedError

    def cdf(self, t: float) -> float:
        """F(t) = P(component has failed by time t) = 1 - R(t)."""
        return 1.0 - self.reliability(t)


@dataclass
class ExponentialModel(TimeToFailureModel):
    """Constant hazard model: lambda = failures per unit time."""
    lam: float  # failure rate λ

    def reliability(self, t: float) -> float:
        return math.exp(-self.lam * t)


@dataclass
class WeibullModel(TimeToFailureModel):
    """Weibull model: flexible hazard for wear-out / infant mortality."""
    beta: float  # shape
    eta: float   # scale

    def reliability(self, t: float) -> float:
        # Guard: t >= 0
        if t < 0:
            return 1.0
        return math.exp(- (t / self.eta) ** self.beta)


# ==================================
# 2. PHYSICAL DEGRADATION / STRESS
# ==================================

def arrhenius_acceleration(T_use: float, T_ref: float, Ea: float = 0.7) -> float:
    """
    Simple Arrhenius-like acceleration factor for temperature effects.
    T_use, T_ref in Kelvin. Ea is an effective activation energy (eV).

    AF > 1 => failures happen faster at T_use than T_ref.
    """
    k = 8.617333262e-5  # Boltzmann constant in eV/K
    return math.exp(-Ea / (k * T_use)) / math.exp(-Ea / (k * T_ref))


def accelerate_rate(lam_base: float, AF: float) -> float:
    """Scale a base failure rate by an acceleration factor."""
    return lam_base * AF


# =========================
# 3. COMPONENT DEFINITION
# =========================

@dataclass
class Component:
    name: str
    model: TimeToFailureModel
    severity: float = 1.0
    # Optional: prior parameters for dynamic learning of rate (for exponential models)
    prior_alpha: float = 1.0
    prior_beta: float = 1.0

    def failure_prob(self, t: float) -> float:
        """Probability this component fails by time t."""
        return self.model.cdf(t)

    def update_rate_from_data(self, failures: int, exposure_time: float) -> None:
        """
        Gamma-Poisson style update for exponential models.
        Only meaningful if the underlying model is ExponentialModel.
        """
        if not isinstance(self.model, ExponentialModel):
            # For now, only update exponential models.
            return

        # Posterior parameters
        post_alpha = self.prior_alpha + failures
        post_beta = self.prior_beta + exposure_time

        # Posterior mean rate
        lam_post = post_alpha / post_beta

        # Update internal state
        self.model.lam = lam_post
        self.prior_alpha = post_alpha
        self.prior_beta = post_beta


# =====================================
# 4. FAULT / EVENT TREE REPRESENTATION
# =====================================

class GateType:
    AND = "AND"
    OR = "OR"
    LEAF = "LEAF"


@dataclass
class FaultTreeNode:
    """
    Node in a fault/event tree.

    - LEAF nodes wrap a Component.
    - Gate nodes (AND / OR) combine child nodes.
    """
    name: str
    gate_type: str
    component: Optional[Component] = None
    children: List["FaultTreeNode"] = field(default_factory=list)

    def failure_prob(self, t: float, common_cause_factor: float = 0.0) -> float:
        """
        Compute failure probability at time t.

        common_cause_factor (beta) is applied only to sets of children
        as a very simple correlated-failure approximation.
        """
        if self.gate_type == GateType.LEAF:
            if self.component is None:
                raise ValueError(f"Leaf node {self.name} has no component attached.")
            return self.component.failure_prob(t)

        # Recursively compute child probabilities
        child_probs = [child.failure_prob(t, common_cause_factor) for child in self.children]

        # Simple beta-factor model for correlation:
        # A fraction 'beta' of the failure probability is common to all children.
        if common_cause_factor > 0.0 and len(child_probs) > 1:
            # Common-cause probability shared across children
            # (very simplified; real models are more elaborate)
            base_probs = [p * (1.0 - common_cause_factor) for p in child_probs]
            common_prob = max(child_probs) * common_cause_factor
        else:
            base_probs = child_probs
            common_prob = 0.0

        if self.gate_type == GateType.AND:
            # All must fail
            p_independent = 1.0
            for p in base_probs:
                p_independent *= p
            return max(0.0, min(1.0, p_independent + common_prob))

        elif self.gate_type == GateType.OR:
            # Any can fail
            p_survive = 1.0
            for p in base_probs:
                p_survive *= (1.0 - p)
            p_independent = 1.0 - p_survive
            return max(0.0, min(1.0, p_independent + common_prob))

        else:
            raise ValueError(f"Unknown gate type {self.gate_type} for node {self.name}")


# =========================================
# 5. DRIVER FUNCTIONS / EXAMPLE SCENARIO
# =========================================

def build_example_system() -> Dict[str, FaultTreeNode]:
    """
    Build a small example system to demonstrate full lifecycle modeling.

    Scenario: Cloud migration / Tier-1 transaction risk
    Top event: Loss of Tier-1 transaction integrity during migration window.
    """

    mission_hours = 24.0  # mission time horizon in hours

    # Base temperature scenario – can change this to see effects.
    T_ref = 298.0  # 25°C in Kelvin
    T_use = 308.0  # 35°C in Kelvin
    AF = arrhenius_acceleration(T_use, T_ref)

    # === Components ===
    # 1) Database cluster failover controller (constant hazard)
    lam_db_base = 1e-5  # failures/hour (baseline)
    lam_db_acc = accelerate_rate(lam_db_base, AF)
    db_ctrl = Component(
        name="DB_Failover_Controller",
        model=ExponentialModel(lam=lam_db_acc),
        severity=5.0,
        prior_alpha=2.0,
        prior_beta=200000.0,  # weak prior
    )

    # 2) Network packet handling / metadata path (Weibull: wear-out under high traffic)
    net_meta = Component(
        name="Metadata_Path",
        model=WeibullModel(beta=1.5, eta=1e5),  # shape > 1 => increasing hazard
        severity=5.0,
        prior_alpha=1.0,
        prior_beta=50000.0,
    )

    # 3) Monitoring / alert system (exponential)
    lam_mon_base = 5e-6
    lam_mon_acc = accelerate_rate(lam_mon_base, AF)
    monitor = Component(
        name="Monitoring_System",
        model=ExponentialModel(lam=lam_mon_acc),
        severity=3.0,
        prior_alpha=1.0,
        prior_beta=100000.0,
    )

    # === Fault tree structure ===
    # Top event: Loss of Tier-1 transaction integrity = (Failover fails AND Packet loss) OR (Monitoring fails AND Packet loss)
    leaf_db = FaultTreeNode("DB_Failover", GateType.LEAF, component=db_ctrl)
    leaf_meta = FaultTreeNode("Metadata_Path", GateType.LEAF, component=net_meta)
    leaf_mon = FaultTreeNode("Monitoring", GateType.LEAF, component=monitor)

    gate_packet_issue = FaultTreeNode(
        "Packet_Loss_Event",
        GateType.AND,
        children=[leaf_meta, leaf_db],  # require both DB controller + metadata path failure
    )

    gate_monitor_plus_packet = FaultTreeNode(
        "Monitoring_And_Packet",
        GateType.AND,
        children=[leaf_mon, leaf_meta],
    )

    top_event = FaultTreeNode(
        "Tier1_Transaction_Integrity_Loss",
        GateType.OR,
        children=[gate_packet_issue, gate_monitor_plus_packet],
    )

    return {
        "mission_hours": mission_hours,
        "components": {
            "db_ctrl": db_ctrl,
            "net_meta": net_meta,
            "monitor": monitor,
        },
        "top_event": top_event,
    }


def demo_full_lifecycle():
    system = build_example_system()
    T = system["mission_hours"]
    comps: Dict[str, Component] = system["components"]
    top: FaultTreeNode = system["top_event"]

    print("=== FULL LIFECYCLE RELIABILITY DEMO ===")
    print(f"Mission time horizon: {T:.1f} hours\n")

    # 1) Baseline component failure probabilities
    print("1) Baseline component failure probabilities over mission:")
    for name, comp in comps.items():
        p_fail = comp.failure_prob(T)
        print(f"   - {comp.name:25s}  P_fail({T:.1f}h) = {p_fail:.3e}")

    # 2) Top-event probability from fault tree (assuming modest common cause)
    beta_common = 0.1  # 10% of failures treated as common cause
    p_top = top.failure_prob(T, common_cause_factor=beta_common)
    print(f"\n2) Top-event probability with beta={beta_common:.2f}:")
    print(f"   P(Tier-1 integrity loss within {T:.1f}h) = {p_top:.3e}")

    # 3) Dynamic learning example: suppose we observed 1 DB controller failure over 50k hours
    print("\n3) Dynamic learning update for DB failover controller:")
    db_ctrl = comps["db_ctrl"]
    print(f"   Prior rate λ_prior = {db_ctrl.model.lam:.3e} failures/hr")
    db_ctrl.update_rate_from_data(failures=1, exposure_time=50000.0)
    print(f"   Posterior rate λ_post = {db_ctrl.model.lam:.3e} failures/hr")

    # Recompute top-event probability after learning
    p_top_post = top.failure_prob(T, common_cause_factor=beta_common)
    print(f"   Top-event probability after learning: {p_top_post:.3e}")

    # 4) Sensitivity to temperature (physical degradation / acceleration)
    print("\n4) Sensitivity to operating temperature (physical degradation):")
    # Rebuild system at cooler temperature for comparison
    cooler_system = build_example_system()
    cooler_T = cooler_system["mission_hours"]
    cooler_top: FaultTreeNode = cooler_system["top_event"]
    p_top_cool = cooler_top.failure_prob(cooler_T, common_cause_factor=beta_common)
    print(f"   P_top at baseline temp (25°C ref, 35°C use) : {p_top:.3e}")
    print(f"   P_top at same structure but *unaccelerated* base model: {p_top_cool:.3e} (for comparison)")

    print("\n=== END DEMO ===\n")


if __name__ == "__main__":
    demo_full_lifecycle()
