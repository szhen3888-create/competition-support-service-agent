# 竞赛辅助服务智能体

面向高校竞赛全生命周期的 AI Agent：知识问答、竞赛推荐、备赛/材料指导、预算借款报销草稿、台账统计与可视化导出、智能组队。

**新手请直接看：** [`docs/新手部署与使用指南.md`](docs/新手部署与使用指南.md)（可转发给同事）

- 产品方案：[`docs/产品方案.md`](docs/产品方案.md)
- 十项需求用法：[`docs/十项需求使用说明.md`](docs/十项需求使用说明.md)
- 部署手册：[`docs/deploy.md`](docs/deploy.md)
- 用户手册：[`docs/user_guide.md`](docs/user_guide.md)

## 技术栈

| 层 | 技术 |
|----|------|
| LLM | DeepSeek（可切换 Qwen/豆包/OpenAI 兼容） |
| Agent | LangGraph |
| RAG | jieba + BM25 + 强制引用 |
| 后端 | Python + FastAPI |
| 数据 | SQLite（可切 MySQL）+ 文件型知识库 |
| 前端 | Vue 3 + Element Plus + ECharts |

## 快速开始（Windows）

### 一键启动

```powershell
cd 学校智能体
.\scripts\start-all.ps1
```

首次会生成 `backend\.env`，请填入自己的 `LLM_API_KEY` 后再跑一次。

### 手动启动

**1. 后端**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
copy .env.example .env
# 编辑 .env 填入 LLM_API_KEY

$env:PYTHONPATH="."
python scripts/seed_samples.py
python scripts/seed_ledger.py
python scripts/seed_team_users.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

**2. 前端**

```powershell
cd frontend
npm install --registry https://registry.npmmirror.com
npm run dev -- --host 127.0.0.1 --port 5173
```

- 前端：http://127.0.0.1:5173  
- API 文档：http://127.0.0.1:8001/docs  

### 演示账号（智能组队）

| 角色 | 账号 | 密码 |
|------|------|------|
| 老师 | teacher1 | teacher123 |
| 学生 | stu1～stu6 | stu123 |

## 功能入口

| 页面 | 能力 |
|------|------|
| 智能对话 | 全意图 Agent |
| 知识库 | 通知/规程导入与启停 |
| 竞赛台账 | 竞赛与参赛获奖 CRUD |
| 数据分析 | KPI / ECharts / Excel 导出 |
| 材料工作台 | 备赛计划、初审、预算/借款/报销 |
| 智能组队 | 师生登录、活动报名、AI 组队与指导队伍 |
| API 配置 | Provider 热切换与连通测试 |

## 目录

详见 [`docs/目录说明.md`](docs/目录说明.md)。

```
├── backend/              # FastAPI + Agent + RAG + 种子脚本
├── frontend/             # Vue 前端
├── knowledge/            # 知识库源 Markdown
├── scripts/start-all.ps1 # 一键启动
├── scripts/kb/           # 知识库抓取/入库工具
├── docs/                 # 文档
├── configs/ · sql/ · docker-compose.yml
```

## 发给别人 / 上传 GitHub 时

- **发**：代码 + `docs/新手部署与使用指南.md` + `docs/目录说明.md`
- **别发 / 已在 .gitignore**：`backend/.env`（含 API Key）、`.venv/`、`node_modules/`、`*.db`、`exports/`、`uploads/`
- 克隆后请 `copy backend\.env.example backend\.env`，自行填写 `LLM_API_KEY`
- 演示账号密码见文档，仅供本地试用，上线请改密并更换 `JWT_SECRET`
