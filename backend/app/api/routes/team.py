"""智能组队 API。"""

from __future__ import annotations

import json
import uuid
from datetime import date
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_student, require_teacher
from app.db.models import (
    Competition,
    Participation,
    StudentProfile,
    Team,
    TeamApplication,
    TeamEvent,
    TeamMember,
    User,
)
from app.db.session import get_db
from app.services.export_docs import save_bytes
from app.services.team_match import explain_match_with_llm, load_pool, match_teams

router = APIRouter(prefix="/team", tags=["team"])


# ---------- schemas ----------


class ProfileBody(BaseModel):
    major: str = ""
    grade: str = ""
    skills: str = ""
    role_prefs: str = ""
    level_self: str = "中"
    available_time: str = ""
    interest_competitions: str = ""
    bio: str = ""


class EventCreate(BaseModel):
    title: str
    competition_id: int | None = None
    competition_name: str = ""
    team_size: int = Field(default=3, ge=2, le=10)
    required_roles: str = "算法,开发,写材料"
    description: str = ""
    deadline: date | None = None


class ApplyBody(BaseModel):
    note: str = ""


class MemberPatch(BaseModel):
    student_user_id: int
    suggested_role: str = ""
    is_leader: bool = False


class TeamPatch(BaseModel):
    name: str | None = None
    members: list[MemberPatch] | None = None


class ConfirmBody(BaseModel):
    sync_ledger: bool = False


def _profile_dict(p: StudentProfile | None) -> dict:
    if not p:
        return {}
    return {
        "major": p.major,
        "grade": p.grade,
        "skills": p.skills,
        "role_prefs": p.role_prefs,
        "level_self": p.level_self,
        "available_time": p.available_time,
        "interest_competitions": p.interest_competitions,
        "bio": p.bio,
    }


def _event_dict(e: TeamEvent) -> dict:
    return {
        "id": e.id,
        "title": e.title,
        "teacher_id": e.teacher_id,
        "competition_id": e.competition_id,
        "competition_name": e.competition_name,
        "team_size": e.team_size,
        "required_roles": e.required_roles,
        "description": e.description,
        "deadline": e.deadline.isoformat() if e.deadline else None,
        "status": e.status,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _team_dict(t: Team, db: Session, *, with_event: bool = False) -> dict:
    members = []
    for m in t.members:
        u = db.get(User, m.student_user_id)
        p = db.scalar(select(StudentProfile).where(StudentProfile.user_id == m.student_user_id))
        members.append(
            {
                "user_id": m.student_user_id,
                "name": (u.display_name or u.username) if u else str(m.student_user_id),
                "username": u.username if u else "",
                "suggested_role": m.suggested_role,
                "is_leader": bool(m.is_leader),
                "major": p.major if p else "",
                "grade": p.grade if p else "",
                "skills": p.skills if p else "",
                "role_prefs": p.role_prefs if p else "",
                "level_self": p.level_self if p else "",
                "available_time": p.available_time if p else "",
                "bio": p.bio if p else "",
            }
        )
    out = {
        "id": t.id,
        "event_id": t.event_id,
        "name": t.name,
        "status": t.status,
        "score": t.score,
        "reason": t.reason,
        "member_count": len(members),
        "members": members,
        "member_names": "、".join(m["name"] for m in members),
        "roles_summary": "、".join(
            f"{m['name']}({m['suggested_role'] or '队员'})" for m in members
        ),
    }
    if with_event:
        e = db.get(TeamEvent, t.event_id)
        out["event"] = _event_dict(e) if e else None
        out["competition_name"] = e.competition_name if e else ""
        out["event_title"] = e.title if e else ""
        out["instructor"] = ""
        if e:
            teacher = db.get(User, e.teacher_id)
            out["instructor"] = (teacher.display_name or teacher.username) if teacher else ""
    return out


@router.get("/my-guided-teams")
def my_guided_teams(
    status: str | None = Query(default=None, description="draft/confirmed，空=全部"),
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """老师指导的全部队伍（跨活动）及队伍详细信息。"""
    event_ids = [
        e.id for e in db.scalars(select(TeamEvent).where(TeamEvent.teacher_id == user.id)).all()
    ]
    if not event_ids:
        return {"items": [], "summary": {"total": 0, "confirmed": 0, "draft": 0}}
    stmt = (
        select(Team)
        .options(selectinload(Team.members))
        .where(Team.event_id.in_(event_ids))
        .order_by(Team.id.desc())
    )
    if status:
        stmt = stmt.where(Team.status == status)
    rows = db.scalars(stmt).all()
    items = [_team_dict(t, db, with_event=True) for t in rows]
    return {
        "items": items,
        "summary": {
            "total": len(items),
            "confirmed": sum(1 for x in items if x["status"] == "confirmed"),
            "draft": sum(1 for x in items if x["status"] == "draft"),
        },
    }


@router.get("/teams/{team_id}")
def get_team_detail(
    team_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.scalar(select(Team).options(selectinload(Team.members)).where(Team.id == team_id))
    if not t:
        raise HTTPException(404, "队伍不存在")
    e = db.get(TeamEvent, t.event_id)
    if not e:
        raise HTTPException(404, "活动不存在")
    if user.role == "teacher" and e.teacher_id != user.id:
        raise HTTPException(403, "无权查看")
    if user.role == "student" and not any(m.student_user_id == user.id for m in t.members):
        raise HTTPException(403, "无权查看")
    return _team_dict(t, db, with_event=True)


# ---------- student profile ----------


@router.get("/profile")
def get_profile(user: User = Depends(require_student), db: Session = Depends(get_db)):
    p = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    return {"profile": _profile_dict(p)}


@router.put("/profile")
def put_profile(body: ProfileBody, user: User = Depends(require_student), db: Session = Depends(get_db)):
    p = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    if not p:
        p = StudentProfile(user_id=user.id)
        db.add(p)
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    db.commit()
    return {"ok": True, "profile": _profile_dict(p)}


# ---------- events ----------


@router.get("/events")
def list_events(
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(TeamEvent).order_by(TeamEvent.id.desc())
    if status:
        stmt = stmt.where(TeamEvent.status == status)
    if user.role == "teacher":
        stmt = stmt.where(TeamEvent.teacher_id == user.id)
    rows = db.scalars(stmt).all()
    items = []
    for e in rows:
        d = _event_dict(e)
        d["applicant_count"] = len(
            db.scalars(
                select(TeamApplication).where(
                    TeamApplication.event_id == e.id,
                    TeamApplication.status.in_(["pending", "accepted"]),
                )
            ).all()
        )
        items.append(d)
    return {"items": items}


@router.post("/events")
def create_event(body: EventCreate, user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    name = body.competition_name.strip()
    if body.competition_id:
        comp = db.get(Competition, body.competition_id)
        if not comp:
            raise HTTPException(404, "竞赛不存在")
        name = name or comp.name
    if not name:
        raise HTTPException(400, "请选择或填写竞赛名称")
    e = TeamEvent(
        teacher_id=user.id,
        competition_id=body.competition_id,
        competition_name=name,
        title=body.title.strip() or f"{name}组队",
        team_size=body.team_size,
        required_roles=body.required_roles,
        description=body.description,
        deadline=body.deadline,
        status="open",
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return _event_dict(e)


@router.get("/events/{event_id}")
def get_event(event_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.get(TeamEvent, event_id)
    if not e:
        raise HTTPException(404, "活动不存在")
    return _event_dict(e)


@router.post("/events/{event_id}/apply")
def apply_event(
    event_id: int,
    body: ApplyBody,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    e = db.get(TeamEvent, event_id)
    if not e or e.status != "open":
        raise HTTPException(400, "活动不可报名")
    exists = db.scalar(
        select(TeamApplication).where(
            TeamApplication.event_id == event_id,
            TeamApplication.student_user_id == user.id,
            TeamApplication.status != "withdrawn",
        )
    )
    if exists:
        raise HTTPException(400, "已报名该活动")
    # 确保有档案
    if not db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id)):
        db.add(StudentProfile(user_id=user.id))
    app = TeamApplication(event_id=event_id, student_user_id=user.id, status="pending", note=body.note)
    db.add(app)
    db.commit()
    return {"ok": True, "application_id": app.id}


@router.post("/events/{event_id}/withdraw")
def withdraw_event(event_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    app = db.scalar(
        select(TeamApplication).where(
            TeamApplication.event_id == event_id,
            TeamApplication.student_user_id == user.id,
            TeamApplication.status != "withdrawn",
        )
    )
    if not app:
        raise HTTPException(404, "未报名")
    app.status = "withdrawn"
    db.commit()
    return {"ok": True}


@router.get("/my-applications")
def my_applications(user: User = Depends(require_student), db: Session = Depends(get_db)):
    apps = db.scalars(
        select(TeamApplication).where(TeamApplication.student_user_id == user.id).order_by(TeamApplication.id.desc())
    ).all()
    items = []
    for a in apps:
        e = db.get(TeamEvent, a.event_id)
        items.append(
            {
                "id": a.id,
                "event_id": a.event_id,
                "status": a.status,
                "note": a.note,
                "event": _event_dict(e) if e else None,
            }
        )
    return {"items": items}


@router.get("/events/{event_id}/pool")
def event_pool(event_id: int, user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    e = db.get(TeamEvent, event_id)
    if not e or e.teacher_id != user.id:
        raise HTTPException(404, "活动不存在")
    pool = load_pool(db, e)
    return {
        "items": [
            {
                "user_id": c.user_id,
                "name": c.name,
                "major": c.major,
                "grade": c.grade,
                "skills": c.skills,
                "role_prefs": c.role_prefs,
                "level": c.level,
                "bio": c.bio,
            }
            for c in pool
        ]
    }


@router.post("/events/{event_id}/match")
async def run_match(event_id: int, user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    e = db.get(TeamEvent, event_id)
    if not e or e.teacher_id != user.id:
        raise HTTPException(404, "活动不存在")
    draft = match_teams(db, e)
    if draft["pool_size"] < e.team_size:
        raise HTTPException(400, f"报名人数不足（当前 {draft['pool_size']}，每队需 {e.team_size}）")

    # 清除旧草案
    old = db.scalars(select(Team).where(Team.event_id == event_id, Team.status == "draft")).all()
    for t in old:
        db.delete(t)
    db.flush()

    saved = []
    for td in draft["teams"]:
        team = Team(
            event_id=event_id,
            name=td["name"],
            status="draft",
            score=float(td["score"]),
            reason="；".join(td.get("reasons") or []),
        )
        db.add(team)
        db.flush()
        for m in td["members"]:
            db.add(
                TeamMember(
                    team_id=team.id,
                    student_user_id=m["user_id"],
                    suggested_role=m.get("suggested_role") or "",
                    is_leader=1 if m.get("is_leader") else 0,
                )
            )
        saved.append(team)
    db.commit()

    explain = await explain_match_with_llm(e, draft)
    teams_out = []
    for t in saved:
        db.refresh(t)
        t = db.scalar(select(Team).options(selectinload(Team.members)).where(Team.id == t.id))
        teams_out.append(_team_dict(t, db))  # type: ignore[arg-type]

    return {
        "draft": draft,
        "teams": teams_out,
        "ai_explain": explain,
        "leftovers": draft.get("leftovers") or [],
    }


@router.get("/events/{event_id}/teams")
def list_teams(event_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.get(TeamEvent, event_id)
    if not e:
        raise HTTPException(404, "活动不存在")
    if user.role == "teacher" and e.teacher_id != user.id:
        raise HTTPException(403, "无权查看")
    rows = db.scalars(
        select(Team).options(selectinload(Team.members)).where(Team.event_id == event_id).order_by(Team.id)
    ).all()
    return {"items": [_team_dict(t, db) for t in rows]}


@router.patch("/teams/{team_id}")
def patch_team(
    team_id: int,
    body: TeamPatch,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    t = db.scalar(select(Team).options(selectinload(Team.members)).where(Team.id == team_id))
    if not t:
        raise HTTPException(404, "队伍不存在")
    e = db.get(TeamEvent, t.event_id)
    if not e or e.teacher_id != user.id:
        raise HTTPException(403, "无权操作")
    if t.status == "confirmed":
        raise HTTPException(400, "已确认队伍不可直接改，请先保持草案状态调整")
    if body.name is not None:
        t.name = body.name.strip() or t.name
    if body.members is not None:
        for m in list(t.members):
            db.delete(m)
        db.flush()
        for m in body.members:
            db.add(
                TeamMember(
                    team_id=t.id,
                    student_user_id=m.student_user_id,
                    suggested_role=m.suggested_role,
                    is_leader=1 if m.is_leader else 0,
                )
            )
    db.commit()
    t = db.scalar(select(Team).options(selectinload(Team.members)).where(Team.id == team_id))
    return _team_dict(t, db)  # type: ignore[arg-type]


@router.post("/teams/{team_id}/confirm")
def confirm_team(
    team_id: int,
    body: ConfirmBody,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    t = db.scalar(select(Team).options(selectinload(Team.members)).where(Team.id == team_id))
    if not t:
        raise HTTPException(404, "队伍不存在")
    e = db.get(TeamEvent, t.event_id)
    if not e or e.teacher_id != user.id:
        raise HTTPException(403, "无权操作")
    t.status = "confirmed"
    for m in t.members:
        app = db.scalar(
            select(TeamApplication).where(
                TeamApplication.event_id == e.id,
                TeamApplication.student_user_id == m.student_user_id,
            )
        )
        if app:
            app.status = "accepted"

    synced = 0
    if body.sync_ledger and e.competition_id:
        for m in t.members:
            stu = db.get(User, m.student_user_id)
            profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == m.student_user_id))
            db.add(
                Participation(
                    competition_id=e.competition_id,
                    year=date.today().year,
                    student_name=(stu.display_name or stu.username) if stu else "",
                    student_id="",
                    major=(profile.major if profile else ""),
                    grade=(profile.grade if profile else ""),
                    team_name=t.name,
                    instructor=user.display_name or user.username,
                    project_title="",
                    award_level="参赛",
                )
            )
            synced += 1
    db.commit()
    return {"ok": True, "synced_participations": synced, "team": _team_dict(t, db)}


@router.get("/events/{event_id}/export")
def export_event(event_id: int, user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    e = db.get(TeamEvent, event_id)
    if not e or e.teacher_id != user.id:
        raise HTTPException(404, "活动不存在")
    teams = db.scalars(
        select(Team).options(selectinload(Team.members)).where(Team.event_id == event_id).order_by(Team.id)
    ).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "组队名单"
    ws.append(["队伍", "状态", "得分", "队员", "角色", "是否队长", "专业", "年级"])
    for t in teams:
        for m in t.members:
            u = db.get(User, m.student_user_id)
            p = db.scalar(select(StudentProfile).where(StudentProfile.user_id == m.student_user_id))
            ws.append(
                [
                    t.name,
                    t.status,
                    t.score,
                    (u.display_name or u.username) if u else m.student_user_id,
                    m.suggested_role,
                    "是" if m.is_leader else "否",
                    p.major if p else "",
                    p.grade if p else "",
                ]
            )
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"team_event_{event_id}_{uuid.uuid4().hex[:6]}.xlsx"
    save_bytes(buf.getvalue(), filename)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
