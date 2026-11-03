# 赛氪竞赛知识库（2026–2027）

来源：赛氪竞赛广场公开接口 + 详情页正文。

## 目录

| 路径 | 说明 |
|------|------|
| `index.json` | 索引（标题、链接、年份、时间、对应 md） |
| `contests/*.md` | 单场赛事 Markdown |
| `赛氪竞赛总览.md` | 总览文档 |

> 抓取过程中的 `raw/`、`list_all.json` 为中间缓存，已清理；需要时可重新生成。

## 更新

```powershell
# 在项目根目录
.\backend\.venv\Scripts\python.exe scripts\kb\fetch_saikr_contests.py
.\backend\.venv\Scripts\python.exe scripts\kb\ingest_saikr_kb.py
```

说明：公开站上明确标注 **2027** 的条目通常较少；本库按标题/URL/时间戳落入 2026–2027 收录。
