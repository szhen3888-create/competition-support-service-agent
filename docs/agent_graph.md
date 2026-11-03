# Agent 工作流与节点配置

## 框架

- LangGraph `StateGraph`
- 状态：`app/agents/state.py` → `AgentState`（含 `artifacts`）
- 工具层：`app/services/agent_tools.py`
- 编译入口：`app/agents/graph.py` → `get_agent_graph()` / `run_agent()`

## 设计原则

**工具增强，而非限制模型**：知识库与台账提供证据和数字；模型负责理解、规划与表达。证据不足时用常识补全并标注「待确认」，禁止空拒答。

## 流程图

```
START
  → classify_intent
      ├ knowledge_qa → retrieve → grade_documents
      │                    ├ needs_rewrite → rewrite_question → retrieve
      │                    └ generate_rag_answer（混合回答）→ END
      ├ recommend → recommend_answer → END
      ├ prep_assist → prep_answer（+ Word 导出）→ END
      ├ review_assist → review_answer（+ Word 导出）→ END
      ├ finance_assist → finance_answer（+ Word/Excel，可估算）→ END
      ├ stats_query → stats_answer（+ ECharts artifacts）→ END
      └ general → general_answer（可附带知识库摘录）→ END
```

## 节点职责

| 节点 | 数据来源 | 行为 |
|------|----------|------|
| classify_intent | 用户文本 / 上传材料 context | 分类；有 material_text 则强制 review |
| retrieve / grade / rewrite | BM25 + 别名扩展 | 空检索不再死循环；证据弱也生成 |
| generate_rag_answer | 检索片段 + 模型常识 | 证据优先；不足则补全并标注待确认 |
| recommend_answer | competitions 表 + KB | 解释候选；可标非台账补充 |
| prep_answer | 台账 + KB + 导出工具 | 始终出计划；附 Word |
| review_answer | checklist + 正文 + 导出 | 无正文也给模板与答辩题；附 Word |
| finance_answer | 结构化乘法 + 可选估算 | 金额不改数；估算单独标注；附导出 |
| stats_answer | SQL + chart option | 数字来自台账；聊天内出图 |
| general_answer | 通用对话 + 可选 KB | 能力说明与综合问答 |

## Artifacts

`run_agent` / `POST /chat/agent` 返回 `artifacts`：

- `{ type: "file", title, url, filename }` → `/api/v1/exports/...`
- `{ type: "chart", title, option }` → 前端 ECharts

## Prompt 文件

见 `docs/prompts.md` 与源码 `app/agents/prompts.py`。

## 配置项（.env）

- `LLM_*`：模型与温度  
- `RAG_TOP_K` / `RAG_MAX_REWRITE`：检索与改写上限  
- `KNOWLEDGE_DIR`：知识库存放路径  
