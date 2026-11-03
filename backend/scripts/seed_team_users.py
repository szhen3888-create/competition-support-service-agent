"""种子账号 + 示例组队活动报名池。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # backend/
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import Competition, StudentProfile, TeamApplication, TeamEvent, User
from app.db.session import SessionLocal, init_db


USERS = [
    ("teacher1", "teacher123", "teacher", "王老师"),
    ("stu1", "stu123", "student", "张三"),
    ("stu2", "stu123", "student", "李四"),
    ("stu3", "stu123", "student", "王五"),
    ("stu4", "stu123", "student", "赵六"),
    ("stu5", "stu123", "student", "钱七"),
    ("stu6", "stu123", "student", "孙八"),
]

PROFILES = {
    "stu1": dict(major="软件工程", grade="大二", skills="Python,算法,数据结构", role_prefs="算法", level_self="高", bio="喜欢刷题"),
    "stu2": dict(major="软件工程", grade="大二", skills="Vue,Java,Spring", role_prefs="开发", level_self="中", bio="做过课程项目"),
    "stu3": dict(major="人工智能", grade="大三", skills="写作,PPT,需求分析", role_prefs="写材料", level_self="中", bio="擅长材料"),
    "stu4": dict(major="计算机科学与技术", grade="大二", skills="C++,算法", role_prefs="算法,开发", level_self="高", bio=""),
    "stu5": dict(major="数字媒体", grade="大三", skills="UI,Figma,视频", role_prefs="设计", level_self="中", bio=""),
    "stu6": dict(major="软件工程", grade="大一", skills="Python,前端入门", role_prefs="开发,写材料", level_self="初", bio="想练手"),
}


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        for username, password, role, display in USERS:
            user = db.scalar(select(User).where(User.username == username))
            if not user:
                user = User(
                    username=username,
                    password_hash=hash_password(password),
                    role=role,
                    display_name=display,
                )
                db.add(user)
                db.flush()
                print("created user", username)
            else:
                print("exists", username)

            if role == "student":
                profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
                if not profile:
                    profile = StudentProfile(user_id=user.id)
                    db.add(profile)
                data = PROFILES.get(username) or {}
                for k, v in data.items():
                    setattr(profile, k, v)

        db.commit()

        teacher = db.scalar(select(User).where(User.username == "teacher1"))
        comp = db.scalars(select(Competition).order_by(Competition.id.desc())).first()
        event = db.scalar(select(TeamEvent).where(TeamEvent.title == "示例：蓝桥杯组队活动"))
        if teacher and not event:
            event = TeamEvent(
                teacher_id=teacher.id,
                competition_id=comp.id if comp else None,
                competition_name=(comp.name if comp else "蓝桥杯全国大学生软件和信息技术大赛"),
                title="示例：蓝桥杯组队活动",
                team_size=3,
                required_roles="算法,开发,写材料",
                description="校内选拔组队，优先技能互补",
                status="open",
            )
            db.add(event)
            db.flush()
            for uname in ("stu1", "stu2", "stu3", "stu4", "stu5", "stu6"):
                u = db.scalar(select(User).where(User.username == uname))
                if not u:
                    continue
                exists = db.scalar(
                    select(TeamApplication).where(
                        TeamApplication.event_id == event.id,
                        TeamApplication.student_user_id == u.id,
                    )
                )
                if not exists:
                    db.add(TeamApplication(event_id=event.id, student_user_id=u.id, status="pending"))
            db.commit()
            print("created sample event", event.id)
        else:
            print("sample event ready")
    finally:
        db.close()
    print("done. teacher1/teacher123 ; stu1~stu6 / stu123")


if __name__ == "__main__":
    main()
