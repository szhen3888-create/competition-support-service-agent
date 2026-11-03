"""对话/工作台导出文件下载。"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.agent_tools import safe_export_path

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/{filename}")
def download_export(filename: str):
    path = safe_export_path(filename)
    if not path:
        raise HTTPException(status_code=404, detail="文件不存在")
    media = "application/octet-stream"
    if path.suffix == ".docx":
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif path.suffix == ".xlsx":
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(path, media_type=media, filename=path.name)
