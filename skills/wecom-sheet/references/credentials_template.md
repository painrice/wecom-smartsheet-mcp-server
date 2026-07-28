# IMA 知识库 — 企业微信文档凭证模板

把下面这段整段复制到 IMA 个人知识库 / 笔记里，**标题固定为 `我的企业微信文档凭证`**。Agent 会按字段名自动读取，下次对话就不用再贴。

---

```text
WECOM_CORPID = ww你的CorpID
WECOM_SECRET = 你的自建应用Secret
WECOM_APP_NAME = 文档助手
WECOM_DOC_PERMISSION = 文档,智能表格
WECOM_IP_WHITELIST = 已配置
```

---

## 字段说明

| 字段 | 必填 | 说明 |
|:---|:-:|:---|
| `WECOM_CORPID` | ✓ | 企业微信「我的企业」页面底部，企业 ID（`ww` 开头） |
| `WECOM_SECRET` | ✓ | 「应用管理」→ 自建应用 → 应用详情里的 Secret（**必须是自建应用，不是机器人**） |
| `WECOM_APP_NAME` |   | 应用名称（便于人工核对） |
| `WECOM_DOC_PERMISSION` |   | 已开通的权限（多个用英文逗号分隔） |
| `WECOM_IP_WHITELIST` |   | IMA 沙箱出口 IP 是否已加白名单 |

## 使用示例

在 IMA 里直接说：

> "用我知识库里的企微凭证，把这份报关单图片解析后写入退税核对表。"

Agent 会自动从笔记读 `WECOM_CORPID` 和 `WECOM_SECRET`，不再追问。

## 安全提醒

- IMA 笔记对 Agent 等同于**明文**——只在自己单人使用的 IMA 账号里用。
- 如需团队复用，把 SECRET 改成短期临时 token，或者在企微后台建受限子账号。
- 怀疑泄露时，立刻到企微管理后台「应用详情」→「Secret」重置。