"""Database-backed LinUCB policies."""

from __future__ import annotations

from typing import Iterable, Mapping

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.rl_policy import RLPolicyParameter
from services.rl_policy import LinUCBPolicy


POLICY_CONFIGS = {
    "assessment": {
        "actions": (
            "EASIER_QUESTION",
            "SAME_DIFFICULTY",
            "HARDER_QUESTION",
            "PREREQUISITE_QUESTION",
        ),
        "dimension": 8,
    },
    "tutor": {
        "actions": (
            "SOCRATIC",
            "DIRECT_EXPLANATION",
            "CODE_FIRST",
            "ANALOGY_BASED",
        ),
        "dimension": 8,
    },
}


class RLPolicyService:
    """Loads and updates persisted policies; database rows are authoritative."""

    def __init__(self, db: Session, alpha: float = 1.0) -> None:
        self.db = db
        self.alpha = alpha

    def _config(self, policy_name: str) -> Mapping[str, object]:
        try:
            return POLICY_CONFIGS[policy_name]
        except KeyError as exc:
            raise ValueError(f"Unknown policy: {policy_name}") from exc

    def _policy(self, policy_name: str, rows: Iterable[RLPolicyParameter]) -> LinUCBPolicy:
        config = self._config(policy_name)
        parameters = {
            row.action: {
                "a_matrix": row.a_matrix,
                "b_vector": row.b_vector,
                "total_updates": row.total_updates,
            }
            for row in rows
        }
        return LinUCBPolicy(
            actions=config["actions"],
            dimension=config["dimension"],
            alpha=self.alpha,
            parameters=parameters,
        )

    def create_policy_if_missing(self, policy_name: str) -> None:
        config = self._config(policy_name)
        existing = self.db.query(RLPolicyParameter).filter_by(policy_name=policy_name).count()
        if existing == len(config["actions"]):
            return
        try:
            identity = LinUCBPolicy(actions=["init"], dimension=config["dimension"])
            for action in config["actions"]:
                present = self.db.query(RLPolicyParameter).filter_by(
                    policy_name=policy_name, action=action
                ).first()
                if not present:
                    self.db.add(
                        RLPolicyParameter(
                            policy_name=policy_name,
                            action=action,
                            dimension=config["dimension"],
                            a_matrix=identity.parameters_for("init")["a_matrix"],
                            b_vector=[0.0] * config["dimension"],
                            total_updates=0,
                        )
                    )
            self.db.commit()
        except IntegrityError:
            self.db.rollback()

    def load_policy(self, policy_name: str) -> LinUCBPolicy:
        self.create_policy_if_missing(policy_name)
        rows = self.db.query(RLPolicyParameter).filter_by(policy_name=policy_name).all()
        config = self._config(policy_name)
        if len(rows) != len(config["actions"]):
            raise RuntimeError(f"Policy {policy_name} is missing persisted actions")
        return self._policy(policy_name, rows)

    def select_action(self, policy_name: str, context: Iterable[float]) -> str:
        return self.load_policy(policy_name).select_action(context)

    def update_policy(
        self,
        policy_name: str,
        action: str,
        context: Iterable[float],
        reward: float,
    ) -> None:
        config = self._config(policy_name)
        if action not in config["actions"]:
            raise ValueError(f"Unknown policy action: {action}")
        self.create_policy_if_missing(policy_name)
        try:
            rows = self.db.query(RLPolicyParameter).filter_by(
                policy_name=policy_name
            ).with_for_update().all()
            policy = self._policy(policy_name, rows)
            policy.update(action, context, reward)
            updated = policy.parameters_for(action)
            row = next(row for row in rows if row.action == action)
            row.a_matrix = updated["a_matrix"]
            row.b_vector = updated["b_vector"]
            row.total_updates = updated["total_updates"]
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
