"""
PRAXIS P6.1 – Bayesian Update Layer

This module exposes a single primary entrypoint that the engine expects:

    bayes_update(basic_probs, priors_cfg, pseudo_n=5.0)

It performs a simple Beta–binomial Bayesian update for each risk:

    prior ~ Beta(alpha, beta)
    p_obs  = basic_probs[risk_id]
    n      = pseudo_n

    alpha_post = alpha + n * p_obs
    beta_post  = beta  + n * (1 - p_obs)
    p_post     = alpha_post / (alpha_post + beta_post)

The priors_cfg is expected to be a dict mapping risk IDs to either:

    {
        "alpha": float,
        "beta":  float
    }

or to a nested dict that contains at least those keys. If a risk ID is
missing from priors_cfg, a default flat prior Beta(1, 1) is used.

To be backward-compatible with older code, we also provide:

    bayes_update_risk(...)

as a thin alias to bayes_update(...).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Tuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class BetaPrior:
    alpha: float = 1.0
    beta: float = 1.0

    @property
    def n_eff(self) -> float:
        return float(self.alpha + self.beta)

    def update(self, p_obs: float, pseudo_n: float) -> "BetaPrior":
        """Return a new BetaPrior representing the posterior."""
        alpha_post = self.alpha + pseudo_n * p_obs
        beta_post = self.beta + pseudo_n * (1.0 - p_obs)
        return BetaPrior(alpha_post, beta_post)

    def mean(self) -> float:
        denom = self.alpha + self.beta
        if denom <= 0:
            return 0.5
        return self.alpha / denom


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_prior_for_risk(priors_cfg: Dict[str, Any], risk_id: str) -> BetaPrior:
    """
    Try to pull a prior for this risk_id from priors_cfg.

    Accepts several shapes:
        priors_cfg[risk_id] = {"alpha": A, "beta": B}
    or:
        priors_cfg[risk_id] = {"prior": {"alpha": A, "beta": B}, ...}

    If nothing suitable is found, default Beta(1, 1) is used.
    """
    raw = priors_cfg.get(risk_id)
    if not isinstance(raw, dict):
        return BetaPrior(1.0, 1.0)

    # Direct alpha/beta at top level
    if "alpha" in raw and "beta" in raw:
        try:
            return BetaPrior(float(raw["alpha"]), float(raw["beta"]))
        except Exception:
            return BetaPrior(1.0, 1.0)

    # Nested "prior"
    prior_block = raw.get("prior")
    if isinstance(prior_block, dict) and "alpha" in prior_block and "beta" in prior_block:
        try:
            return BetaPrior(float(prior_block["alpha"]), float(prior_block["beta"]))
        except Exception:
            return BetaPrior(1.0, 1.0)

    return BetaPrior(1.0, 1.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def bayes_update(
    basic_probs: Dict[str, float],
    priors_cfg: Dict[str, Any],
    pseudo_n: float = 5.0,
) -> Dict[str, Any]:
    """
    Perform a Beta–binomial Bayesian update for each risk.

    Args:
        basic_probs:  dict of {risk_id: p_base}
        priors_cfg:   dict of priors for each risk_id
        pseudo_n:     effective sample size (weight of new evidence)

    Returns:
        A dict with:
            "posterior_probs": {risk_id: p_post}
            "posteriors":      {risk_id: {"alpha_post", "beta_post",
                                          "alpha_prior", "beta_prior",
                                          "p_base", "p_post", "n_eff"}}
    """
    posterior_probs: Dict[str, float] = {}
    details: Dict[str, Dict[str, float]] = {}

    for rid, p_base in basic_probs.items():
        try:
            p = float(p_base)
        except Exception:
            # If probability is garbage, skip or clamp
            continue

        if p < 0.0:
            p = 0.0
        elif p > 1.0:
            p = 1.0

        prior = _extract_prior_for_risk(priors_cfg, rid)
        post = prior.update(p_obs=p, pseudo_n=float(pseudo_n))
        p_post = post.mean()

        posterior_probs[rid] = p_post
        details[rid] = {
            "alpha_prior": prior.alpha,
            "beta_prior": prior.beta,
            "alpha_post": post.alpha,
            "beta_post": post.beta,
            "p_base": p,
            "p_post": p_post,
            "n_eff_prior": prior.n_eff,
            "n_eff_post": post.n_eff,
        }

    return {
        "posterior_probs": posterior_probs,
        "posteriors": details,
    }


def bayes_update_risk(
    basic_probs: Dict[str, float],
    priors_cfg: Dict[str, Any],
    pseudo_n: float = 5.0,
) -> Dict[str, Any]:
    """
    Backwards-compatible alias to bayes_update(...).

    Some older versions of the engine call bayes_update_risk, so we simply
    forward to the main function.
    """
    return bayes_update(basic_probs=basic_probs, priors_cfg=priors_cfg, pseudo_n=pseudo_n)

