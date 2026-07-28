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
<SANDBOX_PUBLIC_IP>
```

> 这是 IMA 沙箱出口 IP，不加白名单所有 API 都会返回 60020 错误。

### 4. 手动创建文档（推荐）

在企微客户端中：
1. 「文档」→ 新建 → **智能表格**
2. 起名（如"出口退税核对表"）
3. 把文档链接发给 AI Agent

> ⚠️ 不要用 API 创建文档后直接发链接——API 创建的需要额外配权限。

---

## 已踩过的坑

| 问题 | 原因 | 解决方案 |
|:---|:---|:---|
| ModuleNotFoundError: httpx | 沙箱无此模块 | 用 curl |
| errcode 60020 | IP 不在白名单 | 添加 `<SANDBOX_PUBLIC_IP>` |
| errcode 2022017 | NUMBER 字段校验失败 | 全用 FIELD_TYPE_TEXT |
| errcode 2022004 | 字段不存在 | 先 add_fields |
| 批量 add_fields 部分失败 | API 限制 | 逐个添加字段 |
| 文档链接打不开 | 默认无用户权限 | 手动建表 or mod_doc_member |

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
