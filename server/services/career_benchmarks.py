"""
Career Benchmarks Service
=========================
Manages industry standard skill requirements for data & tech roles.
Calculates weighted career readiness scores, prioritizes skill gaps, and matches
student proficiency profiles against benchmark standards.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class CareerRole:
    """Represents a target industry career path and its skill benchmark profile."""
    id: str
    title: str
    description: str
    required_skills: Dict[str, float]  # domain -> required mastery threshold (0.0 to 1.0)
    skill_weights: Dict[str, float]    # domain -> importance weight (sums to 1.0)
    critical_concepts: List[str] = field(default_factory=list)  # must-have concept IDs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "required_skills": self.required_skills,
            "skill_weights": self.skill_weights,
            "critical_concepts": self.critical_concepts
        }


class CareerBenchmarkService:
    """
    Service for calculating career readiness, extracting benchmark deficits,
    and ranking career role alignments.
    """

    def __init__(self, data_path: Optional[str] = None):
        self.roles: Dict[str, CareerRole] = {}
        self._load_benchmarks(data_path)

    def _resolve_data_path(self, data_path: Optional[str] = None) -> Path:
        """Finds career_benchmarks.json across common execution directories."""
        if data_path:
            return Path(data_path)

        candidates = [
            Path(__file__).parent.parent / "data" / "career_benchmarks.json",
            Path("server/data/career_benchmarks.json"),
            Path("data/career_benchmarks.json"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()

        raise FileNotFoundError("Could not find 'server/data/career_benchmarks.json'.")

    def _load_benchmarks(self, data_path: Optional[str] = None) -> None:
        """Loads role definitions and benchmarks from decoupled JSON file."""
        file_path = self._resolve_data_path(data_path)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data.get("roles", []):
            role = CareerRole(
                id=item["id"],
                title=item["title"],
                description=item["description"],
                required_skills=item["required_skills"],
                skill_weights=item["skill_weights"],
                critical_concepts=item.get("critical_concepts", [])
            )
            self.roles[role.id] = role

    def get_role(self, role_identifier: str) -> Optional[CareerRole]:
        """
        Retrieves a career role by ID or title (case-insensitive and whitespace tolerant).
        Matches 'data_analyst', 'Data Analyst', or 'analyst'.
        """
        target = role_identifier.strip().lower()
        if target in self.roles:
            return self.roles[target]

        # Check by title match or normalized slug
        slug = target.replace(" ", "_").replace("-", "_")
        if slug in self.roles:
            return self.roles[slug]

        for role in self.roles.values():
            if role.title.lower() == target or target in role.title.lower():
                return role

        # Unknown roles must be handled explicitly by the API. Falling back to
        # Data Analyst silently misrepresents the learner's selected pathway.
        return None

    def supported_roles(self) -> List[Dict[str, str]]:
        return [{"id": role.id, "title": role.title} for role in self.roles.values()]

    # -------------------------------------------------------------------------
    # Readiness Score Calculation
    # -------------------------------------------------------------------------

    def calculate_readiness(
        self,
        student_scores: Dict[str, float],
        role_identifier: str
    ) -> Dict[str, Any]:
        """
        Calculates weighted career readiness score (0.0% to 100.0%) comparing student's
        domain mastery against target role requirements.
        
        Formula:
          readiness = SUM(weight_i * min(1.0, student_score_i / benchmark_i)) * 100
        """
        role = self.get_role(role_identifier)
        if not role:
            return {"readiness_percentage": 0.0, "is_ready": False, "details": {}}

        # Normalize student score keys for case-insensitive lookup
        normalized_scores = {k.strip().lower(): v for k, v in student_scores.items()}

        total_weighted_ratio = 0.0
        details: Dict[str, Dict[str, Any]] = {}

        for domain, benchmark in role.required_skills.items():
            weight = role.skill_weights.get(domain, 0.25)
            student_val = normalized_scores.get(domain.lower(), 0.0)

            # Ratio of student's score relative to benchmark requirement (capped at 1.0)
            ratio = min(1.0, student_val / benchmark) if benchmark > 0 else 1.0
            weighted_contrib = weight * ratio
            total_weighted_ratio += weighted_contrib

            details[domain] = {
                "student_score": round(student_val, 2),
                "benchmark": round(benchmark, 2),
                "weight": weight,
                "attainment_pct": round(ratio * 100, 1),
                "status": "met" if student_val >= benchmark else "gap"
            }

        readiness_pct = round(total_weighted_ratio * 100, 1)

        return {
            "role_id": role.id,
            "role_title": role.title,
            "readiness_percentage": readiness_pct,
            "is_ready": readiness_pct >= 80.0,
            "domain_breakdown": details
        }

    # -------------------------------------------------------------------------
    # Skill Gap Extraction & Prioritization
    # -------------------------------------------------------------------------

    def identify_gaps(
        self,
        student_scores: Dict[str, float],
        role_identifier: str
    ) -> List[Dict[str, Any]]:
        """
        Pinpoints and prioritizes domain skill gaps where student_score < benchmark.
        Sorts gaps by importance (weight * gap_size descending).
        """
        role = self.get_role(role_identifier)
        if not role:
            return []

        normalized_scores = {k.strip().lower(): v for k, v in student_scores.items()}
        gaps: List[Dict[str, Any]] = []

        for domain, benchmark in role.required_skills.items():
            student_val = normalized_scores.get(domain.lower(), 0.0)
            if student_val < benchmark:
                gap_size = round(benchmark - student_val, 2)
                weight = role.skill_weights.get(domain, 0.25)
                priority_score = round(gap_size * weight, 3)

                # Severity classification
                if gap_size >= 0.25:
                    severity = "critical"
                elif gap_size >= 0.12:
                    severity = "moderate"
                else:
                    severity = "minor"

                gaps.append({
                    "domain": domain,
                    "student_score": round(student_val, 2),
                    "required_benchmark": round(benchmark, 2),
                    "gap_size": gap_size,
                    "weight": weight,
                    "priority_score": priority_score,
                    "severity": severity
                })

        # Sort by priority score descending (biggest impact gaps first)
        gaps.sort(key=lambda g: g["priority_score"], reverse=True)
        return gaps

    # -------------------------------------------------------------------------
    # Concept-Level Gap Extraction (Used for Knowledge Graph Traversal)
    # -------------------------------------------------------------------------

    def identify_concept_gaps(
        self,
        concept_mastery: Dict[str, float],
        role_identifier: str,
        mastery_threshold: float = 0.70
    ) -> List[Dict[str, Any]]:
        """
        Identifies specific concept-level gaps by comparing fine-grained concept mastery
        against the target role's critical_concepts list.
        Enables the Gap Analysis Agent to run knowledge_graph.get_root_causes(concept_id).
        """
        role = self.get_role(role_identifier)
        if not role:
            return []

        concept_gaps = []
        for concept_id in role.critical_concepts:
            mastery = concept_mastery.get(concept_id, 0.30)  # default prior if untested
            if mastery < mastery_threshold:
                gap_size = round(mastery_threshold - mastery, 2)
                concept_gaps.append({
                    "concept_id": concept_id,
                    "current_mastery": round(mastery, 2),
                    "target_threshold": mastery_threshold,
                    "gap_size": gap_size,
                    "is_critical": True
                })

        # Sort concept gaps by gap_size descending (largest deficit first)
        concept_gaps.sort(key=lambda cg: cg["gap_size"], reverse=True)
        return concept_gaps

    # -------------------------------------------------------------------------
    # Role Recommendation / Alternative Matching
    # -------------------------------------------------------------------------

    def match_alternative_roles(self, student_scores: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Ranks all known career paths by how well the student's current skill profile matches them.
        Provides alternative career discovery for learners.
        """
        matches = []
        for role_id in self.roles.keys():
            readiness_data = self.calculate_readiness(student_scores, role_id)
            matches.append({
                "role_id": role_id,
                "role_title": readiness_data["role_title"],
                "readiness_percentage": readiness_data["readiness_percentage"],
                "is_ready": readiness_data["is_ready"]
            })

        matches.sort(key=lambda m: m["readiness_percentage"], reverse=True)
        return matches


# Global singleton instance
career_benchmarks = CareerBenchmarkService()

