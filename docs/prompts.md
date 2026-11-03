# Prompt 工程说明

所有 Prompt 集中在 `backend/app/agents/prompts.py`，按节点注入。

**简称/小名**：`REWRITE_PROMPT` + `backend/app/services/knowledge/aliases.py` + `store.search` 扩展。  
人工增补：`backend/data/knowledge/aliases.json`。

**能力定位**：Prompt 强调「工具增强、禁止空拒答」；学校细则无证据时标注待确认，仍要给出可执行建议。

## 设计原则

1. **分类 Prompt 短而严**：只输出意图标识。  
2. **RAG 混合回答**：证据优先；不足用常识补全并标注。  
3. **推荐锁定候选列表**：可补充但须标明非台账。  
4. **预算金额锁定 JSON**：禁止改数；估算写入 assumptions。  
5. **控制面用 fast 模型，生成用主模型**。  
6. **简称可命中全称**：改写 + 别名表。

## 一览

| Prompt 常量 | 用途 |
|-------------|------|
| INTENT_PROMPT | 意图分类 |
| GRADE_PROMPT | 检索片段是否有帮助 |
| REWRITE_PROMPT | 查询改写（含简称→全称） |
| RAG_ANSWER_PROMPT | 知识问答（混合） |
| RECOMMEND_PROMPT | 竞赛推荐 |
| PREP_PROMPT | 备赛计划 |
| REVIEW_PROMPT | 材料初审与答辩题 |
| BUDGET_NARRATE_PROMPT | 预算说明 |
| LOAN_NARRATE_PROMPT | 借款说明 |
| REIMBURSE_PROMPT | 报销整理 |
| STATS_NARRATE_PROMPT | 统计解读 |
| GENERAL_PROMPT | 通用对话与能力说明 |

## 调优建议

- 意图不稳：改 `nodes.classify_intent` 关键词兜底。  
- 简称搜不到：改 `aliases.json`。  
- 仍觉得「弱于直接问 AI」：检查是否误走旧拒答逻辑；确认后端已加载新 `nodes.py`。  
