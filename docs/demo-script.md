# Demonstration Script / 项目展示流程

## 60 秒介绍

NEXUS ALPHA 是一个 evidence-first 的 AI 投研操作系统：将 SEC 原始申报数据转成可追溯的结构化证据，并计划进一步支持 AI 多角度研究、争议裁决和动态投资假设。

当前仓库展示**真实可运行的技术切片**，并没有声称 Web 产品已经完成。

## 终端演示

1. 展示 README 中的产品闭环及系统架构图。
2. 运行 `python -m unittest discover -s tests -v`，确认解析与 as-of 逻辑通过。
3. 在允许访问 SEC 官方 API 的环境中，配置**真实** User-Agent：

   ```bash
   export SEC_USER_AGENT="NexusAlpha Research YOUR_VALID_EMAIL"
   nexus-alpha fetch NVDA --output output/nvda.json
   ```

4. 在生成的 JSON 中展示 `value`、`period_start`、`period_end`、`filed`、`accession`、`concept`、`source.url`。
5. 解释为何 10-Q 不能不加区分地被称作“单季度数据”。
6. 展示 [research-adjudication.md](research-adjudication.md) 的研究裁决方案。

## 发给潜在支持者的一段话

> 我没有先堆砌几十个静态页面，而是从最重要的数据可信度切入。NEXUS ALPHA 的第一段可运行代码已经完成 SEC EDGAR 的 ticker 映射、Company Facts 获取、财务事实结构化、as-of 时间过滤和原始来源追踪，配套离线测试与可审阅的架构设计。下一步会以 NVDA 为例，跑通 API → PostgreSQL → Next.js 研究页 → 带引用的 AI 财报分析。

如果尚未完成真实网络验收，请明确告知“实现已完成，在线链路待验证”。
