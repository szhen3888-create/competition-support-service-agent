# LLM API 配置说明

## 设计目标

后台通过统一的 **Provider 抽象层** 接入大模型，默认 DeepSeek，也可切换：

- `deepseek` → `https://api.deepseek.com`
- `qwen` → 阿里云百炼兼容模式
- `doubao` → 火山方舟
- `openai_compatible` → 任意 OpenAI Chat Completions 兼容服务

业务代码只依赖 `LLMProvider.chat()` / `chat_stream()`，不直接绑定某一家 SDK。

## 配置方式

### 1. 环境变量（推荐，持久化）

复制并编辑 `backend/.env`：

```env
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-你的密钥
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
LLM_TEMPERATURE=0.3
```

### 2. 管理接口（运行时热更新）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/llm/config` | 查看当前配置（Key 脱敏） |
| GET | `/api/v1/llm/providers` | 列出预置厂商 |
| PUT | `/api/v1/llm/config` | 热更新 Provider / Key / Model |
| POST | `/api/v1/llm/test` | 发送探测消息验证连通 |

前端「API 配置」页已对接以上接口。

> 热更新写入进程环境变量，进程重启后仍以 `.env` 为准。正式环境请同步改 `.env`。

## 代码位置

```
backend/app/llm/
  base.py                      # 抽象接口
  factory.py                   # 按配置创建 Provider
  providers/openai_compatible.py  # OpenAI 兼容实现（DeepSeek 等共用）
```
