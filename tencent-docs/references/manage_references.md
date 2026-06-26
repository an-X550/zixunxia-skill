# 咨询侠·腾讯文档 — 文件管理参考

> 精简版：仅保留咨询侠实际使用的 manage 工具。
> 完整版历史见原 tencent-docs skill 分发包。

---

## 文档搜索

### manage.search_file

根据关键词搜索云文档。

| 参数 | 类型 | 必填 | 说明 |
|------|------|-----|------|
| `search_key` | string | ✅ | 搜索关键字 |

**返回**：`list[]` — 含 `file_id`、`title`、`url`

```json
{"search_key": "旭日"}
```

---

## 文档信息查询

### manage.query_file_info

查询文档基础信息（类型、创建人、时间等）。

| 参数 | 类型 | 必填 | 说明 |
|------|------|-----|------|
| `file_id` | string | ✅ | 文档ID |

```json
{"file_id": "DtDywXFgYFru"}
```

---

## 文档权限管理

### manage.set_privilege

设置文档分享权限。创建专业推荐文档后，设置为所有人可读以便分享给考生。

| 参数 | 类型 | 必填 | 说明 |
|------|------|-----|------|
| `file_id` | string | ✅ | 文档ID |
| `policy` | uint32 | ✅ | 2=所有人可读，3=所有人可编辑 |

```json
{"file_id": "DtDywXFgYFru", "policy": 2}
```

---

## 文档删除

### manage.delete_file

删除文档到回收站。

| 参数 | 类型 | 必填 | 说明 |
|------|------|-----|------|
| `file_id` | string | ✅ | 文件ID |

```json
{"file_id": "doc_abc123"}
```

---

## 文档导入（本地文件 → 腾讯文档）

### 推荐方式：使用 import_file.sh 脚本

```bash
bash import_file.sh <文件路径>
```

脚本自动完成 MD5 计算 → pre_import → 上传 COS 三步。成功后在输出中获取参数，手动调用 async_import。

### 手动方式

**manage.pre_import** — 预导入，获取上传链接

| 参数 | 类型 | 必填 | 说明 |
|------|------|-----|------|
| `file_name` | string | ✅ | 文件名（含后缀） |
| `file_size` | integer | ✅ | 文件大小（字节） |
| `file_md5` | string | ✅ | 文件 MD5（32位小写hex） |

返回：`upload_url`、`file_key`、`task_id`

**manage.async_import** — 触发异步导入

| 参数 | 类型 | 必填 | 说明 |
|------|------|-----|------|
| `file_key` | string | ✅ | pre_import 返回 |
| `file_name` | string | ✅ | 需一致 |
| `file_md5` | string | ✅ | 需一致 |
| `file_size` | integer | ✅ | 需一致 |
| `task_id` | string | | pre_import 返回 |

返回：`task_id`

**manage.import_progress** — 轮询导入进度

| 参数 | 类型 | 必填 | 说明 |
|------|------|-----|------|
| `task_id` | string | ✅ | async_import 返回 |

返回：`progress`(0-100)、`file_id`、`file_url`（完成时）
