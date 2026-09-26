"""
ML Engine Service
=================
Implements deterministic student modeling algorithms:
1. 2-Parameter Logistic (2-PL) IRT for adaptive ability estimation (theta).
2. Bayesian Knowledge Tracing (BKT) for concept mastery probability tracking.
3. Struggle & dropout risk detection based on error clusters and response times.
4. Adaptive test termination evaluation (Terminal Graph Node detection).
"""

import logging
import math
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

try:
    from core.logger import workflow_log
except ImportError:
    from server.core.logger import workflow_log


@dataclass
class BKTParameters:
    """
    Standard 4-parameter Bayesian Knowledge Tracing parameters:
    - p_init: Prior probability of knowing the skill initially P(L0)
    - p_transit: Probability of learning the skill between attempts P(T)
    - p_guess: Probability of guessing correctly without knowing P(G)
    - p_slip: Probability of slipping (answering wrong despite knowing) P(S)
    """
    p_init: float = 0.30
    p_transit: float = 0.15
    p_guess: float = 0.20
    p_slip: float = 0.10


@dataclass
class StudentMLProfile:
    """Live ML tracking state for a student during diagnostic assessment."""
    theta: float = 0.0  # IRT ability parameter: -3.0 (Novice) to +3.0 (Master)
    theta_standard_error: float = 1.0  # Uncertainty in ability estimation
    concept_mastery: Dict[str, float] = field(default_factory=dict)  # concept_id -> P(L_t)
    response_history: List[Dict[str, Any]] = field(default_factory=list)
    struggle_risk: float = 0.0  # 0.0 (Smooth) to 1.0 (Critical struggle)
    consecutive_incorrect: int = 0
    consecutive_correct: int = 0
    questions_count: int = 0
    is_terminal: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serializes profile for LangGraph state and database storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StudentMLProfile":
        """Deserializes profile from state or database dictionary."""
        return cls(**data)

    def reset_streak(self) -> None:
        """Resets consecutive streaks when transitioning across knowledge graph domains."""
        self.consecutive_incorrect = 0
        self.consecutive_correct = 0


class MLEngine:
    """
    Deterministic ML engine managing IRT ability updates, BKT mastery probability transitions,
    and adaptive traversal recommendations (traverse_up, traverse_down, terminal).
    """

    LEVEL_PRIORS = {
        "beginner": {"theta": -1.2, "p_init": 0.20},
        "intermediate": {"theta": 0.0, "p_init": 0.45},
        "advanced": {"theta": 1.2, "p_init": 0.70}
    }

    def __init__(self, default_bkt_params: Optional[BKTParameters] = None):
        self.default_bkt = default_bkt_params or BKTParameters()

    def initialize_profile(self, perceived_level: str = "intermediate") -> StudentMLProfile:
        """Initializes a student's ML profile calibrated to their onboarding level."""
        prior = self.LEVEL_PRIORS.get(perceived_level.lower(), self.LEVEL_PRIORS["intermediate"])
        return StudentMLProfile(
            theta=prior["theta"],
            theta_standard_error=1.0,
            concept_mastery={},
            response_history=[],
            struggle_risk=0.1,
            consecutive_incorrect=0,
            consecutive_correct=0,
            questions_count=0,
            is_terminal=False
        )

    # -------------------------------------------------------------------------
    # 1. Item Response Theory (IRT) - 2-PL Model
    # -------------------------------------------------------------------------

    def probability_correct_irt(
        self, theta: float, difficulty: float, discrimination: float = 1.0
    ) -> float:
        """
        2-Parameter Logistic IRT Model:
        P(Correct) = 1 / (1 + exp(-a * (theta - b)))
        where theta = student ability, b = item difficulty, a = discrimination
        """
        # Map 0.0-1.0 difficulty scale to IRT logits (-2.0 to +2.0)
        b = (difficulty - 0.5) * 4.0
        a = max(0.5, min(2.5, discrimination))

        exponent = -a * (theta - b)
        exponent = max(-20.0, min(20.0, exponent))  # Prevent numerical overflow
        return 1.0 / (1.0 + math.exp(exponent))

    def update_irt_ability(
        self,
        profile: StudentMLProfile,
        is_correct: bool,
        difficulty: float,
        discrimination: float = 1.0
    ) -> float:
        """
        Updates student's ability estimate (theta) using damped surprise-proportional steps.
        Theta increases on correct answers and decreases on errors.
        """
        p_hat = self.probability_correct_irt(profile.theta, difficulty, discrimination)
        actual = 1.0 if is_correct else 0.0

        # Learning step size (damped by number of questions answered)
        learning_rate = max(0.25, 0.7 / (1.0 + 0.1 * profile.questions_count))
        theta_delta = learning_rate * (actual - p_hat)
        profile.theta = max(-3.0, min(3.0, profile.theta + theta_delta))

        # Standard error shrinks with more observations
        profile.theta_standard_error = max(0.2, 1.0 / math.sqrt(profile.questions_count + 1))
        return profile.theta

    # -------------------------------------------------------------------------
    # 2. Bayesian Knowledge Tracing (BKT)
    # -------------------------------------------------------------------------

    def update_bkt_mastery(
        self,
        profile: StudentMLProfile,
        concept_id: str,
        is_correct: bool,
        bkt_params: Optional[BKTParameters] = None
    ) -> float:
        """Updates latent concept mastery P(L_t) using Bayes Theorem and learning transition."""
        params = bkt_params or self.default_bkt
        current_mastery = profile.concept_mastery.get(concept_id, params.p_init)

        # Step 1: Observation update (Posterior)
        if is_correct:
            numerator = current_mastery * (1.0 - params.p_slip)
            denominator = numerator + ((1.0 - current_mastery) * params.p_guess)
        else:
            numerator = current_mastery * params.p_slip
            denominator = numerator + ((1.0 - current_mastery) * (1.0 - params.p_guess))

        posterior = numerator / denominator if denominator > 0 else current_mastery

        # Step 2: Learning transition update
        next_mastery = posterior + ((1.0 - posterior) * params.p_transit)
        next_mastery = max(0.01, min(0.99, next_mastery))

        profile.concept_mastery[concept_id] = round(next_mastery, 4)
        return profile.concept_mastery[concept_id]

    # -------------------------------------------------------------------------
    # 3. Struggle & Dropout Risk Scoring
    # -------------------------------------------------------------------------

    def calculate_struggle_risk(
        self,
        profile: StudentMLProfile,
        is_correct: bool,
        response_time_sec: float,
        difficulty: float
    ) -> float:
        """Calculates struggle score (0.0 to 1.0) based on error streaks and latency anomalies."""
        if is_correct:
            profile.consecutive_correct += 1
            profile.consecutive_incorrect = 0
        else:
            profile.consecutive_incorrect += 1
            profile.consecutive_correct = 0

        # Base penalty for consecutive mistakes
        error_penalty = min(0.6, profile.consecutive_incorrect * 0.2)

        # Latency signals: > 90s implies high cognitive struggle; < 4s incorrect implies guessing
        latency_penalty = 0.0
        if response_time_sec > 90:
            latency_penalty = 0.2
        elif response_time_sec < 4 and not is_correct:
            latency_penalty = 0.15

        # Missing an easy question (difficulty <= 0.4) signals foundational gap
        difficulty_penalty = 0.2 if (not is_correct and difficulty <= 0.4) else 0.0

        raw_risk = error_penalty + latency_penalty + difficulty_penalty
        if is_correct and profile.consecutive_correct >= 2:
            raw_risk = max(0.05, raw_risk - 0.25)

        profile.struggle_risk = round(max(0.0, min(1.0, raw_risk)), 2)
        return profile.struggle_risk

    # -------------------------------------------------------------------------
    # 4. Processing Complete Question Interaction
    # -------------------------------------------------------------------------

    def record_interaction(
        self,
        profile: StudentMLProfile,
        concept_id: str,
        is_correct: bool,
        difficulty: float,
        discrimination: float = 1.0,
        response_time_sec: float = 25.0
    ) -> Dict[str, Any]:
        """Primary entrypoint for updating IRT, BKT, struggle risk, and next traversal action."""
        profile.questions_count += 1

        new_theta = self.update_irt_ability(profile, is_correct, difficulty, discrimination)
        new_mastery = self.update_bkt_mastery(profile, concept_id, is_correct)
        risk = self.calculate_struggle_risk(profile, is_correct, response_time_sec, difficulty)

        profile.response_history.append({
            "question_num": profile.questions_count,
            "concept_id": concept_id,
            "is_correct": is_correct,
            "difficulty": difficulty,
            "discrimination": discrimination,
            "response_time_sec": response_time_sec,
            "theta_after": round(new_theta, 3),
            "mastery_after": new_mastery,
            "struggle_risk": risk
        })

        profile.is_terminal = self._check_terminal_condition(profile)

        workflow_log(logging.DEBUG, "[IRT]", question=profile.questions_count, correct=is_correct, theta=round(new_theta, 3), difficulty=difficulty)
        workflow_log(logging.DEBUG, "[BKT]", concept=concept_id, mastery=new_mastery, struggle_risk=profile.struggle_risk)

        if profile.is_terminal:
            next_action = "terminal"
        elif is_correct:
            next_action = "traverse_up"
        else:
            next_action = "traverse_down"

        return {
            "questions_count": profile.questions_count,
            "theta": round(profile.theta, 3),
            "theta_se": round(profile.theta_standard_error, 3),
            "concept_mastery": new_mastery,
            "struggle_risk": profile.struggle_risk,
            "is_terminal": profile.is_terminal,
            "next_action": next_action
        }

    # -------------------------------------------------------------------------
    # 5. Terminal Evaluation & Domain Rollup
    # -------------------------------------------------------------------------

    def _check_terminal_condition(self, profile: StudentMLProfile) -> bool:
        """Keep the assessment length aligned with the public eight-question contract."""
        return profile.questions_count >= 8

    def get_domain_summary(
        self,
        profile: StudentMLProfile,
        concept_domain_map: Dict[str, str]
    ) -> Dict[str, float]:
        """Rolls up fine-grained concept masteries into high-level domain percentage scores."""
        domain_buckets: Dict[str, List[float]] = {
            "SQL": [],
            "Python": [],
            "Statistics": [],
            "Data Visualization": [],
            "Algorithms": [],
            "Software Engineering": [],
            "Machine Learning": [],
            "Data Engineering": [],
            "Cybersecurity": [],
            "Product Strategy": [],
            "Business Analysis": []
        }

        # Normalize concept domain map lookup (case-insensitive)
        normalized_map = {k.strip(): v.strip() for k, v in concept_domain_map.items()}

        for concept_id, mastery in profile.concept_mastery.items():
            domain = normalized_map.get(concept_id.strip())
            for canonical_domain in domain_buckets.keys():
                if domain and domain.lower() == canonical_domain.lower():
                    domain_buckets[canonical_domain].append(mastery)

        # Default baseline if domain was untested
        default_baseline = max(0.2, min(0.9, 0.5 + 0.15 * profile.theta))

        result: Dict[str, float] = {}
        baseline_domains = {"SQL", "Python", "Statistics", "Data Visualization"}
        for domain, scores in domain_buckets.items():
            if scores:
                result[domain] = round(sum(scores) / len(scores), 2)
            elif domain in baseline_domains:
                result[domain] = round(default_baseline, 2)

        return result


# Global singleton instance
ml_engine = MLEngine()

