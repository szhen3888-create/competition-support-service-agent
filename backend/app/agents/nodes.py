"""LangGraph 节点：工具增强，知识库作证据而非唯一答案来源。"""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents.prompts import (
    BUDGET_NARRATE_PROMPT,
    GENERAL_PROMPT,
    GRADE_PROMPT,
    INTENT_PROMPT,
    LOAN_NARRATE_PROMPT,
    PREP_PROMPT,
    RAG_ANSWER_PROMPT,
    RECOMMEND_PROMPT,
    REIMBURSE_PROMPT,
    REVIEW_PROMPT,
    REWRITE_PROMPT,
    STATS_NARRATE_PROMPT,
)
from app.agents.state import AgentState
from app.core.config import get_settings
from app.llm import ChatMessage, ChatRequest, get_llm_provider
from app.services.agent_tools import (
    apply_budget_estimates,
    calc_budget_from_nums,
    chart_option_from_stats,
    export_budget_xlsx,
    export_loan_pack,
    export_markdown,
    lookup_competition,
    parse_finance_numbers,
    query_stats,
    search_knowledge,
)
from app.services.finance import build_loan_text, check_reimbursement_materials, detect_finance_kind
from app.services.recommend import (
    build_recommend_draft,
    competition_to_zh,
    extract_profile,
    match_competitions,
    profile_to_text,
)
from app.services.review import parse_required_materials, rule_check

VALID_INTENTS = {
    "knowledge_qa",
    "recommend",
    "prep_assist",
    "review_assist",
    "finance_assist",
    "stats_query",
    "general",
}


def _last_user_question(state: AgentState) -> str:
    if state.get("question"):
        return state["question"]
    for msg in reversed(state.get("messages") or []):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


async def _llm(
    content: str,
    *,
    system: str | None = None,
    temperature: float = 0.2,
    max_tokens: int | None = None,
    model: str | None = None,
) -> str:
    provider = get_llm_provider()
    messages: list[ChatMessage] = []
    if system:
        messages.append(ChatMessage(role="system", content=system))
    messages.append(ChatMessage(role="user", content=content))
    settings = get_settings()
    resp = await provider.chat(
        ChatRequest(
            messages=messages,
            model=model or settings.llm_fast_model,
            temperature=temperature,
            max_tokens=max_tokens or 1024,
        )
    )
    return (resp.content or "").strip()


async def _llm_main(content: str, *, system: str, temperature: float | None = None) -> str:
    settings = get_settings()
    return await _llm(
        content,
        system=system,
        temperature=settings.llm_temperature if temperature is None else temperature,
        max_tokens=settings.llm_max_tokens,
        model=settings.llm_model,
    )


def _format_context(docs: list[dict[str, Any]]) -> str:
    if not docs:
        return "（本次未检索到知识库片段；请结合通用竞赛经验作答，并标注待确认项。）"
    lines: list[str] = []
    for i, d in enumerate(docs, start=1):
        loc = f"p.{d['page']}" if d.get("page") else "全文"
        lines.append(
            f"[{i}] 来源《{d.get('title') or d.get('filename')}》({loc})\n{d.get('content', '')}"
        )
    return "\n\n".join(lines)


def _citations_from_docs(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "index": i,
            "filename": d.get("filename"),
            "title": d.get("title"),
            "page": d.get("page"),
            "score": d.get("score"),
            "snippet": (d.get("content") or "")[:180],
        }
        for i, d in enumerate(docs, start=1)
    ]


_FIELD_ZH = {
    "major_tags": "适合专业",
    "tech_direction": "技术方向",
    "grade_range": "适合年级",
    "register_deadline": "报名截止",
    "award_setting": "奖项设置",
    "materials": "所需材料",
    "description": "简介",
    "category": "类别",
    "competition_name": "竞赛名称",
    "status": "报名状态",
    "fee": "报名费",
}


def _plain_chinese_cleanup(text: str) -> str:
    """把模型偶发吐出的英文字段名洗成人话。"""
    if not text:
        return text
    out = text
    for en, zh in sorted(_FIELD_ZH.items(), key=lambda x: len(x[0]), reverse=True):
        out = re.sub(rf"`{en}`", zh, out)
        out = re.sub(rf"\b{en}\b", zh, out)
    # 「报名费 为 0」类说法
    out = re.sub(r"报名费\s*为\s*0(?:\s*元)?", "报名费免费", out)
    out = re.sub(r"报名费\s*[:=：]\s*0(?:\s*元)?", "报名费免费", out)
    return out


async def classify_intent(state: AgentState) -> dict[str, Any]:
    question = _last_user_question(state)
    ctx = state.get("context") or {}
    if isinstance(ctx, dict) and ctx.get("material_text"):
        return {
            "question": question,
            "intent": "review_assist",
            "rewrite_count": 0,
            "artifacts": [],
        }

    raw = await _llm(INTENT_PROMPT.format(question=question), temperature=0)
    intent = raw.split()[0].strip().lower().strip("`\"'") if raw else "general"
    for key in VALID_INTENTS:
        if key in intent:
            intent = key
            break
    else:
        q = question
        if any(k in q for k in ("统计", "多少人", "获奖", "数据分析", "图表", "可视化", "出图")):
            intent = "stats_query"
        elif any(k in q for k in ("推荐", "适合我", "哪个竞赛", "报什么赛")):
            intent = "recommend"
        elif any(k in q for k in ("备赛", "备赛计划", "任务清单", "材料准备", "时间线", "周计划")):
            intent = "prep_assist"
        elif any(k in q for k in ("初审", "改一改", "答辩", "申报书", "说明书", "作品说明", "修改建议")):
            intent = "review_assist"
        elif any(k in q for k in ("预算", "借款", "报销", "发票", "经费")):
            intent = "finance_assist"
        elif any(k in q for k in ("截止", "报名", "规程", "通知", "材料需要", "奖项设置", "赛制")):
            intent = "knowledge_qa"
        else:
            intent = "general"
    return {"question": question, "intent": intent, "rewrite_count": 0, "artifacts": []}


async def retrieve(state: AgentState) -> dict[str, Any]:
    settings = get_settings()
    query = state.get("rewritten_query") or state.get("question") or ""
    documents = search_knowledge(query, top_k=settings.rag_top_k)
    return {"documents": documents, "needs_rewrite": False, "refuse": False}


async def grade_documents(state: AgentState) -> dict[str, Any]:
    docs = state.get("documents") or []
    question = state.get("question") or ""
    rewrite_count = int(state.get("rewrite_count") or 0)
    settings = get_settings()

    # 无命中：允许再改写一次；已达上限则直接混合生成（不再死循环/拒答）
    if not docs:
        if rewrite_count >= settings.rag_max_rewrite:
            return {"needs_rewrite": False, "refuse": False}
        return {"needs_rewrite": True, "refuse": False}

    context = "\n\n".join(f"[{i}] {d['content'][:400]}" for i, d in enumerate(docs, start=1))
    raw = await _llm(GRADE_PROMPT.format(question=question, context=context), temperature=0)
    token = re.sub(r"[^A-Za-z]", "", (raw.split() or ["NO"])[0]).upper()
    ok = token == "YES" or raw.strip().upper().startswith("YES")
    if ok:
        return {"needs_rewrite": False, "refuse": False}
    if rewrite_count >= settings.rag_max_rewrite:
        # 证据一般也照样生成，由混合 Prompt 处理
        return {"needs_rewrite": False, "refuse": False}
    return {"needs_rewrite": True, "refuse": False}


async def rewrite_question(state: AgentState) -> dict[str, Any]:
    question = state.get("question") or ""
    rewritten = await _llm(REWRITE_PROMPT.format(question=question), temperature=0.3)
    return {
        "rewritten_query": rewritten or question,
        "rewrite_count": int(state.get("rewrite_count") or 0) + 1,
    }


async def generate_rag_answer(state: AgentState) -> dict[str, Any]:
    docs = state.get("documents") or []
    question = state.get("question") or ""
    context = _format_context(docs)
    answer = await _llm_main(
        RAG_ANSWER_PROMPT.format(context=context, question=question),
        system="你是有用的高校竞赛助手：证据优先，不足时用常识补全并标注待确认，禁止空拒答。",
    )
    return {
        "answer": answer,
        "citations": _citations_from_docs(docs) if docs else [],
        "artifacts": state.get("artifacts") or [],
    }


async def stats_answer(state: AgentState) -> dict[str, Any]:
    from app.db.session import SessionLocal

    question = state.get("question") or ""
    year = None
    m = re.search(r"(20\d{2})", question)
    if m:
        year = int(m.group(1))
    major = None
    mm = re.search(r"(软件工程|计算机|人工智能|数据科学|数字媒体|网络工程|物联网|信息安全)[^\s，。,]{0,4}", question)
    if mm:
        major = mm.group(1)

    prefer = "auto"
    if any(k in question for k in ("获奖",)) and any(k in question for k in ("专业", "各专业")):
        prefer = "award_major"
    elif any(k in question for k in ("专业", "各专业")):
        prefer = "major"
    elif any(k in question for k in ("教师", "指导")):
        prefer = "instructor"

    db = SessionLocal()
    try:
        stats = query_stats(db, year=year, major=major)
    finally:
        db.close()

    chart = chart_option_from_stats(stats, prefer=prefer)
    narrate = await _llm_main(
        STATS_NARRATE_PROMPT.format(
            question=question,
            stats=json.dumps(stats, ensure_ascii=False),
        ),
        system="统计数字必须与 JSON 一致，禁止编造。",
        temperature=0.2,
    )
    scope = f"{year} 年" if year else "全部年份"
    if major:
        scope += f" / {major}"
    footer = (
        f"\n\n---\n台账统计范围：{scope}；"
        f"竞赛 {stats['competition_count']}，参赛 {stats['participation_count']}，"
        f"获奖 {stats['award_count']}。"
    )
    artifacts = [
        {
            "type": "chart",
            "title": chart.get("title", {}).get("text") or "竞赛统计图",
            "option": chart,
        }
    ]
    return {
        "answer": narrate + footer,
        "citations": [],
        "artifacts": artifacts,
    }


async def recommend_answer(state: AgentState) -> dict[str, Any]:
    from app.db.session import SessionLocal

    question = state.get("question") or ""
    profile = extract_profile(question)
    docs = search_knowledge(question + " 推荐 适合", top_k=3)
    db = SessionLocal()
    try:
        comps = match_competitions(db, profile)
        draft = build_recommend_draft(profile, comps)
    finally:
        db.close()

    # 先用中文模板保证可读；模型只做润色，若仍夹英文则回退草稿
    polished = await _llm_main(
        RECOMMEND_PROMPT.format(
            profile=profile_to_text(profile),
            draft=draft,
        ),
        system="只做中文润色，不要添加英文字段名。",
        temperature=0.2,
    )
    polished = _plain_chinese_cleanup(polished)
    if re.search(
        r"\b(major_tags|tech_direction|grade_range|register_deadline)\b",
        polished or "",
    ):
        answer = draft
    else:
        answer = polished or draft

    footer = "\n\n---\n数据来源：竞赛台账" + (" + 知识库检索" if docs else "") + "。"
    return {
        "answer": answer + footer,
        "citations": _citations_from_docs(docs),
        "artifacts": [],
    }


async def prep_answer(state: AgentState) -> dict[str, Any]:
    from app.db.session import SessionLocal

    question = state.get("question") or ""
    docs = search_knowledge(question, top_k=5)
    context = _format_context(docs)

    db = SessionLocal()
    try:
        competition = lookup_competition(db, question) or {}
    finally:
        db.close()
    competition_zh = competition_to_zh(competition) if competition else {"说明": "台账暂未匹配到具体竞赛，按通用备赛给出"}

    answer = await _llm_main(
        PREP_PROMPT.format(
            question=question,
            competition=json.dumps(competition_zh, ensure_ascii=False),
            context=context,
        ),
        system="备赛方案要可执行、白话中文；禁止英文字段名；缺失标待确认。",
    )
    artifacts = [export_markdown("备赛计划", answer, prefix="prep")]
    return {
        "answer": answer + "\n\n已生成 Word 备赛计划，可在下方下载。",
        "citations": _citations_from_docs(docs),
        "artifacts": artifacts,
    }


async def review_answer(state: AgentState) -> dict[str, Any]:
    from app.db.session import SessionLocal

    question = state.get("question") or ""
    ctx = state.get("context") or {}
    content = ""
    if isinstance(ctx, dict):
        content = ctx.get("material_text") or ""
    if not content and len(question) > 80:
        content = question

    db = SessionLocal()
    try:
        comp = lookup_competition(db, question)
        required = parse_required_materials((comp or {}).get("materials") if comp else None)
        competition_name = (comp or {}).get("name") or ""
    finally:
        db.close()

    review = rule_check(content or question, required)
    answer = await _llm_main(
        REVIEW_PROMPT.format(
            question=question,
            review=json.dumps(review.to_dict(), ensure_ascii=False),
            content=(content or "（未提供正文，请给出通用结构模板与答辩准备建议）")[:8000],
        ),
        system="材料指导助手：缺失项说清楚；无正文也要给模板与答辩题。",
    )
    if competition_name:
        answer = f"> 对照竞赛：{competition_name}\n\n" + answer
    artifacts = [export_markdown("材料初审报告", answer, prefix="review")]
    return {
        "answer": answer + "\n\n已生成初审报告 Word，可下载。",
        "citations": [],
        "artifacts": artifacts,
    }


async def finance_answer(state: AgentState) -> dict[str, Any]:
    from app.db.session import SessionLocal

    question = state.get("question") or ""
    kind = detect_finance_kind(question)
    nums = parse_finance_numbers(question)

    db = SessionLocal()
    try:
        comp = lookup_competition(db, question)
        competition_name = (comp or {}).get("name") or "（请指定竞赛）"
        if not nums["registration_fee"] and comp and comp.get("fee"):
            nums["registration_fee"] = float(comp["fee"])
        if not nums["location"] and comp and comp.get("location"):
            nums["location"] = str(comp.get("location") or "")
    finally:
        db.close()

    policy_docs = search_knowledge("预算 借款 报销 材料 流程", top_k=3)
    policy_hint = "\n".join(f"- {d['content'][:140]}" for d in policy_docs) if policy_docs else ""

    if kind == "reimbursement":
        provided = [
            x
            for x in ["发票原件", "行程单据", "参赛证明（通知/参赛证）", "批准预算表"]
            if x[:2] in question or x in question
        ]
        if "发票" in question and "发票原件" not in provided:
            provided.append("发票原件")
        if "行程" in question and "行程单据" not in provided:
            provided.append("行程单据")
        if any(k in question for k in ("参赛证", "通知", "参赛证明")):
            if "参赛证明（通知/参赛证）" not in provided:
                provided.append("参赛证明（通知/参赛证）")
        if "预算" in question and "批准预算表" not in provided:
            provided.append("批准预算表")
        check = check_reimbursement_materials(provided)
        answer = await _llm_main(
            REIMBURSE_PROMPT.format(
                question=question,
                check=json.dumps(check.to_dict(), ensure_ascii=False),
            ),
            system="报销助手：不得编造票据与金额；材料不全也要给流程。",
        )
        if policy_hint:
            answer += "\n\n### 政策摘录（知识库）\n" + policy_hint
        artifacts = [export_markdown("报销材料整理", answer, prefix="reimburse")]
        return {
            "answer": answer + "\n\n已生成报销整理 Word。",
            "citations": _citations_from_docs(policy_docs),
            "artifacts": artifacts,
        }

    # 预算 / 借款：缺参时用估算出草稿，而不是只甩模板
    has_any = bool(
        nums.get("people")
        or nums.get("registration_fee")
        or nums.get("transport_per_person")
        or nums.get("lodging_per_person_night")
        or nums.get("location")
    )
    if not has_any or (
        not nums.get("registration_fee")
        and not nums.get("transport_per_person")
        and not nums.get("lodging_per_person_night")
    ):
        nums = apply_budget_estimates(nums)
    elif nums.get("people") and nums.get("location") and (
        not nums.get("registration_fee")
        or (nums.get("location") != "本校" and not nums.get("transport_per_person"))
    ):
        nums = apply_budget_estimates(nums)

    budget = calc_budget_from_nums(competition_name=competition_name, nums=nums)

    if kind == "loan":
        loan_text = build_loan_text(budget, budget_ref=str(nums.get("budget_ref") or ""))
        answer = await _llm_main(
            LOAN_NARRATE_PROMPT.format(question=question, loan_text=loan_text),
            system="借款文案不得改动金额。",
            temperature=0.2,
        )
        answer += "\n\n### 结构化明细（系统计算）\n```json\n" + json.dumps(
            budget.to_dict(), ensure_ascii=False, indent=2
        ) + "\n```"
        artifacts = export_loan_pack(budget, answer)
        return {
            "answer": answer + "\n\n已生成借款 Word 与预算 Excel。",
            "citations": _citations_from_docs(policy_docs),
            "artifacts": artifacts,
        }

    answer = await _llm_main(
        BUDGET_NARRATE_PROMPT.format(
            question=question,
            budget=json.dumps(budget.to_dict(), ensure_ascii=False, indent=2),
        ),
        system="预算文案金额必须与 JSON 一致。",
        temperature=0.2,
    )
    if policy_hint:
        answer += "\n\n### 政策摘录（知识库）\n" + policy_hint
    artifacts = [
        export_markdown("预算申请说明", answer, prefix="budget"),
        export_budget_xlsx(budget.to_dict(), prefix="budget"),
    ]
    tip = ""
    if nums.get("used_estimates"):
        tip = "\n\n> 提示：本草稿含估算项，可回复真实单价让我重算正式稿。"
    return {
        "answer": answer + tip + "\n\n已生成预算 Word 与 Excel。",
        "citations": _citations_from_docs(policy_docs),
        "artifacts": artifacts,
    }


async def general_answer(state: AgentState) -> dict[str, Any]:
    """通用对话：仍可主动检索知识库，回答不弱于直接问 AI。"""
    question = state.get("question") or ""
    messages = state.get("messages") or [{"role": "user", "content": question}]
    docs = search_knowledge(question, top_k=4)
    kb_hint = ""
    if docs:
        kb_hint = "\n\n【供参考的知识库摘录】\n" + _format_context(docs)

    provider = get_llm_provider()
    settings = get_settings()
    system = GENERAL_PROMPT
    if kb_hint:
        system += "\n若摘录相关，请优先使用并引用；无关则可忽略，用你的知识完整回答。"

    chat_messages = [ChatMessage(role="system", content=system)]
    hist = messages[-8:]
    for i, m in enumerate(hist):
        role = m.get("role", "user")
        if role not in {"system", "user", "assistant"}:
            role = "user"
        content = m.get("content", "")
        if role == "user" and i == len(hist) - 1:
            content = question + kb_hint
        chat_messages.append(ChatMessage(role=role, content=content))

    resp = await provider.chat(
        ChatRequest(
            messages=chat_messages,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
    )
    return {
        "answer": (resp.content or "").strip(),
        "citations": _citations_from_docs(docs) if docs else [],
        "artifacts": [],
    }
