"""竞赛统计、可视化数据与导出（基于结构化台账，不靠 LLM 编造）。"""

from io import BytesIO
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Competition, Participation
from app.db.session import get_db

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview")
def overview(year: int | None = None, db: Session = Depends(get_db)):
    p_stmt = select(func.count(Participation.id))
    c_stmt = select(func.count(Competition.id))
    award_stmt = select(func.count(Participation.id)).where(Participation.award_level != "参赛")
    if year:
        p_stmt = p_stmt.where(Participation.year == year)
        c_stmt = c_stmt.where(Competition.year == year)
        award_stmt = award_stmt.where(Participation.year == year)
    inst_stmt = select(func.count(func.distinct(Participation.instructor))).where(
        Participation.instructor != ""
    )
    if year:
        inst_stmt = inst_stmt.where(Participation.year == year)
    return {
        "competition_count": db.scalar(c_stmt) or 0,
        "participation_count": db.scalar(p_stmt) or 0,
        "award_count": db.scalar(award_stmt) or 0,
        "instructor_count": db.scalar(inst_stmt) or 0,
    }


@router.get("/charts")
def charts(year: int | None = None, db: Session = Depends(get_db)):
    """返回 ECharts 可直接使用的结构化数据。"""

    def _filter(stmt):
        return stmt.where(Participation.year == year) if year else stmt

    by_award = db.execute(
        _filter(
            select(Participation.award_level, func.count(Participation.id)).group_by(
                Participation.award_level
            )
        )
    ).all()
    by_major = db.execute(
        _filter(select(Participation.major, func.count(Participation.id)).group_by(Participation.major))
    ).all()
    by_year = db.execute(
        select(Participation.year, func.count(Participation.id))
        .group_by(Participation.year)
        .order_by(Participation.year)
    ).all()
    by_instructor = db.execute(
        _filter(
            select(Participation.instructor, func.count(Participation.id))
            .where(Participation.instructor != "")
            .group_by(Participation.instructor)
            .order_by(func.count(Participation.id).desc())
            .limit(10)
        )
    ).all()
    by_level = db.execute(
        select(Competition.level, func.count(Competition.id)).group_by(Competition.level)
        if not year
        else select(Competition.level, func.count(Competition.id))
        .where(Competition.year == year)
        .group_by(Competition.level)
    ).all()

    return {
        "award_pie": [{"name": a or "未标注", "value": int(c)} for a, c in by_award],
        "major_bar": {
            "categories": [m or "未标注" for m, _ in by_major],
            "values": [int(c) for _, c in by_major],
        },
        "year_line": {
            "categories": [str(y) for y, _ in by_year],
            "values": [int(c) for _, c in by_year],
        },
        "instructor_bar": {
            "categories": [i for i, _ in by_instructor],
            "values": [int(c) for _, c in by_instructor],
        },
        "level_pie": [{"name": lv or "未标注", "value": int(c)} for lv, c in by_level],
    }


@router.get("/export")
def export_excel(
    year: int | None = None,
    kind: str = Query("participations", pattern="^(participations|competitions)$"),
    db: Session = Depends(get_db),
):
    if kind == "competitions":
        stmt = select(Competition)
        if year:
            stmt = stmt.where(Competition.year == year)
        rows = db.scalars(stmt).all()
        data = [
            {
                "ID": r.id,
                "名称": r.name,
                "级别": r.level,
                "类别": r.category,
                "年份": r.year,
                "专业标签": r.major_tags,
                "技术方向": r.tech_direction,
                "报名截止": r.register_deadline,
                "举办地": r.location,
                "报名费": r.fee,
                "状态": r.status,
            }
            for r in rows
        ]
        filename = f"competitions_{year or 'all'}.xlsx"
    else:
        stmt = select(Participation)
        if year:
            stmt = stmt.where(Participation.year == year)
        rows = db.scalars(stmt).all()
        data = [
            {
                "ID": r.id,
                "年份": r.year,
                "竞赛": r.competition.name if r.competition else "",
                "学生": r.student_name,
                "学号": r.student_id,
                "专业": r.major,
                "年级": r.grade,
                "团队": r.team_name,
                "指导教师": r.instructor,
                "项目": r.project_title,
                "奖项": r.award_level,
                "名次": r.award_rank,
            }
            for r in rows
        ]
        filename = f"participations_{year or 'all'}.xlsx"

    df = pd.DataFrame(data)
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="data")
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
