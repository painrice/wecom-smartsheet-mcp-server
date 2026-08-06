---
name: wecom-sheet
description: 企业微信文档操作技能。当用户需要操作企微智能表格（SmartSheet）、在线表格（类Excel）、在线文档（类Word）时触发。支持读取/写入/更新智能表格记录、读取/编辑在线表格单元格、用 document/batch_update 写入在线文档正文。适用场景：外贸退税核对登记、小说投稿追踪、自媒体数据分析、股票持仓管理、合同/报告自动生成等需要结构化记录到企微文档的业务。不适用于：纯聊天、非企微文档操作。
---

# 企业微信文档操作 Skill

## 概述

通过 shell curl 命令直接调用企业微信文档 API。支持三大文档类型：
- **智能表格（SmartSheet）** → `smartsheet/get_sheet` / `add_records` / `get_records` / `update_records`
- **在线表格（Spreadsheet）** → `spreadsheet/get_data` / `update_spreadsheet_cells`
- **在线文档（Document）** → `document/get`（读结构）+ `document/batch_update`（insert_text / insert_paragraph 写内容）

> ⚠️ **在线文档的"追加文本"接口 `append_document_text` 已于 2024 年后下线（返回 404）**，不要再使用。写入正文必须用 `document/batch_update`，详见下文「在线文档（Document）」章节。

---

## 🔑 凭证获取（自动，无需每次手动提供）

本 Skill 触发后，**首先**从用户笔记中自动获取企微凭证：

```bash
# 用 search 定位笔记
search(source="note", question="企业微信配置")

# 用 fetch 读取内容
fetch(type="note_id", id="7487964674273325", question="提取完整的企业微信配置：CorpID、Secret、AgentId、DocID")
```

**笔记 ID**：`7487964674273325`（标题：企业微信配置）

读取到以下变量后缓存到上下文中：
- `CORPID`：企业 ID
- `SECRET`：应用 Secret
- `DOCID`：默认文档 ID（如有）

如果笔记不存在或内容不全，再向用户询问凭证。

---

## ⚠️ 已知限制与最佳实践（实战踩坑总结）

### 0. 沙箱环境
- IMA 沙箱**没有** `httpx` 和 `requests` 模块
- ✅ 所有 API 调用必须用 **`curl`**，不要试图 pip install
- token 获取命令：`curl -s "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=$CORPID&corpsecret=$SECRET"`

### 1. IP 白名单
- 企微 API 要求应用配置 **企业可信 IP**
- IMA 沙箱出口 IP：`49.235.105.51`（短期不变，长期可能变化；不确定时用 `curl -s https://ifconfig.me` 或在报错 hint `from ip:` 中确认）
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
- 推荐方案：创建后用 `mod_doc_join_rule(rule=2)` 开企业内权限 + `doc_share` 拿分享链接
- 备选方案：让用户在企微里手动创建文档 → 发链接给你 → 你拿 docid 往里写

### 5. 链接访问
- 获取正式分享链接用 `doc_share` API，不要直接用 `create_doc` 返回的 URL
- 用户必须在**企微客户端**内打开链接

### 6. create_doc 正确的 doc_type 枚举（⚠️ 易踩坑）
- 官方最新 `doc_type` 枚举：**3=文档、4=表格、10=智能表格、11=智能文档**
- ❌ 旧版枚举（1/2/3）**已失效**，传了会返回 `640054 invalid param`
- 智能表格 = `10`（smartsheet 系列接口用这个）；在线文档/Word 类 = `3`
- sheet 接口（`smartsheet/get_sheet`、`add_sheet`）只对**智能表格(doc_type=10)**有效；对**在线文档(doc_type=3)**调用会报 `2608668 SheetEngine Service Error`——因为文档类型没有 sheet 子表，不是引擎故障

### 7. 在线文档写入接口：废弃 vs 正确
- ❌ 废弃（返回 404）：`/cgi-bin/wedoc/append_document_text`、`/cgi-bin/doc/*`、`/cgi-bin/wedoc/append_document_text`
- ✅ 正确：
  - 读结构：`POST /cgi-bin/wedoc/document/get` → 返回节点树，含 `type/begin/end` 坐标
  - 写内容：`POST /cgi-bin/wedoc/document/batch_update` → `{"docid":...,"requests":[{"insert_text":{"text":...,"location":{"index":N}}}, ...]}`，单次批量 ≤ **30** 个 operation
- 空文档 `document/get` 结构是 `Document > MainStory > Section > Paragraph`；空占位段落**没有真实 `p` 文本节点（Run/Text 子节点）**，直接 `insert_text` 会报 `2050065`

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

### 在线文档（Document）— 创建 / 读结构 / 写内容

> 以下为**实战验证可用**的完整流程（旧 `append_document_text` 已 404，别再用）。

#### ① 创建在线文档（doc_type=3=文档）

```bash
curl -s -X POST "https://qyapi.weixin.qq.com/cgi-bin/wedoc/create_doc?access_token=$TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"doc_type":3,"doc_name":"业务知识库整理"}'
# 返回 docid 和 url
```

#### ② 读取文档结构（拿插入坐标）

```bash
curl -s -X POST "https://qyapi.weixin.qq.com/cgi-bin/wedoc/document/get?access_token=$TOKEN" \
    -H "Content-Type: application/json" -d '{"docid":"DOCID"}'
# 返回节点树：Document > MainStory > Section > Paragraph，每个节点带 begin/end 坐标
```

#### ③ 写入内容（batch_update，单次 ≤30 个 operation）

```bash
curl -s -X POST "https://qyapi.weixin.qq.com/cgi-bin/wedoc/document/batch_update?access_token=$TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "docid":"DOCID",
      "requests":[
        {"insert_text":{"text":"第一段内容\n","location":{"index":0}}},
        {"insert_text":{"text":"第二段内容\n","location":{"index":0}}}
      ]
    }'
```

#### ④ 写入大段内容的可靠策略（避免 2050065）

`insert_text` 的 `location.index` **必须落在「含 Run/Text 子节点的段落(Paragraph)」内部**；落在空段落 end 或 Section end 会报 `2050065 TextValidator cannot find p parent`。空文档的占位段落没有真实 `p` 节点，所以插在 Paragraph end 也会失败。

✅ **最可靠做法**：始终 `insert` 到 **index=0**（文档开头段落，恒为有效锚点），**按逆序写入各块/各行**，最终正文顺序与原文一致。不要尝试 append 到文档末尾（末尾位置插入必失败）。

```bash
# 伪代码：把长文 text 按 3000 字符分块成 blocks[0..n]，逆序插入 index=0
# for i from n down to 0:  insert_text(text=blocks[i], location={"index":0})
```

✅ **备选做法**：先 `insert_paragraph` 创建真实段落，再 `insert_text` 到该段落内部坐标：

```bash
curl -s -X POST "https://qyapi.weixin.qq.com/cgi-bin/wedoc/document/batch_update?access_token=$TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "docid":"DOCID",
      "requests":[
        {"insert_paragraph":{"location":{"index":0},"para_position":"para_before"}},
        {"insert_text":{"text":"内容\n","location":{"index":1}}}
      ]
    }'
```

> 注意：`batch_update` 里 `\n` 是字面文本，不会自动分段（整段落累积）。需要分段时，要么用多块各自 `insert_paragraph` + `insert_text`，要么在文本中用空行模拟。

---

## 退税核对业务工作流

完整操作步骤：

1. **确认凭证**：用户提供了 CORPID + SECRET
2. **获取 docid**：推荐用户手动建表发链接；或 API `create_doc(doc_type=10)` 后配权限
3. **查看子表**：`get_sheet` 看有无「单证核对表」/「收汇登记表」
4. **建子表**（如无）：`add_sheet` 逐个创建
5. **加字段**（如无）：**逐个** `add_fields`，全用 `FIELD_TYPE_TEXT`
6. **查重**：每条报关单先 `get_records` 筛选
7. **写入**：`add_records` 写入核对表和收汇表
8. **权限**：确保用户能访问文档（`mod_doc_join_rule` + `doc_share`）

### 单证核对表字段（全 TEXT）
报关单号 | 出口日期 | 出口金额USD | 贸易方式 | 外商名称 | 提单号 | 合同号 | 备注

### 收汇登记表字段（全 TEXT）
报关单号 | 收汇日期 | 收汇金额USD | 付款人名称

---

## 错误处理速查

| errcode | 含义 | 处理 |
|:---|:---|:---|
| 60020 | IP 不在白名单 | 提示用户加 `49.235.105.51` |
| 640054 | create_doc 参数非法 | doc_type 用新枚举 **3/4/10/11**，旧枚举 1/2/3 已失效 |
| 2050065 | insert_text 找不到 p 父节点 | 插到 **index=0** 开头段落（逆序写）；或先 insert_paragraph 再写 |
| 2608668 | SheetEngine 错误 | 对 doc_type=3 文档调 sheet 接口了；文档无 sheet，改用 document/batch_update |
| 2022017 | 字段参数校验失败 | 改用 FIELD_TYPE_TEXT，逐个添加 |
| 2022004 | 字段不存在 | 先 add_fields 再写数据 |
| 404 | 接口路径不存在 | 旧接口（append_document_text、/cgi-bin/doc/*）已下线，改用 /cgi-bin/wedoc/document/batch_update |
| 0 | 成功 | — |

---

## 扩展场景

| 场景 | 文档类型 | 关键接口 |
|:---|:---|:---|
| 小说投稿追踪 | 智能表格 | smartsheet 增记录 |
| 自媒体数据 | 智能表格 | smartsheet 增记录 |
| 股票持仓 | 智能表格 | smartsheet 增记录 |
| 合同/长文生成 | 在线文档 | create_doc(3) + document/get + batch_update |
| 知识库内容落盘 | 在线文档 | create_doc(3) + batch_update 逆序写入 index=0 |
