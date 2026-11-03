"""文本分块，尽量按段落切分并保留页码线索。"""

import re
from dataclasses import dataclass


@dataclass
class TextChunk:
    content: str
    page: int | None = None
    index: int = 0


_PAGE_RE = re.compile(r"^\[第(\d+)页\]\s*")


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 80) -> list[TextChunk]:
    if not text or not text.strip():
        return []

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: list[TextChunk] = []
    buf = ""
    current_page: int | None = None
    idx = 0

    def flush():
        nonlocal buf, idx
        if buf.strip():
            chunks.append(TextChunk(content=buf.strip(), page=current_page, index=idx))
            idx += 1
        buf = ""

    for para in paragraphs:
        m = _PAGE_RE.match(para)
        if m:
            current_page = int(m.group(1))
            para = _PAGE_RE.sub("", para).strip()
            if not para:
                continue

        if len(buf) + len(para) + 1 <= chunk_size:
            buf = f"{buf}\n{para}".strip() if buf else para
            continue

        flush()
        # 超长段落硬切
        if len(para) > chunk_size:
            start = 0
            while start < len(para):
                end = min(start + chunk_size, len(para))
                piece = para[start:end]
                chunks.append(TextChunk(content=piece, page=current_page, index=idx))
                idx += 1
                if end >= len(para):
                    break
                start = max(end - overlap, start + 1)
            buf = ""
        else:
            buf = para

    flush()
    return chunks
