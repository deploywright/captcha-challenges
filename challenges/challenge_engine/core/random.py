"""Deterministic random number generation utilities."""

from __future__ import annotations

import hashlib
import random
from typing import Sequence, TypeVar

import numpy as np

T = TypeVar("T")


def derive_seed(base_seed: int, *namespaces: str | int) -> int:
    """Derive a deterministic 32-bit unsigned integer seed from base_seed and namespaces."""
    parts = [str(base_seed)] + [str(ns) for ns in namespaces]
    digest = hashlib.sha256(":".join(parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], byteorder="big", signed=False)


class DeterministicRNG:
    """Encapsulates isolated Python random.Random and numpy.random.Generator instances."""

    def __init__(self, seed: int, namespace: str = "default") -> None:
        self.base_seed = int(seed)
        self.namespace = namespace
        self.derived_seed = derive_seed(self.base_seed, namespace)
        self.py_rng = random.Random(self.derived_seed)
        self.np_rng = np.random.default_rng(self.derived_seed)

    def fork(self, sub_namespace: str | int) -> "DeterministicRNG":
        """Create a deterministic child RNG isolated to a sub-operation."""
        return DeterministicRNG(self.base_seed, f"{self.namespace}:{sub_namespace}")

    def randint(self, low: int, high: int) -> int:
        """Inclusive random integer in [low, high]."""
        return self.py_rng.randint(low, high)

    def uniform(self, low: float, high: float) -> float:
        """Uniform float in [low, high]."""
        return self.py_rng.uniform(low, high)

    def choice(self, seq: Sequence[T]) -> T:
        """Pick one element from a non-empty sequence."""
        if not seq:
            raise ValueError("Cannot choose from an empty sequence")
        return self.py_rng.choice(seq)

    def sample(self, population: Sequence[T], k: int) -> list[T]:
        """Deterministic sample without replacement."""
        return self.py_rng.sample(list(population), k)

    def shuffle(self, items: list[T]) -> list[T]:
        """Shuffle a copy of the list deterministically and return it."""
        copied = list(items)
        self.py_rng.shuffle(copied)
        return copied
