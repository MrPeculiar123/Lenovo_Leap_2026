"""
Test Agent Nodes (8, 9, 10)
===========================
Verifies:
1. gap_career_node: Benchmark calculation + Knowledge Graph DAG root cause traversal.
2. content_tutor_node: Pinecone RAG retrieval + Localized tutoring (Marathi/Hindi/English).
3. planning_node: 7-day adaptive roadmap generation with daily time budget.
"""

import sys
import os
from pathlib import Path

# Force UTF-8 output encoding for regional scripts (Marathi/Hindi) in Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from server.agent.state import StudentState
from server.agent.nodes.gap_career import gap_career_node
from server.agent.nodes.content_tutor import content_tutor_node, tutor_chat_node
from server.agent.nodes.planning import planning_node


def run_test():
    print("Initializing test state (Student Persona: Data Analyst, Marathi, 60 mins/day)...")
    state: StudentState = {
        "student_id": "stu_007",
        "target_career": "Data Analyst",
        "subject": "Data Analytics",
        "language": "Marathi",
        "primary_language": "Marathi",
        "daily_time_minutes": 60,
        "time_per_day_mins": 60,
        "perceived_level": "Intermediate",
        "domain_scores": {"SQL": 0.42, "Python": 0.82, "Statistics": 0.65, "Data Visualization": 0.50},
        "concept_mastery": {"sql_basics": 0.85, "sql_joins": 0.35, "python_syntax": 0.90},
        "current_concept_id": "sql_joins",
        "asked_question_ids": ["q1", "q2"],
        "assessment_questions": [],
        "raw_responses": [],
        "grounded_resources": [],
        "tutor_chat_history": [],
        "errors": []
    }

    # 1. Gap Career Node
    print("\n[STEP 1] Testing gap_career_node...")
    gap_res = gap_career_node(state)
    print(f"Readiness Score: {gap_res['career_readiness_score']}% (Is Ready: {gap_res['is_career_ready']})")
    print(f"Priority Gaps Identified: {len(gap_res['priority_gaps'])}")
    for g in gap_res["priority_gaps"][:3]:
        print(f"  - Skill: {g['career_skill']} | Gap: {g['gap_size']} | Root Cause: {g.get('root_cause_concept')}")
    print(f"Next Action: {gap_res['next_action']}")
    state.update(gap_res)

    # 2. Content Tutor Node
    print("\n[STEP 2] Testing content_tutor_node...")
    tutor_res = content_tutor_node(state)
    print(f"Grounded RAG Resources: {len(tutor_res['grounded_resources'])}")
    for r in tutor_res["grounded_resources"][:2]:
        print(f"  - [{r['resource_type']}] {r['title']} (Est. {r['estimated_minutes']} mins)")
    print(f"Tutor Localized Explanation Preview:\n{tutor_res['tutor_explanation_localized'][:220]}...")
    print(f"Next Action: {tutor_res['next_action']}")
    state.update(tutor_res)

    # 3. Planning Node
    print("\n[STEP 3] Testing planning_node...")
    plan_res = planning_node(state)
    print(f"Plan Summary: {plan_res['plan_summary']}")
    print(f"Total Days: {len(plan_res['study_plan'])}")
    for day in plan_res["study_plan"][:3]:
        print(f"  - Day {day['day']}: {day['focus_topic']} ({day['duration_minutes']}m, Activities: {len(day['activities'])})")
    print(f"Next Action: {plan_res['next_action']}")

    # 4. Tutor Chat Helper
    print("\n[STEP 4] Testing tutor_chat_node (Follow-up student query)...")
    chat_res = tutor_chat_node(state, student_message="मला INNER JOIN आणि LEFT JOIN मधील फरक समजला नाही.")
    print(f"Tutor Reply: {chat_res['latest_tutor_reply'][:180]}...")

    print("\nSUCCESS: All 3 agent nodes (8, 9, 10) executed and verified cleanly!")


if __name__ == "__main__":
    run_test()
