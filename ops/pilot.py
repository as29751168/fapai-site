"""草稿模式試跑：建檔→素材→刊登任務→測試詢問→客戶→預約→追蹤→成效。
案件資料來自既有紀錄，尚未向法院重新查核；客戶是虛構測試資料。不連任何網路、不發布、不發訊息。
用法：python -m ops.pilot <輸出資料夾>"""
import json
import os
import sys

from . import core as C
from . import dashboard_html as H
from . import workflow as W

TODAY = "2026-11-06"
CASE = {
    "case_no": "115庚44703", "object_key": C.norm_addr("台北市信義區虎林街141巷8號3樓"), "title": "信義虎林街公寓",
    "address": "台北市信義區虎林街141巷8號3樓", "area": "台北信義區", "ptype": "公寓", "ping_total": 20.7, "floor": "3/4",
    "round": 2, "auction_date": "2026-11-18", "official_floor_price": 12622000, "deposit": 2530000,
    "delivery": "點交", "status": "待拍", "listing_price_raw": "1263萬",
}


def run(out_dir):
    db = W.migrate(C.connect())
    log = []
    step = lambda name, value: log.append(f"{name}：{value}")

    case_id, state = C.upsert_case(db, CASE, "既有紀錄(未重新查核)", "虎林街141巷8號3樓")
    C.upsert_case(db, CASE, "既有紀錄(未重新查核)", "虎林街141巷8號3樓")
    step("1 建檔", f"{state}，重複匯入後案件數 {db.execute('SELECT COUNT(*) FROM cases').fetchone()[0]}")
    C.set_estimated_price(db, case_id, 10097600, "八折試算")

    asset_id = W.draft_post(db, case_id)
    step("2 文案內容檢查", W.submit_asset(db, asset_id) or "通過")
    W.approve_asset(db, asset_id, "測試審閱者")
    poster, why = W.draft_poster(db, case_id, "FB 4:5直式")
    step("3 海報", poster or why)
    W.add_media(db, case_id, "待提供照片.jpg", "測試", "自有")
    poster, why = W.draft_poster(db, case_id, "FB 4:5直式")
    step("3 海報（標記照片權限後）", f"已建立規格，檢查：{W.submit_asset(db, poster) or '通過'}")

    pub_id = W.prepare_publication(db, case_id, "House-Info", asset_id)
    step("4 刊登任務", db.execute("SELECT state FROM publications WHERE pub_id=?", (pub_id,)).fetchone()[0])
    try:
        W.gated_publish(db, pub_id, lambda p: ("x", "x"), lambda c: None, TODAY)
    except PermissionError as err:
        step("4 未授權發布", f"已擋下：{err}")

    code = W.tracking_code(db, case_id, "House-Info")
    customer, inquiry, _ = W.capture_inquiry(db, "LINE", "TEST-虛構帳號", "pilot-evt-1", code=code, summary="測試詢問", name="測試客戶（虛構）")
    W.capture_inquiry(db, "LINE", "TEST-虛構帳號", "pilot-evt-1", code=code)
    W.mark_inquiry_valid(db, inquiry, True)
    step("5 詢問", f"代碼 {code} 連到案件與來源，重送後詢問數 {db.execute('SELECT COUNT(*) FROM inquiries').fetchone()[0]}")
    step("5 下一個需求問題", W.next_question(db, customer)[1])
    W.update_needs(db, customer, want_areas="台北信義區")
    C.add_interaction(db, customer, "LINE", "確認區域", "Anna", "電話確認預算", "2026-11-07")

    appt = W.book_appointment(db, customer, case_id, "2026-11-08 10:00", "現場周邊勘查", "案件周邊", "攜帶公告影本", "Anna")
    step("6 預約備註", db.execute("SELECT prep FROM appointments WHERE appt_id=?", (appt,)).fetchone()[0])
    segment = W.record_consultation(db, appt, "未成交", "Anna", "資金還在準備", "資金未備妥", today=TODAY)
    step("7 諮詢結果", f"未成交，分流到「{segment}」")

    perf = W.performance(db, "platform", "House-Info")
    step("8 成效", json.dumps(perf, ensure_ascii=False))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "pilot_post_draft.txt"), "w", encoding="utf-8") as fh:
        fh.write(db.execute("SELECT body FROM assets WHERE asset_id=?", (asset_id,)).fetchone()[0])
    with open(os.path.join(out_dir, "pilot_dashboard.html"), "w", encoding="utf-8") as fh:
        fh.write(H.render(db, TODAY, [perf]))
    with open(os.path.join(out_dir, "pilot_log.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(log))
    return log


if __name__ == "__main__":
    print("\n".join(run(sys.argv[1] if len(sys.argv) > 1 else "output")))
