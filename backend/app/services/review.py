"""材料初审：对照竞赛材料清单做规则缺失检测 + 供 LLM 生成改进建议。"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


DEFAULT_CHECKLIST = [
    "报名表",
    "学生证",
    "团队分工",
    "作品说明书",
    "申报书",
    "项目背景",
    "创新点",
    "技术方案",
    "预期成果",
]


@dataclass
class ReviewResult:
    checklist: list[dict[str, Any]]
    missing: list[str]
    covered: list[str]
    text_length: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_required_materials(materials: str | None) -> list[str]:
    if not materials:
        return list(DEFAULT_CHECKLIST)
    parts = re.split(r"[,，;；、/\n]+", materials)
    items = [p.strip() for p in parts if p.strip()]
    return items or list(DEFAULT_CHECKLIST)


def rule_check(content: str, required: list[str]) -> ReviewResult:
    text = content or ""
    covered: list[str] = []
    missing: list[str] = []
    checklist: list[dict[str, Any]] = []
    for item in required:
        # 简单关键词命中；不宣称语义理解
        hit = item in text or item.replace("《", "").replace("》", "") in text
        # 同义宽松：说明书/申报书等
        aliases = {
            "作品说明书": ["说明书", "作品说明"],
            "申报书": ["申请书", "申报"],
            "学生证": ["学籍", "在读证明"],
            "报名表": ["报名", "报名信息"],
            "团队分工": ["分工", "队员职责"],
        }
        if not hit:
            for a in aliases.get(item, []):
                if a in text:
                    hit = True
                    break
        checklist.append({"item": item, "found": hit})
        (covered if hit else missing).append(item)
    return ReviewResult(
        checklist=checklist,
        missing=missing,
        covered=covered,
        text_length=len(text),
    )
