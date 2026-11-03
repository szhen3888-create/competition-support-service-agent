"""写入示例竞赛台账数据。"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.models import Competition, Participation
from app.db.session import SessionLocal, init_db


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        from sqlalchemy import func, select

        if db.scalar(select(func.count()).select_from(Competition)) > 0:
            print("already seeded, skip")
            return

        comps = [
            Competition(
                name="程序设计竞赛",
                level="校级",
                category="学科竞赛",
                major_tags="软件工程,计算机,人工智能",
                grade_range="大一-大四",
                tech_direction="算法",
                organizer="计算与智能技术学院",
                year=2026,
                register_deadline=date(2026, 3, 15),
                contest_date=date(2026, 3, 22),
                location="本校",
                fee=0,
                award_setting="一等奖10%/二等奖20%/三等奖30%",
                materials="报名表,学生证,团队分工说明",
                description="校内程序设计竞赛",
                status="报名中",
            ),
            Competition(
                name="中国大学生计算机设计大赛",
                level="国家级",
                category="学科竞赛",
                major_tags="软件工程,数字媒体,人工智能",
                grade_range="大二-研二",
                tech_direction="软件应用",
                organizer="教育部高等学校计算机类专业教学指导委员会",
                year=2025,
                register_deadline=date(2025, 4, 30),
                contest_date=date(2025, 7, 20),
                location="外省",
                fee=600,
                award_setting="国家一/二/三等奖",
                materials="作品说明书,申报书,视频",
                description="国家级计算机设计大赛",
                status="已结束",
            ),
            Competition(
                name="蓝桥杯大赛",
                level="省级",
                category="学科竞赛",
                major_tags="软件工程,计算机",
                grade_range="大一-大四",
                tech_direction="编程",
                organizer="工业和信息化部人才交流中心",
                year=2025,
                register_deadline=date(2025, 1, 20),
                contest_date=date(2025, 4, 12),
                location="省内",
                fee=300,
                award_setting="省一/二/三等奖",
                materials="报名确认单",
                description="蓝桥杯软件类",
                status="已结束",
            ),
        ]
        db.add_all(comps)
        db.flush()

        parts = [
            Participation(
                competition_id=comps[1].id,
                year=2025,
                student_name="张三",
                student_id="20230101",
                major="软件工程",
                grade="大三",
                team_name="星火队",
                instructor="李老师",
                project_title="校园导航小程序",
                award_level="二等奖",
            ),
            Participation(
                competition_id=comps[1].id,
                year=2025,
                student_name="王五",
                student_id="20230102",
                major="人工智能",
                grade="大二",
                team_name="智行队",
                instructor="李老师",
                project_title="智能答疑助手",
                award_level="三等奖",
            ),
            Participation(
                competition_id=comps[2].id,
                year=2025,
                student_name="赵六",
                student_id="20220111",
                major="软件工程",
                grade="大三",
                team_name="",
                instructor="陈老师",
                project_title="",
                award_level="一等奖",
            ),
            Participation(
                competition_id=comps[2].id,
                year=2025,
                student_name="钱七",
                student_id="20240101",
                major="计算机科学与技术",
                grade="大一",
                instructor="陈老师",
                award_level="参赛",
            ),
            Participation(
                competition_id=comps[0].id,
                year=2026,
                student_name="孙八",
                student_id="20230109",
                major="软件工程",
                grade="大二",
                instructor="周老师",
                award_level="参赛",
            ),
        ]
        db.add_all(parts)
        db.commit()
        print("seeded competitions=", len(comps), "participations=", len(parts))
    finally:
        db.close()


if __name__ == "__main__":
    main()
