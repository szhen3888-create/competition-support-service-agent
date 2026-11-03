"""竞赛简称 / 别名 → 正式名称扩展。

用于检索查询扩展：用户说「大挑」「ACM」「蓝桥」时，能命中全称文档。
别名来源：
1. 内置常见别名
2. knowledge/school_a_class 正文中的「简称：」
3. knowledge/saikr_2026_2027 标题中的【】/简称线索（弱）
4. data/knowledge/aliases.json（可人工维护，优先合并）
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path

from app.core.config import get_settings

# 内置高频别名（可被 aliases.json 覆盖/追加）
_BUILTIN: dict[str, list[str]] = {
    "大挑": ["挑战杯全国大学生课外学术科技作品竞赛", "挑战杯"],
    "小挑": ["挑战杯中国大学生创业计划竞赛", "创青春", "挑战杯"],
    "创青春": ["挑战杯中国大学生创业计划竞赛"],
    "ACM": ["ACM-ICPC国际大学生程序设计竞赛", "ICPC"],
    "ICPC": ["ACM-ICPC国际大学生程序设计竞赛", "ACM"],
    "蓝桥": ["蓝桥杯全国大学生软件和信息技术大赛", "蓝桥杯"],
    "蓝桥杯": ["蓝桥杯全国大学生软件和信息技术大赛"],
    "软件杯": ["中国软件杯大学生软件设计大赛", "中国软件杯"],
    "服创": ["中国大学生服务外包创新创业大赛", "服创赛"],
    "服创赛": ["中国大学生服务外包创新创业大赛"],
    "数模": ["全国大学生数学建模竞赛", "数学建模"],
    "美赛": ["美国大学生数学建模竞赛", "MCM", "ICM", "MCM/ICM"],
    "MCM": ["美赛", "MCM/ICM"],
    "ICM": ["美赛", "MCM/ICM"],
    "电赛": ["全国大学生电子设计竞赛"],
    "智能车": ["全国大学生智能汽车竞赛"],
    "百度之星": ["百度之星程序设计大赛"],
    "C4": ["中国高校计算机大赛", "C4大赛"],
    "C4大赛": ["中国高校计算机大赛"],
    "大英赛": ["全国大学生英语竞赛"],
    "大广赛": ["全国大学生广告艺术大赛"],
    "互联网+": ["中国国际大学生创新大赛", "中国国际大学生创新大赛（原互联网+）"],
    "高教社杯": ["全国大学生数学建模竞赛"],
    "华为ICT": ["华为ICT大赛", "ICT大赛"],
    "ICT大赛": ["华为ICT大赛"],
    "RoboMaster": ["全国大学生机器人大赛RoboMaster", "机甲大师"],
    "机甲大师": ["全国大学生机器人大赛RoboMaster", "RoboMaster"],
    "RoboCon": ["全国大学生机器人大赛RoboCon"],
    "三创赛": ["全国大学生电子商务创新创意及创业挑战赛", "电子商务三创赛"],
    "ISCC": ["全国大学生信息安全与对抗技术竞赛"],
    "CISCN": ["全国大学生信息安全竞赛"],
    "NCDA": ["未来设计师全国高校数字艺术设计大赛", "未来设计师"],
    "未来设计师": ["未来设计师全国高校数字艺术设计大赛"],
    "3C大赛": ["中国好创意暨全国数字艺术设计大赛"],
    "中国创意挑战大赛": ["中国好创意暨全国数字艺术设计大赛"],
    "CRAIC": ["中国机器人及人工智能大赛"],
    "AIC": ["全球校园人工智能算法精英大赛", "AICOMP"],
    "AICOMP": ["全球校园人工智能算法精英大赛"],
    "CMIT": ["全国大学生数字媒体科技作品及创意竞赛"],
    "大唐杯": ["大唐杯全国大学生新一代信息通信技术大赛"],
    "西门子杯": ["西门子杯中国智能制造挑战赛"],
    "学创杯": ["学创杯全国大学生创业综合模拟大赛"],
    "工行杯": ["工行杯全国大学生金融科技创新大赛"],
    "科云杯": ["科云杯全国大学生财会职业能力大赛"],
    "外研社": ["外研社国才杯理解当代中国全国大学生外语能力大赛", "国才杯"],
    "国才杯": ["外研社国才杯理解当代中国全国大学生外语能力大赛"],
    "21世纪杯": ["21世纪杯全国英语演讲比赛"],
    "外教社杯": ["外教社杯全国高校学生跨文化能力大赛"],
    "iCAN": ["iCAN大学生创新创业大赛"],
    "挑战杯": ["挑战杯全国大学生课外学术科技作品竞赛", "挑战杯中国大学生创业计划竞赛"],
}

_lock = threading.RLock()
_alias_map: dict[str, list[str]] | None = None
_alias_mtime: float = 0.0


def _project_root() -> Path:
    # backend/app/services/knowledge/aliases.py → 项目根
    return Path(__file__).resolve().parents[4]


def _aliases_json_path() -> Path:
    settings = get_settings()
    return Path(settings.knowledge_dir).resolve() / "aliases.json"


def _extract_from_a_class() -> dict[str, list[str]]:
    out: dict[str, set[str]] = {}
    folder = _project_root() / "knowledge" / "school_a_class" / "contests"
    if not folder.exists():
        return {}
    for path in folder.glob("*.md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"^#\s+(.+)$", text, re.M)
        name = (m.group(1).strip() if m else path.stem).strip()
        for m2 in re.finditer(r"简称[：:]\s*([^\n。；;]+)", text):
            raw = m2.group(1)
            for part in re.split(r"[、,/，]|或", raw):
                alias = part.strip().strip("“”\"「」『』《》()（）")
                alias = re.sub(r"^(原名为|注：).*$", "", alias).strip()
                if not alias or alias == name or len(alias) > 24:
                    continue
                # 过滤过长说明
                if "注" in alias and len(alias) > 10:
                    continue
                out.setdefault(alias, set()).add(name)
                # 去掉书名号/引号后的纯名也挂上
                bare = alias.strip("\"'“”")
                if bare and bare != alias:
                    out.setdefault(bare, set()).add(name)
    return {k: sorted(v) for k, v in out.items()}


def _load_manual() -> dict[str, list[str]]:
    path = _aliases_json_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    result: dict[str, list[str]] = {}
    for k, v in data.items():
        key = str(k).strip()
        if not key:
            continue
        if isinstance(v, str):
            result[key] = [v]
        elif isinstance(v, list):
            result[key] = [str(x) for x in v if str(x).strip()]
    return result


def _merge(*maps: dict[str, list[str]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for m in maps:
        for k, vals in m.items():
            bucket = merged.setdefault(k, [])
            for v in vals:
                if v not in bucket:
                    bucket.append(v)
    return merged


def get_alias_map(*, force: bool = False) -> dict[str, list[str]]:
    global _alias_map, _alias_mtime
    with _lock:
        path = _aliases_json_path()
        mtime = path.stat().st_mtime if path.exists() else 0.0
        if _alias_map is not None and not force and mtime == _alias_mtime:
            return _alias_map
        _alias_map = _merge(_BUILTIN, _extract_from_a_class(), _load_manual())
        _alias_mtime = mtime
        return _alias_map


def expand_query(query: str) -> str:
    """把简称扩展进查询字符串，提升 BM25 命中全称文档的概率。"""
    q = (query or "").strip()
    if not q:
        return q
    alias_map = get_alias_map()
    extras: list[str] = []
    # 优先长别名，避免「挑战杯」被「挑战」误伤（这里都是完整别名键）
    keys = sorted(alias_map.keys(), key=len, reverse=True)
    hit_keys: list[str] = []
    for key in keys:
        if key in q:
            hit_keys.append(key)
            for full in alias_map[key]:
                if full not in q and full not in extras:
                    extras.append(full)
    # 英文别名大小写不敏感
    q_upper = q.upper()
    for key in keys:
        if not re.search(r"[A-Za-z]", key):
            continue
        if key.upper() in q_upper and key not in hit_keys:
            hit_keys.append(key)
            for full in alias_map[key]:
                if full not in q and full not in extras:
                    extras.append(full)
    if not extras:
        return q
    return q + " " + " ".join(extras)


def resolve_aliases(query: str) -> list[str]:
    """返回查询中命中的别名对应正式名列表。"""
    q = query or ""
    alias_map = get_alias_map()
    names: list[str] = []
    for key, vals in sorted(alias_map.items(), key=lambda x: len(x[0]), reverse=True):
        if key in q or (re.search(r"[A-Za-z]", key) and key.upper() in q.upper()):
            for v in vals:
                if v not in names:
                    names.append(v)
    return names


def ensure_aliases_template() -> Path:
    """确保 data/knowledge/aliases.json 存在，便于人工增补。"""
    path = _aliases_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        sample = {
            "_comment": "简称/小名 → 正式竞赛名列表。修改后下次检索自动生效。",
            "大挑": ["“挑战杯”全国大学生课外学术科技作品竞赛", "挑战杯"],
            "蓝桥": ["蓝桥杯全国大学生软件和信息技术大赛"],
        }
        path.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
