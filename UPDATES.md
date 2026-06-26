# 更新日志

> 倒序时间线，记录每次改动的摘要和受影响文件。

---

---
---
## 2026-06-26

### README.md 重写 — 部署流程 + 全流程使用指南 ✅
- **摘要**：面向新咨询侠接手项目，重写 README.md。新增部署三步（解压→setup.bat→设置Key）、全流程概览图（六阶段）、日常指令速查（按场景分组）、文件结构更新（反映 v2.6.0 完整目录树）、自然语言推断扩展（含批量触发词）、技术栈一览
- **状态**：已完成
- **开始时间**：2026-06-26T20:00
- **受影响文件**：`README.md` — 完全重写

### 部署与批量交互优化 ✅
- **摘要**：7项优化降低部署门槛、简化批量操作——.mcp.json 改为相对路径、config.py API Key 缺失提示、setup.bat 一键安装、batch/nodes.py 汇总打印跟进指令、output_writer.py 生成跟进.txt、SKILL.md 批量触发词+行为规则、data_loader.py 纯文本输入解析（中英文标签）
- **状态**：已完成
- **开始时间**：2026-06-26T19:30
- **实际产出**：
  - `.mcp.json` — 绝对路径改为相对路径（`./mcp-server/server.py` + `ZIXUNXIA_SKILL_DIR=.`），解耦用户目录
  - `batch/config.py` — API Key 未设置时打印提示（`set DEEPSEEK_API_KEY=...` 或 `.env`）
  - `setup.bat` — 一键安装脚本（阿里云镜像，pip install 5个依赖）
  - `batch/nodes.py` — `summarize_batch_node` 打印需跟进考生列表 + `@咨询侠:切换:xxx` 指令
  - `batch/output_writer.py` — 新增 `write_followup_txt()`，为需跟进考生生成 `cases/{nickname}/跟进.txt`
  - `SKILL.md` — YAML 新增 `batchKeywords` 8个触发词；自然语言推断表 +3行；新增「批量模式」行为章节
  - `batch/data_loader.py` — 新增 `_parse_plain_text()`，支持 `.txt` 空格分隔 `key=value` + 中文冒号标签
- **受影响文件**：
  - `.mcp.json` — 路径改为相对
  - `batch/config.py` — 新增 API Key 告警提示
  - `setup.bat` — 新建
  - `batch/nodes.py` — summarize 打印扩展
  - `batch/output_writer.py` — 新增 write_followup_txt
  - `SKILL.md` — YAML + 推断表 + 批量章节
  - `batch/data_loader.py` — 新增纯文本解析

### LangGraph 批量并行分析 — 咨询前模块 ✅
- **摘要**：新增 `batch/` 模块，使用 LangGraph `Send` API 实现多考生并行咨询前分析。每个考生独立 StateGraph（上下文隔离），CSV/JSON 批量输入 → Prompt0 → Prompt1 → Prompt2 并行执行。直接复用 `mcp-server/db_queries.py`（不走 MCP 子进程），LLM 调用 DeepSeek API 预注入 SQLite 数据。产物与交互模式完全兼容。
- **状态**：已完成
- **开始时间**：2026-06-26T16:15
- **实际产出**：
  - `batch/` 目录（9 个文件 / ~58KB）
  - `batch/config.py` — 集中配置（路径/API/并发限制）
  - `batch/state.py` — TypedDict 状态定义（StudentInput/StudentState/BatchState）
  - `batch/data_loader.py` — CSV/JSON 解析 + 字段校验 + profile 格式化
  - `batch/db_adapter.py` — 封装 `db_queries.py`（连接管理 + 查询适配）
  - `batch/prompts.py` — 加载/分割/模板化 Prompt0/1/2
  - `batch/output_writer.py` — MD 归档 + goal_state.json + 批量汇总报告
  - `batch/nodes.py` — 节点函数（prompt0/1/2 + LLM 重试 + SQLite 数据预格式化 + orchestrator）
  - `batch/graph.py` — LangGraph 图构建（BatchOrchestrator fan-out）
  - `batch/run_batch.py` — CLI 入口（--dry-run / --resume / --concurrency）
  - `cases/_test_batch_input.csv` — 3 人测试数据
- **架构决策**：
  - 数据走直接 SQLite（复用 `db_queries.py`），不走 MCP 子进程
  - LLM 调用前预注入 SQLite 数据——LLM 只管推理不做工具调用
  - 批量模式跳过交互式补问循环——低置信度标记 followup
  - 每考生独立 StateGraph 实例，无状态泄漏
  - 新依赖：`langgraph` + `langchain-core` + `langchain-deepseek`（~5MB）
- **受影响文件**：
  - `batch/` — 全部新建
  - `cases/_test_batch_input.csv` — 新建
  - `PROJECT_STATUS.md` — 计划中 + 技术栈同步
  - `UPDATES.md` — 本条目

### 已知问题演化史写入 CHANGELOG + 文档同步 ✅
- **摘要**：7 个已知问题追溯至出现版本/根因/解决方式，写入 CHANGELOG.md。P3d 考生档案扩展 + SKILL.md 第二轮压缩 + PROJECT_STATUS.md 待办同步
- **受影响文件**：`CHANGELOG.md`、`SKILL.md`、`PROJECT_STATUS.md`

### MCP Server Phase 5 — SQLite 数据库 + 院校专业关联 ✅
- **摘要**：从现有知识库 Markdown 构建 SQLite 数据库（18表/1076行/332KB），新增 query_school_by_major 和 query_major_by_school 两个 MCP 工具
- **状态**：已完成
- **开始时间**：2026-06-26T16:00
- **实际产出**：
  - `mcp-server/build_sqlite.py` — 复用 6 个解析器，将 dict 数据 INSERT 到 SQLite（49ms 构建完成）
  - `mcp-server/server.py` — 新增 2 个 MCP 工具（共 10 个工具）+ SQLite 查询层
  - 18 张表覆盖：专业卡片/分叉/误区/新增专业、院校名单/部委直属、院校-专业强弱关系（506行）、城市层级/类型/产业集群、省份志愿配置、薪资数据源/工具速查/B站资源
  - core relation: `school_major_strength` 表从部委直属 + 专业卡片典型方向两个来源提取院校-专业关联
  - SKILL.md 工具速查表 +2 行（10 个工具）
- **受影响文件**：
  - `mcp-server/build_sqlite.py` — 新建
  - `mcp-server/server.py` — 新增 2 工具定义 + 2 handler + SQLite helper（+170行）
  - `SKILL.md` — 工具速查表新增 2 行
  - `PROJECT_STATUS.md` — 已完成功能 + 计划中 + 技术栈 + 已知问题 #3
  - `CHANGELOG.md` — v2.5.0 路线图
  - `UPDATES.md` — 本条目

### 文档修正：移除虚假的 撑伞侠知识库.db 前提 ✅
- **摘要**：确认 `撑伞侠知识库.db` 实际不存在，移除 PROJECT_STATUS.md / CHANGELOG.md / CLAUDE.md 中基于此虚假前提的内容
- **状态**：已完成
- **受影响文件**：
  - `PROJECT_STATUS.md` — 已知问题#3 改写为"专业-院校反向查询能力缺失"；移除 Phase 5 SQLite 计划；移除条件触发中的 SQLite 条目
  - `CHANGELOG.md` — v2.5.0 路线图行改为"待规划"
  - `CLAUDE.md` — 核心边界规则#4 改为"数据源确定后再设计 SQLite 方案"

---
## 版本发布

### v2.4.0 发布 — 2026-06-26 🏗️

**代号**：Goal State Agent Loop

**一句话**：咨询中模块从菜单式指令驱动升级为目标状态驱动的自主 Agent Loop。咨询侠无需再记忆 30+ 触发词逐个点击推进，AI 自动检查状态、决定下一步、推进流程。

**架构变更**：
- 新增 Goal State 自动推进系统（11 目标字段 + 8 级优先级 + Turn 循环）
- 新增自动校验规则 5 条（输出检查/疑问检测/疲惫信号/轮次预算）
- 新增人工审批点 3 个（推荐审核/维度确认/收尾确认）
- 新增 goal_state.json 持久化（完整 JSON schema + 中断恢复）
- 手动模式全兼容（暂停/恢复/跳过）

**里程碑对比**：
| | v2.3.1 | v2.4.0 |
|:--|:--|:--|
| 流程驱动 | 菜单式触发词（30+） | Goal State 自动推进 |
| 咨询侠操作 | 每节点手动输入指令 | 3 个审批点确认即可 |
| 中断恢复 | 靠人记忆 + checkbox | goal_state.json 自动定位 |
| 异常处理 | 靠 LLM 推断 | 5 条结构化校验规则 |
| SKILL.md 行数 | 1155 | 1302 |

详见 [CHANGELOG.md](CHANGELOG.md)。

## 2026-06-26

### Goal State Agent Loop — 咨询中模块目标状态驱动改造 ✅
- **摘要**：将咨询中模块从菜单式指令驱动改造为目标状态驱动的 Agent Loop，基于 Hermes Agent 架构理念。AI 自主检查 goal_state、推进流程，咨询侠无需记忆 30+ 触发词逐个点击
- **状态**：已完成
- **开始时间**：2026-06-26T00:30
- **实际产出**：
  - SKILL.md 咨询中「触发」→ 增加自动推进模式说明
  - SKILL.md 咨询中「行为」→ 菜单式指令改为 Goal State 自动推进（8 优先级队列 + Turn 循环）
  - 新增「咨询中目标状态」定义（11 个目标字段：opening_done → 5 维度 → confirmation → city/school → summary）
  - 新增「自动校验规则」5 条（完整输出检查 / 疑问检测 / 整体确认 / 疲惫信号 / 轮次预算）
  - 新增「人工审批点」3 个（专业推荐审核 / 五维度确认 / 收尾确认）
  - 新增「手动模式兼容」指令：`暂停自动推进` / `恢复自动推进` / `跳过：{目标名}`
  - 改造「状态管理」→ 新增 goal_state.json 持久化规范（完整 JSON schema + 初始化/更新/读取规则）
  - 更新「全局指令」表格（3 条新指令）+「自然语言推断」表格（1 条新规则）+「输出风格」（状态感知替代下一步引导）
  - SKILL.md：1155 行 → 1302 行（+147 行，主要是 Goal State 定义 + 自动校验 + 持久化规范）
- **受影响文件**：
  - `SKILL.md` — 咨询中模块流程控制层重构（话术模板/MCP 工具/方法论不动）
  - `PROJECT_STATUS.md` — 架构/进度/已知问题/关键决策同步更新
  - `UPDATES.md` — 本条目

## 2026-06-25

### 验证测试 ✅
- **摘要**：64/64 项测试全部通过——解析器正确性、8 工具逻辑、数据完整性、回归测试
- **状态**：已完成
- **开始时间**：2026-06-25T21:00
- **测试覆盖**：
  - 6 个解析器：21 项（字段完整性、行数校验、空值检测）
  - 8 个工具逻辑：23 项（精确匹配/模糊匹配/未找到/无效输入/无参数）
  - 数据完整性：4 项（卡片无空值、分支无空值、省份字段完整）
  - 回归测试：11 项（SKILL.md 模块完整、旧引用已清除、.mcp.json 有效、脚本文件存在）
  - 性能：6 文件解析 6-8ms（缓存命中）

### MCP Server Phase 3 — SKILL.md 精简 ✅

### MCP Server Phase 3 — SKILL.md 精简 ✅
- **摘要**：删除数据引用章节、替换嵌入式检索指令为 MCP 工具调用。实际 1191→1155 行（-36行/-3.0%）
- **状态**：已完成
- **开始时间**：2026-06-25T20:30
- **实际产出**：
  - 删除「素材源」章节（41行：知识库路径表 + 外部 Skill 表）
  - 删除「知识库使用指南」章节（24行：模块→文件映射表 + 检索原则）
  - 删除「各维度知识库检索对照」表（12行）
  - 替换 2 处 `检索 \`数据层/XX.md\`` 为 MCP 工具调用指令
  - 新增「数据查询工具（MCP）」章节（35行：8工具速查表 + 知识库文件说明）
  - **计划预估 25% 缩减过于乐观**——实际可删除的数据引用仅占 3%，其余 97% 为编排流程/行为规则/话术模板/集成规范，不可删除
  - 所有关键模块完整：核心身份、首次启动引导、状态管理、模块一二三、在线服务集成、全局指令、输出风格
- **受影响文件**：
  - `SKILL.md` — 精简 36 行

### MCP Server Phase 2 — 全部解析器 + 8 个工具 ✅
- **摘要**：完成剩余 5 个数据文件解析器，实现全部 8 个 MCP 核心工具的注册和分发
- **状态**：已完成
- **开始时间**：2026-06-25T19:50
- **实际产出**：
  - `parsers/salary_tools.py` — 行业薪资与工具箱解析器（8 个数据维度：salary_paths/framework/tools/quadrants/trends/quake/bilibili/toolbox）
  - `parsers/major_decision.py` — 专业决策库解析器（15 个专业卡片 + 12 门类速查 + 45 条名称误区）
  - `parsers/city_industry.py` — 城市产业库解析器（5 层体系 + 5 种类型 + 31 省产业集群 + 13 条专业-城市匹配）
  - `parsers/filling_rules.py` — 填报规则库解析器（23 省模式配置 + 7 类规则主题）
  - `parsers/school_evaluation.py` — 院校评估库解析器（39 所 985 + 96 所 211 + 36 所双一流A + 6 所双一流B + 14 个部委系统）
  - `data_store.py` — 新增全部 6 个解析器调用 + 关键词搜索 `search()` 方法
  - `server.py` — 重写，注册全部 8 个工具 + 统一分发 + 异常处理
  - 性能：全部 6 文件解析 88-163ms，JSON 缓存后 ~0ms
- **受影响文件**：
  - `mcp-server/parsers/salary_tools.py` — 新建
  - `mcp-server/parsers/major_decision.py` — 新建
  - `mcp-server/parsers/city_industry.py` — 新建
  - `mcp-server/parsers/filling_rules.py` — 新建
  - `mcp-server/parsers/school_evaluation.py` — 新建
  - `mcp-server/data_store.py` — 重写
  - `mcp-server/server.py` — 重写

### MCP Server Phase 1 — 基础框架 ✅
- **摘要**：创建 Python MCP 服务器骨架 + `query_major_branches` 工具端到端验证
- **状态**：已完成
- **开始时间**：2026-06-25T19:30
- **实际产出**：
  - `pip install mcp` → `mcp-1.28.0`（阿里云镜像，Python 3.14 兼容性验证通过）
  - `mcp-server/` 目录结构（9 个源文件）
  - `config.py` — 路径配置 + 环境变量注入
  - `parsers/table_utils.py` — Markdown 表格解析（`parse_md_table` / `split_by_headings`）
  - `parsers/major_branches.py` — 专业内部分叉解析器（27 个专业，9ms 解析完成）
  - `data_store.py` — 内存存储 + JSON 缓存（`cache/parsed_data.json` 57KB）
  - `server.py` — MCP stdio 入口 + `query_major_branches` 工具（精确/模糊/未找到三级返回）
  - `.mcp.json` — MCP 服务器注册（`zixunxia-knowledge`，stdio 传输）
- **受影响文件**：
  - `mcp-server/config.py` — 新建
  - `mcp-server/server.py` — 新建
  - `mcp-server/data_store.py` — 新建
  - `mcp-server/parsers/__init__.py` — 新建
  - `mcp-server/parsers/table_utils.py` — 新建
  - `mcp-server/parsers/major_branches.py` — 新建
  - `mcp-server/tools/__init__.py` — 新建
  - `mcp-server/cache/parsed_data.json` — 自动生成（首次 9ms，后续 ~0ms）
  - `.mcp.json` — 新建
  - `c:\Users\panda\.claude\settings.json` — 未修改（`mcpServers` 不在 schema 中，走 `.mcp.json`）

### Stop Hook 配置 ✅
- **摘要**：在 `~/.claude/settings.json` 添加 Stop hook，每次对话结束前自动弹出提醒更新 UPDATES.md 和 PROJECT_STATUS.md
- **状态**：已完成
- **受影响文件**：
  - `c:\Users\panda\.claude\settings.json` — 新增 `hooks.Stop` 配置块

### Bootstrap — 项目文档初始化 ✅
- **摘要**：创建项目状态文件、更新日志和项目规则文件，为后续开发建立文档基础设施
- **状态**：已完成
- **受影响文件**：
  - `PROJECT_STATUS.md` — 新建
  - `UPDATES.md` — 新建
  - `CLAUDE.md` — 新建
