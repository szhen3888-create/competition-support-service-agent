# 测试报告

> 执行命令：`python scripts/run_acceptance_tests.py`  
> 机器可读结果：`backend/data/exports/acceptance_report.json`  
> 最近一次执行：2026-10-26，**10/10 通过**

## 1. 测试范围

| 模块 | 内容 |
|------|------|
| 知识问答 | BM25 检索；Agent `knowledge_qa`；引用/拒答策略 |
| 数据统计 | SQL 聚合；Agent `stats_query` |
| 推荐 | 台账匹配；Agent `recommend` |
| 财务 | 乘法汇总正确性；报销缺失项规则 |
| 导出 | Excel / Word 非空文件 |
| 多步 Agent | 财务意图生成与金额一致 |

## 2. 最近一次结果

| ID | 用例 | 结果 | 摘要 |
|----|------|------|------|
| T1 | finance_math | PASS | total=1850.0 |
| T2 | reimbursement_check | PASS | 正确检出缺失材料 |
| T3 | knowledge_search | PASS | 命中「2026程序设计竞赛通知」 |
| T4 | stats_sql | PASS | comps=3 parts=5 |
| T5 | recommend_match | PASS | 软件工程+算法 → 程序设计竞赛 |
| T6 | export_files | PASS | xlsx/docx 已生成 |
| T7 | agent knowledge_qa | PASS | 截止时间回答正确 |
| T8 | agent stats_query | PASS | 2025：竞赛2/参赛4/获奖3 |
| T9 | agent recommend | PASS | 输出排序推荐 |
| T10 | agent finance_assist | PASS | 生成预算说明且基于结构化计算 |

## 3. 人工抽检清单（演示）

- [ ] 知识问答引用可点开对照原文  
- [ ] 无文档时拒答  
- [ ] 数据分析图与导出一致  
- [ ] 工作台下载 Word/Excel 可打开  
- [ ] API 配置页切换 Provider 后连通  

## 4. 已知限制

1. 检索默认 BM25（见 `configs/rag.yaml`），未强制在线 Embedding。  
2. 材料初审规则层为关键词命中，复杂表述需教师复核。  
3. 财务草稿不替代正式审批。  
