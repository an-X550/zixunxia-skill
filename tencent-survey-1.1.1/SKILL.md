---
name: tencent-survey
description: >-
  腾讯问卷（wj.qq.com）— 咨询侠专用精简版。
  创建问卷（题目包一键导出）、获取问卷详情、查看考生作答、更新题目。
homepage: https://wj.qq.com
version: 2.0.0
author: 咨询侠（基于 tencent-survey 1.1.1 精简）
---

# 咨询侠·腾讯问卷 MCP 使用指南

> 本文档是 `tencent-survey` MCP Skill 的**咨询侠专用精简版**。
> 移除了自动更新机制，聚焦咨询侠核心场景：题目包 → 问卷 → 回收答案。

---

## 触发场景

以下情况应激活本 skill：
- 咨询侠工作流中的「导出腾讯问卷」「创建在线问卷」
- 用户提供了 `wj.qq.com` 链接
- 需要查看考生作答

| 用户表述 | 判断方式 |
|---------|---------|
| 「导出腾讯问卷」 | 调用 create_survey，scene=1 |
| 「看看问卷的回答」 | 调用 list_answers |
| 「我有个问卷链接…」 | 解析链接提取 survey_id，调用 get_survey |
| 「修改问卷的第X题」 | 先 get_survey 获取 question_id，再 update_question |

---

## 配置

**在首次调用工具前**，完成鉴权检查（详见 `references/auth.md`）：

### 方式一：环境变量（推荐）

```bash
TENCENT_SURVEY_TOKEN=xxx bash "${SKILL_DIR}/setup.sh" wj_check_and_start_auth
```

输出 `READY` 即就绪。

### 方式二：OAuth 设备授权

```bash
bash "${SKILL_DIR}/setup.sh" wj_check_and_start_auth
```

按提示完成授权流程。

> 鉴权通过后同一会话内无需重复。工具返回 `invalid_token` 时才需重新鉴权。

---

## 工具列表

| 工具 | 用途 | 参考文档 |
|------|------|---------|
| `create_survey` | 用纯文本 DSL 创建问卷 | `references/create_survey.md` |
| `get_survey` | 获取问卷详情（含题目和选项） | `references/get_survey.md` |
| `list_answers` | 获取考生回答（支持分页） | `references/list_answers.md` |
| `update_question` | 修改问卷中的某道题 | `references/update_question.md` |
| `update_logic` | 设置条件逻辑（跳题/显示/隐藏） | `references/update_logic.md` |

---

## URL 解析

问卷投放链接格式：`https://wj.qq.com/s2/{survey_id}/{hash}`

取路径第二段为 `survey_id`。

---

## 咨询侠常用工作流

### 题目包 → 问卷

```
1. 按 DSL 语法将题目包转为 text（详见 create_survey.md）
2. create_survey(text=..., scene=1) → 返回 survey_id + hash
3. 拼接链接：https://wj.qq.com/s2/{survey_id}/{hash}
```

### 回收考生答案

```
1. list_answers(survey_id=...) → 返回答案列表
2. 如果 list.length == per_page，用 last_answer_id 翻页
3. 解析每条 answer 的嵌套结构
```

### 调整问卷题目

```
1. get_survey(survey_id=...) → 获取 question_id
2. update_question(survey_id=..., question_id=..., text=...)
```

---

## 注意事项

- **text 必填**：换行用 `\n`，选项不需要字母前缀
- **分页**：list_answers 使用游标分页，注意翻页
- **update_logic 整体覆盖**：追加逻辑需先获取当前 survey_dsl.code
- **非幂等**：create_survey 每次调用创建新问卷

## 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `missing_token` | 未鉴权 | 重新执行配置流程 |
| `invalid_text_format` | DSL 语法错误 | 检查 text 格式 |
| `claim_error` | 问卷不属于当前团队 | 确认问卷 ID 正确 |
| `survey_not_editable` | 问卷正在回收中 | 先暂停问卷 |
