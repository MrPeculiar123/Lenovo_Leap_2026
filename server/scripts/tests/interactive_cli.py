"""
Interactive Terminal Test Harness for PathForge
===============================================
Runs the entire LangGraph workflow directly in your terminal:
1. Collects student onboarding choices (Career, Language, Daily Time, Level).
2. Serves adaptive diagnostic questions interactively in real time.
3. Evaluates answers, updates IRT theta & BKT mastery scores.
4. Automatically triggers the post-assessment remediation pipeline (Gap Analysis -> Tutor -> Plan).
5. Opens an interactive chat loop with the Regional AI Tutor.
"""

import os
import sys
from pathlib import Path

# Enforce UTF-8 encoding for regional language output (Marathi/Hindi) in Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path dynamically
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.agent.state import StudentState
from server.agent.graph import (
    run_next_assessment_step,
    submit_assessment_answer,
    run_remediation_pipeline,
)
from server.agent.nodes.content_tutor import tutor_chat_node


def run_cli():
    print("\n" + "=" * 60)
    print("   🎓 PATHFORGE ADAPTIVE LEARNING PLATFORM - CLI HARNESS 🎓   ")
    print("=" * 60 + "\n")

    # -------------------------------------------------------------------------
    # STEP 1: ONBOARDING PREFERENCES
    # -------------------------------------------------------------------------
    print("--- STUDENT ONBOARDING ---")
    target_career = input("Target Career [Default: Data Analyst]: ").strip() or "Data Analyst"
    
    print("\nSupported Regional Languages: Marathi, Hindi, English")
    language = input("Preferred Language [Default: Marathi]: ").strip() or "Marathi"
    
    daily_time_str = input("Daily Study Time in Minutes [Default: 60]: ").strip() or "60"
    try:
        daily_time = int(daily_time_str)
    except ValueError:
        daily_time = 60

    print("\nPerceived Skill Levels: Beginner, Intermediate, Advanced")
    perceived_level = input("Perceived Skill Level [Default: Intermediate]: ").strip() or "Intermediate"

    # Initialize StudentState
    state: StudentState = {
        "student_id": "cli_student_01",
        "target_career": target_career,
        "subject": "Data Analytics",
        "language": language,
        "primary_language": language,
        "daily_time_minutes": daily_time,
        "time_per_day_mins": daily_time,
        "perceived_level": perceived_level,
        "asked_question_ids": [],
        "concept_mastery": {},
        "domain_scores": {},
        "current_step": 0,
        "is_assessment_complete": False,
        "assessment_questions": [],
        "raw_responses": [],
        "grounded_resources": [],
        "tutor_chat_history": [],
        "errors": []
    }

    print("\n" + "-" * 60)
    print(f"✓ Profile Initialized | Role: {target_career} | Language: {language} | Time: {daily_time}m/day")
    print("-" * 60 + "\n")

    # -------------------------------------------------------------------------
    # STEP 2: INTERACTIVE CAT ASSESSMENT LOOP
    # -------------------------------------------------------------------------
    print("=" * 60)
    print("   PHASE 1: COMPUTERIZED ADAPTIVE TESTING (CAT DIAGNOSTIC)   ")
    print("=" * 60 + "\n")

    while not state.get("is_assessment_complete", False):
        # Generate next question
        state = run_next_assessment_step(state)
        
        if state.get("is_assessment_complete"):
            break

        q = state.get("current_question")
        if not q:
            print("Notice: No question returned. Finalizing assessment...")
            break

        step = state.get("current_step", 1)
        print(f"\n[QUESTION {step} / 8] Concept: '{q.get('concept_id')}'")
        print(f"Difficulty (b): {q.get('difficulty', 0.5):.2f} | Type: {q.get('question_type', 'MCQ')}")
        print("-" * 50)
        print(f"Prompt: {q.get('question')}\n")

        options = q.get("options", [])
        for opt in options:
            print(f"   {opt}")

        # Collect user answer
        print("\nOptions: Type option text or letter (e.g. A, B, C, D or exact text)")
        user_input = input("👉 Your Answer: ").strip()

        if not user_input:
            user_input = q.get("correct_answer", "A")  # Safety fallback

        # Grade & update state
        state = submit_assessment_answer(state, student_answer=user_input, response_time_sec=18.0)

        # Display real-time ML metrics
        ml_prof = state.get("ml_profile", {})
        theta = ml_prof.get("theta", 0.0)
        print("\n[ML Update] Ability Theta (θ):", f"{theta:+.2f}")
        print("Current Mastery Map:", state.get("concept_mastery", {}))
        print("Domain Summary:", state.get("domain_scores", {}))

    print("\n" + "=" * 60)
    print(" 🎉 DIAGNOSTIC ASSESSMENT COMPLETE! RUNNING REMEDIATION PIPELINE... ")
    print("=" * 60 + "\n")

    # -------------------------------------------------------------------------
    # STEP 3: DISPLAY REMEDIATION PIPELINE OUTPUTS
    # -------------------------------------------------------------------------
    if not state.get("study_plan"):
        state.update(run_remediation_pipeline(state))

    print("=" * 60)
    print("   PHASE 2: CAREER READINESS & GAP DIAGNOSIS   ")
    print("=" * 60)
    print(f"Target Career: {target_career}")
    print(f"Readiness Score: {state.get('career_readiness_score', 0.0)}%")
    print(f"Career Ready Status: {state.get('is_career_ready', False)}")

    print("\nPrioritized Skill Deficits & DAG Root Causes:")
    gaps = state.get("priority_gaps", [])
    if not gaps:
        print("  ✓ No major skill gaps detected!")
    else:
        for idx, g in enumerate(gaps, 1):
            print(f"  {idx}. Skill: {g.get('career_skill')} | Domain: {g.get('domain')}")
            print(f"     Gap Size: {g.get('gap_size')} | Severity: {g.get('severity')}")
            print(f"     Prerequisite Root Cause Node: {g.get('root_cause_concept')}")
            print(f"     DAG Prerequisite Path: {g.get('prerequisite_path')}")

    print("\n" + "=" * 60)
    print("   PHASE 3: GROUNDED REGIONAL TUTOR EXPLANATION   ")
    print("=" * 60)
    print(f"Language: {language}\n")
    print(state.get("tutor_explanation_localized", "No explanation generated."))

    print("\nRetrieved Grounded RAG Documents:")
    for r in state.get("grounded_resources", []):
        print(f"  - [{r.get('resource_type')}] {r.get('title')} (Est: {r.get('estimated_minutes')} mins)")

    print("\n" + "=" * 60)
    print("   PHASE 4: 7-DAY ADAPTIVE STUDY ROADMAP   ")
    print("=" * 60)
    print(f"Summary: {state.get('plan_summary')}\n")

    for day_item in state.get("study_plan", []):
        print(f"📅 DAY {day_item.get('day')}: {day_item.get('focus_topic')} ({day_item.get('duration_minutes')} mins)")
        for act in day_item.get("activities", []):
            print(f"   • [{act.get('type')}] {act.get('title')} ({act.get('duration_minutes')} mins): {act.get('description')}")
        print()

    # -------------------------------------------------------------------------
    # STEP 4: INTERACTIVE SOCRATIC TUTOR CHAT
    # -------------------------------------------------------------------------
    print("=" * 60)
    print("   INTERACTIVE AI TUTOR CHAT (Type 'exit' or 'quit' to end)   ")
    print("=" * 60 + "\n")

    while True:
        chat_input = input("💬 Ask Tutor a Question: ").strip()
        if not chat_input or chat_input.lower() in ["exit", "quit"]:
            print("\nExiting CLI session. Great work today!")
            break

        chat_res = tutor_chat_node(state, student_message=chat_input)
        state.update(chat_res)
        print(f"\n🤖 Tutor ({language}):\n{chat_res.get('latest_tutor_reply')}\n")


if __name__ == "__main__":
    run_cli()