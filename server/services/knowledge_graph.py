"""
Knowledge Graph Service
=======================
Implements an educational prerequisite Directed Acyclic Graph (DAG) using NetworkX.
Decouples curriculum data (server/data/curriculum.json) from DAG operations.
Powers adaptive test navigation (traverse_up / traverse_down), root-cause prerequisite tracing (ancestors),
duplicate question filtering, and fallback hooks for dynamic LLM generation.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import networkx as nx


@dataclass
class DiagnosticQuestion:
    """Represents a diagnostic question tied directly to a knowledge graph concept."""
    id: str
    concept_id: str
    difficulty: float  # IRT b parameter: 0.2 (Easy), 0.5 (Medium), 0.8 (Hard)
    question_type: str  # "MCQ" | "Scenario-based" | "Coding"
    question: str
    options: List[str]
    correct_answer: str
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "concept_id": self.concept_id,
            "difficulty": self.difficulty,
            "question_type": self.question_type,
            "question": self.question,
            "options": self.options,
            "correct_answer": self.correct_answer,
            "explanation": self.explanation
        }


@dataclass
class ConceptNode:
    """A node in the Knowledge Graph representing a distinct educational skill/concept."""
    id: str
    name: str
    domain: str  # e.g., "SQL", "Python", "Statistics", "Data Visualization"
    depth_level: int  # 1: Foundational, 2: Intermediate, 3: Advanced
    difficulty_baseline: float  # 0.1 to 1.0
    description: str
    prerequisites: List[str] = field(default_factory=list)
    questions: List[DiagnosticQuestion] = field(default_factory=list)


class KnowledgeGraph:
    """
    NetworkX-powered Directed Acyclic Graph (DAG) managing educational concepts,
    prerequisite dependencies, and Computerized Adaptive Testing (CAT) traversal.
    """

    def __init__(self, data_path: Optional[str] = None):
        self.graph: nx.DiGraph = nx.DiGraph()
        self.concept_nodes: Dict[str, ConceptNode] = {}
        self._load_curriculum(data_path)

    # -------------------------------------------------------------------------
    # Data Loading & Initialization
    # -------------------------------------------------------------------------

    def _resolve_data_path(self, data_path: Optional[str] = None) -> Path:
        """Finds curriculum.json across common execution directories."""
        if data_path:
            return Path(data_path)

        candidates = [
            Path(__file__).parent.parent / "data" / "curriculum.json",
            Path("server/data/curriculum.json"),
            Path("data/curriculum.json"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()

        raise FileNotFoundError("Could not find 'server/data/curriculum.json'.")

    def _load_curriculum(self, data_path: Optional[str] = None) -> None:
        """Loads concepts, dependencies, and questions from the decoupled JSON file into NetworkX."""
        file_path = self._resolve_data_path(data_path)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Add all concept nodes
        for item in data.get("concepts", []):
            questions = [
                DiagnosticQuestion(
                    id=q["id"],
                    concept_id=q["concept_id"],
                    difficulty=float(q["difficulty"]),
                    question_type=q["question_type"],
                    question=q["question"],
                    options=list(q["options"]),
                    correct_answer=q["correct_answer"],
                    explanation=q["explanation"]
                )
                for q in item.get("questions", [])
            ]

            node = ConceptNode(
                id=item["id"],
                name=item["name"],
                domain=item["domain"],
                depth_level=int(item["depth_level"]),
                difficulty_baseline=float(item["difficulty_baseline"]),
                description=item["description"],
                prerequisites=list(item.get("prerequisites", [])),
                questions=questions
            )

            self.concept_nodes[node.id] = node
            # Store node attributes in NetworkX
            self.graph.add_node(
                node.id,
                name=node.name,
                domain=node.domain,
                depth_level=node.depth_level,
                difficulty_baseline=node.difficulty_baseline
            )

        # 2. Add directed edges: prerequisite -> target_concept
        for node_id, node in self.concept_nodes.items():
            for prereq_id in node.prerequisites:
                if self.graph.has_node(prereq_id):
                    self.graph.add_edge(prereq_id, node_id)

    # -------------------------------------------------------------------------
    # Concept Retrieval & Dynamic Question Appending
    # -------------------------------------------------------------------------

    def get_concept(self, concept_id: str) -> Optional[ConceptNode]:
        """Retrieves concept node details by ID."""
        return self.concept_nodes.get(concept_id)

    def append_dynamic_question(self, concept_id: str, question: DiagnosticQuestion) -> None:
        """
        Appends a newly generated LLM diagnostic question to the node's in-memory pool.
        Enables the hybrid pipeline: dynamic LLM questions expand the pool for future attempts.
        """
        node = self.get_concept(concept_id)
        if node:
            node.questions.append(question)

    # -------------------------------------------------------------------------
    # Adaptive Graph Traversal (NetworkX Powered)
    # -------------------------------------------------------------------------

    def traverse_up(self, current_concept_id: str) -> Optional[str]:
        """
        Traverses UP the DAG toward more advanced concepts.
        Called when a student answers a question CORRECTLY.
        Uses nx.successors() to find downstream advanced concepts.
        """
        if not self.graph.has_node(current_concept_id):
            return None

        successors = list(self.graph.successors(current_concept_id))
        if not successors:
            return None

        # Sort successors by (depth_level, difficulty_baseline)
        successor_nodes = [self.concept_nodes[s_id] for s_id in successors if s_id in self.concept_nodes]
        successor_nodes.sort(key=lambda n: (n.depth_level, n.difficulty_baseline))
        return successor_nodes[0].id if successor_nodes else None

    def traverse_down(self, current_concept_id: str) -> Optional[str]:
        """
        Traverses DOWN the DAG toward foundational prerequisites.
        Called when a student answers a question INCORRECTLY.
        Uses nx.predecessors() to find direct prerequisite concepts.
        """
        if not self.graph.has_node(current_concept_id):
            return None

        predecessors = list(self.graph.predecessors(current_concept_id))
        if not predecessors:
            return None

        # Pick the most immediate prerequisite with highest depth
        prereq_nodes = [self.concept_nodes[p_id] for p_id in predecessors if p_id in self.concept_nodes]
        prereq_nodes.sort(key=lambda n: (-n.depth_level, -n.difficulty_baseline))
        return prereq_nodes[0].id if prereq_nodes else None

    def get_root_causes(self, failed_concept_id: str) -> List[str]:
        """
        Finds all prerequisite ancestors of a failed concept using nx.ancestors().
        Returns a topologically sorted list of root-cause prerequisite IDs.
        """
        if not self.graph.has_node(failed_concept_id):
            return []

        ancestors_set = nx.ancestors(self.graph, failed_concept_id)
        if not ancestors_set:
            return []

        # Return ancestors in topological order from bedrock up to immediate prereq
        subgraph = self.graph.subgraph(ancestors_set)
        return list(nx.topological_sort(subgraph))

    def get_initial_concept(self, domain: str, perceived_level: str) -> str:
        """
        Selects starting concept node based on student's domain & onboarding level.
        - Beginner: Level 1 foundational node
        - Intermediate: Level 2 mid-chain node
        - Advanced: Level 3 advanced node
        """
        domain_nodes = [node for node in self.concept_nodes.values() if node.domain.lower() == domain.lower()]
        if not domain_nodes:
            return "sql_basics"

        target_depth = 1
        if perceived_level.lower() == "intermediate":
            target_depth = 2
        elif perceived_level.lower() == "advanced":
            target_depth = 3

        matching = [n for n in domain_nodes if n.depth_level == target_depth]
        if matching:
            return matching[0].id
        return domain_nodes[0].id

    # -------------------------------------------------------------------------
    # Question Selection with Duplicate Filtering & Dynamic LLM Fallback Hook
    # -------------------------------------------------------------------------

    def get_question_for_concept(
        self,
        concept_id: str,
        asked_question_ids: Optional[List[str]] = None,
        preferred_type: Optional[str] = None
    ) -> Optional[DiagnosticQuestion]:
        """
        Selects an unasked diagnostic question for a concept.
        
        Refactoring features:
        1. Duplicate Filtering: Excludes questions whose ID is in `asked_question_ids`.
        2. Format Filtering: Prefers the student's preferred question_type if available.
        3. Dynamic LLM Fallback Hook: Returns None if all pre-seeded questions are exhausted,
           signaling to the Assessment Agent that an LLM prompt must generate a new question.
        """
        node = self.get_concept(concept_id)
        if not node or not node.questions:
            return None

        asked_set = set(asked_question_ids or [])
        available = [q for q in node.questions if q.id not in asked_set]

        if not available:
            # FALLBACK HOOK: Pool exhausted -> signal Assessment Agent LLM to generate dynamically
            return None

        if preferred_type:
            type_matched = [q for q in available if q.question_type.lower() == preferred_type.lower()]
            if type_matched:
                return type_matched[0]

        return available[0]


# Global singleton instance
knowledge_graph = KnowledgeGraph()
