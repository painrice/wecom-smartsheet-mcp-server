# 企业微信文档 Skill — 初始化指南

## 前置条件

### 1. 创建自建应用（不是机器人）

1. 登录 [企业微信管理后台](https://work.weixin.qq.com/)
2. 「我的企业」→ 页面底部复制 **企业ID**（即 CorpID）
3. 「应用管理」→「应用」→「创建应用」→ 起名（如"文档助手"）
4. 进入应用详情 → 复制 **Secret**

### 2. 开通权限

应用详情页 →「文档」→ 勾选：
- ☑ 文档
- ☑ 智能表格

### 3. 配置 IP 白名单 ⚠️ 必须做

应用详情页 →「企业可信 IP」→ 添加：
```
49.235.105.51
```

> 这是 IMA 沙箱出口 IP。不确定时可临时用 `curl -s https://ifconfig.me` 核实，或在报错 hint 的 `from ip:` 中确认（IP 可能随时间变化）。不加白名单所有 API 都会返回 60020 错误。

### 4. 创建文档

两种方式均可：

**方式 A（API 自动创建，已实战可行）**
- `create_doc` 用正确 `doc_type`：**3=文档 / 10=智能表格**
- 创建后立即 `mod_doc_join_rule(rule=2)` 开企业内权限
- `doc_share` 拿分享链接发给用户
- 写内容：智能表格用 `add_records`；在线文档用 `document/batch_update`

**方式 B（用户手动创建，最省心）**
1. 在企微客户端中「文档」→ 新建 → **智能表格**（或在线文档）
2. 起名（如"出口退税核对表"）
3. 把文档链接发给 AI Agent
4. Agent 从 URL 提取 docid 后写入

---

## 已踩过的坑

| 问题 | 原因 | 解决方案 |
|:---|:---|:---|
| ModuleNotFoundError: httpx | 沙箱无此模块 | 用 curl |
| errcode 60020 | IP 不在白名单 | 添加 49.235.105.51 |
| errcode 640054 | create_doc 用了旧 doc_type 枚举(1/2/3) | 改用新枚举 **3=文档/4=表格/10=智能表格/11=智能文档** |
| errcode 2050065 | insert_text 找不到 p 父节点（空文档占位段落无 Run/Text 子节点） | 插到 **index=0** 开头段落、逆序写入；或先 insert_paragraph 再 insert_text |
| errcode 2608668 | 对在线文档(doc_type=3)调了 sheet 接口 | 文档无 sheet 子表；改用 document/batch_update；sheet 接口只用于智能表格(doc_type=10) |
| 404 / 接口不存在 | 旧接口 append_document_text、/cgi-bin/doc/* 已下线 | 改用 /cgi-bin/wedoc/document/batch_update + document/get |
| errcode 2022017 | NUMBER 字段校验失败 | 全用 FIELD_TYPE_TEXT |
| errcode 2022004 | 字段不存在 | 先 add_fields |
| 批量 add_fields 部分失败 | API 限制 | 逐个添加字段 |
| 文档链接打不开 | 默认无用户权限 | 创建后 mod_doc_join_rule + doc_share |

---

## 快速启动示例

用户在 IMA 中说：

> "帮我创建退税核对表，我的企业ID是 xxx，Secret是 xxx，文档链接是 https://doc.weixin.qq.com/smartsheet/s3_xxx"

AI Agent 执行流程：
1. 从 URL 提取 docid
2. `get_sheet` 查看子表
3. 若需新建子表 → `add_sheet` + 逐个 `add_fields`（全 TEXT）
4. `add_records` 写入数据（每条先去重）
5. 用户手机企微打开链接即可查看

若用户要"把内容存进在线文档"：
> "把整理好的内容存到企业微信的在线文档里"

AI Agent 执行流程：
1. `create_doc(doc_type=3)` 创建在线文档
2. `document/get` 确认结构（空文档有 Document>MainStory>Section>Paragraph）
3. `document/batch_update` 按 **index=0 逆序**写入分块内容，规避 2050065
4. `mod_doc_join_rule(rule=2)` + `doc_share` 交付链接
