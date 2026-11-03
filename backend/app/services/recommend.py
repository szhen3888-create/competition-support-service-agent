"""竞赛推荐：先结构化匹配台账，再用 LLM 解释（不编造不存在的竞赛）。"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Competition


def extract_profile(text: str) -> dict[str, str]:
    major = ""
    grade = ""
    direction = ""

    m = re.search(r"(软件工程|计算机|人工智能|数据科学|数字媒体|网络工程|物联网|信息安全)[^\s，。,]{0,6}", text)
    if m:
        major = m.group(1)

    g = re.search(r"(大[一二三四]|研[一二三]|本科|研究生)", text)
    if g:
        grade = g.group(1)

    d = re.search(r"(算法|编程|软件应用|人工智能|大数据|嵌入式|前端|后端|全栈|机器学习|深度学习)", text)
    if d:
        direction = d.group(1)

    return {"major": major, "grade": grade, "direction": direction}


def match_competitions(db: Session, profile: dict[str, str], limit: int = 8) -> list[Competition]:
    rows = db.scalars(select(Competition).order_by(Competition.year.desc(), Competition.id.desc())).all()
    scored: list[tuple[int, Competition]] = []
    major = profile.get("major") or ""
    grade = profile.get("grade") or ""
    direction = profile.get("direction") or ""

    for c in rows:
        score = 0
        tags = (c.major_tags or "") + " " + (c.name or "")
        if major and major in tags:
            score += 3
        if direction and (direction in (c.tech_direction or "") or direction in (c.name or "") or direction in tags):
            score += 2
        if grade and grade in (c.grade_range or ""):
            score += 1
        if c.status == "报名中":
            score += 1
        if score > 0 or (not major and not direction):
            # 无画像时仍返回近期竞赛，但标记低分
            scored.append((score if score > 0 else 0, c))

    scored.sort(key=lambda x: (x[0], x[1].year), reverse=True)
    # 有匹配分优先；若全 0 则取前 limit 条近期
    positive = [c for s, c in scored if s > 0]
    if positive:
        return positive[:limit]
    return [c for _, c in scored[:limit]]


def competition_to_dict(c: Competition) -> dict[str, Any]:
    return {
        "id": c.id,
        "name": c.name,
        "year": c.year,
        "level": c.level,
        "category": c.category,
        "major_tags": c.major_tags,
        "grade_range": c.grade_range,
        "tech_direction": c.tech_direction,
        "register_deadline": c.register_deadline.isoformat() if c.register_deadline else None,
        "fee": c.fee,
        "status": c.status,
        "materials": c.materials,
        "award_setting": c.award_setting,
        "description": c.description,
    }


def competition_to_zh(c: Competition | dict[str, Any]) -> dict[str, Any]:
    """给人读的中文字段，避免模型把英文字段名念出来。"""
    if not isinstance(c, dict):
        d = competition_to_dict(c)
    else:
        d = c
    fee = d.get("fee")
    if fee is None or fee == "" or float(fee or 0) == 0:
        fee_text = "免费"
    else:
        fee_text = f"{fee} 元"
    return {
        "竞赛名称": d.get("name") or "",
        "年份": d.get("year"),
        "级别": d.get("level") or "",
        "类别": d.get("category") or "",
        "适合专业": d.get("major_tags") or "",
        "适合年级": d.get("grade_range") or "",
        "技术方向": d.get("tech_direction") or "",
        "报名截止": d.get("register_deadline") or "未标注",
        "报名费": fee_text,
        "报名状态": d.get("status") or "",
        "所需材料": d.get("materials") or "",
        "奖项设置": d.get("award_setting") or "",
        "简介": d.get("description") or "",
    }


def profile_to_zh(profile: dict[str, str]) -> dict[str, str]:
    return {
        "专业": profile.get("major") or "未说明",
        "年级": profile.get("grade") or "未说明",
        "方向兴趣": profile.get("direction") or "未说明",
    }


def profile_to_text(profile: dict[str, str]) -> str:
    z = profile_to_zh(profile)
    return f"专业：{z['专业']}；年级：{z['年级']}；方向兴趣：{z['方向兴趣']}"


def competition_to_text(c: Competition | dict[str, Any], index: int | None = None) -> str:
    z = competition_to_zh(c)
    head = f"{index}. " if index is not None else ""
    lines = [
        f"{head}{z['竞赛名称']}（{z['年份']}，{z['级别'] or '级别未标注'}）",
        f"  适合专业：{z['适合专业'] or '未标注'}",
        f"  适合年级：{z['适合年级'] or '未标注'}",
        f"  技术方向：{z['技术方向'] or '未标注'}",
        f"  报名状态：{z['报名状态'] or '未标注'}；报名截止：{z['报名截止']}；报名费：{z['报名费']}",
    ]
    if z.get("所需材料"):
        lines.append(f"  所需材料：{z['所需材料']}")
    if z.get("奖项设置"):
        lines.append(f"  奖项设置：{z['奖项设置']}")
    if z.get("简介"):
        lines.append(f"  简介：{z['简介']}")
    return "\n".join(lines)


def build_recommend_draft(profile: dict[str, str], comps: list[Competition], limit: int = 5) -> str:
    """用中文模板生成推荐草稿，避免模型照抄英文字段。"""
    lines = [
        "## 1. 推荐排序",
        "",
    ]
    for i, c in enumerate(comps[:limit], start=1):
        z = competition_to_zh(c)
        lines.append(f"{i}. **{z['竞赛名称']}**（{z['年份']}，{z['级别'] or '级别未标注'}）")
    if not comps:
        lines.append("（台账暂无匹配竞赛，请先录入竞赛台账或换个专业关键词）")

    lines += ["", "## 2. 推荐理由", ""]
    major = profile.get("major") or ""
    grade = profile.get("grade") or ""
    direction = profile.get("direction") or ""

    for i, c in enumerate(comps[:limit], start=1):
        z = competition_to_zh(c)
        lines.append(f"**{i}）{z['竞赛名称']}（{z['年份']}）**")
        if z["适合专业"]:
            if major and major in z["适合专业"]:
                lines.append(f"- 和你的专业匹配：台账写明适合「{z['适合专业']}」，包含你的「{major}」。")
            else:
                lines.append(f"- 适合专业方向：{z['适合专业']}。")
        if z["技术方向"]:
            if direction and direction in z["技术方向"]:
                lines.append(f"- 技术方向对口：偏「{z['技术方向']}」，和你关注的「{direction}」一致。")
            else:
                lines.append(f"- 技术方向：{z['技术方向']}。")
        if z["适合年级"]:
            if grade and grade in z["适合年级"]:
                lines.append(f"- 年级合适：适合「{z['适合年级']}」，覆盖你当前的「{grade}」。")
            else:
                lines.append(f"- 适合年级：{z['适合年级']}" + ("；你未填写年级，可对照确认。" if not grade else "。"))
        status = z["报名状态"] or ""
        if "报名" in status:
            lines.append(f"- 当前可报名：状态为「{status}」，截止时间 {z['报名截止']}。")
        elif "结束" in status or "已结束" in status:
            lines.append(f"- 本届已结束：截止时间 {z['报名截止']}，建议关注下一届通知，可先当备赛目标。")
        else:
            lines.append(f"- 报名情况：{status or '未标注'}；截止时间 {z['报名截止']}。")
        lines.append(f"- 报名费：{z['报名费']}。")
        if z["奖项设置"]:
            lines.append(f"- 奖项设置：{z['奖项设置']}。")
        lines.append("")

    lines += ["## 3. 下一步建议", ""]
    open_ones = [competition_to_zh(c) for c in comps[:limit] if "报名" in (competition_to_zh(c).get("报名状态") or "")]
    if open_ones:
        first = open_ones[0]
        lines.append(
            f"- 优先关注正在报名的「{first['竞赛名称']}」，在 {first['报名截止']} 前准备材料。"
        )
        if first.get("所需材料"):
            lines.append(f"- 建议准备：{first['所需材料']}。")
    else:
        lines.append("- 当前列表里可报名赛事较少，建议关注校内通知或下一届开放时间。")
    lines.append("- 若你补充年级（如大二）和方向（如算法/大模型），我可以再帮你收窄推荐。")
    return "\n".join(lines)
