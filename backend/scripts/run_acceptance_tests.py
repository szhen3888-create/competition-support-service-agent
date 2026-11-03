"""验收测试脚本：覆盖问答/检索/统计/推荐/财务计算/导出。

用法（backend 目录）：
  set PYTHONPATH=.
  python scripts/run_acceptance_tests.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REPORT: list[dict] = []


def ok(name: str, detail: str = ""):
    REPORT.append({"name": name, "pass": True, "detail": detail})
    print("[PASS]", name, detail)


def fail(name: str, detail: str):
    REPORT.append({"name": name, "pass": False, "detail": detail})
    print("[FAIL]", name, detail)


def test_finance_math():
    from app.services.finance import build_budget, check_reimbursement_materials

    b = build_budget(
        competition_name="测试赛",
        people=3,
        location="外省",
        registration_fee=100,
        transport_per_person=200,
        lodging_per_person_night=150,
        nights=2,
        local_transport=50,
    )
    expected = 100 * 3 + 200 * 3 + 150 * 3 * 2 + 50
    if abs(b.total - expected) > 1e-6:
        fail("finance_math", f"total={b.total} expected={expected}")
    else:
        ok("finance_math", f"total={b.total}")

    c = check_reimbursement_materials(["发票原件"])
    if c.ok or "批准预算表" not in c.missing:
        fail("reimbursement_check", str(c.to_dict()))
    else:
        ok("reimbursement_check", f"missing={c.missing}")


def test_knowledge_search():
    from app.services.knowledge import get_knowledge_store

    store = get_knowledge_store()
    hits = store.search("程序设计竞赛 报名截止", top_k=3)
    if not hits:
        fail("knowledge_search", "no hits — 请先 seed_samples")
    else:
        ok("knowledge_search", f"top={hits[0].chunk.title} score={hits[0].score:.3f}")


def test_stats_sql():
    from sqlalchemy import func, select

    from app.db.models import Competition, Participation
    from app.db.session import SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        c = db.scalar(select(func.count(Competition.id))) or 0
        p = db.scalar(select(func.count(Participation.id))) or 0
        if c < 1 or p < 1:
            fail("stats_sql", f"comps={c} parts={p} — 请先 seed_ledger")
        else:
            ok("stats_sql", f"comps={c} parts={p}")
    finally:
        db.close()


def test_recommend_match():
    from app.db.session import SessionLocal, init_db
    from app.services.recommend import extract_profile, match_competitions

    init_db()
    profile = extract_profile("我是软件工程大二，喜欢算法")
    db = SessionLocal()
    try:
        rows = match_competitions(db, profile, limit=5)
        if not rows:
            fail("recommend_match", "no competitions")
        else:
            ok("recommend_match", f"profile={profile} top={rows[0].name}")
    finally:
        db.close()


def test_export_files():
    from app.services.export_docs import budget_to_xlsx, markdownish_to_docx, save_bytes
    from app.services.finance import build_budget

    b = build_budget(competition_name="X", people=1, location="本校", registration_fee=10)
    x = save_bytes(budget_to_xlsx(b.to_dict()), "_test_budget.xlsx")
    d = save_bytes(markdownish_to_docx("测试", "# 标题\n- a\n- b"), "_test.docx")
    if x.exists() and d.exists() and x.stat().st_size > 0 and d.stat().st_size > 0:
        ok("export_files", f"{x.name},{d.name}")
    else:
        fail("export_files", "file missing")


async def test_agent_intents():
    from app.agents.graph import reset_agent_graph, run_agent

    reset_agent_graph()
    cases = [
        ("knowledge_qa", "2026程序设计竞赛报名截止时间是什么时候？"),
        ("stats_query", "2025年获奖情况怎么样？"),
        ("recommend", "软件工程大二算法方向推荐竞赛"),
        ("finance_assist", "帮我做预算：3人 外省 报名费100 交通200 住宿150 2晚 市内交通50"),
    ]
    for expect, q in cases:
        try:
            r = await run_agent([{"role": "user", "content": q}])
            intent = r.get("intent")
            ans = (r.get("answer") or "")[:80].replace("\n", " ")
            if intent != expect:
                fail(f"agent_intent:{expect}", f"got={intent} ans={ans}")
            elif not r.get("answer"):
                fail(f"agent_intent:{expect}", "empty answer")
            else:
                ok(f"agent_intent:{expect}", f"ans={ans}...")
        except Exception as exc:  # noqa: BLE001
            fail(f"agent_intent:{expect}", str(exc))


def main():
    test_finance_math()
    test_knowledge_search()
    test_stats_sql()
    test_recommend_match()
    test_export_files()
    asyncio.run(test_agent_intents())

    out = ROOT / "data" / "exports" / "acceptance_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(1 for r in REPORT if r["pass"])
    total = len(REPORT)
    print(f"\nSUMMARY {passed}/{total} passed → {out}")
    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
