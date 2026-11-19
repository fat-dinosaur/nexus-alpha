# Delivery Plan / 开发路线图

## P0 — Honest, reproducible proof of concept

**交付：**

- [x] Product brief and technical architecture
- [x] SEC ticker-to-CIK lookup
- [x] SEC Company Facts ingestion
- [x] Structured snapshot with `accn`, `filed`, `start`, `end`, `unit` and taxonomy concept
- [x] As-of filing cutoff
- [x] Offline unit tests and CI definition
- [x] Offline interactive financial terminal preview with SEC JSON import and local notes
- [ ] Live end-to-end SEC verification (requires outbound SEC access and real User-Agent)

**验收：** 已知 ticker 能生成有来源的 JSON；没有可用真实数据时，不伪造结果。

## P1 — First end-to-end research experience

1. FastAPI `/companies/{ticker}/financials`，读取 SEC Adapter 或持久化表。
2. PostgreSQL、迁移及去重存储，唯一键考虑 `accession + concept + unit + period_start + period_end`。
3. Next.js 公司研究页、指标表和原始来源入口。
4. 用户上传或官方申报文件检索，最小 RAG 问答与段落引用。
5. 端到端测试：查询 NVDA → 查看财务事实 → 对来源核查。

**验收：** 不需要在 UI 里手动粘贴 JSON；用户能看到真实、标明时效的公司财务数据与原始证据。

## P2 — Differentiated AI research

1. 多 Agent 研究任务合同与状态管理。
2. 统一证据账本和原始来源引用。
3. 多空观点裁决器、反证条件、研究成本控制。
4. 用户可保存、重开并审核研究结论。

**验收：** 对同一争议点能指出哪些事实成立、哪些假设相冲突、什么信息可以帮助裁决。

## P3 — Living Thesis

1. Thesis / ThesisVersion / Evidence 数据模型。
2. 研究观点的版本 Diff 和确认流程。
3. 新财报事件触发候选更改，用户审核后采用。
4. 研究事项与关键指标监控（先应用内通知）。

## P4 — Advanced terminal

行业知识图谱、公司比较、量化筛选、估值情景和多市场数据 Provider；受数据授权和质量门槛限制。

## Non-goals for P0

- 不支持真实或模拟下单。
- 不生成自动投资建议。
- 不提供“实时行情”或股票价格预测。
- 不宣称系统已具备自动化监控、多 Agent 或完整 UI。
