"""对话接口：接入 LangGraph Agent。"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.agents.graph import run_agent
from app.api.schemas import ChatBody, ChatResult
from app.llm import ChatMessage, ChatRequest, get_llm_provider
from app.services.export_docs import save_bytes
from app.services.knowledge.parser import parse_file

router = APIRouter(prefix="/chat", tags=["chat"])


class AgentChatResult(BaseModel):
    content: str
    intent: str = "general"
    citations: list[dict] = Field(default_factory=list)
    artifacts: list[dict] = Field(default_factory=list)
    model: str = ""
    provider: str = ""


@router.post("/agent", response_model=AgentChatResult)
async def chat_agent(body: ChatBody) -> AgentChatResult:
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    context = body.context or {}
    try:
        result = await run_agent(messages, context=context)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Agent 调用失败: {exc}") from exc

    settings_provider = get_llm_provider()
    return AgentChatResult(
        content=result.get("answer") or "",
        intent=result.get("intent") or "general",
        citations=result.get("citations") or [],
        artifacts=result.get("artifacts") or [],
        provider=settings_provider.name,
        model="",
    )


@router.post("/agent/review-upload", response_model=AgentChatResult)
async def chat_review_upload(
    file: UploadFile = File(...),
    question: str = Form("请对上传材料做初审，给出修改建议和 5 道答辩题"),
):
    """聊天侧上传材料 → 解析正文 → 走 review 意图。"""
    suffix = (file.filename or "x.txt").rsplit(".", 1)[-1].lower()
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "空文件")
    tmp = save_bytes(raw, f"chat_upload_{file.filename or 'x'}.{suffix}", root="./data/uploads")
    try:
        text = parse_file(tmp)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"解析失败: {exc}") from exc

    try:
        result = await run_agent(
            [{"role": "user", "content": question}],
            context={"material_text": text[:12000]},
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Agent 调用失败: {exc}") from exc

    provider = get_llm_provider()
    return AgentChatResult(
        content=result.get("answer") or "",
        intent=result.get("intent") or "review_assist",
        citations=result.get("citations") or [],
        artifacts=result.get("artifacts") or [],
        provider=provider.name,
        model="",
    )


@router.post("", response_model=ChatResult)
async def chat_direct(body: ChatBody) -> ChatResult:
    """直连 LLM（调试用，不走 Agent）。"""
    if body.stream:
        raise HTTPException(status_code=400, detail="请使用 /chat/agent；直连接口暂不支持 stream")

    provider = get_llm_provider()
    request = ChatRequest(
        messages=[ChatMessage(role=m.role, content=m.content) for m in body.messages],
        model=body.model,
        temperature=body.temperature,
    )
    try:
        result = await provider.chat(request)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"LLM 调用失败: {exc}") from exc

    return ChatResult(
        content=result.content,
        model=result.model,
        provider=result.provider,
        usage=result.usage,
    )
