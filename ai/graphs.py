"""LangGraph graphs wiring the agents together."""

from langgraph.graph import StateGraph

from ai.agents import ai_evaluation_agent, ai_recommendation_agent, jd_analyzer, resume_parser
from models.state import HiringState


# -------------------------------------------------
# LANGGRAPH — extraction and explanation nodes only; scoring happens
# between jd_analyzer and as a plain deterministic function
# call (see evaluate_candidate), not as a graph node, so it never touches
# the LLM.
# -------------------------------------------------
extraction_builder = StateGraph(HiringState)
extraction_builder.add_node("resume_parser", resume_parser)
extraction_builder.set_entry_point("resume_parser")
extraction_builder.set_finish_point("resume_parser")
resume_extraction_graph = extraction_builder.compile()

jd_builder = StateGraph(HiringState)
jd_builder.add_node("jd_analyzer", jd_analyzer)
jd_builder.set_entry_point("jd_analyzer")
jd_builder.set_finish_point("jd_analyzer")
jd_extraction_graph = jd_builder.compile()

explanation_builder = StateGraph(HiringState)
explanation_builder.add_node("ai_evaluation_agent", ai_evaluation_agent)
explanation_builder.add_node("ai_recommendation_agent", ai_recommendation_agent)

explanation_builder.set_entry_point("ai_evaluation_agent")
explanation_builder.add_edge("ai_evaluation_agent", "ai_recommendation_agent")

explanation_builder.set_finish_point("ai_recommendation_agent")
explanation_graph = explanation_builder.compile()
