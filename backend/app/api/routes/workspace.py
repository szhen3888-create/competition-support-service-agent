"""材料工作台：备赛/初审/预算借款报销表单生成与导出。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.graph import run_agent
from app.db.models import FinanceDraft, WorkspaceDraft
from app.db.session import get_db
from app.services.export_docs import budget_to_xlsx, markdownish_to_docx, save_bytes
from app.services.finance import build_budget, build_loan_text, check_reimbursement_materials
from app.services.knowledge.parser import parse_file
from app.services.review import parse_required_materials, rule_check

router = APIRouter(prefix="/workspace", tags=["workspace"])


class BudgetForm(BaseModel):
    competition_name: str = ""
    people: int = 0
    location: str = ""
    registration_fee: float = 0
    transport_per_person: float = 0
    lodging_per_person_night: float = 0
    nights: int = 0
    local_transport: float = 0
    other: float = 0
    other_note: str = ""
    budget_ref: str = ""
    kind: str = Field(default="budget", pattern="^(budget|loan)$")


class ReimburseForm(BaseModel):
    competition_name: str = ""
    provided_materials: list[str] = Field(default_factory=list)
    note: str = ""


@router.post("/budget")
async def create_budget(body: BudgetForm, db: Session = Depends(get_db)):
    draft = build_budget(
        competition_name=body.competition_name,
        people=body.people,
        location=body.location,
        registration_fee=body.registration_fee,
        transport_per_person=body.transport_per_person,
        lodging_per_person_night=body.lodging_per_person_night,
        nights=body.nights,
        local_transport=body.local_transport,
        other=body.other,
        other_note=body.other_note,
    )
    data = draft.to_dict()
    if body.kind == "loan":
        content = build_loan_text(draft, budget_ref=body.budget_ref)
        title = f"借款说明-{body.competition_name or '未命名'}"
        xlsx = budget_to_xlsx(data)
        path = save_bytes(xlsx, f"loan_{uuid.uuid4().hex[:8]}.xlsx")
        # 同时存 word
        docx = markdownish_to_docx(title, content)
        docx_path = save_bytes(docx, f"loan_{uuid.uuid4().hex[:8]}.docx")
        export_path = str(docx_path)
        kind = "loan"
    else:
        content = (
            f"# 预算申请草稿\n\n竞赛：{draft.competition_name}\n\n"
            f"人数：{draft.people}　地点：{draft.location}\n\n"
            "## 明细\n\n"
            + "\n".join(
                f"- {i.name}：{i.amount:.2f} 元（{i.quantity}×{i.unit_price:.2f}）"
                for i in draft.items
            )
            + f"\n\n**合计：{draft.total:.2f} 元**\n"
        )
        title = f"预算申请-{body.competition_name or '未命名'}"
        path = save_bytes(budget_to_xlsx(data), f"budget_{uuid.uuid4().hex[:8]}.xlsx")
        export_path = str(path)
        kind = "budget"

    row = FinanceDraft(
        kind=kind,
        title=title,
        competition_name=body.competition_name,
        payload_json=json.dumps(data, ensure_ascii=False),
        content_md=content,
        export_path=export_path,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "kind": row.kind,
        "title": row.title,
        "content_md": row.content_md,
        "budget": data,
        "export_path": row.export_path,
        "download_url": f"/api/v1/workspace/downloads/{row.id}?type=finance",
    }


@router.post("/reimbursement")
async def create_reimbursement(body: ReimburseForm, db: Session = Depends(get_db)):
    check = check_reimbursement_materials(body.provided_materials)
    content = (
        f"# 报销材料整理\n\n竞赛：{body.competition_name or '（未填）'}\n\n"
        f"## 完整性：{'通过' if check.ok else '未通过'}\n\n"
        f"- 必备：{('、'.join(check.required))}\n"
        f"- 已提供：{('、'.join(check.provided)) or '无'}\n"
        f"- 缺失：{('、'.join(check.missing)) or '无'}\n\n"
        f"## 备注\n{body.note or '无'}\n"
    )
    path = save_bytes(
        markdownish_to_docx("报销材料整理", content),
        f"reimburse_{uuid.uuid4().hex[:8]}.docx",
    )
    row = FinanceDraft(
        kind="reimbursement",
        title=f"报销整理-{body.competition_name or '未命名'}",
        competition_name=body.competition_name,
        payload_json=json.dumps(check.to_dict(), ensure_ascii=False),
        content_md=content,
        export_path=str(path),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "check": check.to_dict(),
        "content_md": content,
        "download_url": f"/api/v1/workspace/downloads/{row.id}?type=finance",
    }


@router.post("/review")
async def review_material(
    file: UploadFile = File(...),
    competition_materials: str = Form(""),
    question: str = Form("请对上传材料做初审并给出答辩题"),
    db: Session = Depends(get_db),
):
    suffix = (file.filename or "x.txt").rsplit(".", 1)[-1].lower()
    raw = await file.read()
    tmp = save_bytes(raw, f"upload_{uuid.uuid4().hex[:8]}.{suffix}", root="./data/uploads")
    try:
        text = parse_file(tmp)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"解析失败: {exc}") from exc

    required = parse_required_materials(competition_materials)
    review = rule_check(text, required)
    result = await run_agent(
        [{"role": "user", "content": question}],
        context={"material_text": text[:12000]},
    )
    path = save_bytes(
        markdownish_to_docx("材料初审报告", result.get("answer") or ""),
        f"review_{uuid.uuid4().hex[:8]}.docx",
    )
    row = WorkspaceDraft(
        kind="review",
        title=f"初审-{file.filename}",
        content_md=result.get("answer") or "",
        meta_json=json.dumps({"review": review.to_dict(), "filename": file.filename}, ensure_ascii=False),
        export_path=str(path),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "intent": result.get("intent"),
        "review": review.to_dict(),
        "content_md": row.content_md,
        "download_url": f"/api/v1/workspace/downloads/{row.id}?type=workspace",
    }


@router.post("/prep")
async def prep_plan(body: dict, db: Session = Depends(get_db)):
    question = (body or {}).get("question") or "请生成备赛计划"
    result = await run_agent([{"role": "user", "content": question}])
    path = save_bytes(
        markdownish_to_docx("备赛计划", result.get("answer") or ""),
        f"prep_{uuid.uuid4().hex[:8]}.docx",
    )
    row = WorkspaceDraft(
        kind="prep",
        title="备赛计划",
        content_md=result.get("answer") or "",
        meta_json="{}",
        export_path=str(path),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "intent": result.get("intent"),
        "content_md": row.content_md,
        "citations": result.get("citations") or [],
        "download_url": f"/api/v1/workspace/downloads/{row.id}?type=workspace",
    }


@router.get("/drafts")
def list_drafts(db: Session = Depends(get_db)):
    finances = db.scalars(select(FinanceDraft).order_by(FinanceDraft.id.desc()).limit(50)).all()
    works = db.scalars(select(WorkspaceDraft).order_by(WorkspaceDraft.id.desc()).limit(50)).all()
    return {
        "finance": [
            {
                "id": r.id,
                "kind": r.kind,
                "title": r.title,
                "created_at": r.created_at.isoformat() if isinstance(r.created_at, datetime) else r.created_at,
                "download_url": f"/api/v1/workspace/downloads/{r.id}?type=finance",
            }
            for r in finances
        ],
        "workspace": [
            {
                "id": r.id,
                "kind": r.kind,
                "title": r.title,
                "created_at": r.created_at.isoformat() if isinstance(r.created_at, datetime) else r.created_at,
                "download_url": f"/api/v1/workspace/downloads/{r.id}?type=workspace",
            }
            for r in works
        ],
    }


@router.get("/downloads/{draft_id}")
def download_draft(draft_id: int, type: str = "finance", db: Session = Depends(get_db)):
    if type == "workspace":
        row = db.get(WorkspaceDraft, draft_id)
    else:
        row = db.get(FinanceDraft, draft_id)
    if not row or not row.export_path:
        raise HTTPException(404, "文件不存在")
    from pathlib import Path

    path = Path(row.export_path)
    if not path.exists():
        raise HTTPException(404, "文件已失效")
    return FileResponse(path, filename=path.name)
