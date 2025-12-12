"""
PRAXIS Core Engine - Version Info
"""

PRAXIS_MAJOR = 1
PRAXIS_MINOR = 1
PRAXIS_PATCH = 0

PRAXIS_VERSION_STR = f"{PRAXIS_MAJOR}.{PRAXIS_MINOR}.{PRAXIS_PATCH}"


def get_version() -> str:
    """
    Return the human-readable version string.
    """
    return PRAXIS_VERSION_STR
