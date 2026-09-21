"""
Gap Analysis & Career Agent Node (Combined - Dynamic Multi-Model NVIDIA NIM)
=============================================================================
Combines Career Benchmark Matching with Knowledge Graph Root-Cause Traversal:
1. Evaluates student domain scores and concept mastery against target career requirements.
2. Identifies blocking skill deficits (concept gaps).
3. Traverses the prerequisite DAG in the Knowledge Graph to identify bedrock root causes.
4. Synthesizes a prioritized gap list, career readiness score, and alternative roles.
5. Employs dynamic NVIDIA NIM routing (ChatNVIDIA) with deterministic fallback.
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import SystemMessage, HumanMessage

try:
    from agent.state import StudentState, PrioritizedGap
    from agent.prompts import format_gap_career_prompt
    from services.career_benchmarks import career_benchmarks
    from services.knowledge_graph import knowledge_graph
except ImportError:
    from server.agent.state import StudentState, PrioritizedGap
    from server.agent.prompts import format_gap_career_prompt
    from server.services.career_benchmarks import career_benchmarks
    from server.services.knowledge_graph import knowledge_graph

# Load environment variables
for env_path in [Path("server/.env"), Path(".env"), Path(__file__).parent.parent.parent / ".env"]:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        break

DEFAULT_GAP_CAREER_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"


def get_nvidia_client(
    model_name: str = DEFAULT_GAP_CAREER_MODEL,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    enable_thinking: bool = True,
    reasoning_budget: int = 2048
) -> Optional[ChatNVIDIA]:
    """Dynamically instantiates ChatNVIDIA client for any specified model ID."""
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return None

    try:
        client_kwargs: Dict[str, Any] = {
            "model": model_name,
            "api_key": api_key,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if "nemotron" in model_name.lower() or enable_thinking:
            client_kwargs["reasoning_budget"] = reasoning_budget
            client_kwargs["chat_template_kwargs"] = {"enable_thinking": True}

        return ChatNVIDIA(**client_kwargs)
    except Exception as e:
        print(f"[GapCareerNode] Error initializing model '{model_name}': {e}")
        return None


def _clean_json_string(raw_text: str) -> str:
    """Strips thinking blocks and markdown formatting from LLM JSON response."""
    raw_text = raw_text.strip()
    if "</think>" in raw_text:
        raw_text = raw_text.split("</think>")[-1].strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]
    elif raw_text.startswith("```"):
        raw_text = raw_text[3:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
    return raw_text.strip()


def gap_career_node(state: StudentState) -> Dict[str, Any]:
    """
    LangGraph Node: Combined Gap Analysis & Career Intelligence.
    Executes benchmark matching + backward prerequisite graph traversal.
    """
    target_career = state.get("target_career", "Data Analyst")
    domain_scores = state.get("domain_scores", {})
    concept_mastery = state.get("concept_mastery", {})

    # 1. Calculate baseline readiness & domain gaps via CareerBenchmarkService
    readiness_data = career_benchmarks.calculate_readiness(domain_scores, target_career)
    concept_gaps = career_benchmarks.identify_concept_gaps(concept_mastery, target_career)
    alt_roles = career_benchmarks.match_alternative_roles(domain_scores)

    # 2. Trace prerequisite root causes via Knowledge Graph DAG for every deficit concept
    prereq_root_causes: List[Dict[str, Any]] = []
    enriched_gaps: List[PrioritizedGap] = []

    for gap in concept_gaps:
        concept_id = gap["concept_id"]
        concept_node = knowledge_graph.get_concept(concept_id)
        concept_name = concept_node.name if concept_node else concept_id.replace("_", " ").title()
        domain = concept_node.domain if concept_node else "General"
        target_threshold = gap.get("target_threshold", 0.70)

        # Query DAG for all prerequisite ancestors (topological order)
        ancestors = knowledge_graph.get_root_causes(concept_id)
        root_cause = ancestors[0] if ancestors else None

        prereq_root_causes.append({
            "concept_id": concept_id,
            "concept_name": concept_name,
            "domain": domain,
            "current_mastery": gap["current_mastery"],
            "benchmark_threshold": target_threshold,
            "gap_size": gap["gap_size"],
            "root_cause_concept": root_cause,
            "prerequisite_chain": ancestors
        })

        # Calculate priority score: (gap_size * 0.7) + (0.3 if root_cause else 0.0)
        priority_score = round(min(1.0, gap["gap_size"] * 1.1), 2)
        severity = "critical" if gap["gap_size"] >= 0.25 else ("moderate" if gap["gap_size"] >= 0.12 else "minor")

        enriched_gaps.append({
            "domain": domain,
            "career_skill": concept_name,
            "required_benchmark": target_threshold,
            "current_score": gap["current_mastery"],
            "gap_size": gap["gap_size"],
            "severity": severity,
            "priority_score": priority_score,
            "root_cause_concept": root_cause,
            "prerequisite_path": ancestors
        })

    # Sort gaps descending by priority score
    enriched_gaps.sort(key=lambda g: g.get("priority_score", 0.0), reverse=True)

    # 3. Dynamic Multi-Model LLM Refinement via ChatNVIDIA
    target_model = state.get("gap_career_model") or DEFAULT_GAP_CAREER_MODEL
    nvidia_client = get_nvidia_client(model_name=target_model)

    if nvidia_client:
        try:
            role_obj = career_benchmarks.get_role(target_career)
            role_dict = role_obj.to_dict() if role_obj else {}

            prompt_str = format_gap_career_prompt(
                target_career=target_career,
                career_benchmarks=role_dict,
                domain_scores=domain_scores,
                concept_mastery=concept_mastery,
                prerequisite_root_causes=prereq_root_causes
            )

            messages = [
                SystemMessage(content="You are an expert Career & Learning Gap Intelligence Agent. Output strictly raw JSON."),
                HumanMessage(content=prompt_str)
            ]
            response = nvidia_client.invoke(messages)
            if response and response.content:
                cleaned = _clean_json_string(str(response.content))
                data = json.loads(cleaned)

                # Use LLM refined insights if schema matches
                if "career_readiness_score" in data and "priority_gaps" in data:
                    parsed_gaps: List[PrioritizedGap] = []
                    for pg in data.get("priority_gaps", []):
                        parsed_gaps.append({
                            "domain": pg.get("domain", "General"),
                            "career_skill": pg.get("career_skill", ""),
                            "required_benchmark": float(pg.get("required_benchmark", 0.7)),
                            "current_score": float(pg.get("current_score", 0.5)),
                            "gap_size": float(pg.get("gap_size", 0.2)),
                            "severity": pg.get("severity", "moderate"),
                            "priority_score": float(pg.get("priority_score", 0.5)),
                            "root_cause_concept": pg.get("root_cause_concept"),
                            "prerequisite_path": pg.get("prerequisite_path", [])
                        })

                    return {
                        "career_readiness_score": float(data.get("career_readiness_score", readiness_data["readiness_percentage"])),
                        "is_career_ready": bool(data.get("is_career_ready", readiness_data["is_ready"])),
                        "priority_gaps": parsed_gaps or enriched_gaps,
                        "alternative_roles": data.get("alternative_roles", alt_roles[:3]),
                        "next_action": "tutor"
                    }
        except Exception as e:
            print(f"[GapCareerNode] LLM refinement error with '{target_model}': {e}. Using deterministic synthesis.")

    # 4. Deterministic fallback
    return {
        "career_readiness_score": readiness_data["readiness_percentage"],
        "is_career_ready": readiness_data["is_ready"],
        "priority_gaps": enriched_gaps,
        "alternative_roles": alt_roles[:3],
        "next_action": "tutor"
    }
