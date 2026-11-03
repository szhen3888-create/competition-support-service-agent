"""
竞赛辅助主编排图（覆盖全部业务意图）。

classify_intent
  ├ knowledge_qa  → retrieve → grade → rewrite? → generate
  ├ recommend     → recommend_answer
  ├ prep_assist   → prep_answer
  ├ review_assist → review_answer
  ├ finance_assist→ finance_answer
  ├ stats_query   → stats_answer
  └ general       → general_answer
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    classify_intent,
    finance_answer,
    general_answer,
    generate_rag_answer,
    grade_documents,
    prep_answer,
    recommend_answer,
    retrieve,
    review_answer,
    rewrite_question,
    stats_answer,
)
from app.agents.state import AgentState

IntentRoute = Literal[
    "retrieve",
    "recommend",
    "prep",
    "review",
    "finance",
    "stats",
    "general",
]


def _route_by_intent(state: AgentState) -> IntentRoute:
    mapping: dict[str, IntentRoute] = {
        "knowledge_qa": "retrieve",
        "recommend": "recommend",
        "prep_assist": "prep",
        "review_assist": "review",
        "finance_assist": "finance",
        "stats_query": "stats",
        "general": "general",
    }
    return mapping.get(state.get("intent") or "general", "general")


def _route_after_grade(state: AgentState) -> Literal["rewrite", "generate"]:
    return "rewrite" if state.get("needs_rewrite") else "generate"


def build_agent_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("rewrite_question", rewrite_question)
    workflow.add_node("generate_rag_answer", generate_rag_answer)
    workflow.add_node("recommend_answer", recommend_answer)
    workflow.add_node("prep_answer", prep_answer)
    workflow.add_node("review_answer", review_answer)
    workflow.add_node("finance_answer", finance_answer)
    workflow.add_node("stats_answer", stats_answer)
    workflow.add_node("general_answer", general_answer)

    workflow.add_edge(START, "classify_intent")
    workflow.add_conditional_edges(
        "classify_intent",
        _route_by_intent,
        {
            "retrieve": "retrieve",
            "recommend": "recommend_answer",
            "prep": "prep_answer",
            "review": "review_answer",
            "finance": "finance_answer",
            "stats": "stats_answer",
            "general": "general_answer",
        },
    )
    workflow.add_edge("retrieve", "grade_documents")
    workflow.add_conditional_edges(
        "grade_documents",
        _route_after_grade,
        {"rewrite": "rewrite_question", "generate": "generate_rag_answer"},
    )
    workflow.add_edge("rewrite_question", "retrieve")
    for node in (
        "generate_rag_answer",
        "recommend_answer",
        "prep_answer",
        "review_answer",
        "finance_answer",
        "stats_answer",
        "general_answer",
    ):
        workflow.add_edge(node, END)

    return workflow.compile()


@lru_cache
def get_agent_graph():
    return build_agent_graph()


def reset_agent_graph() -> None:
    get_agent_graph.cache_clear()


async def run_agent(
    messages: list[dict[str, str]],
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    graph = get_agent_graph()
    question = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            question = m.get("content", "")
            break
    result = await graph.ainvoke(
        {
            "messages": messages,
            "question": question,
            "rewrite_count": 0,
            "context": context or {},
            "artifacts": [],
        }
    )
    return {
        "answer": result.get("answer", ""),
        "intent": result.get("intent", "general"),
        "citations": result.get("citations") or [],
        "documents": result.get("documents") or [],
        "artifacts": result.get("artifacts") or [],
    }
