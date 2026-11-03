"""竞赛台账结构化模型。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Competition(Base):
    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(50), default="校级")  # 国家级/省级/校级
    category: Mapped[str] = mapped_column(String(80), default="学科竞赛")
    major_tags: Mapped[str] = mapped_column(String(255), default="")  # 逗号分隔
    grade_range: Mapped[str] = mapped_column(String(80), default="")
    tech_direction: Mapped[str] = mapped_column(String(120), default="")
    organizer: Mapped[str] = mapped_column(String(120), default="")
    year: Mapped[int] = mapped_column(Integer, index=True)
    register_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    contest_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    location: Mapped[str] = mapped_column(String(120), default="")
    fee: Mapped[float] = mapped_column(Float, default=0)
    award_setting: Mapped[str] = mapped_column(Text, default="")
    materials: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="报名中")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    participations: Mapped[list["Participation"]] = relationship(back_populates="competition")


class Participation(Base):
    __tablename__ = "participations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    student_name: Mapped[str] = mapped_column(String(80), index=True)
    student_id: Mapped[str] = mapped_column(String(40), default="")
    major: Mapped[str] = mapped_column(String(80), default="", index=True)
    grade: Mapped[str] = mapped_column(String(40), default="")
    team_name: Mapped[str] = mapped_column(String(120), default="")
    instructor: Mapped[str] = mapped_column(String(80), default="", index=True)
    project_title: Mapped[str] = mapped_column(String(200), default="")
    award_level: Mapped[str] = mapped_column(String(40), default="参赛")  # 一等奖/二等奖/...
    award_rank: Mapped[str] = mapped_column(String(40), default="")
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    competition: Mapped[Competition] = relationship(back_populates="participations")


class FinanceDraft(Base):
    """预算/借款/报销草稿（结构化结果，可导出）。"""

    __tablename__ = "finance_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)  # budget/loan/reimbursement
    title: Mapped[str] = mapped_column(String(200), default="")
    competition_name: Mapped[str] = mapped_column(String(200), default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    content_md: Mapped[str] = mapped_column(Text, default="")
    export_path: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WorkspaceDraft(Base):
    """备赛计划 / 材料初审等写作草稿。"""

    __tablename__ = "workspace_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)  # prep/review/recommend
    title: Mapped[str] = mapped_column(String(200), default="")
    content_md: Mapped[str] = mapped_column(Text, default="")
    meta_json: Mapped[str] = mapped_column(Text, default="{}")
    export_path: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class User(Base):
    """轻量账号：老师 / 学生。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), index=True)  # teacher | student
    display_name: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    profile: Mapped["StudentProfile | None"] = relationship(back_populates="user", uselist=False)


class StudentProfile(Base):
    """学生能力档案。"""

    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    major: Mapped[str] = mapped_column(String(80), default="")
    grade: Mapped[str] = mapped_column(String(40), default="")
    skills: Mapped[str] = mapped_column(String(255), default="")  # 逗号分隔
    role_prefs: Mapped[str] = mapped_column(String(255), default="")  # 算法/开发/设计/写材料
    level_self: Mapped[str] = mapped_column(String(40), default="中")  # 高/中/初
    available_time: Mapped[str] = mapped_column(String(120), default="")
    interest_competitions: Mapped[str] = mapped_column(String(255), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="profile")


class TeamEvent(Base):
    """老师创建的组队活动（绑定竞赛）。"""

    __tablename__ = "team_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    competition_id: Mapped[int | None] = mapped_column(ForeignKey("competitions.id"), nullable=True)
    competition_name: Mapped[str] = mapped_column(String(200), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    team_size: Mapped[int] = mapped_column(Integer, default=3)
    required_roles: Mapped[str] = mapped_column(String(255), default="算法,开发,写材料")
    description: Mapped[str] = mapped_column(Text, default="")
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open")  # open/closed
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    applications: Mapped[list["TeamApplication"]] = relationship(back_populates="event")
    teams: Mapped[list["Team"]] = relationship(back_populates="event")


class TeamApplication(Base):
    """学生对组队活动的报名。"""

    __tablename__ = "team_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("team_events.id"), index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending/accepted/withdrawn
    note: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    event: Mapped["TeamEvent"] = relationship(back_populates="applications")


class Team(Base):
    """组队结果（草案或已确认）。"""

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("team_events.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(30), default="draft")  # draft/confirmed
    score: Mapped[float] = mapped_column(Float, default=0)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    event: Mapped["TeamEvent"] = relationship(back_populates="teams")
    members: Mapped[list["TeamMember"]] = relationship(back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    suggested_role: Mapped[str] = mapped_column(String(80), default="")
    is_leader: Mapped[int] = mapped_column(Integer, default=0)  # 0/1

    team: Mapped["Team"] = relationship(back_populates="members")
