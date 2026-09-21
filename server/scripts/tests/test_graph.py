"""
Test LangGraph Orchestration (server/agent/graph.py)
===================================================
Tests end-to-end execution of the Master LangGraph workflow with a mock student state:
1. Generates adaptive questions.
2. Submits answers and updates BKT/IRT tracking.
3. Automatically triggers post-assessment remediation pipeline:
   Gap Analysis & Career -> Content & Regional Tutor -> 7-Day Planning.
"""

import sys
import os
from pathlib import Path

# Force UTF-8 console output for regional language scripts (Marathi/Hindi)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from server.agent.state import StudentState
from server.agent.graph import (
    adaptive_learning_graph,
    remediation_pipeline,
    run_next_assessment_step,
    submit_assessment_answer,
    run_remediation_pipeline
)


def test_full_remediation_pipeline():
    print("\n=======================================================")
    print("TEST 1: DIRECT REMEDIATION PIPELINE (Gap -> Tutor -> Plan)")
    print("=======================================================")

    mock_state: StudentState = {
        "student_id": "stu_marathi_01",
        "target_career": "Data Analyst",
        "subject": "Data Analytics",
        "language": "Marathi",
        "primary_language": "Marathi",
        "daily_time_minutes": 60,
        "time_per_day_mins": 60,
        "perceived_level": "Intermediate",
        "domain_scores": {"SQL": 0.43, "Python": 0.80, "Statistics": 0.65, "Data Visualization": 0.50},
        "concept_mastery": {
            "sql_basics": 0.70,
            "sql_joins": 0.35,      # Critical gap
            "python_basics": 0.85
        },
        "current_concept_id": "sql_joins",
        "asked_question_ids": ["q_sql_1", "q_sql_2"],
        "assessment_questions": [],
        "raw_responses": [],
        "grounded_resources": [],
        "tutor_chat_history": [],
        "errors": []
    }

    result = run_remediation_pipeline(mock_state)

    print(f"1. Career Readiness Score: {result.get('career_readiness_score')}%")
    print(f"2. Career Ready: {result.get('is_career_ready')}")
    print(f"3. Priority Gaps Detected: {len(result.get('priority_gaps', []))}")
    for g in result.get("priority_gaps", [])[:2]:
        print(f"   - {g['career_skill']} (Gap={g['gap_size']}, Root Cause={g.get('root_cause_concept')})")

    print(f"4. Grounded RAG Resources Retrieved: {len(result.get('grounded_resources', []))}")
    for r in result.get("grounded_resources", [])[:2]:
        print(f"   - [{r['resource_type']}] {r['title']}")

    print(f"5. Localized Tutor Explanation:\n{result.get('tutor_explanation_localized', '')[:250]}...\n")

    print(f"6. 7-Day Plan Summary: {result.get('plan_summary')}")
    print(f"7. Total Roadmap Days: {len(result.get('study_plan', []))}")
    for d in result.get("study_plan", [])[:3]:
        print(f"   - Day {d['day']}: {d['focus_topic']} ({d['duration_minutes']} mins, Activities: {len(d['activities'])})")

    assert result.get("study_plan"), "Study plan should have items"
    assert len(result.get("study_plan")) == 7, "Study plan should contain 7 days"
    print("\n>>> TEST 1 PASSED SUCCESSFULLY! <<<\n")


def test_interactive_assessment_flow():
    print("=======================================================")
    print("TEST 2: ADAPTIVE ASSESSMENT QUESTION & SUBMISSION FLOW")
    print("=======================================================")

    state: StudentState = {
        "student_id": "stu_interactive_02",
        "target_career": "Data Analyst",
        "subject": "Data Analytics",
        "language": "English",
        "primary_language": "English",
        "daily_time_minutes": 45,
        "perceived_level": "Intermediate",
        "asked_question_ids": [],
        "concept_mastery": {},
        "current_step": 0,
        "is_assessment_complete": False,
        "assessment_questions": [],
        "raw_responses": [],
        "grounded_resources": [],
        "tutor_chat_history": [],
        "errors": []
    }

    # Step 1: Generate first question
    print("Generating Question 1...")
    state = run_next_assessment_step(state)
    q1 = state["current_question"]
    print(f"Question 1 Served: ID={q1['id']}, Concept={state['current_concept_id']}")
    print(f"Problem: {q1['question'][:80]}...")
    print(f"Target Difficulty: {q1['difficulty']}, Discrimination: {q1['discrimination']}")

    # Step 2: Submit an answer
    print("\nSubmitting answer to Question 1...")
    state = submit_assessment_answer(state, student_answer=q1["correct_answer"], response_time_sec=14.5)
    print(f"Current Ability (theta): {state['ml_profile']['theta']}")
    print(f"Concept Mastery: {state['concept_mastery']}")
    print(f"Domain Scores: {state['domain_scores']}")
    print(f"Is Assessment Complete: {state.get('is_assessment_complete')}")

    # Step 3: Fast-forward to test completion (Simulate 7 more answers to reach terminal)
    print("\nSimulating remaining answers to reach test termination...")
    for step in range(2, 9):
        state = run_next_assessment_step(state)
        q = state["current_question"]
        state = submit_assessment_answer(state, student_answer=q["correct_answer"], response_time_sec=18.0)

    print(f"\nFinal Question Count: {state['ml_profile']['questions_count']}")
    print(f"Is Assessment Complete: {state.get('is_assessment_complete')}")
    print(f"Automated Pipeline Execution Triggered:")
    print(f"  - Career Readiness: {state.get('career_readiness_score')}%")
    print(f"  - Priority Gaps: {len(state.get('priority_gaps', []))}")
    print(f"  - Localized Explanation Generated: {bool(state.get('tutor_explanation_localized'))}")
    print(f"  - 7-Day Study Plan Generated: {len(state.get('study_plan', []))} days")

    assert state.get("is_assessment_complete"), "Assessment should be complete"
    assert len(state.get("study_plan", [])) == 7, "Full 7-day study plan should be attached"
    print("\n>>> TEST 2 PASSED SUCCESSFULLY! <<<\n")


if __name__ == "__main__":
    test_full_remediation_pipeline()
    test_interactive_assessment_flow()
    print("ALL TESTS IN test_graph.py COMPLETED AND VERIFIED!")

