"""產生唯讀管理畫面（單一 HTML 檔）。資料都經過跳脫，避免客戶輸入的文字變成程式。"""
import html

from . import workflow as W

SECTIONS = ("今日需回覆與追蹤", "今日預約", "即將投標(7日內)", "待更新／待下架", "待補資料", "自動化異常")
STYLE = """
body{margin:0;background:#f7f8fa;color:#14233c;font:16px/1.6 "Microsoft JhengHei","PingFang TC",sans-serif}
header{background:#14233c;color:#fff;padding:16px 20px;border-bottom:4px solid #c9a96a}
h1{font-size:20px;margin:0} header p{margin:4px 0 0;font-size:14px;color:#e8dcc3}
main{max-width:1000px;margin:auto;padding:16px} section{background:#fff;border:1px solid #dfe3ea;border-radius:8px;margin:0 0 14px;padding:14px}
h2{font-size:17px;margin:0 0 8px;color:#14233c} .n{color:#8a6d2f;font-weight:700}
.wrap{overflow-x:auto} table{border-collapse:collapse;width:100%;font-size:14px} th,td{padding:7px 8px;border-bottom:1px solid #edf0f4;text-align:left;white-space:nowrap}
th{color:#52606d} .empty{color:#6b7785;font-size:14px;margin:0} footer{color:#52606d;font-size:13px;padding:0 4px 20px}
"""


LABELS = {
    "customer_id": "客戶編號", "kind": "工作", "reason": "內容", "due": "期限", "appt_id": "預約編號", "at": "時間", "mode": "方式",
    "case_id": "案件編號", "address": "地址", "auction_date": "拍賣日", "round": "拍次", "platform": "平台", "state": "狀態",
    "review_reason": "原因", "task_id": "工作編號", "last_error": "錯誤",
}


def _table(rows):
    if not rows:
        return '<p class="empty">目前沒有項目</p>'
    keys = list(rows[0].keys())
    head = "".join(f"<th>{html.escape(LABELS.get(k, str(k)))}</th>" for k in keys)
    body = "".join("<tr>" + "".join(f"<td>{html.escape('' if r[k] is None else str(r[k]))}</td>" for k in keys) + "</tr>" for r in rows)
    return f'<div class="wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def render(db, today=None, performance_rows=(), banner="草稿模式：未連接任何平台，不會發布或發訊息"):
    board = W.daily_board(db, today)
    parts = []
    for name in SECTIONS:
        rows = board[name]
        parts.append(f'<section><h2>{html.escape(name)} <span class="n">{len(rows)}</span></h2>{_table(rows)}</section>')
    if performance_rows:
        parts.append(f"<section><h2>成效</h2>{_table(list(performance_rows))}</section>")
    defs = "；".join(f"{k}：{v}" for k, v in W.DEFINITIONS.items())
    return (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>每日待辦｜104法拍網</title><style>{STYLE}</style></head><body><header><h1>104法拍網｜法拍服務團隊</h1>"
            f"<p>{html.escape(banner)}</p></header><main>{''.join(parts)}<footer>指標定義：{html.escape(defs)}。缺資料顯示未取得。</footer></main></body></html>")
