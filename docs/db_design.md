# 数据库设计说明

## 1. 选型

- 开发默认：`SQLite`（`backend/data/competition_agent.db`），零依赖可运行  
- 生产可切换：在 `.env` 设置 `DATABASE_URL=mysql+pymysql://user:pwd@host:3306/competition_agent`  
- ORM：SQLAlchemy 2.x；启动时 `init_db()` 自动建表  

## 2. ER 概览

```
competitions 1───* participations
finance_drafts（独立草稿）
workspace_drafts（独立草稿）
知识库文档/分块：JSON 文件存储于 data/knowledge/（非 SQL）
```

## 3. 表结构

### competitions（竞赛台账）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| name | VARCHAR(200) | 竞赛名称 |
| level | VARCHAR(50) | 国家级/省级/校级 |
| category | VARCHAR(80) | 类别 |
| major_tags | VARCHAR(255) | 面向专业，逗号分隔 |
| grade_range | VARCHAR(80) | 年级范围 |
| tech_direction | VARCHAR(120) | 技术方向 |
| organizer | VARCHAR(120) | 主办方 |
| year | INTEGER | 年度 |
| register_deadline | DATE | 报名截止 |
| contest_date | DATE | 比赛日期 |
| location | VARCHAR(120) | 地点 |
| fee | FLOAT | 报名费（结构化，供预算引用） |
| award_setting | TEXT | 奖项设置描述 |
| materials | TEXT | 报名材料清单 |
| description | TEXT | 简介 |
| status | VARCHAR(30) | 报名中/已结束等 |
| created_at | DATETIME | |

### participations（参赛/获奖）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| competition_id | FK → competitions.id | |
| year | INTEGER | |
| student_name / student_id | | 学生信息 |
| major / grade | | 专业年级 |
| team_name | | 团队 |
| instructor | | 指导教师 |
| project_title | | 项目名称 |
| award_level | | 参赛/一等奖/… |
| award_rank / remark | | 名次与备注 |

### finance_drafts

预算/借款/报销草稿：`kind`、`title`、`payload_json`、`content_md`、`export_path`。

### workspace_drafts

备赛计划/材料初审草稿：`kind`、`title`、`content_md`、`meta_json`、`export_path`。

## 4. 知识库存储（文件）

目录：`backend/data/knowledge/`

- `documents.json`：文档元数据  
- `chunks.json`：分块正文  
- `files/`：原始上传文件  

检索：jieba 分词 + BM25（见 `configs/rag.yaml`）。

## 5. 数据原则

1. **统计数字只来自 SQL 聚合**，禁止 LLM 生成人次/奖级数量。  
2. **预算金额只来自用户单价 × 数量或台账 fee 字段**，禁止模型改数。  
3. **政策条文只来自知识库检索片段 + 引用**。  
