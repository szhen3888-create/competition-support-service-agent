"""导入示例竞赛文档到知识库。

用法（在 backend 目录）：
  set PYTHONPATH=.
  python scripts/seed_samples.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.knowledge import get_knowledge_store


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    samples = root / "data" / "samples"
    store = get_knowledge_store()
    mapping = [
        ("2026_程序设计竞赛通知.md", "2026程序设计竞赛通知", "程序设计竞赛", "2026", "通知"),
        ("竞赛经费管理办法摘录.md", "竞赛经费管理办法摘录", "", "2026", "政策"),
    ]
    for name, title, competition, year, doc_type in mapping:
        path = samples / name
        if not path.exists():
            print("skip missing", name)
            continue
        meta = store.ingest_bytes(
            filename=name,
            data=path.read_bytes(),
            title=title,
            competition=competition,
            year=year,
            doc_type=doc_type,
        )
        print("ingested", meta.id, meta.title, "chunks=", meta.chunk_count)
    print("stats", store.stats())


if __name__ == "__main__":
    main()
