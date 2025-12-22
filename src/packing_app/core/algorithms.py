"""Compatibility facade for palletizer_core.algorithms."""

from palletizer_core.algorithms import *  # noqa: F403
from palletizer_core import algorithms as _core_algorithms

__all__ = list(_core_algorithms.__all__)
