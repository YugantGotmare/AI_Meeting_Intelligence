from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.nodes import (
    transcribe, diarize, extract_intelligence,
    quality_check, generate_email, should_retry,
)


def increment_retry(state: AgentState) -> AgentState:
    return {**state, "retry_count": state.get("retry_count", 0) + 1}


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("transcribe", transcribe)
    graph.add_node("diarize", diarize)
    graph.add_node("extract_intelligence", extract_intelligence)
    graph.add_node("quality_check", quality_check)
    graph.add_node("increment_retry", increment_retry)
    graph.add_node("generate_email", generate_email)
    graph.set_entry_point("transcribe")
    graph.add_edge("transcribe", "diarize")
    graph.add_edge("diarize", "extract_intelligence")
    graph.add_edge("extract_intelligence", "quality_check")
    graph.add_conditional_edges(
        "quality_check", should_retry,
        {"retry": "increment_retry", "proceed": "generate_email", "failed": END}
    )
    graph.add_edge("increment_retry", "extract_intelligence")
    graph.add_edge("generate_email", END)
    return graph.compile()


meeting_agent = build_graph()
