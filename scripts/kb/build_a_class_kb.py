"""从《A类学生竞赛分析.xlsx》生成学校 A 类竞赛知识库，并入库 BM25。"""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "knowledge" / "school_a_class"
CONTESTS = OUT / "contests"
# 优先使用 knowledge 目录内台账，兼容根目录旧路径
XLSX = OUT / "A类学生竞赛分析.xlsx"
if not XLSX.exists():
    XLSX = ROOT / "A类学生竞赛分析.xlsx"

# 后端入库
sys.path.insert(0, str(ROOT / "backend"))


def safe_name(text: str, fallback: str) -> str:
    text = re.sub(r'[\\/:*?"<>|\s]+', "_", str(text)).strip("_")
    return (text[:100] or fallback)


def row_to_md(i: int, row: dict) -> str:
    name = str(row.get("竞赛名称") or f"竞赛_{i}").strip()
    fields = [
        ("竞赛分类", row.get("竞赛分类")),
        ("举办时间", row.get("举办时间")),
        ("报名时间", row.get("报名时间")),
        ("官网", row.get("官网")),
        ("备注", row.get("备注")),
        ("是否适合计算机类学生参加", row.get("是否适合计算机类学生参加")),
        ("理由（分析依据）", row.get("理由（分析依据）")),
        ("适应专业", row.get("适应专业")),
        ("适应年级", row.get("适应年级")),
        ("适应学期", row.get("适应学期")),
    ]
    lines = [
        f"# {name}",
        "",
        "- 来源：学校《A类学生竞赛分析》台账",
        f"- 级别：A类",
        f"- 生成时间：{datetime.now(timezone.utc).astimezone().isoformat()}",
        "",
        "## 基本信息",
        "",
    ]
    for label, val in fields:
        v = "" if pd.isna(val) else str(val).strip()
        if not v:
            continue
        lines.append(f"- **{label}**：{v}")
    lines.extend(
        [
            "",
            "## 检索摘要",
            "",
            f"本校 A 类竞赛「{name}」。"
            f"分类：{row.get('竞赛分类') or '未标注'}。"
            f"适合计算机类：{row.get('是否适合计算机类学生参加') or '未标注'}。"
            f"适应专业：{row.get('适应专业') or '见上'}。"
            f"适应年级：{row.get('适应年级') or '见上'}。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    if not XLSX.exists():
        raise SystemExit(f"找不到文件: {XLSX}")

    OUT.mkdir(parents=True, exist_ok=True)
    CONTESTS.mkdir(parents=True, exist_ok=True)

    # 若从根目录旧路径读取，则复制进 knowledge
    dest_xlsx = OUT / "A类学生竞赛分析.xlsx"
    if XLSX.resolve() != dest_xlsx.resolve():
        shutil.copy2(XLSX, dest_xlsx)

    df = pd.read_excel(XLSX, sheet_name="Sheet1")
    df = df.dropna(how="all")
    # 去掉无名称行
    df = df[df["竞赛名称"].notna()]
    df = df[df["竞赛名称"].astype(str).str.strip() != ""]

    records = []
    for i, row in df.iterrows():
        d = row.to_dict()
        name = str(d["竞赛名称"]).strip()
        slug = safe_name(f"A类_{name}", f"a_class_{i}")
        md_path = CONTESTS / f"{slug}.md"
        # 防重名
        if md_path.exists():
            md_path = CONTESTS / f"{slug}_{i}.md"
        text = row_to_md(int(i) if isinstance(i, int) else 0, d)
        md_path.write_text(text, encoding="utf-8")
        records.append(
            {
                "title": name,
                "category": "" if pd.isna(d.get("竞赛分类")) else str(d.get("竞赛分类")),
                "level": "A类",
                "suitable_cs": ""
                if pd.isna(d.get("是否适合计算机类学生参加"))
                else str(d.get("是否适合计算机类学生参加")),
                "majors": "" if pd.isna(d.get("适应专业")) else str(d.get("适应专业")),
                "grades": "" if pd.isna(d.get("适应年级")) else str(d.get("适应年级")),
                "website": "" if pd.isna(d.get("官网")) else str(d.get("官网")),
                "file": str(md_path.relative_to(OUT)).replace("\\", "/"),
            }
        )
        print(f"[md] {name}")

    # 汇总文档，便于一次检索浏览
    overview_lines = [
        "# 学校 A 类学生竞赛名单总览",
        "",
        f"- 来源：A类学生竞赛分析.xlsx",
        f"- 条目数：{len(records)}",
        f"- 生成时间：{datetime.now(timezone.utc).astimezone().isoformat()}",
        "",
        "| 序号 | 竞赛名称 | 分类 | 适合计算机类 | 官网 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for n, r in enumerate(records, 1):
        overview_lines.append(
            f"| {n} | {r['title']} | {r['category']} | {r['suitable_cs']} | {r['website']} |"
        )
    overview_path = OUT / "A类竞赛总览.md"
    overview_path.write_text("\n".join(overview_lines) + "\n", encoding="utf-8")

    index = {
        "source": "A类学生竞赛分析.xlsx",
        "level": "A类",
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "count": len(records),
        "items": records,
    }
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# 学校 A 类竞赛知识库\n\n"
        "由《A类学生竞赛分析.xlsx》生成。\n\n"
        "| 路径 | 说明 |\n|------|------|\n"
        "| `A类学生竞赛分析.xlsx` | 原始台账 |\n"
        "| `index.json` | 索引 |\n"
        "| `A类竞赛总览.md` | 名单总表 |\n"
        "| `contests/*.md` | 单场赛事 |\n\n"
        "更新：`backend\\.venv\\Scripts\\python.exe scripts\\build_a_class_kb.py`\n",
        encoding="utf-8",
    )
    print(f"[folder] {len(records)} contests -> {OUT}")

    # 入库 RAG
    from app.services.knowledge import get_knowledge_store

    store = get_knowledge_store()
    # 避免重复：先删掉同名/同源已入库文档
    to_delete = [
        d.id
        for d in store.list_documents()
        if d.doc_type == "A类竞赛" or (d.title and d.title.startswith("A类_"))
        or d.filename.startswith("A类_")
        or d.filename == "A类竞赛总览.md"
    ]
    for did in to_delete:
        try:
            store.delete(did)
        except KeyError:
            pass

    ingested = 0
    # 总览
    overview_bytes = overview_path.read_bytes()
    store.ingest_bytes(
        filename="A类竞赛总览.md",
        data=overview_bytes,
        title="学校A类学生竞赛名单总览",
        competition="A类竞赛",
        year="",
        doc_type="A类竞赛",
    )
    ingested += 1

    for r in records:
        md_file = OUT / r["file"]
        store.ingest_bytes(
            filename=md_file.name,
            data=md_file.read_bytes(),
            title=r["title"],
            competition=r["title"],
            year="",
            doc_type="A类竞赛",
        )
        ingested += 1

    stats = store.stats()
    print(f"[rag] ingested {ingested}, store={stats}")


if __name__ == "__main__":
    main()
