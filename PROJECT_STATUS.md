# 咨询侠 — 项目状态

> 最后更新：2026-06-26 | 版本：v2.6.0

---

## 项目概述

**咨询侠**是问问大象团队的「高考志愿咨询 AI 副驾驶」，基于 Claude Code SKILL.md 构建。
AI 定位为**内容生产引擎**，咨询官（人类咨询侠）承担需求翻译和决策过滤的角色。

### 核心原则

> 授人以渔，而非授人以鱼。重点是教考生方法，而非替考生做决定。

### 三大模块

| 模块 | 功能 | 触发 |
|------|------|------|
| **咨询前** — AI 分析引擎 | 信息确认题目包（Prompt0）→ 专业推荐文档（Prompt1）→ 城市推荐文档（Prompt2） | `开始咨询前准备` |
| **咨询中** — 目标状态驱动话术引导 | 五维度专业讲解 + 城市/院校板块 + 答疑 + 总结收尾。**v2.4.0 已升级为 Goal State 自动推进模式**，咨询侠无需手动点击每个节点 | `开始咨询` |
| **咨询后** — AI 复盘 | 手段-目的分析四步复盘（问题→手段→效果→改进） | `开始复盘` |

---

## 技术栈

| 层 | 技术 | 用途 |
|:--|:--|:--|
| 编排定义 | Claude Code SKILL.md（1302行/~68KB） | 全流程控制逻辑 + Goal State 自动推进 + 话术模板 + 行为规则 |
| 知识库 | Markdown ×13 文件（~186KB） | 数据层 6 份（83KB）+ 核心方法论 7 份（103KB） |
| 文档导出 | Python 3.14 + python-docx | MD → DOCX 转换（专业推荐/复盘报告） |
| MCP 集成 | Node.js + mcporter CLI | 腾讯文档（在线文档创建）+ 腾讯问卷（在线问卷创建） |
| MCP 知识查询 | Python 3.14 + mcp SDK + SQLite 3 | 本地知识库 MCP Server（10 个工具：8 数据查询 + 2 院校专业关联） |
| LLM 后端 | DeepSeek API（Anthropic 兼容端点） | deepseek-v4-pro 模型，xhigh effort |

---

## 架构

```
咨询侠v2.5.0/
│
├── SKILL.md                    ← 核心编排文件（1302行/68KB）— Goal State 自动推进 + 话术模板 + 行为规则 + 触发词
├── README.md                   ← 用户速查手册
├── 咨询侠skill使用方法（sop）.md  ← AI使用SOP + 输出验证清单
│
├── 知识库/                      ← 两层知识体系
│   ├── 撑伞侠2026目录.md         ← 总索引 + AI检索优先级表
│   ├── 数据层/（6份，83KB）       ← AI蒸馏速查库
│   │   ├── 专业决策库.md          ← 12门类 + 热门专业卡片（6字段）+ 60+误区表
│   │   ├── 专业内部分叉速查.md     ← 21个内部分叉专业（5列统一表格）
│   │   ├── 院校评估库.md          ← 985/211/双一流 + 7维评估 + 部委直属
│   │   ├── 城市产业库.md          ← 5层格局 + 31省产业集群 + 专业-城市匹配
│   │   ├── 填报规则库.md          ← 投档/退档/调剂/选科/赋分/省模式/稳保策略
│   │   └── 行业薪资与工具箱.md     ← 薪资路径 + 6因素框架 + 就业四象限 + 工具速查
│   └── 核心方法论/（7份，103KB）   ← AI工作流核心文档（未改动）
│       ├── AI提示词模板.md         ← Prompt0/1/2 完整定义
│       ├── 咨询侠AI工作流.md       ← 全流程v2.0 + 新人引导
│       ├── 咨询侠话术与操作指南（培训版）.md ← 完整话术库
│       ├── 咨询侠培训｜咨询思路.md   ← 手段-目的分析法 + 六大根本矛盾
│       ├── 咨询侠AI复盘全流程.md    ← 复盘四步结构
│       ├── humanizer.md            ← 去AI化规则（12类检测标准）
│       ├── 高考志愿填报信息收集清单（咨询侠提问版）.md
│       └── 高考志愿填报信息收集清单（考生版）.md
│
├── script/                      ← Python导出脚本
│   ├── export_docx.py           ← 专业推荐 MD→DOCX
│   ├── export_review_docx.py    ← 复盘报告 MD→DOCX
│   ├── export_career_docx.py    ← 通用 MD→DOCX 转换
│   ├── export_docx_stdlib.py    ← 无python-docx依赖的备选方案
│   ├── convert_docx_to_md.py    ← DOCX→MD 反向转换
│   ├── batch_convert.py         ← PDF/DOCX/DOC 批量转换
│   └── upload_to_tdoc.js        ← MD分块上传腾讯文档
│
├── batch/                        ← 【v2.6.0】LangGraph 批量并行分析
│   ├── config.py                 ← 集中配置（路径/API Key/并发）
│   ├── state.py                  ← TypedDict 状态定义
│   ├── data_loader.py            ← CSV/JSON/TXT 批量输入解析（含纯文本粘贴）
│   ├── db_adapter.py             ← db_queries.py 封装（不走MCP子进程）
│   ├── prompts.py                ← Prompt0/1/2 模板加载
│   ├── output_writer.py          ← MD归档 + goal_state.json + 跟进.txt 写入
│   ├── nodes.py                  ← 节点函数（LLM调用+SQLite预注入+重试）
│   ├── graph.py                  ← LangGraph 双层图构建
│   └── run_batch.py              ← CLI入口
│
├── tencent-docs/                ← 腾讯文档 MCP 子Skill（mcporter HTTP模式）
├── tencent-survey-1.1.1/        ← 腾讯问卷 MCP 子Skill（mcporter HTTP模式）
│
├── cases/                       ← 考生档案目录（按考生分目录，当前为空）
├── 教程/                         ← 3篇新手教程（软件准备/使用指南/项目说明）
│
├── mcp-server/                  ← Python MCP 知识查询服务器（10个工具）
│   ├── server.py                ← stdio MCP 入口 + 10工具注册/分发 + SQLite查询
│   ├── config.py                ← 路径配置（含 DB_PATH）
│   ├── data_store.py            ← 内存存储 + JSON 缓存（8个老工具用）
│   ├── build_sqlite.py          ← 【v2.5.0】MD→SQLite 构建脚本
│   ├── parsers/（6个解析器）     ← Markdown→结构化数据
│   └── 撑伞侠知识库.db           ← 【v2.5.0】SQLite 数据库（18表/1076行/332KB）
│
└── .mcp.json                    ← MCP 服务器注册（zixunxia-knowledge）
```

### 控制流：Goal State 驱动（v2.4.0 新增）

```
咨询官输入 → Claude Code (Agent Loop)
                  │
                  ├── 读取 goal_state.json → 找到第一个未完成目标
                  ├── 调用 MCP 工具获取数据
                  ├── 按话术模板输出节点内容
                  ├── 更新 goal_state.json（标记 ✅）
                  ├── 执行校验规则（疑问/疲惫/轮次预算）
                  └── 下个 turn 重复，直到全部目标完成
```

**人工审批点**：专业推荐审核 / 五维度整体确认 / 收尾确认。其余自动推进。

### 数据流（交互模式）

```
咨询官输入 → Claude Code (Agent Loop)
                  │
                  ├── SKILL.md（规则+编排+Goal State 定义，始终在上下文）
                  ├── goal_state.json（结构化进度状态，每 turn 读写）
                  ├── MCP Server（10 个数据查询工具，按需调用）
                  │     ├── 8 个工具 → 内存 dict（JSON 缓存，88ms 冷启动）
                  │     └── 2 个工具 → SQLite（query_school_by_major / query_major_by_school）
                  ├── 核心方法论文件（话术库/复盘流程/humanizer，按需 Read）
                  ├── Python 脚本（DOCX 导出，execSync 调用）
                  └── mcporter → tencent-docs / tencent-survey（在线服务）
```

### 数据流（批量模式 — v2.6.0 新增）

```
CSV/JSON/TXT 批量输入
    │
    ▼
load_batch: 解析 → 创建 cases/{nickname}/ 目录
    │
    ▼
fan_out: LangGraph Send() × N 并行
    │
    ├── Student Agent 1 ──── prompt0 ──→ prompt1 ──→ prompt2 ──→ finalize
    ├── Student Agent 2 ──── prompt0 ──→ prompt1 ──→ prompt2 ──→ finalize
    └── Student Agent N ──── prompt0 ──→ prompt1 ──→ prompt2 ──→ finalize
                                           │
    ┌──────────────────────────────────────┘
    │  每节点:
    │  1. SQLite 直接查询（batch/db_adapter.py → mcp-server/db_queries.py）
    │  2. LLM 调用 DeepSeek API（预注入 SQLite 数据）
    │  3. 写入 cases/{nickname}/（与交互模式完全兼容）
    ▼
summarize: 批量汇总报告 → cases/_batch_summary_{timestamp}.md
```

### 上下文压力分析

| 组件 | 大小 | 加载方式 | 优化后 |
|------|------|---------|--------|
| SKILL.md | 68KB / 1302行 | 全量 | Goal State 自动推进规则替代 300 行流程控制指令 |
| 数据层 | 83KB | 按需 MCP 工具调用（2-5KB/次） | SQLite 数据库（18表/1076行/332KB）提供结构化关联查询 |
| 方法论层 | 103KB | 按需 Read 全文 | 不变（方法论不能工具化） |
| goal_state.json | <1KB | 每 turn 读写 | 结构化状态，替代手动 checkbox 追踪 |
| **基线上下文** | **~255KB 峰值** | | **~172KB + 按需 MCP**（Goal State + SQLite 替代流程控制和全文检索） |

---

## 当前进度

### 已完成功能

| 模块 | 功能 | 完成度 | 说明 |
|------|------|--------|------|
| 咨询前 | Prompt0 题目包生成 | 100% | ≤15题选择题，5个范围判断 |
| 咨询前 | Prompt1 专业推荐 | 100% | 3-5个专业 + 对比表 + 避坑清单 |
| 咨询前 | Prompt2 城市推荐 | 100% | 专业发展优先的城市推荐框架 |
| 咨询前 | 建联话术 | 100% | 私聊→拉群三段话术→咨询前提醒 |
| 咨询中 | 五维度专业讲解 | 100% | 5段结构（定义→教方法→截图→核实→分析） |
| 咨询中 | 城市/院校板块 | 100% | 三维度城市 + 五维度院校 |
| 咨询中 | 答疑场景 | 100% | 7种场景策略 |
| 咨询中 | 收尾话术 | 100% | 通用总结（必发）+ 定制总结（按需） |
| 咨询中 | 特殊场景 | 100% | 父母干预/考生未到/延时申请 |
| 咨询后 | AI复盘 | 100% | 四步手段-目的分析 |
| 导出 | DOCX生成 | 100% | 专业推荐/复盘报告 Word 导出 |
| 导出 | 腾讯文档在线创建 | 100% | 智能文档创建 + 分享链接 |
| 导出 | 腾讯问卷创建 | 100% | 题目包 → 在线问卷 + 投放链接 |
| 辅助 | 人机感检测 | 100% | 12类AI写作痕迹检测 + 优化 |
| 咨询中 | Goal State 自动推进 | 100% | 目标状态驱动 Agent Loop + goal_state.json 持久化 + 自动校验 + 人工审批点 |
| 辅助 | 进度管理 | 100% | goal_state.json 状态追踪 + MD checkbox 双轨同步 |
| 辅助 | 考生档案管理 | 100% | MD档案 + goal_state.json + 中断恢复 + 自动追加产出 |
| MCP | SQLite 数据库构建 | 100% | 18表/1076行/332KB，build_sqlite.py 从知识库MD构建 |
| MCP | 专业-院校反向查询工具 | 100% | query_school_by_major + query_major_by_school 两个新MCP工具 |
| 部署 | 一键安装脚本 | 100% | `setup.bat` — pip install 5项依赖（阿里云镜像） |
| 部署 | 相对路径解耦 | 100% | `.mcp.json` 改为 `./mcp-server/server.py`，不依赖绝对路径 |
| 批量 | 纯文本输入解析 | 100% | 支持 `.txt` 空格分隔 + 中文冒号标签粘贴 |
| 批量 | 跟进标记与追踪 | 100% | 批量汇总打印 `@咨询侠:切换:xxx` + 生成 `跟进.txt` |
| 批量 | Claude Code 内触发 | 100% | SKILL.md 批量触发词 + 自然语言推断 + 行为规则

### 计划中

| 任务 | 状态 | 计划文件 |
|------|------|---------|
| MCP Server Phase 1 — 基础框架 | ✅ 已完成 | `plans/mcp-skill-plan-peppy-duckling.md` |
| MCP Server Phase 2 — 全部解析器 + 8 工具 | ✅ 已完成 | 同上 |
| MCP Server Phase 3 — SKILL.md 精简 | ✅ 已完成（1305→1141行/-12.6%） | 同上 |
| MCP Server Phase 4 — Goal State Agent Loop | ✅ 已完成 | `plans/ai-hermes-agent-loop-curried-patterson.md` |
| MCP Server Phase 5 — SQLite 数据库 + 院校专业关联 | ✅ 已完成（MCP工具10个，18表/1076行） | 本对话 |
| **P1b** Windows编码修复 | ✅ 已完成 | `server.py` UTF-8强制 + `encoding_check.py` |
| **P2a** 双数据源统一 | ✅ 已完成 | `db_queries.py` + 8 handler SQLite迁移 |
| **P2b** SKILL.md上下文精简 | ✅ 已完成（1305→1141行/-12.6%） | 去重/并表/压缩引导 |
| **P2c** 五维度时延优化 | ✅ 已完成 | MCP调用优化指导 |
| **P3a** 解析器单元测试 | ✅ 已完成 | 9文件/40用例/pytest |
| **P3b** MCP延迟基准 | ✅ 已完成 | `benchmark.py` |
| **P3c** 首次启动依赖检查 | ✅ 已完成 | `check_deps.py` |
| **P3d** 考生档案扩展 | ✅ 已完成 | `candidate_profile` 结构化约束 |
| **P4a** LangGraph 批量并行分析 | ✅ 已完成 | `plans/langgraph-structured-valiant.md` |

---

## 待办事项

### 高优先级
- [x] **Phase 1**: 搭建 Python MCP Server 基础框架 ✅
- [x] **Phase 2**: 完成全部 6 个数据文件解析器 + 8 个 MCP 工具 ✅
- [x] **Phase 3**: SKILL.md 精简（1191→1155 行）✅

### 条件触发
- [ ] 专业-院校反向查询增强版（需先获取外部全量专业-院校关联数据源。当前 v2.5.0 基础版已有 506 行关联，可满足基本查询）

### 中优先级
- [x] `pip install mcp` — ✅ mcp-1.28.0 在 Python 3.14.4 已验证
- [x] 首次启动引导增加 MCP 依赖检查 — ✅ `check_deps.py` 已交付
- [x] Windows stdio 编码兼容性测试 — ✅ `server.py` 已加 UTF-8 强制 + `encoding_check.py`
- [x] 在 `~/.claude/settings.json` 注册 MCP Server — ⚠️ 不需要：走 `.mcp.json` 注册，Claude Code 自动管理

### 低优先级
- [x] 解析器单元测试（pytest）— ✅ 9文件/40用例已交付
- [x] MCP 工具调用延迟基准测试 — ✅ `benchmark.py` 已交付
- [ ] DeepSeek 模型工具调用质量评估（P1a，用户明确跳过）

### 条件触发
- [x] ~~如 `mcp` SDK 不兼容 Python 3.14~~ — ✅ 已验证兼容，此项关闭

---

## 已知问题

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| 1 | **上下文膨胀**：SKILL.md 从 1305→1141 行（-12.6%），数据走 10 个 MCP 工具按需查询 | 大幅缓解，40分钟咨询后期注意力衰减风险降低 | ✅ 已优化 |
| 2 | **数据幻觉风险**：LLM 凭记忆回答专业数据 | 10 个 MCP 工具提供结构化查询，幻觉风险根除 | ✅ 已解决 |
| 3 | **专业-院校反向查询能力**：v2.5.0 已实现基础版（506 行关联），增强版待外部数据源 | 基础查询已可用，全量覆盖待外部数据 | ⚠️ 部分解决 |
| 4 | **DeepSeek 工具调用质量未知**：MCP 工具调用可靠性未经测试 | 工具调用可能不稳定 | P1a 被用户明确跳过，实际使用中观察 |
| 5 | **Python 3.14 兼容性** | — | ✅ 已解决 — `mcp-1.28.0` 在 Python 3.14.4 正常运行 |
| 6 | **Windows 编码**：stdio MCP 中文 JSON 在 Windows 下可能乱码 | 已加 UTF-8 强制 + encoding_check.py | ✅ 已解决 |
| 7 | **Goal State 自动推进可靠性**：DeepSeek 自主推进未测试 | 自动推进可能出错 | 实际使用中观察（与 #4 同源） |

---

## 关键决策记录

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-06-25 | **数据走MCP、规则留SKILL.md** — 不把方法论工具化 | 方法论是行为约束需始终在场；数据是按需查询的 |
| 2026-06-25 | **Python MCP SDK (stdio) 而非 mcporter** — 本地知识库工具用 stdio 模式 | 本地数据无需 auth/网络；Claude Code 自动管理进程生命周期 |
| 2026-06-25 | **8个核心MCP工具，SQLite工具条件触发** — 数据库不存在时不开发 | 避免浪费；当前环境未找到 .db 文件 |
| 2026-06-25 | **启动时全量解析 + JSON缓存** — 不按需解析 | 83KB 解析 300-500ms；缓存后 50ms；按需解析延迟不可接受 |
| 2026-06-25 | **正则+规则解析，不用 embeddings** — 不做向量检索 | 83KB 不值得建向量库；大部分已是结构化表格 |
| 2026-06-25 | **SKILL.md 只做减法不做重写** — 精简到 ~900行 | 经过实战验证的编排文件，不做结构性改动 |
| 2026-06-25 | **tencent-docs/tencent-survey 保持 mcporter 模式不动** — 两种MCP模式共存 | 远程HTTP API需要auth，适合mcporter；本地数据适合stdio |
| 2026-06-25 | **MCP 注册走 .mcp.json 而非 settings.json** — `mcpServers` 不在 settings.json schema 中 | settings.json 只管理 `enabledMcpjsonServers`；服务器定义放 `.mcp.json` |
| 2026-06-26 | **目标状态驱动 > 硬编码状态机** — 咨询中流程用 Goal State Agent Loop，不用 LangGraph 式编译图 | 咨询场景分支多、无法预先枚举；目标状态 + 自然语言规则让 LLM 自主选路径，灵活性远高于硬编码图 |
| 2026-06-26 | **自动推进 + 人工审批点混合** — 日常节点 AI 自动推进，关键节点等人确认 | 既减少咨询侠的手动指令负担（30+ 触发词），又保留人在回路的决策权（专业推荐审核/收尾确认） |
| 2026-06-26 | **goal_state.json 双轨制** — 与 MD 档案共存，不替代 | MD 档案是人类可读的咨询记录；goal_state.json 是结构化的机器状态。两者各司其职，互不替代 |
| 2026-06-26 | **Claude Code 内触发批量** — 通过 SKILL.md 触发词+自然语言推断，无需打开终端 | 用户粘贴数据即可自动创建文件并执行 `run_batch.py`，降低使用门槛。命令行模式保留作为备用 |
| 2026-06-26 | **相对路径解耦 MCP 注册** — `.mcp.json` 使用相对路径而非绝对路径 | 项目 zip 分发给不同用户后，绝对路径会失效；相对路径以项目目录为基准，开箱即用 |
| 2026-06-26 | **纯文本输入优于 CSV** — 批量数据优先采用空格分隔的 key=value 纯文本 | 用户从微信/聊天记录粘贴学生信息更方便，且中文标签（省份：广东）比 CSV 英文列名更直观 |
