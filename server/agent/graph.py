"""LangGraph workflow construction and assessment helpers."""

from typing import Any, Dict, Literal, Optional

from langgraph.graph import END, StateGraph

try:
    from services.checkpoint_store import checkpoint_state, get_checkpointer
    from agent.state import StudentState
    from agent.nodes.assessment import assessment_node, record_answer_node
    from agent.nodes.gap_career import gap_career_node
    from agent.nodes.content_tutor import content_tutor_node
    from agent.nodes.planning import planning_node
except ImportError:
    from server.services.checkpoint_store import checkpoint_state, get_checkpointer
    from server.agent.state import StudentState
    from server.agent.nodes.assessment import assessment_node, record_answer_node
    from server.agent.nodes.gap_career import gap_career_node
    from server.agent.nodes.content_tutor import content_tutor_node
    from server.agent.nodes.planning import planning_node


def route_after_assessment(state: StudentState) -> Literal["gap_career", "evaluate_answer", "__end__"]:
    if state.get("is_assessment_complete", False):
        return "gap_career"
    if state.get("current_question", {}).get("student_answer"):
        return "evaluate_answer"
    return "__end__"


def route_after_answer_eval(state: StudentState) -> Literal["gap_career", "assessment", "__end__"]:
    if state.get("pause_after_evaluation") and not state.get("is_assessment_complete", False):
        return "__end__"
    return "gap_career" if state.get("is_assessment_complete", False) else "assessment"


def _workflow() -> StateGraph:
    workflow = StateGraph(StudentState)
    workflow.add_node("assessment", assessment_node)
    workflow.add_node("evaluate_answer", record_answer_node)
    workflow.add_node("gap_career", gap_career_node)
    workflow.add_node("content_tutor", content_tutor_node)
    workflow.add_node("planning", planning_node)
    workflow.set_entry_point("assessment")
    workflow.add_conditional_edges(
        "assessment",
        route_after_assessment,
        {"gap_career": "gap_career", "evaluate_answer": "evaluate_answer", "__end__": END},
    )
    workflow.add_conditional_edges(
        "evaluate_answer",
        route_after_answer_eval,
        {"gap_career": "gap_career", "assessment": "assessment", "__end__": END},
    )
    workflow.add_edge("gap_career", "content_tutor")
    workflow.add_edge("content_tutor", "planning")
    workflow.add_edge("planning", END)
    return workflow


def _remediation_workflow() -> StateGraph:
    workflow = StateGraph(StudentState)
    workflow.add_node("gap_career", gap_career_node)
    workflow.add_node("content_tutor", content_tutor_node)
    workflow.add_node("planning", planning_node)
    workflow.set_entry_point("gap_career")
    workflow.add_edge("gap_career", "content_tutor")
    workflow.add_edge("content_tutor", "planning")
    workflow.add_edge("planning", END)
    return workflow


def create_adaptive_learning_graph():
    return _workflow().compile(checkpointer=get_checkpointer())


def create_remediation_pipeline_graph():
    return _remediation_workflow().compile(checkpointer=get_checkpointer())


adaptive_learning_graph = None
remediation_pipeline = None


def initialize_graphs() -> None:
    global adaptive_learning_graph, remediation_pipeline
    adaptive_learning_graph = create_adaptive_learning_graph()
    remediation_pipeline = create_remediation_pipeline_graph()


def get_adaptive_learning_graph():
    if adaptive_learning_graph is None:
        raise RuntimeError("LangGraph graphs have not been initialized")
    return adaptive_learning_graph


def _direct_remediation(state: StudentState) -> StudentState:
    result = dict(state)
    for node in (gap_career_node, content_tutor_node, planning_node):
        result.update(node(result))
    return result


def run_remediation_pipeline(state: StudentState) -> StudentState:
    """Runs the deterministic helper path used by scripts and unit tests."""
    return _direct_remediation(state)


async def run_remediation_pipeline_async(
    state: StudentState,
    config: Optional[Dict[str, Any]] = None,
) -> StudentState:
    if config is None:
        return _direct_remediation(state)
    if remediation_pipeline is None:
        raise RuntimeError("LangGraph graphs have not been initialized")
    return await remediation_pipeline.ainvoke(state, config=config)


async def load_persisted_state(thread_id: str) -> Optional[StudentState]:
    return await checkpoint_state(thread_id)

async def update_persisted_state(thread_id: str, updates: Dict[str, Any]) -> Optional[StudentState]:
    """Persist a bounded partial state update through the official graph API."""
    graph = get_adaptive_learning_graph()
    await graph.aupdate_state({"configurable": {"thread_id": thread_id}}, updates)
    return await checkpoint_state(thread_id)

async def persist_tutor_history(thread_id: str, history: list[Dict[str, str]]) -> Optional[StudentState]:
    return await update_persisted_state(thread_id, {"tutor_chat_history": history[-10:]})
def run_next_assessment_step(state: StudentState) -> StudentState:
    result = assessment_node(state)
    updated_state = dict(state)
    updated_state.update(result)
    return updated_state


def submit_assessment_answer(
    state: StudentState,
    student_answer: str,
    response_time_sec: float = 20.0,
) -> StudentState:
    current_q = state.get("current_question")
    if not current_q:
        raise ValueError("Cannot submit answer: no active question found in state.")
    current_q_copy = dict(current_q)
    current_q_copy["student_answer"] = student_answer
    current_q_copy["response_time_sec"] = response_time_sec
    eval_state = dict(state)
    eval_state["current_question"] = current_q_copy
    eval_state.update(record_answer_node(eval_state))
    if eval_state.get("is_assessment_complete"):
        eval_state.update(_direct_remediation(eval_state))
    return eval_state
