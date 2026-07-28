#!/usr/bin/env python3
"""企业微信文档 API 客户端（本地开发版本）。

⚠️ 注意：IMA 沙箱无 httpx 模块，此脚本仅用于本地开发环境。
在 IMA Skill 中请使用 SKILL.md 中的 curl 命令模板。

用法:
    pip install httpx
    python client.py token --corpid xxx --secret xxx
    python client.py create_doc --corpid xxx --secret xxx --title "测试"
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
    """创建文档（智能表格/在线表格/在线文档），返回 docid 和 url。

    doc_type: 10=智能表格, 4=在线表格, 3=在线文档
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
        frow = []
        for cell in row:
            if isinstance(cell, dict):
                frow.append(cell)
            elif isinstance(cell, (int, float)):
                frow.append({"value": str(cell), "value_type": "number"})
            else:
                frow.append({"value": str(cell), "value_type": "text"})
        formatted.append(frow)

    result = api_call(SPREADSHEET_BASE, "edit_data", {
        "docid": args.docid,
        "requests": [{"update_range": {
            "sheet_id": args.sheet_id,
            "data": formatted,
            "start_row": args.start_row,
            "start_col": args.start_col,
            "rows": rows,
            "cols": cols,
        }}]
    }, args.corpid, args.secret)
    print(json.dumps(result, ensure_ascii=False))


# ═══════════════════════════════════════
# 在线文档操作
# ═══════════════════════════════════════

def cmd_get_document(args):
    result = api_call(DOCUMENT_BASE, "get", {"docid": args.docid}, args.corpid, args.secret)
    print(json.dumps(result, ensure_ascii=False))


def cmd_append_document_text(args):
    # 先获取版本号
    doc_info = api_call(DOCUMENT_BASE, "get", {"docid": args.docid}, args.corpid, args.secret)
    version = doc_info.get("version", 0)

    result = api_call(DOCUMENT_BASE, "edit", {
        "docid": args.docid,
        "requests": [{
            "insert_text": {
                "text": args.text,
                "location": {"index": 0},
                "version": version,
            }
        }]
    }, args.corpid, args.secret)
    print(json.dumps(result, ensure_ascii=False))


# ═══════════════════════════════════════
# CLI
# ═══════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="企微文档 API 客户端")
    sub = parser.add_subparsers(dest="command")

    # 公共参数
    def add_common(p):
        p.add_argument("--corpid", default=os.getenv("WECOM_CORPID", ""))
        p.add_argument("--secret", default=os.getenv("WECOM_SECRET", ""))

    def add_docid(p):
        p.add_argument("--docid", required=True)

    # token
    p = sub.add_parser("token")
    add_common(p)

    # 创建文档
    p = sub.add_parser("create_doc")
    add_common(p)
    p.add_argument("--title", required=True, help="文档标题")
    p.add_argument("--doc_type", type=int, default=10, help="10=智能表格, 4=在线表格, 3=在线文档")
    p.add_argument("--admin_users", help="管理员用户ID列表，逗号分隔")

    # 智能表格
    p = sub.add_parser("list_sheets")
    add_common(p); add_docid(p)

    p = sub.add_parser("add_records")
    add_common(p); add_docid(p)
    p.add_argument("--sheet_id", required=True)
    p.add_argument("--records", required=True, help='JSON: [{"values": {...}}]')

    p = sub.add_parser("get_records")
    add_common(p); add_docid(p)
    p.add_argument("--sheet_id", required=True)
    p.add_argument("--filter_field")
    p.add_argument("--filter_value")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--limit", type=int, default=100)

    p = sub.add_parser("update_records")
    add_common(p); add_docid(p)
    p.add_argument("--sheet_id", required=True)
    p.add_argument("--records", required=True)

    # 在线表格
    p = sub.add_parser("get_spreadsheet_data")
    add_common(p); add_docid(p)
    p.add_argument("--sheet_id", default="")
    p.add_argument("--start_row", type=int, default=0)
    p.add_argument("--end_row", type=int, default=50)
    p.add_argument("--start_col", type=int, default=0)
    p.add_argument("--end_col", type=int, default=20)

    p = sub.add_parser("update_spreadsheet_cells")
    add_common(p); add_docid(p)
    p.add_argument("--sheet_id", required=True)
    p.add_argument("--data", required=True, help='JSON: [["A1","B1"],["A2","B2"]]')
    p.add_argument("--start_row", type=int, default=0)
    p.add_argument("--start_col", type=int, default=0)

    # 在线文档
    p = sub.add_parser("get_document")
    add_common(p); add_docid(p)

    p = sub.add_parser("append_document_text")
    add_common(p); add_docid(p)
    p.add_argument("--text", required=True)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    func_map = {
        "token": cmd_token,
        "create_doc": cmd_create_doc,
        "list_sheets": cmd_list_sheets,
        "add_records": cmd_add_records,
        "get_records": cmd_get_records,
        "update_records": cmd_update_records,
        "get_spreadsheet_data": cmd_get_spreadsheet_data,
        "update_spreadsheet_cells": cmd_update_spreadsheet_cells,
        "get_document": cmd_get_document,
        "append_document_text": cmd_append_document_text,
    }
    func_map[args.command](args)


if __name__ == "__main__":
    main()
