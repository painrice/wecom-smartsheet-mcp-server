---
name: wecom-sheet
description: 企业微信文档操作技能。当用户需要操作企微智能表格（SmartSheet）、在线表格（类Excel）、在线文档（类Word）时触发。支持读取/写入/更新智能表格记录、读取/编辑在线表格单元格、读取/追加在线文档文本。适用场景：外贸退税核对登记、小说投稿追踪、自媒体数据分析、股票持仓管理、合同/报告自动生成等所有需要结构化记录到企微文档的业务。不适用于：纯聊天、非企微文档操作。
---

# 企业微信文档操作 Skill

## 概述

通过 shell curl 命令直接调用企业微信文档 API。支持三大文档类型：
- **智能表格（SmartSheet）** → `add_records` / `get_records` / `update_records`
- **在线表格（Spreadsheet）** → `get_spreadsheet_data` / `update_spreadsheet_cells`
- **在线文档（Document）** → `get_document` / `append_document_text`

---

## ⚠️ 已知限制与最佳实践（实战踩坑总结）

### 0. 沙箱环境
- IMA 沙箱**没有** `httpx` 和 `requests` 模块
- ✅ 所有 API 调用必须用 **`curl`**，不要试图 pip install
- token 获取命令：`curl -s "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=$CORPID&corpsecret=$SECRET"`

### 1. IP 白名单
- 企微 API 要求应用配置 **企业可信 IP**
- IMA 沙箱出口 IP：`<SANDBOX_PUBLIC_IP>`（短期不变，长期可能变化）
- 如果 API 返回 `errcode: 60020`，提示用户去企业微信管理后台加白名单

### 2. 字段类型限制
- ❌ `FIELD_TYPE_NUMBER`：总是报错 2022017，**不要用**
- ❌ `FIELD_TYPE_DATE_TIME`：需要额外属性，避免使用
- ✅ **全部使用 `FIELD_TYPE_TEXT`**，数据可靠且兼容
- 金额、日期等信息以文本格式存储即可，企微表格支持文本排序和筛选

### 3. 添加字段规则
- ❌ 一次 `add_fields` 传多个字段：可能部分失败
- ✅ **逐个字段调用 `add_fields`**，每次只传 1 个字段

### 4. 文档权限（关键！）
- API 创建的文档**默认只有应用自己能访问**，用户看不到
- **推荐方案**：让用户在企微里手动创建智能表格 → 发链接给你 → 你拿 docid 往里写
- 备选方案：创建后用 `mod_doc_join_rule` 开企业内权限 + `mod_doc_member` 加用户为管理员

### 5. 链接访问
- 获取正式分享链接用 `doc_share` API，不要直接用 `create_doc` 返回的 URL
- 用户必须在**企微客户端**内打开链接

---

## 前提

用户需提供：
- `WECOM_CORPID`：企业微信 CorpID
- `WECOM_SECRET`：自建应用 Secret（⚠️ 必须是自建应用，不是机器人）

引导模板见 `references/setup_guide.md`。

### 推荐：用户手动建表

**最优流程**：
1. 用户打开企微 → 文档 → 新建智能表格 → 起名
2. 把文档链接发给你
3. 你从 URL 提取 docid→查询子表→若无则建子表和字段→写入数据

---

## 核心操作（curl 命令模板）

所有命令固定格式：
```bash
TOKEN=$(curl -s "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=$CORPID&corpsecret=$SECRET" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### 智能表格

```bash
# 查看子表
curl -s -X POST "https://qyapi.weixin.qq.com/cgi-bin/wedoc/smartsheet/get_sheet?access_token=$TOKEN" \
    -H "Content-Type: application/json" -d '{"docid":"DOCID"}'

# 添加子表
curl -s -X POST "https://qyapi.weixin.qq.com/cgi-bin/wedoc/smartsheet/add_sheet?access_token=$TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"docid":"DOCID","properties":{"title":"单证核对表"}}'

# 逐个添加字段（⭐ 必须逐个，不要批量）
for field in "报关单号" "出口日期" "出口金额USD"; do
  curl -s -X POST "https://qyapi.weixin.qq.com/cgi-bin/wedoc/smartsheet/add_fields?access_token=$TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"docid\":\"DOCID\",\"sheet_id\":\"SHEETID\",\"fields\":[{\"field_title\":\"$field\",\"field_type\":\"FIELD_TYPE_TEXT\"}]}"
done

# 查重
curl -s -X POST "https://qyapi.weixin.qq.com/cgi-bin/wedoc/smartsheet/get_records?access_token=$TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"docid":"DOCID","sheet_id":"SHEETID","filter_spec":{"conditions":[{"field_title":"报关单号","operator":"is","value":["223120260001409030"]}]}}'

# 写入记录
curl -s -X POST "https://qyapi.weixin.qq.com/cgi-bin/wedoc/smartsheet/add_records?access_token=$TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
  "docid": "DOCID",
  "sheet_id": "SHEETID",
  "key_type": "CELL_VALUE_KEY_TYPE_FIELD_TITLE",
  "records": [{"values": {
    "报关单号": [{"type": "text", "text": "223120260001409030"}],
    "出口日期": [{"type": "text", "text": "2026-04-15"}],
    "出口金额USD": [{"type": "text", "text": "4031.20"}]
  }}]
}'
```

### 权限修复

```bash
# 企业内可访问
curl -s -X POST "https://qyapi.weixin.qq.com/cgi-bin/wedoc/mod_doc_join_rule?access_token=$TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"docid":"DOCID","enable_corp_internal":true,"corp_internal_auth":1}'

# 加特定用户为管理员
curl -s -X POST "https://qyapi.weixin.qq.com/cgi-bin/wedoc/mod_doc_member?access_token=$TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"docid":"DOCID","update_file_member_list":[{"userid":"USERID","type":1,"auth":7}]}'

# 获取分享链接
curl -s -X POST "https://qyapi.weixin.qq.com/cgi-bin/wedoc/doc_share?access_token=$TOKEN" \
    -H "Content-Type: application/json" -d '{"docid":"DOCID"}'
```

---

## 退税核对业务工作流

完整操作步骤：

1. **确认凭证**：用户提供了 CORPID + SECRET
2. **获取 docid**：推荐用户手动建表发链接；或者 API 创建后配权限
3. **查看子表**：`get_sheet` 看有无「单证核对表」/「收汇登记表」
4. **建子表**（如无）：`add_sheet` 逐个创建
5. **加字段**（如无）：**逐个** `add_fields`，全用 `FIELD_TYPE_TEXT`
6. **查重**：每条报关单先 `get_records` 筛选
7. **写入**：`add_records` 写入核对表和收汇表
8. **权限**：确保用户能访问文档

### 单证核对表字段（全 TEXT）
报关单号 | 出口日期 | 出口金额USD | 贸易方式 | 外商名称 | 提单号 | 合同号 | 备注

### 收汇登记表字段（全 TEXT）
报关单号 | 收汇日期 | 收汇金额USD | 付款人名称

---

## 错误处理速查

| errcode | 含义 | 处理 |
|:---|:---|:---|
| 60020 | IP 不在白名单 | 提示用户加 `<SANDBOX_PUBLIC_IP>` |
| 2022017 | 字段参数校验失败 | 改用 FIELD_TYPE_TEXT，逐个添加 |
| 2022004 | 字段不存在 | 先 add_fields 再写数据 |
| 0 | 成功 | — |

## 扩展场景

| 场景 | 用智能表格 |
|:---|:---|
| 小说投稿追踪 | 书名、平台、状态、字数 |
| 自媒体数据 | 标题、阅读量、点赞、评论 |
| 股票持仓 | 代码、名称、成本、盈亏 |
| 合同生成 | 用在线文档 append |
