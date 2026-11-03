"""Agent 共享状态。"""

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    messages: list[dict[str, str]]
    question: str
    intent: str
    rewritten_query: str
    documents: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]
    answer: str
    needs_rewrite: bool
    rewrite_count: int
    refuse: bool
    context: dict[str, Any]
