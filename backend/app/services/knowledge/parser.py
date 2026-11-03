"""多格式文档解析：PDF / Word / Excel / TXT / MD。"""

from pathlib import Path


def parse_file(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _parse_pdf(path)
    if suffix in {".docx", ".doc"}:
        return _parse_docx(path)
    if suffix in {".xlsx", ".xls"}:
        return _parse_excel(path)
    if suffix in {".txt", ".md", ".markdown", ".csv"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"暂不支持的文件类型: {suffix}")


def _parse_pdf(path: Path) -> str:
    import fitz  # PyMuPDF

    parts: list[str] = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            text = (page.get_text("text") or "").strip()
            if text:
                parts.append(f"[第{i}页]\n{text}")
    return "\n\n".join(parts)


def _parse_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    return "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())


def _parse_excel(path: Path) -> str:
    from openpyxl import load_workbook

    wb = load_workbook(str(path), data_only=True)
    parts: list[str] = []
    for sheet in wb.worksheets:
        rows: list[str] = []
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
            if cells:
                rows.append(" | ".join(cells))
        if rows:
            parts.append(f"[工作表:{sheet.title}]\n" + "\n".join(rows))
    return "\n\n".join(parts)
