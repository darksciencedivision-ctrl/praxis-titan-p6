"""
praxis_core – Private PRAXIS Engine Core

This package contains the proprietary numerical risk, Bayesian, PRA,
and lifecycle reliability logic for the PRAXIS engine.

Distribution is restricted. See commercial licensing terms.
"""

from .core_engine import run_engine

__all__ = ["run_engine"]
