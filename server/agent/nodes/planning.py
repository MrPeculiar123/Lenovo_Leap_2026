"""
Personalized Planning Agent Node (Dynamic Multi-Model NVIDIA NIM)
=================================================================
Creates an adaptive 7-day daily study roadmap:
1. Strictly adheres to the student's daily time limit (e.g. 60 mins/day).
2. Prerequisite-First Strategy: Remediates root causes before advancing to career blocker skills.
3. Associates each day's focus with retrieved grounded educational resources.
4. Generates structured daily activities, time breakdowns, and learning objectives.
5. Employs dynamic multi-model routing via ChatNVIDIA with robust deterministic fallback.
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
    from agent.state import StudentState, DailyPlanItem, GroundedResource
    from agent.prompts import format_planning_prompt
except ImportError:
    from server.agent.state import StudentState, DailyPlanItem, GroundedResource
    from server.agent.prompts import format_planning_prompt

# Load environment variables
for env_path in [Path("server/.env"), Path(".env"), Path(__file__).parent.parent.parent / ".env"]:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        break

DEFAULT_PLANNING_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"


def get_nvidia_client(
    model_name: str = DEFAULT_PLANNING_MODEL,
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
        print(f"[PlanningNode] Error initializing model '{model_name}': {e}")
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


def _generate_fallback_plan(
    target_career: str,
    daily_time: int,
    priority_gaps: List[Dict[str, Any]],
    resources: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generates a deterministic 7-day adaptive curriculum respecting time bounds."""
    # Identify root causes and blocker topics
    root_causes = [g.get("root_cause_concept") for g in priority_gaps if g.get("root_cause_concept")]
    primary_topics = [g.get("career_skill") for g in priority_gaps if g.get("career_skill")]

    day1_topic = (root_causes[0] if root_causes else "Foundational Data Relationships").replace("_", " ").title()
    day2_topic = (root_causes[1] if len(root_causes) > 1 else (primary_topics[0] if primary_topics else "Relational Keys")).replace("_", " ").title()
    day3_topic = (primary_topics[0] if primary_topics else "SQL Joins & Multi-Table Queries").replace("_", " ").title()
    day4_topic = (primary_topics[1] if len(primary_topics) > 1 else "Grouping & Aggregation Functions").replace("_", " ").title()

    reading_mins = max(15, int(daily_time * 0.35))
    practice_mins = daily_time - reading_mins

    curriculum_days = [
        {
            "day": 1,
            "focus_topic": f"Prerequisite Bedrock: {day1_topic}",
            "duration_minutes": daily_time,
            "learning_objectives": [
                f"Master core concepts of {day1_topic}",
                "Identify entity relationships and constraints"
            ],
            "activities": [
                {"title": "Core Reading & Video", "type": "reading", "duration_minutes": reading_mins, "description": f"Review foundational reference guide on {day1_topic}."},
                {"title": "Guided Schema Practice", "type": "practice", "duration_minutes": practice_mins, "description": "Solve 5 foundational constraint exercises."}
            ],
            "recommended_resources": resources[:1],
            "completion_status": "pending"
        },
        {
            "day": 2,
            "focus_topic": f"Prerequisite Strengthening: {day2_topic}",
            "duration_minutes": daily_time,
            "learning_objectives": [
                f"Deep dive into {day2_topic}",
                "Bridge prerequisite gaps into intermediate data operations"
            ],
            "activities": [
                {"title": "Theory & Code Walkthrough", "type": "reading", "duration_minutes": reading_mins, "description": f"Explore query mechanics of {day2_topic}."},
                {"title": "Query Writing Lab", "type": "practice", "duration_minutes": practice_mins, "description": "Write syntax queries on sample datasets."}
            ],
            "recommended_resources": resources[1:2] or resources[:1],
            "completion_status": "pending"
        },
        {
            "day": 3,
            "focus_topic": f"Core Career Skill: {day3_topic}",
            "duration_minutes": daily_time,
            "learning_objectives": [
                f"Master workplace applications of {day3_topic}",
                "Construct multi-stage queries without syntax errors"
            ],
            "activities": [
                {"title": "Workflow Review", "type": "reading", "duration_minutes": reading_mins, "description": "Best practices for join conditions and filter order."},
                {"title": "Multi-Table Join Drills", "type": "practice", "duration_minutes": practice_mins, "description": "Join customer, orders, and products tables."}
            ],
            "recommended_resources": resources[:2],
            "completion_status": "pending"
        },
        {
            "day": 4,
            "focus_topic": f"Advanced Skill: {day4_topic}",
            "duration_minutes": daily_time,
            "learning_objectives": [
                f"Apply aggregation and grouping logic",
                "Debug complex query execution plans"
            ],
            "activities": [
                {"title": "Aggregation Walkthrough", "type": "reading", "duration_minutes": reading_mins, "description": "Understand GROUP BY vs WHERE execution sequence."},
                {"title": "Metric Computation Lab", "type": "practice", "duration_minutes": practice_mins, "description": "Compute rolling averages and cohort aggregations."}
            ],
            "recommended_resources": resources[1:3] or resources[:1],
            "completion_status": "pending"
        },
        {
            "day": 5,
            "focus_topic": "Practical Optimization & Real-World Edge Cases",
            "duration_minutes": daily_time,
            "learning_objectives": [
                "Handle NULL values, duplicates, and data anomalies",
                "Optimize queries for fast database execution"
            ],
            "activities": [
                {"title": "Edge Case Analysis", "type": "reading", "duration_minutes": reading_mins, "description": "Explore outer join null behavior and indexing."},
                {"title": "Speed & Optimization Drills", "type": "practice", "duration_minutes": practice_mins, "description": "Refactor slow queries on 50k+ row sample tables."}
            ],
            "recommended_resources": resources[:1],
            "completion_status": "pending"
        },
        {
            "day": 6,
            "focus_topic": f"Capstone Challenge: Workplace Simulation for {target_career}",
            "duration_minutes": daily_time,
            "learning_objectives": [
                f"End-to-end practical project simulating a {target_career} deliverable",
                "Synthesize business questions into analytical answers"
            ],
            "activities": [
                {"title": "Business Problem Statement", "type": "reading", "duration_minutes": 15, "description": "Analyze an executive brief requesting churn analysis."},
                {"title": "Project Implementation", "type": "practice", "duration_minutes": daily_time - 15, "description": "Build query pipeline answering 4 key business KPIs."}
            ],
            "recommended_resources": resources[:2],
            "completion_status": "pending"
        },
        {
            "day": 7,
            "focus_topic": "Comprehensive Skill Milestone & Self-Assessment Quiz",
            "duration_minutes": daily_time,
            "learning_objectives": [
                "Verify remediation of diagnosed prerequisite root causes",
                "Assess readiness milestone for upcoming career applications"
            ],
            "activities": [
                {"title": "Milestone Quiz (8 Questions)", "type": "quiz", "duration_minutes": 30, "description": "CAT adaptive re-assessment on all remediated skills."},
                {"title": "Personal Progress Review", "type": "review", "duration_minutes": daily_time - 30, "description": "Review score delta and plan next advancement milestones."}
            ],
            "recommended_resources": resources[:1],
            "completion_status": "pending"
        }
    ]

    return {
        "plan_summary": f"Personalized 7-Day Curriculum tailored for {target_career}, dedicating {daily_time} mins/day to remediate prerequisite root causes ({day1_topic}) before advancing to applied skills ({day3_topic}).",
        "study_plan": curriculum_days
    }


def planning_node(state: StudentState) -> Dict[str, Any]:
    """
    LangGraph Node: Personalized Study Planning.
    1. Reads daily time limit and priority gaps with root causes.
    2. Builds a 7-day time-budgeted curriculum roadmap.
    3. Leverages dynamic Multi-Model ChatNVIDIA with deterministic fallback.
    """
    target_career = state.get("target_career", "Data Analyst")
    daily_time = state.get("daily_time_minutes") or state.get("time_per_day_mins") or 60
    perceived_level = state.get("perceived_level", "Intermediate")
    priority_gaps = state.get("priority_gaps", [])
    grounded_resources = state.get("grounded_resources", [])

    # 1. Multi-Model LLM Planning via ChatNVIDIA
    target_model = state.get("planning_model") or DEFAULT_PLANNING_MODEL
    nvidia_client = get_nvidia_client(model_name=target_model)

    if nvidia_client:
        try:
            prompt_str = format_planning_prompt(
                target_career=target_career,
                daily_time_minutes=daily_time,
                perceived_level=perceived_level,
                priority_gaps=priority_gaps,
                available_resources=grounded_resources
            )

            messages = [
                SystemMessage(content="You are PathForge's Adaptive Curriculum Planning Agent. Return strictly valid raw JSON."),
                HumanMessage(content=prompt_str)
            ]
            response = nvidia_client.invoke(messages)
            if response and response.content:
                cleaned = _clean_json_string(str(response.content))
                data = json.loads(cleaned)

                if "study_plan" in data and isinstance(data["study_plan"], list):
                    plan_items: List[DailyPlanItem] = []
                    for idx, day_data in enumerate(data["study_plan"], 1):
                        plan_items.append({
                            "day": day_data.get("day", idx),
                            "focus_topic": day_data.get("focus_topic", f"Day {idx} Topic"),
                            "duration_minutes": day_data.get("duration_minutes", daily_time),
                            "learning_objectives": day_data.get("learning_objectives", []),
                            "activities": day_data.get("activities", []),
                            "recommended_resources": grounded_resources[:2],
                            "completion_status": "pending"
                        })

                    return {
                        "study_plan": plan_items,
                        "plan_summary": data.get("plan_summary", f"7-Day remediation plan for {target_career}"),
                        "next_action": "complete"
                    }
        except Exception as e:
            print(f"[PlanningNode] Error generating plan with '{target_model}': {e}. Using deterministic fallback.")

    # 2. Deterministic Fallback
    fallback_data = _generate_fallback_plan(
        target_career=target_career,
        daily_time=daily_time,
        priority_gaps=priority_gaps,
        resources=grounded_resources
    )

    return {
        "study_plan": fallback_data["study_plan"],
        "plan_summary": fallback_data["plan_summary"],
        "next_action": "complete"
    }
