"""Agent 可调用的工具：检索、找竞赛、统计、经费、导出。

原则：工具给出结构化事实；模型负责解释与规划。金额/统计数字不由模型编造。
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.services.export_docs import budget_to_xlsx, markdownish_to_docx, save_bytes
from app.services.finance import (
    BudgetDraft,
    build_budget,
    build_loan_text,
    check_reimbursement_materials,
)
from app.services.knowledge import get_knowledge_store
from app.services.knowledge.aliases import expand_query, get_alias_map, resolve_aliases
from app.services.recommend import competition_to_dict


# 缺官方单价时的常见区间（仅作估算草稿，须标注）
_ESTIMATE_DEFAULTS = {
    "registration_fee": 200.0,
    "transport_本校": 0.0,
    "transport_省内": 150.0,
    "transport_外省": 450.0,
    "lodging_per_person_night": 180.0,
    "nights_外省": 2,
    "nights_省内": 1,
    "local_transport": 80.0,
}


def search_knowledge(query: str, *, top_k: int = 5) -> list[dict[str, Any]]:
    store = get_knowledge_store()
    hits = store.search(query, top_k=top_k)
    return [
        {
            "id": h.chunk.id,
            "content": h.chunk.content,
            "score": h.score,
            "filename": h.chunk.filename,
            "title": h.chunk.title,
            "page": h.chunk.page,
            "competition": h.chunk.competition,
            "year": h.chunk.year,
            "doc_type": h.chunk.doc_type,
        }
        for h in hits
    ]


def lookup_competition(db: Session, question: str) -> dict[str, Any] | None:
    """按全称 / 简称 / 别名在台账中查找竞赛。"""
    from app.db.models import Competition

    rows = db.scalars(select(Competition).order_by(Competition.year.desc())).all()
    if not rows:
        return None

    q = question or ""
    expanded = expand_query(q)
    alias_names = resolve_aliases(q)

    # 1) 全名包含
    for c in rows:
        if c.name and c.name in q:
            return competition_to_dict(c)

    year_m = re.search(r"(20\d{2})", q)
    year = int(year_m.group(1)) if year_m else None

    scored: list[tuple[int, Any]] = []
    alias_map = get_alias_map()
    for c in rows:
        if year and c.year != year:
            continue
        name = c.name or ""
        score = 0
        if name and len(name) >= 4 and name[:4] in q:
            score += 4
        if name and name in expanded:
            score += 5
        for alias, fulls in alias_map.items():
            if alias in q and any(f in name or alias in name for f in fulls + [alias]):
                score += 3
            if alias in q and (alias in name or any(x in name for x in fulls if len(x) >= 2)):
                score += 3
        for full in alias_names:
            # 别名对应全称与台账名模糊匹配
            key = re.sub(r"[“”\"'\s]", "", full)[:6]
            if key and key in re.sub(r"[“”\"'\s]", "", name):
                score += 4
        if score:
            scored.append((score, c))

    if not scored:
        # 知识库标题兜底：不返回台账，但调用方可另搜 KB
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    return competition_to_dict(scored[0][1])


def query_stats(db: Session, *, year: int | None = None, major: str | None = None) -> dict[str, Any]:
    from app.db.models import Competition, Participation

    c_stmt = select(func.count(Competition.id))
    p_stmt = select(func.count(Participation.id))
    a_stmt = select(func.count(Participation.id)).where(Participation.award_level != "参赛")
    if year:
        c_stmt = c_stmt.where(Competition.year == year)
        p_stmt = p_stmt.where(Participation.year == year)
        a_stmt = a_stmt.where(Participation.year == year)
    if major:
        p_stmt = p_stmt.where(Participation.major.contains(major))
        a_stmt = a_stmt.where(Participation.major.contains(major))

    comps = db.scalar(c_stmt) or 0
    parts = db.scalar(p_stmt) or 0
    awards = db.scalar(a_stmt) or 0

    award_q = select(Participation.award_level, func.count()).group_by(Participation.award_level)
    major_q = select(Participation.major, func.count()).group_by(Participation.major)
    inst_q = (
        select(Participation.instructor, func.count())
        .where(Participation.instructor != "")
        .group_by(Participation.instructor)
        .order_by(func.count().desc())
        .limit(10)
    )
    if year:
        award_q = award_q.where(Participation.year == year)
        major_q = major_q.where(Participation.year == year)
        inst_q = inst_q.where(Participation.year == year)
    if major:
        award_q = award_q.where(Participation.major.contains(major))
        major_q = major_q.where(Participation.major.contains(major))
        inst_q = inst_q.where(Participation.major.contains(major))

    by_award = db.execute(award_q).all()
    by_major = db.execute(major_q).all()
    by_inst = db.execute(inst_q).all()

    award_major_q = (
        select(Participation.major, func.count())
        .where(Participation.award_level != "参赛")
        .group_by(Participation.major)
    )
    if year:
        award_major_q = award_major_q.where(Participation.year == year)
    if major:
        award_major_q = award_major_q.where(Participation.major.contains(major))
    by_award_major = db.execute(award_major_q).all()

    return {
        "year": year,
        "major": major,
        "competition_count": int(comps),
        "participation_count": int(parts),
        "award_count": int(awards),
        "by_award": [{"name": a or "未标注", "value": int(c)} for a, c in by_award],
        "by_major": {
            "categories": [m or "未标注" for m, _ in by_major],
            "values": [int(c) for _, c in by_major],
        },
        "by_award_major": {
            "categories": [m or "未标注" for m, _ in by_award_major],
            "values": [int(c) for _, c in by_award_major],
        },
        "by_instructor": {
            "categories": [i for i, _ in by_inst],
            "values": [int(c) for _, c in by_inst],
        },
    }


def chart_option_from_stats(stats: dict[str, Any], prefer: str = "auto") -> dict[str, Any]:
    """生成可直接给 ECharts 的 option。"""
    year_suffix = f"（{stats.get('year')}）" if stats.get("year") else ""
    if prefer in ("award_major", "获奖专业"):
        bm = stats.get("by_award_major") or stats.get("by_major") or {}
        return {
            "title": {"text": f"各专业获奖人次{year_suffix}", "left": "center"},
            "color": ["#0f766e"],
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": bm.get("categories") or [], "axisLabel": {"rotate": 30}},
            "yAxis": {"type": "value"},
            "series": [{"type": "bar", "data": bm.get("values") or []}],
        }
    if prefer in ("major", "专业"):
        bm = stats.get("by_major") or {}
        return {
            "title": {"text": f"各专业参赛人次{year_suffix}", "left": "center"},
            "color": ["#0f766e"],
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": bm.get("categories") or [], "axisLabel": {"rotate": 30}},
            "yAxis": {"type": "value"},
            "series": [{"type": "bar", "data": bm.get("values") or []}],
        }
    if prefer in ("instructor", "教师", "指导"):
        bi = stats.get("by_instructor") or {}
        return {
            "title": {"text": "指导教师指导量 Top", "left": "center"},
            "color": ["#c46b2d"],
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": bi.get("categories") or [], "axisLabel": {"rotate": 30}},
            "yAxis": {"type": "value"},
            "series": [{"type": "bar", "data": bi.get("values") or []}],
        }
    # default award pie
    return {
        "title": {"text": f"奖项分布" + (f"（{stats.get('year')}）" if stats.get("year") else ""), "left": "center"},
        "color": ["#0f766e", "#c46b2d", "#1b3554", "#59a5a0", "#d9a066"],
        "tooltip": {"trigger": "item"},
        "series": [{"type": "pie", "radius": ["40%", "65%"], "data": stats.get("by_award") or []}],
    }


def parse_finance_numbers(text: str) -> dict[str, Any]:
    def _num(patterns: list[str], default: float = 0.0) -> float:
        for p in patterns:
            m = re.search(p, text)
            if m:
                return float(m.group(1))
        return default

    people = int(_num([r"(\d+)\s*人", r"人数[:：\s]*(\d+)"], 0))
    nights = int(_num([r"(\d+)\s*晚", r"住宿\s*(\d+)"], 0))
    fee = _num([r"报名费[:：\s]*(\d+(?:\.\d+)?)", r"报名[:：\s]*(\d+(?:\.\d+)?)元"])
    transport = _num([r"交通[:：\s]*(\d+(?:\.\d+)?)", r"往返[:：\s]*(\d+(?:\.\d+)?)"])
    lodging = _num([r"住宿[:：\s]*(\d+(?:\.\d+)?)", r"房费[:：\s]*(\d+(?:\.\d+)?)", r"每晚[:：\s]*(\d+(?:\.\d+)?)"])
    local = _num([r"市内交通[:：\s]*(\d+(?:\.\d+)?)"])
    other = _num([r"其他[:：\s]*(\d+(?:\.\d+)?)"])
    location = ""
    lm = re.search(r"地点[:：\s]*([^\s，,。]+)", text)
    if lm:
        location = lm.group(1)
    elif "外省" in text:
        location = "外省"
    elif "省内" in text:
        location = "省内"
    elif "本校" in text or "校内" in text:
        location = "本校"
    budget_ref = ""
    bm = re.search(r"(?:预算文号|批准文号|文号)[:：\s]*([A-Za-z0-9\-_/]+)", text)
    if bm:
        budget_ref = bm.group(1)
    return {
        "people": people,
        "nights": nights,
        "registration_fee": fee,
        "transport_per_person": transport,
        "lodging_per_person_night": lodging,
        "local_transport": local,
        "other": other,
        "location": location,
        "budget_ref": budget_ref,
        "used_estimates": False,
        "estimate_notes": [],
    }


def apply_budget_estimates(nums: dict[str, Any]) -> dict[str, Any]:
    """在缺单价时填入常见估算值，并标记。"""
    out = dict(nums)
    notes: list[str] = list(out.get("estimate_notes") or [])
    loc = str(out.get("location") or "")
    used = False

    if not out.get("people"):
        out["people"] = 3
        notes.append("人数未提供，暂按 3 人估算")
        used = True

    if not loc:
        out["location"] = "外省"
        loc = "外省"
        notes.append("地点未提供，暂按外省估算")
        used = True

    if not out.get("registration_fee"):
        out["registration_fee"] = _ESTIMATE_DEFAULTS["registration_fee"]
        notes.append(f"报名费未提供，暂按 {_ESTIMATE_DEFAULTS['registration_fee']:.0f} 元/人估算")
        used = True

    if not out.get("transport_per_person"):
        key = f"transport_{loc}" if f"transport_{loc}" in _ESTIMATE_DEFAULTS else "transport_外省"
        if loc == "本校":
            key = "transport_本校"
        elif loc == "省内":
            key = "transport_省内"
        else:
            key = "transport_外省"
        out["transport_per_person"] = _ESTIMATE_DEFAULTS[key]
        notes.append(f"交通费未提供，暂按 {out['transport_per_person']:.0f} 元/人估算（{loc}）")
        used = True

    if loc != "本校":
        if not out.get("lodging_per_person_night"):
            out["lodging_per_person_night"] = _ESTIMATE_DEFAULTS["lodging_per_person_night"]
            notes.append(
                f"住宿单价未提供，暂按 {_ESTIMATE_DEFAULTS['lodging_per_person_night']:.0f} 元/人·晚估算"
            )
            used = True
        if not out.get("nights"):
            out["nights"] = _ESTIMATE_DEFAULTS["nights_外省"] if loc == "外省" else _ESTIMATE_DEFAULTS["nights_省内"]
            notes.append(f"住宿晚数未提供，暂按 {out['nights']} 晚估算")
            used = True
        if not out.get("local_transport"):
            out["local_transport"] = _ESTIMATE_DEFAULTS["local_transport"]
            notes.append(f"市内交通未提供，暂按 {_ESTIMATE_DEFAULTS['local_transport']:.0f} 元估算")
            used = True

    out["used_estimates"] = used
    out["estimate_notes"] = notes
    return out


def calc_budget_from_nums(
    *,
    competition_name: str,
    nums: dict[str, Any],
) -> BudgetDraft:
    draft = build_budget(
        competition_name=competition_name,
        people=int(nums.get("people") or 0),
        location=str(nums.get("location") or ""),
        registration_fee=float(nums.get("registration_fee") or 0),
        transport_per_person=float(nums.get("transport_per_person") or 0),
        lodging_per_person_night=float(nums.get("lodging_per_person_night") or 0),
        nights=int(nums.get("nights") or 0),
        local_transport=float(nums.get("local_transport") or 0),
        other=float(nums.get("other") or 0),
    )
    if nums.get("used_estimates"):
        draft.assumptions = list(draft.assumptions) + [
            "以下含估算项，非正式学院标准，提交前请核对："
        ] + list(nums.get("estimate_notes") or [])
    return draft


def export_markdown(title: str, body: str, prefix: str = "draft") -> dict[str, str]:
    path = save_bytes(markdownish_to_docx(title, body), f"{prefix}_{uuid.uuid4().hex[:8]}.docx")
    return {
        "type": "file",
        "title": title,
        "filename": path.name,
        "url": f"/api/v1/exports/{path.name}",
    }


def export_budget_xlsx(budget: dict[str, Any], prefix: str = "budget") -> dict[str, str]:
    path = save_bytes(budget_to_xlsx(budget), f"{prefix}_{uuid.uuid4().hex[:8]}.xlsx")
    return {
        "type": "file",
        "title": "预算明细 Excel",
        "filename": path.name,
        "url": f"/api/v1/exports/{path.name}",
    }


def export_loan_pack(budget: BudgetDraft, loan_text: str) -> list[dict[str, str]]:
    arts = [
        export_markdown("借款申请说明", loan_text, prefix="loan"),
        export_budget_xlsx(budget.to_dict(), prefix="loan_budget"),
    ]
    return arts


def safe_export_path(filename: str) -> Path | None:
    root = Path("./data/exports").resolve()
    root.mkdir(parents=True, exist_ok=True)
    name = Path(filename).name
    if not name or name.startswith("."):
        return None
    path = (root / name).resolve()
    if not str(path).startswith(str(root)):
        return None
    return path if path.exists() else None
