---
name: tencent-docs
description: >-
  腾讯文档（docs.qq.com）— 咨询侠专用精简版。
  创建智能文档（专业推荐 / 复盘报告）、搜索已有文档、导入本地文件、管理文档权限。
homepage: https://docs.qq.com/home
version: 2.0.0
author: 咨询侠（基于 tencent-docs 1.0.31 精简）
---

# 咨询侠·腾讯文档 MCP 使用指南

> 本文档是 `tencent-docs` MCP Skill 的**咨询侠专用精简版**。
> 移除了与高考志愿咨询无关的功能（Excel/PPT/脑图/流程图/智能表格/知识空间/Word引擎）。
> 只保留咨询侠实际需要的：**智能文档 + 文件管理 + 公共接口**。

---

## 支持的功能

| 功能 | 说明 | 咨询侠用途 |
|------|------|-----------|
| 智能文档（smartcanvas） | 创建排版美观的在线文档，MDX 格式 | 专业推荐文档、AI 复盘报告 |
| 文件搜索 | 按关键词搜索已有文档 | 查找之前创建的文档 |
| 文件导入 | 本地文件上传为在线文档 | 导入考生资料等 |
| 文档权限 | 设置文档分享权限 | 创建后设为"所有人可读"分享给考生 |
| 公共接口 | 读取文档内容、上传图片、网页剪藏 | 读取/处理文档内容 |

---

## 快速配置

首次使用需完成认证，详见 `references/auth.md`。

---

## 场景路由

| 你要做什么 | 用什么 | 参考文档 |
|-----------|--------|---------|
| 创建专业推荐 / 复盘报告 | `smartcanvas` MDX 创建 | `smartcanvas/entry.md` |
| 编辑已创建的文档 | `smartcanvas.edit` | `smartcanvas/entry.md` |
| MDX 格式怎么写 | 组件与语法参考 | `smartcanvas/mdx_references.md` |
| 搜索已有文档 | `manage.search_file` | `references/manage_references.md` |
| 导入本地文件 | `import_file.sh` + `manage.async_import` | `references/manage_references.md` |
| 设置文档为可分享 | `manage.set_privilege` | `references/manage_references.md` |
| 读取文档内容 | `get_content` | `references/workflows.md` |
| 上传图片到文档 | `upload_image` | `references/workflows.md` |
| 网页剪藏 | `scrape_url` | `references/workflows.md` |

---

## 核心工作流

### 创建文档并分享（最常用）

```
1. smartcanvas.create_smartcanvas_by_mdx
   → 传入 title + MDX 内容
   → 返回 file_id + url

2. manage.set_privilege
   → 传入 file_id，policy=2（所有人可读）
   → 分享 url 给考生
```

### 导入本地文件为在线文档

```
1. bash import_file.sh <文件路径>
   → 脚本自动完成预导入 + COS 上传
2. manage.async_import
   → 传入返回的 task_id/file_key 等
3. manage.import_progress
   → 轮询直到 progress=100，获取 file_url
```

---

## 遵循原则

1. **smartcanvas 优先**：新文档默认使用 smartcanvas via MDX，排版美观、链接分享体验好
2. **创建即分享**：生成专业推荐 / 复盘报告后，自动设置为所有人可读
3. **不碰已移除功能**：Excel/PPT/脑图/流程图/智能表格/知识空间/Word引擎等已从 Skill 移除，不可用
