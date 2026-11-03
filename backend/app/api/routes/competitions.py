"""竞赛台账与参赛记录 API。"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Competition, Participation
from app.db.session import get_db

router = APIRouter(prefix="/competitions", tags=["competitions"])


class CompetitionIn(BaseModel):
    name: str
    level: str = "校级"
    category: str = "学科竞赛"
    major_tags: str = ""
    grade_range: str = ""
    tech_direction: str = ""
    organizer: str = ""
    year: int
    register_deadline: date | None = None
    contest_date: date | None = None
    location: str = ""
    fee: float = 0
    award_setting: str = ""
    materials: str = ""
    description: str = ""
    status: str = "报名中"


class CompetitionOut(CompetitionIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ParticipationIn(BaseModel):
    competition_id: int
    year: int
    student_name: str
    student_id: str = ""
    major: str = ""
    grade: str = ""
    team_name: str = ""
    instructor: str = ""
    project_title: str = ""
    award_level: str = "参赛"
    award_rank: str = ""
    remark: str = ""


class ParticipationOut(ParticipationIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    competition_name: str = ""


@router.get("", response_model=list[CompetitionOut])
def list_competitions(
    year: int | None = None,
    level: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Competition).order_by(Competition.year.desc(), Competition.id.desc())
    if year:
        stmt = stmt.where(Competition.year == year)
    if level:
        stmt = stmt.where(Competition.level == level)
    if q:
        stmt = stmt.where(Competition.name.contains(q))
    return db.scalars(stmt).all()


@router.post("", response_model=CompetitionOut)
def create_competition(body: CompetitionIn, db: Session = Depends(get_db)):
    obj = Competition(**body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{comp_id}", response_model=CompetitionOut)
def update_competition(comp_id: int, body: CompetitionIn, db: Session = Depends(get_db)):
    obj = db.get(Competition, comp_id)
    if not obj:
        raise HTTPException(404, "竞赛不存在")
    for k, v in body.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{comp_id}")
def delete_competition(comp_id: int, db: Session = Depends(get_db)):
    obj = db.get(Competition, comp_id)
    if not obj:
        raise HTTPException(404, "竞赛不存在")
    # 级联删除参赛记录
    for p in list(obj.participations):
        db.delete(p)
    db.delete(obj)
    db.commit()
    return {"ok": True}


@router.get("/participations/list", response_model=list[ParticipationOut])
def list_participations(
    year: int | None = None,
    major: str | None = None,
    instructor: str | None = None,
    award_level: str | None = None,
    competition_id: int | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Participation).order_by(Participation.year.desc(), Participation.id.desc())
    if year:
        stmt = stmt.where(Participation.year == year)
    if major:
        stmt = stmt.where(Participation.major.contains(major))
    if instructor:
        stmt = stmt.where(Participation.instructor.contains(instructor))
    if award_level:
        stmt = stmt.where(Participation.award_level == award_level)
    if competition_id:
        stmt = stmt.where(Participation.competition_id == competition_id)
    rows = db.scalars(stmt).all()
    out: list[ParticipationOut] = []
    for r in rows:
        item = ParticipationOut.model_validate(r)
        item.competition_name = r.competition.name if r.competition else ""
        out.append(item)
    return out


@router.post("/participations", response_model=ParticipationOut)
def create_participation(body: ParticipationIn, db: Session = Depends(get_db)):
    if not db.get(Competition, body.competition_id):
        raise HTTPException(400, "竞赛不存在")
    obj = Participation(**body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    item = ParticipationOut.model_validate(obj)
    item.competition_name = obj.competition.name if obj.competition else ""
    return item


@router.delete("/participations/{pid}")
def delete_participation(pid: int, db: Session = Depends(get_db)):
    obj = db.get(Participation, pid)
    if not obj:
        raise HTTPException(404, "记录不存在")
    db.delete(obj)
    db.commit()
    return {"ok": True}
