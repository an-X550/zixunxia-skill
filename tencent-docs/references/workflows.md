# 咨询侠·腾讯文档 — 公共接口与常用工作流

> 精简版：仅保留咨询侠实际使用的工作流。
> 完整版历史见原 tencent-docs skill 分发包。

---

## 公共接口

### get_content

获取文档完整内容（所有文档类型通用）。

```json
{"file_id": "doc_1234567890"}
```

返回：`content`（文档的 Markdown 内容）

---

### upload_image

上传图片，返回有效期一天的 imageID，用于智能文档中嵌入图片。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_base64` | string | ✅ | 图片 base64 编码（非文件路径） |
| `file_name` | string | ✅ | 文件名，如 `photo.png` |

```json
{"image_base64": "iVBORw0KGgo...", "file_name": "screenshot.png"}
```

返回：`image_id`

---

## 咨询侠常用工作流

### 工作流一：创建专业推荐 / 复盘报告并分享

```
1. create_smartcanvas_by_mdx（传入标题 + MDX 内容）→ 返回 file_id + url
2. manage.set_privilege（传入 file_id，policy=2 所有人可读）→ 分享给考生
```

### 工作流二：搜索已有文档

```
manage.search_file（传入关键词）→ 从返回列表获取 file_id
```

### 工作流三：读取文档内容

```
get_content（传入 file_id）→ 返回 Markdown 内容
```

### 工作流四：导入本地文件

```
1. bash import_file.sh <文件路径> → 完成预导入 + COS 上传
2. manage.async_import（传入 task_id/file_key/file_name/file_md5/file_size）
3. manage.import_progress（传入 task_id）→ 轮询直到 progress=100，获取 file_url
```

### 工作流五：网页剪藏

```
1. scrape_url（传入 url）→ 返回 task_id
2. scrape_progress（传入 task_id）→ 每隔 2 秒轮询，status=2 时获取 file_url
```
