"""将 knowledge/saikr_2026_2027 下的 Markdown 批量写入 BM25 检索库。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAIKR = ROOT / "knowledge" / "saikr_2026_2027"
INDEX = SAIKR / "index.json"

sys.path.insert(0, str(ROOT / "backend"))


def main() -> None:
    if not INDEX.exists():
        raise SystemExit(f"找不到索引: {INDEX}")

    from app.services.knowledge import get_knowledge_store

    store = get_knowledge_store()
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    items = data.get("items") or []

    old = [d.id for d in store.list_documents() if d.doc_type == "赛氪竞赛"]
    for did in old:
        try:
            store.delete(did)
        except KeyError:
            pass
    print(f"[clean] removed {len(old)} old saikr docs; remaining={store.stats()}")

    overview_lines = [
        "# 赛氪 2026–2027 竞赛资料总览",
        "",
        "- 来源：赛氪公开竞赛广场",
        f"- 条目数：{len(items)}",
        f"- 年份：{', '.join(data.get('years') or [])}",
        "",
        "| 序号 | 年份 | 竞赛名称 | 链接 |",
        "| --- | --- | --- | --- |",
    ]
    for n, it in enumerate(items, 1):
        overview_lines.append(
            f"| {n} | {it.get('year', '')} | {it.get('title', '')} | {it.get('url', '')} |"
        )
    overview = "\n".join(overview_lines) + "\n"
    (SAIKR / "赛氪竞赛总览.md").write_text(overview, encoding="utf-8")
    store.ingest_bytes(
        filename="赛氪竞赛总览.md",
        data=overview.encode("utf-8"),
        title="赛氪2026-2027竞赛资料总览",
        competition="赛氪竞赛",
        year="",
        doc_type="赛氪竞赛",
        defer_index=True,
    )

    ok = 0
    fail = 0
    for i, it in enumerate(items, 1):
        rel = it.get("file") or ""
        md_path = SAIKR / rel
        if not md_path.exists():
            fail += 1
            print(f"[miss] {rel}")
            continue
        title = it.get("title") or md_path.stem
        year = str(it.get("year") or "")
        try:
            store.ingest_bytes(
                filename=md_path.name,
                data=md_path.read_bytes(),
                title=title,
                competition=title,
                year=year,
                doc_type="赛氪竞赛",
                defer_index=True,
            )
            ok += 1
        except Exception as exc:  # noqa: BLE001
            fail += 1
            print(f"[fail] {title}: {exc}")
        if i % 100 == 0 or i == len(items):
            print(f"[ingest] {i}/{len(items)} ok={ok} fail={fail}")

    print("[commit] rebuilding BM25 index...")
    store.commit()
    print(f"[done] ok={ok} fail={fail} store={store.stats()}")


if __name__ == "__main__":
    main()
