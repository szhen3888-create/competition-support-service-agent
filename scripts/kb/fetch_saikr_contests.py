"""从赛氪公开 API 拉取 2026/2027 竞赛，写入 knowledge/saikr_2026_2027/。

数据来源：https://apiv4buffer.saikr.com/api/pc/contest/lists （公开列表接口）
详情页：https://www.saikr.com/{contest_url}
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "knowledge" / "saikr_2026_2027"
RAW = OUT / "raw"
CONTESTS = OUT / "contests"
INDEX = OUT / "index.json"
LIST_CACHE = OUT / "list_all.json"

LIST_API = "https://apiv4buffer.saikr.com/api/pc/contest/lists"
DETAIL_BASE = "https://www.saikr.com/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.saikr.com/contests",
    "Origin": "https://www.saikr.com",
}

YEAR_RE = re.compile(r"2026|2027")


def ts_to_str(ts: int | float | None) -> str:
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    except (OSError, OverflowError, ValueError):
        return ""


def year_of_item(item: dict) -> str | None:
    name = str(item.get("contest_name") or "")
    url = str(item.get("contest_url") or "")
    blob = name + " " + url
    m = YEAR_RE.search(blob)
    if m:
        return m.group(0)
    # 用报名/比赛时间戳判断是否落在 2026–2027
    for key in (
        "regist_start_time",
        "regist_end_time",
        "contest_start_time",
        "contest_end_time",
    ):
        ts = item.get(key)
        if not ts:
            continue
        try:
            y = datetime.fromtimestamp(int(ts), tz=timezone.utc).year
        except (OSError, OverflowError, ValueError):
            continue
        if y in (2026, 2027):
            return str(y)
    return None


def safe_name(text: str, fallback: str) -> str:
    text = re.sub(r'[\\/:*?"<>|\s]+', "_", text).strip("_")
    return (text[:90] or fallback)


def clean_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    main = (
        soup.select_one("article")
        or soup.select_one(".contest-detail")
        or soup.select_one(".content")
        or soup.select_one("main")
        or soup.body
    )
    if not main:
        return ""
    lines = [ln.strip() for ln in main.get_text("\n", strip=True).splitlines() if ln.strip()]
    out: list[str] = []
    for ln in lines:
        if out and out[-1] == ln:
            continue
        out.append(ln)
    return "\n".join(out)


def guess_fields(text: str) -> dict:
    fields = {"organizer": "", "register_time": "", "contest_time": ""}
    for key, pat in [
        ("organizer", r"主办方[:：\s]*([^\n]{2,100})"),
        ("register_time", r"报名时间[:：\s]*([^\n]{6,80})"),
        ("contest_time", r"(?:比赛|竞赛|活动)时间[:：\s]*([^\n]{6,80})"),
    ]:
        m = re.search(pat, text)
        if m:
            fields[key] = m.group(1).strip()
    return fields


def fetch_all_lists(client: httpx.Client, limit: int = 50) -> list[dict]:
    if LIST_CACHE.exists():
        cached = json.loads(LIST_CACHE.read_text(encoding="utf-8"))
        if cached.get("items"):
            print(f"[cache] reuse {LIST_CACHE} ({len(cached['items'])})")
            return cached["items"]

    first = client.get(
        LIST_API,
        params={"page": 1, "limit": limit, "univs_id": "", "class_id": "", "level": 0, "sort": 0},
        timeout=30,
    )
    first.raise_for_status()
    payload = first.json()
    if payload.get("code") != 200:
        raise RuntimeError(f"list api failed: {payload}")

    data = payload.get("data") or {}
    items = list(data.get("list") or [])
    # 尝试从 total / last_page 推断
    total = int(data.get("total") or data.get("count") or 0)
    last_page = int(data.get("last_page") or data.get("totalPage") or 0)
    if not last_page and total:
        last_page = (total + limit - 1) // limit
    if not last_page:
        # 页面显示约 517 页 @10 条；limit=50 时约 104 页，保守多翻直到空页
        last_page = 200

    print(f"[list] page1 got {len(items)}, total={total}, last_page≈{last_page}")

    page = 2
    empty_streak = 0
    while page <= max(last_page, page) and page <= 300:
        try:
            r = client.get(
                LIST_API,
                params={
                    "page": page,
                    "limit": limit,
                    "univs_id": "",
                    "class_id": "",
                    "level": 0,
                    "sort": 0,
                },
                timeout=30,
            )
            r.raise_for_status()
            body = r.json()
            batch = list((body.get("data") or {}).get("list") or [])
            if not batch:
                empty_streak += 1
                if empty_streak >= 2:
                    break
            else:
                empty_streak = 0
                items.extend(batch)
            if page % 10 == 0:
                print(f"[list] page {page}, accumulated {len(items)}")
            page += 1
            time.sleep(0.25)
        except Exception as exc:  # noqa: BLE001
            print(f"[list-fail] page {page}: {exc}")
            time.sleep(1.0)
            empty_streak += 1
            if empty_streak >= 3:
                break
            page += 1

    # 按 contest_id 去重
    uniq: dict[int | str, dict] = {}
    for it in items:
        cid = it.get("contest_id") or it.get("contest_url")
        if cid is None:
            continue
        uniq[cid] = it
    merged = list(uniq.values())
    LIST_CACHE.write_text(
        json.dumps(
            {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "count": len(merged),
                "items": merged,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[list] unique {len(merged)} -> {LIST_CACHE}")
    return merged


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    CONTESTS.mkdir(parents=True, exist_ok=True)

    with httpx.Client(headers=HEADERS, http2=False, follow_redirects=True) as client:
        # 先探测更大 limit 是否可用
        probe = client.get(
            LIST_API,
            params={"page": 1, "limit": 50, "univs_id": "", "class_id": "", "level": 0, "sort": 0},
            timeout=30,
        ).json()
        probe_n = len((probe.get("data") or {}).get("list") or [])
        limit = 50 if probe_n >= 20 else 10
        print(f"[probe] limit={limit} returned {probe_n}")

        all_items = fetch_all_lists(client, limit=limit)
        targets = []
        for it in all_items:
            y = year_of_item(it)
            if y in {"2026", "2027"}:
                targets.append((y, it))
        print(f"[filter] 2026/2027 candidates: {len(targets)} / {len(all_items)}")

        records = []
        for i, (year, it) in enumerate(targets, 1):
            name = str(it.get("contest_name") or f"contest_{it.get('contest_id')}")
            rel = str(it.get("contest_url") or "").lstrip("/")
            url = DETAIL_BASE + rel if rel else ""
            slug = safe_name(
                f"{year}_{name}_{it.get('contest_id')}",
                f"contest_{it.get('contest_id')}",
            )
            md_path = CONTESTS / f"{slug}.md"
            raw_path = RAW / f"{slug}.html"

            detail_text = ""
            page_title = name
            if url:
                try:
                    html = client.get(url, timeout=30).text
                    raw_path.write_text(html, encoding="utf-8", errors="ignore")
                    soup = BeautifulSoup(html, "lxml")
                    if soup.title and soup.title.get_text(strip=True):
                        page_title = soup.title.get_text(strip=True)
                    detail_text = clean_text(soup)
                    time.sleep(0.35)
                except Exception as exc:  # noqa: BLE001
                    print(f"[detail-fail] {url}: {exc}")

            extra = guess_fields(detail_text)
            organizer = extra["organizer"] or str(it.get("organizer") or it.get("host") or "")
            reg = extra["register_time"] or (
                f"{ts_to_str(it.get('regist_start_time'))} ~ {ts_to_str(it.get('regist_end_time'))}".strip(" ~")
            )
            ctime = extra["contest_time"] or (
                f"{ts_to_str(it.get('contest_start_time'))} ~ {ts_to_str(it.get('contest_end_time'))}".strip(" ~")
            )

            md = (
                f"# {name}\n\n"
                f"- 来源：赛氪公开竞赛广场\n"
                f"- 原文链接：{url or '（列表无无详情 URL）'}\n"
                f"- 抓取时间：{datetime.now(timezone.utc).astimezone().isoformat()}\n"
                f"- 年份：{year}\n"
                f"- contest_id：{it.get('contest_id')}\n"
                f"- 主办方：{organizer or '见正文/列表'}\n"
                f"- 报名时间：{reg or '见正文'}\n"
                f"- 比赛时间：{ctime or '见正文'}\n"
                f"- 竞赛级别：{it.get('level_name') or it.get('level') or '见正文'}\n\n"
                f"## 列表字段（原始）\n\n"
                f"```json\n{json.dumps(it, ensure_ascii=False, indent=2)}\n```\n\n"
                f"## 详情页正文摘录\n\n"
                f"{(detail_text[:18000] if detail_text else '（未能抓取详情正文，仅保留列表信息）')}\n"
            )
            md_path.write_text(md, encoding="utf-8")
            records.append(
                {
                    "title": name,
                    "page_title": page_title,
                    "url": url,
                    "year": year,
                    "contest_id": it.get("contest_id"),
                    "organizer": organizer,
                    "register_time": reg,
                    "contest_time": ctime,
                    "file": str(md_path.relative_to(OUT)).replace("\\", "/"),
                }
            )
            if i % 20 == 0 or i == len(targets):
                print(f"[detail] {i}/{len(targets)} saved")

    INDEX.write_text(
        json.dumps(
            {
                "source": "saikr.com / apiv4buffer.saikr.com",
                "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
                "count": len(records),
                "years": sorted({r["year"] for r in records}),
                "items": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[done] {len(records)} contests -> {OUT}")


if __name__ == "__main__":
    main()
