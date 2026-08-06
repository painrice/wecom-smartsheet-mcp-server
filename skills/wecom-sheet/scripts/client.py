#!/usr/bin/env python3
"""企业微信文档 API 客户端（本地开发版本）。

⚠️ 注意：IMA 沙箱无 httpx 模块，此脚本仅用于本地开发环境。
在 IMA Skill 中请使用 SKILL.md 中的 curl 命令模板。

用法:
    pip install httpx
    python client.py token --corpid xxx --secret xxx
    python client.py create_doc --corpid xxx --secret xxx --title "测试" --doc-type 3
    python client.py get_document --docid xxx
    python client.py batch_update --docid xxx --text "内容"
"""

import argparse
import json
import os
import sys
import time

# ⚠️ httpx 在 IMA 沙箱不可用，本地开发需手动安装
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    print("⚠️ httpx 未安装。在 IMA 沙箱中请使用 SKILL.md 中的 curl 命令。", file=sys.stderr)
    print("   本地开发：pip install httpx", file=sys.stderr)


# ── API 端点 ──
TOKEN_URL = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
SMARTSHEET_BASE = "https://qyapi.weixin.qq.com/cgi-bin/wedoc/smartsheet"
SPREADSHEET_BASE = "https://qyapi.weixin.qq.com/cgi-bin/wedoc/spreadsheet"
DOCUMENT_BASE = "https://qyapi.weixin.qq.com/cgi-bin/wedoc/document"
CREATE_DOC_URL = "https://qyapi.weixin.qq.com/cgi-bin/wedoc/create_doc"
MOD_JOIN_RULE_URL = "https://qyapi.weixin.qq.com/cgi-bin/wedoc/mod_doc_join_rule"
DOC_SHARE_URL = "https://qyapi.weixin.qq.com/cgi-bin/wedoc/doc_share"

# ── doc_type 正确枚举（旧枚举 1/2/3 已失效，报 640054）──
# 3=文档 | 4=表格 | 10=智能表格 | 11=智能文档
DOC_TYPE_DOCUMENT = 3
DOC_TYPE_SPREADSHEET = 4
DOC_TYPE_SMARTSHEET = 10
DOC_TYPE_SMART_DOC = 11

# ── 缓存 token ──
_token_cache: dict = {}


def get_token(corpid: str, secret: str) -> str:
    cache_key = f"{corpid}:{secret}"
    now = time.time()
    cached = _token_cache.get(cache_key)
    if cached and now < cached["expires"] - 300:
        return cached["token"]

    resp = httpx.get(TOKEN_URL, params={"corpid": corpid, "corpsecret": secret}, timeout=30)
    data = resp.json()
    if data.get("errcode") != 0:
        print(json.dumps({"error": f"获取token失败: {data}"}))
        sys.exit(1)

    _token_cache[cache_key] = {
        "token": data["access_token"],
        "expires": now + data.get("expires_in", 7200),
    }
    return data["access_token"]


def api_call(base: str, path: str, body: dict, corpid: str, secret: str) -> dict:
    token = get_token(corpid, secret)
    url = f"{base}/{path}"
    resp = httpx.post(url, params={"access_token": token}, json=body, timeout=30)
    return resp.json()


def cmd_token(args):
    token = get_token(args.corpid, args.secret)
    print(json.dumps({"token": token}))


def cmd_create_doc(args):
    """创建文档。

    doc_type: 3=在线文档 | 10=智能表格（旧枚举 1/2/3 已失效，报 640054）
    """
    token = get_token(args.corpid, args.secret)
    url = f"{CREATE_DOC_URL}?access_token={token}"
    body = {"doc_type": args.doc_type, "doc_name": args.title}
    if args.admin_users:
        body["admin_users"] = args.admin_users.split(",")
    resp = httpx.post(url, json=body, timeout=30)
    result = resp.json()
    if result.get("errcode") == 0:
        print(json.dumps({
            "docid": result["docid"],
            "url": result.get("url", ""),
            "doc_type": args.doc_type,
            "title": args.title,
        }, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))


# ═══════════════════════════════════════
# 智能表格操作
# ═══════════════════════════════════════

def cmd_list_sheets(args):
    result = api_call(SMARTSHEET_BASE, "get_sheet", {"docid": args.docid}, args.corpid, args.secret)
    print(json.dumps(result, ensure_ascii=False))


def cmd_add_records(args):
    records = json.loads(args.records)
    result = api_call(SMARTSHEET_BASE, "add_records", {
        "docid": args.docid,
        "sheet_id": args.sheet_id,
        "key_type": "CELL_VALUE_KEY_TYPE_FIELD_TITLE",
        "records": records,
    }, args.corpid, args.secret)
    print(json.dumps(result, ensure_ascii=False))


def cmd_get_records(args):
    body = {
        "docid": args.docid,
        "sheet_id": args.sheet_id,
        "offset": args.offset,
        "limit": args.limit,
    }
    if args.filter_field and args.filter_value:
        body["filter_spec"] = {
            "conditions": [{
                "field_title": args.filter_field,
                "operator": "is",
                "value": [args.filter_value],
            }]
        }
    result = api_call(SMARTSHEET_BASE, "get_records", body, args.corpid, args.secret)
    print(json.dumps(result, ensure_ascii=False))


def cmd_update_records(args):
    records = json.loads(args.records)
    result = api_call(SMARTSHEET_BASE, "update_records", {
        "docid": args.docid,
        "sheet_id": args.sheet_id,
        "key_type": "CELL_VALUE_KEY_TYPE_FIELD_TITLE",
        "records": records,
    }, args.corpid, args.secret)
    print(json.dumps(result, ensure_ascii=False))


# ═══════════════════════════════════════
# 在线表格操作
# ═══════════════════════════════════════

def cmd_get_spreadsheet_data(args):
    result = api_call(SPREADSHEET_BASE, "get_data", {
        "docid": args.docid,
        "sheet_id": args.sheet_id or "",
        "start_row": args.start_row,
        "end_row": args.end_row,
        "start_col": args.start_col,
        "end_col": args.end_col,
    }, args.corpid, args.secret)
    print(json.dumps(result, ensure_ascii=False))


def cmd_update_spreadsheet_cells(args):
    data = json.loads(args.data)
    rows = len(data)
    cols = max((len(r) for r in data), default=0)

    formatted = []
    for row in data:
        formatted.append([{"text": str(c)} for c in row])

    result = api_call(SPREADSHEET_BASE, "update_cells", {
        "docid": args.docid,
        "sheet_id": args.sheet_id or "",
        "data": formatted,
    }, args.corpid, args.secret)
    print(json.dumps(result, ensure_ascii=False))


# ═══════════════════════════════════════
# 在线文档操作（Document）— 实战可用
# 旧接口 append_document_text 已 404，改用 document/get + batch_update
# ═══════════════════════════════════════

def cmd_get_document(args):
    """读取文档结构，获取插入坐标（begin/end）。"""
    result = api_call(DOCUMENT_BASE, "get", {"docid": args.docid}, args.corpid, args.secret)
    print(json.dumps(result, ensure_ascii=False))


def cmd_batch_update(args):
    """向在线文档写入文本。

    最佳实践：始终插到 index=0 开头段落、逆序写入各块，规避 2050065。
    单次 batch_update 最多 30 个 operation。
    """
    # text 可传多块，每块逆序插入 index=0
    blocks = [b for b in args.text.split("\u0000") if b] if args.split0 else [args.text]
    requests = [{"insert_text": {"text": b, "location": {"index": 0}}} for b in reversed(blocks)]
    result = api_call(DOCUMENT_BASE, "batch_update", {
        "docid": args.docid,
        "requests": requests,
    }, args.corpid, args.secret)
    print(json.dumps(result, ensure_ascii=False))


def cmd_doc_share(args):
    """获取正式分享链接（不要直接用 create_doc 返回的 url）。"""
    token = get_token(args.corpid, args.secret)
    resp = httpx.post(f"{DOC_SHARE_URL}?access_token={token}",
                      json={"docid": args.docid}, timeout=30)
    print(json.dumps(resp.json(), ensure_ascii=False))


def cmd_mod_join_rule(args):
    """配置文档权限（rule=2 企业内可见）。"""
    token = get_token(args.corpid, args.secret)
    resp = httpx.post(f"{MOD_JOIN_RULE_URL}?access_token={token}", json={
        "docid": args.docid,
        "enable_corp_internal": True,
        "corp_internal_auth": 1,
    }, timeout=30)
    print(json.dumps(resp.json(), ensure_ascii=False))


# ═══════════════════════════════════════
# CLI
# ═══════════════════════════════════════

def build_parser():
    p = argparse.ArgumentParser(description="企业微信文档 API 客户端（本地版）")
    sub = p.add_subparsers(dest="cmd")

    def add_common(sp):
        sp.add_argument("--corpid", required=True)
        sp.add_argument("--secret", required=True)

    sp = sub.add_parser("token"); add_common(sp); sp.set_defaults(func=cmd_token)

    sp = sub.add_parser("create_doc"); add_common(sp)
    sp.add_argument("--title", required=True)
    sp.add_argument("--doc-type", type=int, default=DOC_TYPE_SMARTSHEET,
                    help="3=文档 4=表格 10=智能表格 11=智能文档")
    sp.add_argument("--admin-users", default="")
    sp.set_defaults(func=cmd_create_doc)

    sp = sub.add_parser("list_sheets"); add_common(sp)
    sp.add_argument("--docid", required=True); sp.set_defaults(func=cmd_list_sheets)

    sp = sub.add_parser("add_records"); add_common(sp)
    sp.add_argument("--docid", required=True); sp.add_argument("--sheet-id", required=True)
    sp.add_argument("--records", required=True); sp.set_defaults(func=cmd_add_records)

    sp = sub.add_parser("get_records"); add_common(sp)
    sp.add_argument("--docid", required=True); sp.add_argument("--sheet-id", required=True)
    sp.add_argument("--offset", type=int, default=0); sp.add_argument("--limit", type=int, default=100)
    sp.add_argument("--filter-field", default=""); sp.add_argument("--filter-value", default="")
    sp.set_defaults(func=cmd_get_records)

    sp = sub.add_parser("update_records"); add_common(sp)
    sp.add_argument("--docid", required=True); sp.add_argument("--sheet-id", required=True)
    sp.add_argument("--records", required=True); sp.set_defaults(func=cmd_update_records)

    sp = sub.add_parser("get_spreadsheet_data"); add_common(sp)
    sp.add_argument("--docid", required=True); sp.add_argument("--sheet-id", default="")
    sp.add_argument("--start-row", type=int, default=0); sp.add_argument("--end-row", type=int, default=100)
    sp.add_argument("--start-col", type=int, default=0); sp.add_argument("--end-col", type=int, default=50)
    sp.set_defaults(func=cmd_get_spreadsheet_data)

    sp = sub.add_parser("update_spreadsheet_cells"); add_common(sp)
    sp.add_argument("--docid", required=True); sp.add_argument("--sheet-id", default="")
    sp.add_argument("--data", required=True); sp.set_defaults(func=cmd_update_spreadsheet_cells)

    sp = sub.add_parser("get_document"); add_common(sp)
    sp.add_argument("--docid", required=True); sp.set_defaults(func=cmd_get_document)

    sp = sub.add_parser("batch_update"); add_common(sp)
    sp.add_argument("--docid", required=True); sp.add_argument("--text", required=True)
    sp.add_argument("--split0", action="store_true", help="用 \\0 分块，各自逆序插入 index=0")
    sp.set_defaults(func=cmd_batch_update)

    sp = sub.add_parser("doc_share"); add_common(sp)
    sp.add_argument("--docid", required=True); sp.set_defaults(func=cmd_doc_share)

    sp = sub.add_parser("mod_join_rule"); add_common(sp)
    sp.add_argument("--docid", required=True); sp.set_defaults(func=cmd_mod_join_rule)

    return p


def main():
    if not HAS_HTTPX:
        print("请先安装 httpx：pip install httpx", file=sys.stderr)
        sys.exit(1)
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "cmd", None):
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
