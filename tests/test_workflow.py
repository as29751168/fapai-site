"""驗收測試。沒有 pytest 也能跑：python tests/test_workflow.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ops import content as K
from ops import core as C
from ops import dashboard_html as H
from ops import modules as M
from ops import pilot as P
from ops import workflow as W

TODAY = "2026-11-06"


def fresh():
    db = W.migrate(C.connect())
    case_id, _ = C.upsert_case(db, dict(P.CASE), "測試", "T1")
    return db, case_id


def ready_pub(db, case_id, platform="House-Info"):
    asset = W.draft_post(db, case_id)
    assert W.submit_asset(db, asset) == []
    W.approve_asset(db, asset, "審閱者")
    return W.prepare_publication(db, case_id, platform, asset), asset


def expect(err, fn):
    try:
        fn()
    except err:
        return True
    raise AssertionError(f"應該拋出 {err.__name__}")


def test_migration_rerun_safe():
    db, _ = fresh()
    W.migrate(db)
    assert db.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 1


def test_duplicate_import_no_new_case():
    db, _ = fresh()
    _, state = C.upsert_case(db, dict(P.CASE), "測試", "T1")
    assert state == "same" and db.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 1


def test_same_case_no_other_court_or_object_not_merged():
    db, _ = fresh()
    C.upsert_case(db, {**P.CASE, "object_key": "虎林街141巷8號4樓"}, "測試", "T2")
    C.upsert_case(db, dict(P.CASE), "測試", "T3", court="士林地院")
    assert db.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 3


def test_official_and_estimated_kept_apart():
    db, case_id = fresh()
    C.set_estimated_price(db, case_id, 10097600, "測試")
    case = db.execute("SELECT * FROM cases").fetchone()
    assert (case["official_floor_price"], case["estimated_price"]) == (12622000, 10097600)
    text = K.build_post(case)
    assert "公告底價：1,262.2 萬元" in text and "約 1,009.76 萬元（預估，非法院公告）" in text
    assert K.check_content(case, text) == []
    assert "預估價格被寫成底價" in K.check_content(case, text.replace("公告底價：1,262.2", "公告底價：1,009.76"))
    assert "預估價格未標示非法院公告" in K.check_content(case, text.replace("（預估，非法院公告）", ""))


def test_content_checks():
    db, _ = fresh()
    case = db.execute("SELECT * FROM cases").fetchone()
    good = K.build_post(case)
    assert K.check_content(case, good) == []
    assert "保證金" not in " ".join(K.check_content(case, good + "保證金約兩成"))
    assert any("保證" in i for i in K.check_content(case, good + "保證貸款"))
    assert any("可看室內" in i for i in K.check_content(case, good + "可看室內"))
    assert any("無法看室內" in i for i in K.check_content(case, good.replace("無法看室內", "")))
    assert any("Pitt" in i for i in K.check_content(case, good.replace("0918-313-888", "")))


def test_failed_check_cannot_be_approved():
    db, case_id = fresh()
    C.upsert_case(db, {**P.CASE, "official_floor_price": None}, "測試", "T1")
    db.execute("UPDATE cases SET official_floor_price=NULL")
    asset = W.draft_post(db, case_id)
    assert W.submit_asset(db, asset)
    expect(ValueError, lambda: W.approve_asset(db, asset, "審閱者"))


def test_case_change_invalidates_approval():
    db, case_id = fresh()
    asset = W.draft_post(db, case_id)
    W.submit_asset(db, asset)
    C.upsert_case(db, {**P.CASE, "round": 3}, "測試", "T1")
    expect(ValueError, lambda: W.approve_asset(db, asset, "審閱者"))


def test_poster_needs_photo_right_and_approved_format():
    db, case_id = fresh()
    assert W.draft_poster(db, case_id, "4:3橫式")[0] is None
    W.add_media(db, case_id, "別人的照片.jpg", "同業網站", "禁用")
    assert W.draft_poster(db, case_id, "4:3橫式")[0] is None
    W.add_media(db, case_id, "自拍.jpg", "Anna", "自有")
    asset, _ = W.draft_poster(db, case_id, "FB 4:5直式")
    assert asset and W.submit_asset(db, asset) == []
    case = db.execute("SELECT * FROM cases").fetchone()
    expect(ValueError, lambda: K.poster_spec(case, [], "1:1"))
    assert K.POSTER_FORMATS["FB 4:5直式"] == (1080, 1350)


def test_no_authorization_no_publish():
    db, case_id = fresh()
    pub, _ = ready_pub(db, case_id)
    calls = []
    poster = lambda p: (calls.append(1), ("R", "http://x"))[1]
    expect(PermissionError, lambda: W.gated_publish(db, pub, poster, lambda c: None, TODAY))
    assert not calls
    W.authorize_publish(db, "House-Info", "發布", "2026-11-01", "2026-11-30", "Anna")
    assert W.gated_publish(db, pub, poster, lambda c: None, TODAY) == "已發布"
    assert W.gated_publish(db, pub, poster, lambda c: None, TODAY) == "已發布"
    assert len(calls) == 1


def test_expired_authorization_rejected():
    db, case_id = fresh()
    pub, _ = ready_pub(db, case_id)
    W.authorize_publish(db, "House-Info", "發布", "2026-01-01", "2026-01-31", "Anna")
    expect(PermissionError, lambda: W.gated_publish(db, pub, lambda p: ("R", "u"), lambda c: None, TODAY))


def test_recheck_blocks_publish():
    db, case_id = fresh()
    pub, _ = ready_pub(db, case_id)
    W.authorize_publish(db, "House-Info", "發布", "2026-11-01", "2026-11-30", "Anna")
    calls = []
    expect(PermissionError, lambda: W.gated_publish(db, pub, lambda p: calls.append(1), lambda c: "公告查不到", TODAY))
    assert not calls and db.execute("SELECT needs_review FROM cases").fetchone()[0] == 1


def test_publish_failure_not_done():
    db, case_id = fresh()
    pub, _ = ready_pub(db, case_id)
    W.authorize_publish(db, "House-Info", "發布", "2026-11-01", "2026-11-30", "Anna")
    def boom(_):
        raise RuntimeError("登入失敗")
    assert W.gated_publish(db, pub, boom, lambda c: None, TODAY) == "失敗"
    assert db.execute("SELECT state FROM publications").fetchone()[0] == "失敗"


def test_unready_publication_stays_out():
    db, case_id = fresh()
    pub = W.prepare_publication(db, case_id, "買屋網")
    row = db.execute("SELECT state,last_error FROM publications WHERE pub_id=?", (pub,)).fetchone()
    assert row["state"] == "素材完成" and "素材" in row["last_error"]


def test_manual_report_needs_evidence_for_verified():
    db, case_id = fresh()
    pub, _ = ready_pub(db, case_id, "House-Info")
    W.report_manual_publication(db, pub, "HH1", "http://example.test/1", None)
    assert db.execute("SELECT state FROM publications").fetchone()[0] == "已發布"
    C.mark_verified(db, pub, "截圖.png")
    assert db.execute("SELECT state FROM publications").fetchone()[0] == "發布已驗證"


def test_stop_auction_finds_affected_publications():
    db, case_id = fresh()
    pub, _ = ready_pub(db, case_id)
    W.report_manual_publication(db, pub, "HH1", "http://example.test/1", "截圖.png")
    C.upsert_case(db, {**P.CASE, "status": "停拍"}, "測試", "T1")
    made = C.find_affected(db)
    assert made and made[0][2] == "下架" and C.find_affected(db) == []
    assert db.execute("SELECT state FROM publications").fetchone()[0] == "待下架"


def test_inquiry_links_case_source_and_no_duplicates():
    db, case_id = fresh()
    code = W.tracking_code(db, case_id, "FB粉專", "camp1", "https://tomin104.com/x")
    assert W.tracking_code(db, case_id, "FB粉專", "camp1", "https://tomin104.com/x") == code
    first = W.capture_inquiry(db, "LINE", "U1", "e1", code=code)
    second = W.capture_inquiry(db, "LINE", "U1", "e1", code=code)
    assert first[2] and not second[2]
    row = db.execute("SELECT case_id,source_platform,campaign_id,source_kind FROM inquiries").fetchone()
    assert tuple(row) == (case_id, "FB粉專", "camp1", "直接追蹤")
    assert db.execute("SELECT COUNT(*) FROM customer_cases").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM tasks WHERE kind='回覆新詢問'").fetchone()[0] == 1


def test_unknown_source_can_be_backfilled_and_same_name_not_merged():
    db, _ = fresh()
    a = W.capture_inquiry(db, "電話", "0900", "e1", name="王小明")
    b = W.capture_inquiry(db, "LINE", "U9", "e2", name="王小明")
    assert a[0] != b[0]
    assert db.execute("SELECT source_kind FROM inquiries WHERE inquiry_id=?", (a[1],)).fetchone()[0] == "未知"
    W.backfill_source(db, a[1], "FB社團")
    assert db.execute("SELECT source_kind,source_platform FROM inquiries WHERE inquiry_id=?", (a[1],)).fetchone()[:] == ("人工補登", "FB社團")


def test_one_customer_many_cases():
    db, case_id = fresh()
    other, _ = C.upsert_case(db, {**P.CASE, "object_key": "x", "case_no": "1"}, "測試", "T2")
    customer = W.capture_inquiry(db, "LINE", "U1", "e1", case_id=case_id)[0]
    W.watch_case(db, customer, other)
    W.watch_case(db, customer, other)
    assert db.execute("SELECT COUNT(*) FROM customer_cases").fetchone()[0] == 2


def test_progressive_questions():
    db, _ = fresh()
    customer = W.capture_inquiry(db, "LINE", "U1", "e1")[0]
    assert W.next_question(db, customer)[0] == "want_areas"
    W.update_needs(db, customer, want_areas="信義")
    assert W.next_question(db, customer)[0] == "budget"
    assert db.execute("SELECT stage FROM customers").fetchone()[0] == "需求確認"


def test_appointment_and_survey_never_promises_interior():
    db, case_id = fresh()
    customer = W.capture_inquiry(db, "LINE", "U1", "e1")[0]
    expect(ValueError, lambda: W.book_appointment(db, customer, case_id, "2026-11-08 10:00", "到場", "", ""))
    appt = W.book_appointment(db, customer, case_id, "2026-11-08 10:00", "現場周邊勘查", "案件周邊", "帶公告")
    assert W.book_appointment(db, customer, case_id, "2026-11-08 10:00", "現場周邊勘查", "案件周邊", "帶公告") == appt
    assert W.SURVEY_NOTE in db.execute("SELECT prep FROM appointments").fetchone()[0]
    assert db.execute("SELECT COUNT(*) FROM appointments").fetchone()[0] == 1


def test_outcome_routes():
    db, case_id = fresh()
    customer = W.capture_inquiry(db, "LINE", "U1", "e1")[0]
    appt = W.book_appointment(db, customer, case_id, "2026-11-08 10:00", "電話", "電話", "備資料")
    expect(ValueError, lambda: W.record_consultation(db, appt, "未成交", "Anna", lost_reason="亂填", today=TODAY))
    assert W.record_consultation(db, appt, "未成交", "Anna", lost_reason="資金未備妥", today=TODAY) == "資金準備中"
    row = db.execute("SELECT stage,lost_reason,segment FROM customers").fetchone()
    assert tuple(row) == ("未成交", "資金未備妥", "資金準備中")
    assert db.execute("SELECT due FROM tasks WHERE kind='未成交追蹤'").fetchone()[0] == "2027-02-04"


def test_mandate_flow_requires_next_step():
    db, case_id = fresh()
    customer = W.capture_inquiry(db, "LINE", "U1", "e1")[0]
    appt = W.book_appointment(db, customer, case_id, "2026-11-08 10:00", "到場", "辦公室", "身分證")
    mandate = W.record_consultation(db, appt, "委託", "Anna", service="全程代標", today=TODAY)
    expect(ValueError, lambda: W.advance_mandate(db, mandate, "投標準備", "x", "", ""))
    W.advance_mandate(db, mandate, "投標準備", "備票", "確認出價", "2026-11-15")
    W.advance_mandate(db, mandate, "得標", "得標", "安排繳款", "2026-11-25")
    assert db.execute("SELECT stage,result FROM mandates").fetchone()[:] == ("得標", "得標")
    W.advance_mandate(db, mandate, "結案", "完成", "", "")
    assert db.execute("SELECT stage FROM customers").fetchone()[0] == "結案"


def test_stop_contact_blocks_everything():
    db, case_id = fresh()
    customer = W.capture_inquiry(db, "LINE", "U1", "e1")[0]
    W.set_contact_preference(db, customer, "只用電話", True)
    W.stop_contact(db, customer)
    assert db.execute("SELECT state FROM tasks WHERE kind='回覆新詢問'").fetchone()[0] == "取消"
    assert W.send_message(db, customer, "LINE@", "m1", lambda c: "ok", TODAY).startswith("拒絕")
    appt = W.book_appointment(db, customer, case_id, "2026-11-08 10:00", "電話", "電話", "資料")
    W.record_consultation(db, appt, "未成交", "Anna", lost_reason="仍在了解", today=TODAY)
    assert db.execute("SELECT COUNT(*) FROM tasks WHERE kind='未成交追蹤'").fetchone()[0] == 0
    assert W.daily_board(db, "2030-01-01")["今日需回覆與追蹤"] == [] or all(t["customer_id"] != customer for t in W.daily_board(db, "2030-01-01")["今日需回覆與追蹤"])


def test_message_needs_subscription_authorization_and_only_once():
    db, _ = fresh()
    customer = W.capture_inquiry(db, "LINE", "U1", "e1")[0]
    sent = []
    sender = lambda c: (sent.append(c), "msg-id")[1]
    assert "未訂閱" in W.send_message(db, customer, "LINE@", "m1", sender, TODAY)
    W.set_contact_preference(db, customer, subscribed=True)
    assert "未設定" in W.send_message(db, customer, "LINE@", "m1", sender, TODAY)
    W.authorize_publish(db, "LINE@", "發訊息", "2026-11-01", "2026-11-30", "Anna")
    assert W.send_message(db, customer, "LINE@", "m1", sender, TODAY) == "完成"
    assert W.send_message(db, customer, "LINE@", "m1", sender, TODAY) == "完成"
    assert len(sent) == 1


def test_referral_keeps_source():
    db, _ = fresh()
    old = W.capture_inquiry(db, "LINE", "U1", "e1")[0]
    new = W.capture_inquiry(db, "電話", "0911", "e2", source_platform="舊客轉介")[0]
    W.add_referral(db, new, old)
    assert db.execute("SELECT referred_by,source_platform FROM customers WHERE customer_id=?", (new,)).fetchone()[:] == (old, "舊客轉介")
    expect(ValueError, lambda: W.add_referral(db, old, old))


def test_no_spend_without_authorization():
    db, _ = fresh()
    db.execute("INSERT INTO campaigns (campaign_id,platform,name) VALUES ('c1','FB廣告','測試')")
    expect(PermissionError, lambda: C.activate_campaign(db, "c1", TODAY))
    assert db.execute("SELECT state,spend_cap FROM campaigns").fetchone()[:] == ("待授權", None)


def test_performance_empty_is_unavailable_not_zero():
    db, case_id = fresh()
    for dim, key in (("platform", "FB廣告"), ("campaign", "none"), ("case", case_id)):
        perf = W.performance(db, dim, key)
        for name in ("曝光", "點擊", "費用", "詢問", "有效詢問", "預約", "委託", "每有效詢問成本", "資料性質"):
            assert perf[name] == W.UNAVAILABLE, (dim, name, perf[name])
    expect(ValueError, lambda: W.performance(db, "x", "y"))


def test_performance_with_data_uses_defined_denominators():
    db, case_id = fresh()
    db.execute("INSERT INTO campaigns (campaign_id,platform,name) VALUES ('c1','FB廣告','測試')")
    db.execute("INSERT INTO ad_stats VALUES ('c1',?, '2026-11-01',1000,50,3000,'人工登記')", (case_id,))
    code = W.tracking_code(db, case_id, "FB廣告", "c1")
    c1, q1, _ = W.capture_inquiry(db, "LINE", "U1", "e1", code=code)
    W.capture_inquiry(db, "LINE", "U2", "e2", code=code)
    W.mark_inquiry_valid(db, q1, True)
    appt = W.book_appointment(db, c1, case_id, "2026-11-08 10:00", "到場", "辦公室", "身分證")
    W.record_consultation(db, appt, "委託", "Anna", service="全程代標", today=TODAY)
    perf = W.performance(db, "campaign", "c1")
    assert perf["詢問"] == 2 and perf["有效詢問"] == 1 and perf["每有效詢問成本"] == 3000.0
    assert perf["每預約成本"] == 3000.0 and perf["每委託成本"] == 3000.0 and perf["資料性質"] == "人工登記"
    assert W.performance(db, "platform", "FB廣告")["費用"] == 3000


def test_fee_conflicts_not_usable_until_confirmed():
    db, _ = fresh()
    W.seed_fee_terms(db)
    W.seed_fee_terms(db)
    assert db.execute("SELECT COUNT(*) FROM fee_terms").fetchone()[0] == len(W.FEE_SEED)
    assert W.fee_for_public_use(db, "fee-full-under-6m") is None
    W.confirm_fee(db, "fee-apply", "50,000 元", "服務項目 01–05", "2026-01-01", "Anna")
    assert W.fee_for_public_use(db, "fee-apply") == "50,000 元"
    W.confirm_fee(db, "fee-package", "120,000 元", "x", "2026-01-01", "Anna", effective_to="2026-02-01")
    assert W.fee_for_public_use(db, "fee-package") is None


def test_dashboard_html_escapes_and_is_honest():
    db, _ = fresh()
    W.capture_inquiry(db, "LINE", "U1", "e1", summary="<script>alert(1)</script>")
    page = H.render(db, C.now()[:10], [W.performance(db, "platform", "FB廣告")])
    assert "<script>" not in page and "&lt;script&gt;" in page and "未取得" in page and "草稿模式" in page


def test_modules_complete():
    assert len(M.MODULES) == 8
    for module in M.MODULES:
        assert all(module[k] for k, _ in M.HEADERS), module["name"]
    assert "完成條件" in M.markdown_table()


def test_pilot_runs_end_to_end():
    with tempfile.TemporaryDirectory() as folder:
        log = "\n".join(P.run(folder))
        assert "已擋下" in log and "案件數 1" in log and "詢問數 1" in log and "分流到" in log
        assert os.path.exists(os.path.join(folder, "pilot_dashboard.html"))


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS", name)
        except Exception as err:
            failed += 1
            print("FAIL", name, repr(err))
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
