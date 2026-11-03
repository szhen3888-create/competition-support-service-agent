# 系统部署手册

## 环境要求

- Windows / Linux / macOS
- Python 3.11+（本机已用 3.12 验证）
- Node.js 18+
- （可选）Docker / Docker Compose

## 本地开发部署

### 1. 后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
copy .env.example .env
# 编辑 .env：填入 LLM_API_KEY
$env:PYTHONPATH="."
python scripts/seed_samples.py
python scripts/seed_ledger.py
python scripts/seed_team_users.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```


### 2. 前端

```powershell
cd frontend
npm install --registry https://registry.npmmirror.com
npm run dev -- --host 127.0.0.1 --port 5173
```

访问：http://127.0.0.1:5173  
API 文档：http://127.0.0.1:8001/docs  

> `frontend/vite.config.js` 默认把 `/api` 代理到 `8001`。

### 3. Docker Compose

```powershell
# 先准备 backend/.env
docker compose up -d --build
```

- Web：http://127.0.0.1:8080  
- API：http://127.0.0.1:8000  

## 配置清单

| 变量 | 含义 |
|------|------|
| LLM_PROVIDER | deepseek / qwen / doubao / openai_compatible |
| LLM_API_KEY | 密钥 |
| LLM_BASE_URL / LLM_MODEL | 接口与模型 |
| DATABASE_URL | sqlite 或 mysql |
| KNOWLEDGE_DIR | 知识库目录 |
| RAG_TOP_K / RAG_MAX_REWRITE | 检索参数 |

## 数据目录

```
backend/data/
  competition_agent.db
  knowledge/
  exports/
  uploads/
  samples/
```

请定期备份 `competition_agent.db` 与 `knowledge/`。

## 切换 MySQL

1. 创建库 `competition_agent`  
2. `.env` 设置 `DATABASE_URL=mysql+pymysql://user:pwd@host:3306/competition_agent`  
3. 重启后端（自动建表）  
4. 重新执行 seed 脚本（如需要）  
