"""将草稿导出为 Word / Excel（交付物：结果导出）。"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from docx import Document
from openpyxl import Workbook


def ensure_export_dir(root: str | Path = "./data/exports") -> Path:
    path = Path(root).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def markdownish_to_docx(title: str, body: str) -> bytes:
    doc = Document()
    doc.add_heading(title, level=1)
    for raw in body.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("### "):
            doc.add_heading(line[4:], level=3)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)
        elif line.startswith("# "):
            doc.add_heading(line[2:], level=2)
        elif line.startswith("- ") or line.startswith("* "):
            doc.add_paragraph(line[2:], style="List Bullet")
        elif line[:2].isdigit() and ". " in line[:4]:
            doc.add_paragraph(line.split(". ", 1)[-1], style="List Number")
        else:
            doc.add_paragraph(line)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def budget_to_xlsx(budget: dict[str, Any]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "预算明细"
    ws.append(["竞赛", budget.get("competition_name")])
    ws.append(["人数", budget.get("people")])
    ws.append(["地点", budget.get("location")])
    ws.append([])
    ws.append(["项目", "数量", "单价", "金额", "备注"])
    for item in budget.get("items") or []:
        ws.append(
            [
                item.get("name"),
                item.get("quantity"),
                item.get("unit_price"),
                item.get("amount"),
                item.get("note"),
            ]
        )
    ws.append([])
    ws.append(["合计", "", "", budget.get("total"), ""])
    ws.append([])
    ws.append(["假设/说明"])
    for a in budget.get("assumptions") or []:
        ws.append([a])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def save_bytes(data: bytes, filename: str, root: str | Path = "./data/exports") -> Path:
    folder = ensure_export_dir(root)
    path = folder / filename
    path.write_bytes(data)
    return path
