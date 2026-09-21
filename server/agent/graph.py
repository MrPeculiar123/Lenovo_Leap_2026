"""
LangGraph Workflow Architecture (PathForge Core Orchestrator)
=============================================================
Compiles the multi-agent adaptive learning pipeline into an executable StateGraph:

1. Assessment Node: Serves adaptive diagnostic questions calibrated by 2-PL IRT.
2. Evaluate Answer Node: Deterministically updates latent ability (theta) & BKT mastery.
3. Gap & Career Node: Evaluates career benchmarks + traverses DAG for prerequisite root causes.
4. Content & Regional Tutor Node: RAG retrieval from Pinecone + code-switched localized explanation.
5. Planning Node: Synthesizes 7-day adaptive roadmap adhering to daily time constraints.
"""

from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END

try:
    from agent.state import StudentState
    from agent.nodes.assessment import assessment_node, record_answer_node
    from agent.nodes.gap_career import gap_career_node
    from agent.nodes.content_tutor import content_tutor_node
    from agent.nodes.planning import planning_node
except ImportError:
    from server.agent.state import StudentState
    from server.agent.nodes.assessment import assessment_node, record_answer_node
    from server.agent.nodes.gap_career import gap_career_node
    from server.agent.nodes.content_tutor import content_tutor_node
    from server.agent.nodes.planning import planning_node


# =============================================================================
# ROUTING & CONDITIONAL EDGE LOGIC
# =============================================================================

def route_after_assessment(state: StudentState) -> Literal["gap_career", "evaluate_answer", "__end__"]:
    """
    Decides whether to proceed to gap analysis, evaluate an answer, or wait for student answer.
    """
    if state.get("is_assessment_complete", False):
        return "gap_career"
    if state.get("current_question", {}).get("student_answer"):
        return "evaluate_answer"
    return "__end__"


def route_after_answer_eval(state: StudentState) -> Literal["gap_career", "assessment"]:
    """
    Decides whether the assessment has concluded or needs another question.
    """
    if state.get("is_assessment_complete", False):
        return "gap_career"
    return "assessment"


# =============================================================================
# GRAPH COMPILATION FACTORIES
# =============================================================================

def create_adaptive_learning_graph():
    """
    Compiles the Master LangGraph StateGraph connecting all 5 agent nodes.
    Supports both step-by-step adaptive testing and autonomous remediation planning.
    """
    workflow = StateGraph(StudentState)

    # 1. Register Nodes
    workflow.add_node("assessment", assessment_node)
    workflow.add_node("evaluate_answer", record_answer_node)
    workflow.add_node("gap_career", gap_career_node)
    workflow.add_node("content_tutor", content_tutor_node)
    workflow.add_node("planning", planning_node)

    # 2. Entry Point
    workflow.set_entry_point("assessment")

    # 3. Assessment & Grading Edges
    workflow.add_conditional_edges(
        "assessment",
        route_after_assessment,
        {
            "gap_career": "gap_career",
            "evaluate_answer": "evaluate_answer",
            "__end__": END
        }
    )

    workflow.add_conditional_edges(
        "evaluate_answer",
        route_after_answer_eval,
        {
            "gap_career": "gap_career",
            "assessment": "assessment"
        }
    )

    # 4. Remediation Pipeline (Linear Chain: Gap/Career -> Content/Tutor -> Planner -> END)
    workflow.add_edge("gap_career", "content_tutor")
    workflow.add_edge("content_tutor", "planning")
    workflow.add_edge("planning", END)

    return workflow.compile()


def create_remediation_pipeline_graph():
    """
    Specialized lightweight sub-graph for running the post-assessment
    remediation pipeline directly: Gap Analysis -> Content/Tutor -> Planning.
    """
    workflow = StateGraph(StudentState)

    workflow.add_node("gap_career", gap_career_node)
    workflow.add_node("content_tutor", content_tutor_node)
    workflow.add_node("planning", planning_node)

    workflow.set_entry_point("gap_career")
    workflow.add_edge("gap_career", "content_tutor")
    workflow.add_edge("content_tutor", "planning")
    workflow.add_edge("planning", END)

    return workflow.compile()


# Global compiled graph instances
adaptive_learning_graph = create_adaptive_learning_graph()
remediation_pipeline = create_remediation_pipeline_graph()


# =============================================================================
# HIGH-LEVEL RUNNER CONVENIENCE HELPERS
# =============================================================================

def run_remediation_pipeline(state: StudentState) -> StudentState:
    """Runs Gap Analysis -> Regional Tutor -> Study Planner in one execution pass."""
    return remediation_pipeline.invoke(state)


def run_next_assessment_step(state: StudentState) -> StudentState:
    """Generates the next adaptive diagnostic question."""
    result = assessment_node(state)
    updated_state = dict(state)
    updated_state.update(result)
    return updated_state


def submit_assessment_answer(
    state: StudentState,
    student_answer: str,
    response_time_sec: float = 20.0
) -> StudentState:
    """
    Grades student answer, updates ML ability, and if complete, runs the full
    remediation pipeline automatically.
    """
    current_q = state.get("current_question")
    if not current_q:
        raise ValueError("Cannot submit answer: no active question found in state.")

    current_q_copy = dict(current_q)
    current_q_copy["student_answer"] = student_answer
    current_q_copy["response_time_sec"] = response_time_sec

    eval_state = dict(state)
    eval_state["current_question"] = current_q_copy

    eval_res = record_answer_node(eval_state)
    eval_state.update(eval_res)

    # If the test just finished, trigger the remediation pipeline
    if eval_state.get("is_assessment_complete"):
        final_state = run_remediation_pipeline(eval_state)
        eval_state.update(final_state)

    return eval_state

