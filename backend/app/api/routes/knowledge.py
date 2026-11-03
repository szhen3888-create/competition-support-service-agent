"""知识库管理：上传、列表、启停、删除。"""

from dataclasses import asdict

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services.knowledge import get_knowledge_store

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

ALLOWED_EXT = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".md", ".markdown", ".csv"}


@router.get("/stats")
async def knowledge_stats():
    return get_knowledge_store().stats()


@router.get("/documents")
async def list_documents():
    store = get_knowledge_store()
    return {"items": [asdict(d) for d in store.list_documents()]}


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(""),
    competition: str = Form(""),
    year: str = Form(""),
    doc_type: str = Form("通知"),
):
    filename = file.filename or "upload.bin"
    suffix = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if suffix not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {suffix}")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="空文件")
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大（上限 20MB）")

    try:
        meta = get_knowledge_store().ingest_bytes(
            filename=filename,
            data=data,
            title=title,
            competition=competition,
            year=year,
            doc_type=doc_type,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"解析失败: {exc}") from exc

    return asdict(meta)


@router.patch("/documents/{doc_id}")
async def patch_document(doc_id: str, active: bool):
    try:
        meta = get_knowledge_store().set_active(doc_id, active)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="文档不存在") from exc
    return asdict(meta)


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    try:
        get_knowledge_store().delete(doc_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="文档不存在") from exc
    return {"ok": True}


@router.post("/search")
async def search_knowledge(body: dict):
    query = (body or {}).get("query", "")
    top_k = int((body or {}).get("top_k") or 5)
    if not query.strip():
        raise HTTPException(status_code=400, detail="query 不能为空")
    hits = get_knowledge_store().search(query, top_k=top_k)
    return {
        "items": [
            {
                "rank": h.rank,
                "score": h.score,
                "id": h.chunk.id,
                "filename": h.chunk.filename,
                "title": h.chunk.title,
                "page": h.chunk.page,
                "content": h.chunk.content,
                "competition": h.chunk.competition,
                "year": h.chunk.year,
            }
            for h in hits
        ]
    }
