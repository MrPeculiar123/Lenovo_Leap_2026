"""Generic LinUCB contextual-bandit implementation."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

import numpy as np


class LinUCBPolicy:
    """A fixed-dimension LinUCB policy with deterministic tie-breaking."""

    def __init__(
        self,
        actions: Iterable[str],
        dimension: int,
        alpha: float = 1.0,
        parameters: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> None:
        self.actions = tuple(actions)
        self.dimension = int(dimension)
        self.alpha = float(alpha)
        if not self.actions:
            raise ValueError("LinUCB requires at least one action")
        if self.dimension <= 0:
            raise ValueError("LinUCB context dimension must be positive")
        if self.alpha < 0:
            raise ValueError("LinUCB exploration coefficient cannot be negative")

        self._a: dict[str, np.ndarray] = {}
        self._b: dict[str, np.ndarray] = {}
        self._updates: dict[str, int] = {}
        for action in self.actions:
            stored = parameters.get(action, {}) if parameters else {}
            self._a[action] = self._matrix(stored.get("a_matrix"), identity=True)
            self._b[action] = self._vector(stored.get("b_vector"))
            self._updates[action] = int(stored.get("total_updates", 0))

    def _context(self, context: Iterable[float]) -> np.ndarray:
        vector = np.asarray(list(context), dtype=float)
        if vector.ndim != 1 or vector.shape[0] != self.dimension:
            raise ValueError(f"Context must have exactly {self.dimension} dimensions")
        if not np.all(np.isfinite(vector)):
            raise ValueError("Context must contain only finite numeric values")
        return vector

    def _matrix(self, value: Any, identity: bool = False) -> np.ndarray:
        matrix = np.eye(self.dimension) if value is None and identity else np.asarray(value, dtype=float)
        if matrix.shape != (self.dimension, self.dimension):
            raise ValueError("Stored A matrix has an invalid shape")
        return matrix

    def _vector(self, value: Any) -> np.ndarray:
        vector = np.zeros(self.dimension) if value is None else np.asarray(value, dtype=float)
        if vector.shape != (self.dimension,):
            raise ValueError("Stored b vector has an invalid shape")
        return vector

    def _validate_action(self, action: str) -> None:
        if action not in self.actions:
            raise ValueError(f"Unknown LinUCB action: {action}")

    def select_action(self, context: Iterable[float]) -> str:
        vector = self._context(context)
        scores = []
        for action in self.actions:
            matrix = self._a[action]
            theta = np.linalg.solve(matrix, self._b[action])
            confidence = self.alpha * np.sqrt(
                max(0.0, float(vector @ np.linalg.solve(matrix, vector)))
            )
            scores.append(float(theta @ vector) + confidence)
        return self.actions[int(np.argmax(scores))]

    def update(self, action: str, context: Iterable[float], reward: float) -> None:
        self._validate_action(action)
        vector = self._context(context)
        numeric_reward = float(reward)
        if not np.isfinite(numeric_reward):
            raise ValueError("Reward must be finite")
        self._a[action] += np.outer(vector, vector)
        self._b[action] += numeric_reward * vector
        self._updates[action] += 1

    def parameters_for(self, action: str) -> dict[str, Any]:
        self._validate_action(action)
        return {
            "a_matrix": self._a[action].tolist(),
            "b_vector": self._b[action].tolist(),
            "total_updates": self._updates[action],
        }

    def serialize(self) -> dict[str, Any]:
        return {action: self.parameters_for(action) for action in self.actions}

    @classmethod
    def deserialize(
        cls,
        actions: Iterable[str],
        dimension: int,
        payload: Mapping[str, Mapping[str, Any]],
        alpha: float = 1.0,
    ) -> "LinUCBPolicy":
        return cls(actions, dimension, alpha=alpha, parameters=payload)
