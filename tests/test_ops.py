import json, os, sys, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from ops import core as C

def item(hid="HH1", status="待標中", price="售1329萬", rnd="2", case="114乙184648", addr="龍江路412巷6號2樓"):
    return {"編號": hid, "地址": "濱江市場【榮星花園】" + addr, "區域": "台北中山區-公寓-0房", "類型": "公寓", "價格": price, "狀態": status,
            "資訊": {"案號": case, "拍次": rnd, "開標日期": "115/11/19", "總登記坪數": "23.2坪", "筆錄": "【本件拍定後點交】",
                     "拍賣紀錄": "第一拍 10/15 底標價： 1662 萬\n第二拍 11/19 底標價： 1329 萬\n第三拍 未定 底標價： 1064 萬"}}

@pytest.fixture
def db(): return C.connect()

def count(db, t): return db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]

def test_reimport_no_duplicate(db):
    C.import_104(db, [item()]); r = C.import_104(db, [item()])
    assert count(db, "cases") == 1 and r["same"] == 1
    # 另一平台編號、同案號同物件 → 併入同一案件
    C.upsert_case(db, C._fields_from_104(item("HX9")), "買屋網", "X9")
    assert count(db, "cases") == 1 and count(db, "case_alias") == 2

def test_same_case_no_different_object_not_merged(db):
    C.import_104(db, [item("A", addr="龍江路412巷6號2樓"), item("B", addr="龍江路412巷6號3樓")])
    assert count(db, "cases") == 2

def test_official_vs_estimated_price_separate(db):
    C.import_104(db, [item()]); cid = db.execute("SELECT case_id FROM cases").fetchone()[0]
    assert db.execute("SELECT official_floor_price,estimated_price FROM cases").fetchone()[:] == (13290000, None)
    C.set_estimated_price(db, cid, 15000000, "anna")
    C.import_104(db, [item()])                     # 再匯入不得改動預估價，也不得把預估價當底價
    r = db.execute("SELECT official_floor_price,estimated_price FROM cases").fetchone()
    assert r[:] == (13290000, 15000000)

def test_no_official_price_never_filled_from_listing_price(db):
    x = item(); x["資訊"]["拍賣紀錄"] = ""         # 公告查不到
    C.import_104(db, [x]); r = db.execute("SELECT official_floor_price,needs_review,review_reason FROM cases").fetchone()
    assert r[0] is None and r[1] == 1 and "底價" in r[2]
    cid = db.execute("SELECT case_id FROM cases").fetchone()[0]
    assert C.can_publish(db, cid)[0] is False       # 阻擋自動發布

def test_cancel_or_price_change_finds_affected_ads(db):
    C.import_104(db, [item()]); cid = db.execute("SELECT case_id FROM cases").fetchone()[0]
    p1 = C.register_publication(db, cid, "House-Info", "H1"); p2 = C.register_publication(db, cid, "FB粉專", "F1")
    for p in (p1, p2): assert C.publish(db, p, lambda pub: ("ref", "http://x")) == "已發布"
    assert C.find_affected(db) == []
    C.import_104(db, [item(status="停拍（可能再拍）")])
    got = C.find_affected(db); assert {g[0] for g in got} == {"House-Info", "FB粉專"} and all(g[2] == "下架" for g in got)
    assert C.find_affected(db) == []                # 重跑不重複建任務
    assert count(db, "tasks") == 2

def test_price_change_creates_update_task(db):
    C.import_104(db, [item()]); cid = db.execute("SELECT case_id FROM cases").fetchone()[0]
    p = C.register_publication(db, cid, "自有網站", "W1"); C.publish(db, p, lambda pub: ("W1", "u"))
    x = item(rnd="3"); x["資訊"]["拍賣紀錄"] = "第三拍 12/20 底標價： 1064 萬"
    C.import_104(db, [x])
    assert [g[2] for g in C.find_affected(db)] == ["更新"]

def test_failed_publish_not_marked_done_and_retry_not_duplicate(db):
    C.import_104(db, [item()]); cid = db.execute("SELECT case_id FROM cases").fetchone()[0]
    p = C.register_publication(db, cid, "House-Info", "H1")
    def boom(pub): raise RuntimeError("登入失敗")
    assert C.publish(db, p, boom) == "失敗"
    assert db.execute("SELECT state FROM publications").fetchone()[0] == "失敗"
    calls = []
    ok = lambda pub: (calls.append(1), ("H1", "u"))[1]
    assert C.publish(db, p, ok) == "已發布" and C.publish(db, p, ok) == "已發布"
    assert len(calls) == 1                           # 重送不會重複發布

def test_published_not_verified_until_evidence(db):
    C.import_104(db, [item()]); cid = db.execute("SELECT case_id FROM cases").fetchone()[0]
    p = C.register_publication(db, cid, "買屋網", "B1"); C.publish(db, p, lambda q: ("B1", "u"))
    with pytest.raises(ValueError): C.mark_verified(db, p, "")
    C.mark_verified(db, p, "截圖.png")
    assert db.execute("SELECT state FROM publications").fetchone()[0] == "發布已驗證"

def test_task_retry_limits(db):
    tid, c1 = C.add_task(db, "k1", "x"); _, c2 = C.add_task(db, "k1", "x"); assert c1 and not c2
    n = []
    def flaky(t): n.append(1); raise RuntimeError("timeout")
    for _ in range(5): C.run_task(db, tid, flaky)
    assert len(n) == C.MAX_RETRY and db.execute("SELECT state FROM tasks WHERE task_id=?", (tid,)).fetchone()[0] == "失敗"
    t2, _ = C.add_task(db, "k2", "x"); calls = []
    def perm(t): calls.append(1); raise RuntimeError("權限不足")
    C.run_task(db, t2, perm); C.run_task(db, t2, perm)
    assert len(calls) == 1 and db.execute("SELECT state FROM tasks WHERE task_id=?", (t2,)).fetchone()[0] == "待人工"
    t3, _ = C.add_task(db, "k3", "x"); done = []
    C.run_task(db, t3, lambda t: "ok"); C.run_task(db, t3, lambda t: done.append(1) or "ok")
    assert not done                                  # 完成後重跑不再執行

def test_inquiry_links_case_and_source_and_dedupes(db):
    C.import_104(db, [item()]); cid = db.execute("SELECT case_id FROM cases").fetchone()[0]
    a = C.record_inquiry(db, "LINE", "Uabc", "evt1", cid, "FB粉專", None, "想看這間", source_kind="直接追蹤")
    b = C.record_inquiry(db, "LINE", "Uabc", "evt1", cid, "FB粉專")
    assert a[2] is True and b[2] is False and count(db, "customers") == 1 and count(db, "inquiries") == 1 and count(db, "tasks") == 1
    # 同名不同帳號不自動合併
    C.record_inquiry(db, "電話", "0900", "evt2", name="王小明"); C.record_inquiry(db, "LINE", "Uxyz", "evt3", name="王小明")
    assert count(db, "customers") == 3
    r = db.execute("SELECT case_id,source_platform,source_kind FROM inquiries WHERE event_key='evt1'").fetchone()
    assert r[:] == (cid, "FB粉專", "直接追蹤")

def test_interaction_needs_next_step_and_appointment(db):
    cust, _, _ = C.record_inquiry(db, "LINE", "U1", "e1")
    with pytest.raises(ValueError): C.add_interaction(db, cust, "LINE", "聊過", "anna", "", "")
    C.add_interaction(db, cust, "LINE", "確認預算", "anna", "寄兩件適合案件", "2026-11-06")
    aid = C.book(db, cust, None, "2026-11-06 14:00", "到場", "辦公室", "帶身分證")
    assert C.book(db, cust, None, "2026-11-06 14:00", "到場", "辦公室", "帶身分證") == aid and count(db, "appointments") == 1
    d = C.dashboard(db, "2026-11-06"); assert d["今日預約"][0]["appt_id"] == aid

def test_no_authorization_no_spend(db):
    db.execute("INSERT INTO campaigns (campaign_id,platform,name) VALUES ('c1','FB廣告','測試')"); db.commit()
    with pytest.raises(PermissionError): C.activate_campaign(db, "c1")
    assert db.execute("SELECT state,spend_cap FROM campaigns").fetchone()[:] == ("待授權", None)
    C.authorize_spend(db, "FB廣告", 3000, "2026-11-01", "2026-11-30", "anna")
    C.activate_campaign(db, "c1", "2026-11-05"); assert db.execute("SELECT state,spend_cap FROM campaigns").fetchone()[:] == ("進行中", 3000)

def test_empty_dashboard_shows_unavailable(db):
    d = C.dashboard(db); assert d["成效"]["曝光"] == "未取得" and d["成效"]["每有效詢問成本"] == "未取得" and d["成效"]["詢問(依來源)"] == "未取得"
    assert d["今日需回覆與追蹤"] == []

def test_real_data_import_idempotent(db):
    p = os.path.join(os.path.dirname(__file__), "..", "site", "data.json")
    items = json.load(open(p, encoding="utf-8"))["104"]
    r1 = C.import_104(db, items); n = count(db, "cases"); r2 = C.import_104(db, items)
    assert count(db, "cases") == n and r2["new"] == 0
    assert n <= len(items)
