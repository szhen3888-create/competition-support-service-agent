"""组队匹配：规则打分 + AI 解释。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import StudentProfile, TeamApplication, TeamEvent, User


def _split_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [x.strip() for x in re.split(r"[,，、/;；\s]+", raw) if x.strip()]


@dataclass
class Candidate:
    user_id: int
    name: str
    major: str
    grade: str
    skills: list[str]
    role_prefs: list[str]
    level: str
    bio: str


def load_pool(db: Session, event: TeamEvent) -> list[Candidate]:
    from sqlalchemy import select

    apps = db.scalars(
        select(TeamApplication).where(
            TeamApplication.event_id == event.id,
            TeamApplication.status.in_(["pending", "accepted"]),
        )
    ).all()
    out: list[Candidate] = []
    for app in apps:
        user = db.get(User, app.student_user_id)
        if not user:
            continue
        profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
        out.append(
            Candidate(
                user_id=user.id,
                name=user.display_name or user.username,
                major=(profile.major if profile else "") or "",
                grade=(profile.grade if profile else "") or "",
                skills=_split_tags(profile.skills if profile else ""),
                role_prefs=_split_tags(profile.role_prefs if profile else ""),
                level=(profile.level_self if profile else "") or "中",
                bio=(profile.bio if profile else "") or "",
            )
        )
    return out


def _level_score(levels: list[str]) -> float:
    # 希望有高有中，避免全是初或全是高垄断
    uniq = set(levels)
    if len(uniq) >= 2:
        return 2.0
    if "中" in uniq:
        return 1.0
    return 0.0


def _role_cover_score(members: list[Candidate], required: list[str]) -> tuple[float, list[str]]:
    if not required:
        return 1.0, []
    covered: set[str] = set()
    for m in members:
        for r in m.role_prefs:
            for need in required:
                if need in r or r in need:
                    covered.add(need)
    missing = [r for r in required if r not in covered]
    ratio = (len(required) - len(missing)) / max(len(required), 1)
    return ratio * 5.0, missing


def _team_score(members: list[Candidate], event: TeamEvent, required: list[str]) -> tuple[float, list[str], list[str]]:
    reasons: list[str] = []
    role_score, missing = _role_cover_score(members, required)
    if missing:
        reasons.append("角色缺口：" + "、".join(missing))
    else:
        reasons.append("角色覆盖较完整")

    # 技能互补：并集越大越好
    skill_union = set()
    for m in members:
        skill_union.update(m.skills)
    skill_score = min(len(skill_union), 8) * 0.6
    reasons.append(f"技能覆盖 {len(skill_union)} 项")

    # 专业与活动名/描述的弱匹配
    blob = (event.competition_name or "") + " " + (event.description or "") + " " + (event.title or "")
    major_hits = sum(1 for m in members if m.major and m.major in blob)
    major_score = major_hits * 0.8
    if major_hits:
        reasons.append(f"{major_hits} 人专业与活动相关")

    level_score = _level_score([m.level for m in members])
    reasons.append("水平搭配：" + "、".join(m.level for m in members))

    grades = {m.grade for m in members if m.grade}
    grade_score = 1.0 if len(grades) >= 2 else 0.3
    total = role_score + skill_score + major_score + level_score + grade_score
    return total, reasons, missing


def match_teams(db: Session, event: TeamEvent) -> dict[str, Any]:
    """贪心组队：按角色覆盖优先凑满 team_size。"""
    pool = load_pool(db, event)
    size = max(int(event.team_size or 3), 2)
    required = _split_tags(event.required_roles)
    remaining = list(pool)
    teams: list[dict[str, Any]] = []
    team_idx = 1

    while len(remaining) >= size:
        # 先选一个「核心」：有稀缺角色或技能多的人
        remaining.sort(key=lambda c: (len(set(c.role_prefs) & set(required)), len(c.skills)), reverse=True)
        seed = remaining.pop(0)
        members = [seed]
        # 逐个补人：优先补缺失角色
        while len(members) < size and remaining:
            missing = _role_cover_score(members, required)[1]
            best_i = 0
            best_gain = -1e9
            for i, cand in enumerate(remaining):
                trial = members + [cand]
                score, _, _miss2 = _team_score(trial, event, required)
                gain = score
                for need in missing:
                    if any(need in r or r in need for r in cand.role_prefs):
                        gain += 3
                if gain > best_gain:
                    best_gain = gain
                    best_i = i
            members.append(remaining.pop(best_i))

        score, reasons, missing = _team_score(members, event, required)
        # 分配建议角色
        used_roles: set[str] = set()
        member_rows = []
        for i, m in enumerate(members):
            role = ""
            for pref in m.role_prefs:
                for need in required:
                    if (need in pref or pref in need) and need not in used_roles:
                        role = need
                        used_roles.add(need)
                        break
                if role:
                    break
            if not role:
                role = m.role_prefs[0] if m.role_prefs else (required[i % len(required)] if required else "队员")
            member_rows.append(
                {
                    "user_id": m.user_id,
                    "name": m.name,
                    "major": m.major,
                    "grade": m.grade,
                    "skills": m.skills,
                    "level": m.level,
                    "suggested_role": role,
                    "is_leader": i == 0,
                }
            )
        teams.append(
            {
                "name": f"第{team_idx}队",
                "score": round(score, 2),
                "reasons": reasons,
                "missing_roles": missing,
                "members": member_rows,
            }
        )
        team_idx += 1

    leftovers = [
        {
            "user_id": c.user_id,
            "name": c.name,
            "major": c.major,
            "grade": c.grade,
            "role_prefs": c.role_prefs,
            "skills": c.skills,
        }
        for c in remaining
    ]
    return {
        "event_id": event.id,
        "team_size": size,
        "required_roles": required,
        "pool_size": len(pool),
        "teams": teams,
        "leftovers": leftovers,
    }


TEAM_EXPLAIN_PROMPT = """你是竞赛组队顾问。下面是【规则引擎给出的组队草案】，报名池学生名单已锁定。

要求：
1. 用白话中文解释每支队伍为什么这样搭（互补、角色、水平）。
2. 对落单同学给出具体建议（并入哪队或等下一轮），禁止虚构不在名单中的学生。
3. 可提出 1-3 条微调建议（例如交换两名队员），但必须点名现有学生。
4. 不要输出英文字段名。

活动信息：
{event}

组队草案 JSON：
{draft}
"""


async def explain_match_with_llm(event: TeamEvent, draft: dict[str, Any]) -> str:
    from app.agents.nodes import _llm_main

    event_text = (
        f"标题：{event.title}\n竞赛：{event.competition_name}\n"
        f"每队人数：{event.team_size}\n需要角色：{event.required_roles}\n说明：{event.description}"
    )
    try:
        return await _llm_main(
            TEAM_EXPLAIN_PROMPT.format(
                event=event_text,
                draft=json.dumps(draft, ensure_ascii=False),
            ),
            system="只解释与微调现有报名池学生，禁止编造人员。",
            temperature=0.3,
        )
    except Exception as exc:  # noqa: BLE001
        return f"（AI 解释暂不可用：{exc}）\n可先按草案分数与角色覆盖人工确认。"
