"""
Adaptive Assessment Agent Node (Dynamic Multi-Model NVIDIA NIM)
===============================================================
Implements Computerized Adaptive Testing (CAT) for PathForge:
1. Dynamically navigates prerequisite Knowledge Graph DAG (traverse_up / traverse_down).
2. Calibrates question difficulty (b) and discrimination (a) to student latent ability (theta).
3. Generates questions using dynamically selected NVIDIA NIM models via ChatNVIDIA.
4. Seamlessly falls back to pre-seeded curriculum questions if offline/rate-limited.
5. Evaluates student responses deterministically via 2-PL IRT and BKT (MLEngine).
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv

from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import SystemMessage, HumanMessage

try:
    from agent.state import StudentState, QuestionItem
    from agent.prompts import format_assessment_prompt
    from services.knowledge_graph import knowledge_graph, DiagnosticQuestion
    from services.ml_engine import ml_engine, StudentMLProfile
    from services.career_benchmarks import career_benchmarks as career_benchmarks_service
except ImportError:
    from server.agent.state import StudentState, QuestionItem
    from server.agent.prompts import format_assessment_prompt
    from server.services.knowledge_graph import knowledge_graph, DiagnosticQuestion
    from server.services.ml_engine import ml_engine, StudentMLProfile
    from server.services.career_benchmarks import career_benchmarks as career_benchmarks_service

# Load environment variables
for env_path in [Path("server/.env"), Path(".env"), Path(__file__).parent.parent.parent / ".env"]:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        break

# Default fallback model if none specified by caller
DEFAULT_ASSESSMENT_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"


def get_nvidia_client(
    model_name: str = DEFAULT_ASSESSMENT_MODEL,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    enable_thinking: bool = True,
    reasoning_budget: int = 2048
) -> Optional[ChatNVIDIA]:
    """
    Dynamically instantiates a ChatNVIDIA client for any specified model ID.
    """
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        print("[NVIDIA NIM] Warning: NVIDIA_API_KEY is not set.")
        return None

    try:
        client_kwargs: Dict[str, Any] = {
            "model": model_name,
            "api_key": api_key,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        # Configure thinking/reasoning parameters for supported reasoning models
        if "nemotron" in model_name.lower() or enable_thinking:
            client_kwargs["reasoning_budget"] = reasoning_budget
            client_kwargs["chat_template_kwargs"] = {"enable_thinking": True}

        return ChatNVIDIA(**client_kwargs)
    except Exception as e:
        print(f"[NVIDIA NIM] Error initializing model '{model_name}': {e}")
        return None


def select_next_concept(state: StudentState) -> str:
    """Selects next concept using DAG traversal or unassessed career requirements."""
    target_career = state.get("target_career", "Data Analyst")
    role = career_benchmarks_service.get_role(target_career)
    critical_concepts = role.critical_concepts if role else []
    concept_mastery = state.get("concept_mastery", {})
    current_concept_id = state.get("current_concept_id")
    raw_responses = state.get("raw_responses", [])

    if not raw_responses or not current_concept_id:
        if critical_concepts:
            return critical_concepts[0]
        return knowledge_graph.get_initial_concept("SQL", state.get("perceived_level", "Intermediate"))

    last_response = raw_responses[-1]
    is_correct = last_response.get("is_correct", False)
    next_concept = knowledge_graph.traverse_up(current_concept_id) if is_correct else knowledge_graph.traverse_down(current_concept_id)

    if next_concept and next_concept not in concept_mastery:
        return next_concept

    for c_id in critical_concepts:
        if c_id not in concept_mastery:
            return c_id

    for node_id in knowledge_graph.concept_nodes.keys():
        if node_id not in concept_mastery:
            return node_id

    return current_concept_id or "sql_basics"


def compute_target_parameters(profile: StudentMLProfile) -> Tuple[float, float]:
    """Maps student theta to 2-PL IRT difficulty (b) and discrimination (a)."""
    normalized_difficulty = max(0.1, min(0.9, 0.5 + (profile.theta * 0.15)))
    discrimination = 1.2
    return normalized_difficulty, discrimination


def _clean_json_string(raw_text: str) -> str:
    """Strips markdown code blocks and reasoning/thinking sections from LLM output."""
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


def generate_question(
    concept_id: str,
    difficulty: float,
    discrimination: float,
    state: StudentState,
    step: int,
    model_override: Optional[str] = None
) -> QuestionItem:
    """
    Generates calibrated diagnostic question using dynamic NVIDIA NIM model.
    Falls back to pre-seeded curriculum pool if offline/failed.
    """
    concept_node = knowledge_graph.get_concept(concept_id)
    concept_name = concept_node.name if concept_node else concept_id.replace("_", " ").title()
    domain = concept_node.domain if concept_node else "SQL"
    asked_ids = state.get("asked_question_ids", [])
    perceived_level = state.get("perceived_level", "Intermediate")
    target_career = state.get("target_career", "Data Analyst")
    preferred_types = state.get("preferred_question_types", ["MCQ"])
    q_type = preferred_types[0] if preferred_types else "MCQ"

    # Determine model dynamically (State Override -> Function Arg -> Default)
    target_model = model_override or state.get("assessment_model") or DEFAULT_ASSESSMENT_MODEL

    # Try dynamic LLM Generation via ChatNVIDIA
    nvidia_client = get_nvidia_client(model_name=target_model)
    if nvidia_client:
        try:
            prompt_str = format_assessment_prompt(
                concept_id=concept_id,
                concept_name=concept_name,
                domain=domain,
                difficulty=difficulty,
                discrimination=discrimination,
                question_type=q_type,
                perceived_level=perceived_level,
                target_career=target_career,
                step=step,
                asked_questions=asked_ids
            )
            messages = [
                SystemMessage(content="You are an expert CAT psychometrician. Respond strictly with valid raw JSON."),
                HumanMessage(content=prompt_str)
            ]
            response = nvidia_client.invoke(messages)
            if response and response.content:
                cleaned = _clean_json_string(str(response.content))
                data = json.loads(cleaned)
                if all(k in data for k in ["question", "options", "correct_answer"]):
                    question_item: QuestionItem = {
                        "id": data.get("id", f"q_{concept_id}_{step}"),
                        "concept_id": concept_id,
                        "question": data["question"],
                        "options": data["options"],
                        "correct_answer": data["correct_answer"],
                        "explanation": data.get("explanation", ""),
                        "difficulty": float(data.get("difficulty", difficulty)),
                        "discrimination": float(data.get("discrimination", discrimination)),
                        "question_type": data.get("question_type", q_type),
                        "student_answer": None,
                        "is_correct": None,
                        "response_time_sec": None
                    }
                    knowledge_graph.append_dynamic_question(
                        concept_id,
                        DiagnosticQuestion(
                            id=question_item["id"],
                            concept_id=concept_id,
                            difficulty=question_item["difficulty"],
                            question_type=question_item["question_type"],
                            question=question_item["question"],
                            options=question_item["options"],
                            correct_answer=question_item["correct_answer"],
                            explanation=question_item["explanation"]
                        )
                    )
                    return question_item
        except Exception as e:
            print(f"[AssessmentNode] Model '{target_model}' generation error: {e}. Falling back to curriculum.")

    # Fallback: Pre-seeded question pool
    cached_q = knowledge_graph.get_question_for_concept(
        concept_id=concept_id,
        asked_question_ids=asked_ids,
        preferred_type=q_type
    )
    if cached_q:
        return {
            "id": cached_q.id,
            "concept_id": cached_q.concept_id,
            "question": cached_q.question,
            "options": cached_q.options,
            "correct_answer": cached_q.correct_answer,
            "explanation": cached_q.explanation,
            "difficulty": cached_q.difficulty,
            "discrimination": discrimination,
            "question_type": cached_q.question_type,
            "student_answer": None,
            "is_correct": None,
            "response_time_sec": None
        }

    # Default fallback question
    return {
        "id": f"q_{concept_id}_{step}_fallback",
        "concept_id": concept_id,
        "question": f"Which SQL statement is used to retrieve data from a table in {concept_name}?",
        "options": [
            "A) SELECT * FROM table_name;",
            "B) GET DATA FROM table_name;",
            "C) FETCH ALL table_name;",
            "D) QUERY table_name;"
        ],
        "correct_answer": "A) SELECT * FROM table_name;",
        "explanation": "The SELECT statement is the foundational SQL command used to query and retrieve data.",
        "difficulty": difficulty,
        "discrimination": discrimination,
        "question_type": "MCQ",
        "student_answer": None,
        "is_correct": None,
        "response_time_sec": None
    }


def assessment_node(state: StudentState) -> Dict[str, Any]:
    """LangGraph Node: Serves adaptive diagnostic questions."""
    ml_dict = state.get("ml_profile")
    profile = StudentMLProfile.from_dict(ml_dict) if ml_dict else ml_engine.initialize_profile(state.get("perceived_level", "Intermediate"))

    if state.get("is_assessment_complete") or profile.is_terminal:
        return {
            "is_assessment_complete": True,
            "next_action": "analyze_gaps",
            "ml_profile": profile.to_dict()
        }

    current_step = state.get("current_step", 0) + 1
    if current_step > 8 or profile.questions_count >= 8:
        profile.is_terminal = True
        return {
            "is_assessment_complete": True,
            "next_action": "analyze_gaps",
            "ml_profile": profile.to_dict()
        }

    next_concept_id = select_next_concept(state)
    target_b, target_a = compute_target_parameters(profile)

    question = generate_question(
        concept_id=next_concept_id,
        difficulty=target_b,
        discrimination=target_a,
        state=state,
        step=current_step
    )

    return {
        "current_concept_id": next_concept_id,
        "current_question": question,
        "current_step": current_step,
        "asked_question_ids": [question["id"]],
        "is_assessment_complete": False,
        "next_action": "await_answer",
        "ml_profile": profile.to_dict()
    }


def record_answer_node(state: StudentState) -> Dict[str, Any]:
    """LangGraph Node: Evaluates student answers and updates IRT/BKT state."""
    current_q = state.get("current_question")
    if not current_q or not current_q.get("student_answer"):
        return {"errors": ["No active question or student answer provided to evaluate."]}

    student_ans = current_q["student_answer"].strip().lower()
    correct_ans = current_q["correct_answer"].strip().lower()
    is_correct = (student_ans == correct_ans) or (student_ans[:2] == correct_ans[:2])
    response_time = current_q.get("response_time_sec", 25.0) or 25.0
    difficulty = current_q.get("difficulty", 0.5)
    discrimination = current_q.get("discrimination", 1.0)
    concept_id = current_q.get("concept_id", "sql_basics")

    graded_q: QuestionItem = dict(current_q)
    graded_q["is_correct"] = is_correct

    ml_dict = state.get("ml_profile")
    profile = StudentMLProfile.from_dict(ml_dict) if ml_dict else ml_engine.initialize_profile(state.get("perceived_level", "Intermediate"))

    eval_result = ml_engine.record_interaction(
        profile=profile,
        concept_id=concept_id,
        is_correct=is_correct,
        difficulty=difficulty,
        discrimination=discrimination,
        response_time_sec=response_time
    )

    concept_domain_map = {cid: node.domain for cid, node in knowledge_graph.concept_nodes.items()}
    domain_scores = ml_engine.get_domain_summary(profile, concept_domain_map)
    is_complete = eval_result.get("is_terminal", False) or profile.questions_count >= 8

    return {
        "assessment_questions": [graded_q],
        "raw_responses": [{
            "concept_id": concept_id,
            "is_correct": is_correct,
            "response_time_sec": response_time,
            "theta": eval_result["theta"],
            "difficulty": difficulty
        }],
        "concept_mastery": profile.concept_mastery,
        "domain_scores": domain_scores,
        "ml_profile": profile.to_dict(),
        "is_assessment_complete": is_complete,
        "next_action": "analyze_gaps" if is_complete else "assess"
    }
