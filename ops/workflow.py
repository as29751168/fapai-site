"""案件到委託的完整流程。建立在 core.py 之上，不修改 core.py。
預設只有草稿：沒有有效授權就不會發布或發訊息，也不含任何平台的連線程式。"""
import datetime
import glob
import json
import os

from . import content as K
from . import core as C

HERE = os.path.dirname(__file__)
# 各通路目前的操作方式；「人工」代表系統只產生工作內容，由人回報結果
CHANNEL_MODE = {
    "自有網站": "資料流已有，刊登紀錄需人工回報", "House-Info": "人工", "買屋網": "人工",
    "FB廣告": "需 Meta 授權", "FB粉專": "需 Meta 授權", "LINE@": "需 Messaging API 金鑰", "FB社團": "人工（無官方發文 API）",
}
NEEDS_ORDER = (("want_areas", "想看哪些區域？"), ("budget", "預算大約多少？"), ("down_payment", "自備款大概準備了多少？"), ("purpose", "是自住還是投資？"), ("buy_timing", "預計什麼時候購買？"))
# 未成交分流。追蹤天數是初始建議值，請業務確認後調整
LOST_ROUTES = {"資金未備妥": ("資金準備中", 90, "確認資金進度"), "暫無適合案件": ("等待案件", 14, "推薦符合需求的新案件"), "仍在了解": ("教育培養", 30, "提供法拍知識與流程說明"), "延後購買": ("延後購買", 90, "確認購買時間是否改變"), "其他": ("其他", 30, "確認客戶近況")}
MANDATE_STAGES = ("委託簽約", "投標準備", "投標", "得標", "未得標", "繳款", "產權登記", "點交處理", "交屋", "結案")
SURVEY_NOTE = "現場勘查僅限周邊與外觀，不含室內。"


def migrate(db):
    """依序套用 migrations，重跑不會重複。"""
    db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, at TEXT)")
    for path in sorted(glob.glob(os.path.join(HERE, "migrations", "*.sql"))):
        name = os.path.basename(path)
        if db.execute("SELECT 1 FROM schema_migrations WHERE name=?", (name,)).fetchone():
            continue
        with open(path, encoding="utf-8") as fh:
            db.executescript(fh.read())
        db.execute("INSERT INTO schema_migrations VALUES (?,?)", (name, C.now()))
    db.commit()
    return db


def _case(db, case_id):
    row = db.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
    if not row:
        raise ValueError("找不到案件")
    return row


def _event(db, pub_id, action, result, detail="", evidence=None):
    db.execute("INSERT INTO publication_events (pub_id,at,action,result,detail,evidence) VALUES (?,?,?,?,?,?)", (pub_id, C.now(), action, result, detail, evidence))


# ---------- 素材 ----------
def add_media(db, case_id, url, origin, usage_right="待確認", kind="照片"):
    db.execute("INSERT OR IGNORE INTO case_media (case_id,kind,url,origin,usage_right) VALUES (?,?,?,?,?)", (case_id, kind, url, origin, usage_right))
    db.commit()


def draft_post(db, case_id, platform_format="FB貼文", template_version="post-v1"):
    case = _case(db, case_id)
    asset_id = "S" + C._h(case_id, platform_format, str(case["version"]), template_version)
    body = K.build_post(case)
    db.execute("INSERT OR IGNORE INTO assets (asset_id,case_id,kind,platform_format,case_version,template_version,body,review_state,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
               (asset_id, case_id, "文案", platform_format, case["version"], template_version, body, "草稿", C.now()))
    db.commit()
    return asset_id


def draft_poster(db, case_id, fmt, template_version="poster-approved"):
    """有照片權限才建立海報工作；回傳 (asset_id 或 None, 原因)。"""
    case = _case(db, case_id)
    media = db.execute("SELECT * FROM case_media WHERE case_id=?", (case_id,)).fetchall()
    spec, why = K.poster_spec(case, media, fmt)
    if not spec:
        return None, why
    asset_id = "S" + C._h(case_id, fmt, str(case["version"]), template_version)
    db.execute("INSERT OR IGNORE INTO assets (asset_id,case_id,kind,platform_format,case_version,template_version,body,review_state,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
               (asset_id, case_id, "海報規格", fmt, case["version"], template_version, json.dumps(spec, ensure_ascii=False), "草稿", C.now()))
    db.commit()
    return asset_id, ""


def submit_asset(db, asset_id):
    """檢查通過才能送審；海報規格是由案件資料產生，檢查其完整內容。"""
    asset = db.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
    case = _case(db, asset["case_id"])
    text = asset["body"] or ""
    if asset["kind"] == "海報規格":
        spec = json.loads(text)
        text = "\n".join([*spec["lines"], spec["contacts"], spec["brand"], spec["footer"], K.SEIZED_NOTICE])
    issues = K.check_content(case, text)
    state = "草稿" if issues else "待審"
    db.execute("UPDATE assets SET check_result=?, review_state=? WHERE asset_id=?", (json.dumps(issues, ensure_ascii=False), state, asset_id))
    db.commit()
    return issues


def approve_asset(db, asset_id, reviewer):
    asset = db.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
    if asset["review_state"] != "待審":
        raise ValueError("素材未通過檢查，不能核可")
    if asset["case_version"] != _case(db, asset["case_id"])["version"]:
        raise ValueError("案件資料已更新，素材需重做")
    db.execute("UPDATE assets SET review_state='已核可', reviewed_by=?, reviewed_at=? WHERE asset_id=?", (reviewer, C.now(), asset_id))
    db.commit()


# ---------- 刊登 ----------
def prepare_publication(db, case_id, platform, asset_id=None):
    """建立刊登紀錄與工作。素材已核可且案件可發布才進「待發布」，不會真的發布。"""
    pub_id = C.register_publication(db, case_id, platform, "", "", asset_id)
    row = db.execute("SELECT state FROM publications WHERE pub_id=?", (pub_id,)).fetchone()
    if row["state"] not in ("素材完成", "失敗"):
        return pub_id
    ok, why = C.can_publish(db, case_id)
    approved = False
    if asset_id:
        asset = db.execute("SELECT review_state,case_version FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
        approved = asset["review_state"] == "已核可" and asset["case_version"] == _case(db, case_id)["version"]
    if ok and approved:
        db.execute("UPDATE publications SET state='待發布', asset_id=?, last_error=NULL WHERE pub_id=?", (asset_id, pub_id))
        _event(db, pub_id, "準備發布", "待發布", CHANNEL_MODE.get(platform, ""))
        C.add_task(db, f"刊登:{pub_id}", "刊登", f"{platform}（{CHANNEL_MODE.get(platform, '')}）", due=C.now()[:10], case_id=case_id, pub_id=pub_id)
    else:
        reason = why or "素材尚未核可"
        db.execute("UPDATE publications SET last_error=? WHERE pub_id=?", (reason, pub_id))
        _event(db, pub_id, "準備發布", "未通過", reason)
    db.commit()
    return pub_id


def authorize_publish(db, platform, action, valid_from, valid_to, granted_by, note=""):
    db.execute("INSERT INTO publish_authorizations (platform,action,valid_from,valid_to,granted_by,note) VALUES (?,?,?,?,?,?)", (platform, action, valid_from, valid_to, granted_by, note))
    db.commit()


def is_authorized(db, platform, action, today=None):
    today = today or C.now()[:10]
    return bool(db.execute("SELECT 1 FROM publish_authorizations WHERE platform=? AND action=? AND valid_from<=? AND valid_to>=?", (platform, action, today, today)).fetchone())


def gated_publish(db, pub_id, poster, recheck, today=None):
    """正式發布的唯一入口：需待發布狀態、有效授權，並於上線前重新查核。
    recheck(case) 回傳 None 表示通過，回傳文字表示無法查核。"""
    pub = db.execute("SELECT * FROM publications WHERE pub_id=?", (pub_id,)).fetchone()
    if pub["state"] in ("已發布", "發布已驗證"):
        return pub["state"]
    if pub["state"] != "待發布":
        raise PermissionError("素材未核可或案件未通過檢查")
    if not is_authorized(db, pub["platform"], "發布", today):
        _event(db, pub_id, "發布", "拒絕", "未設定發布授權")
        db.commit()
        raise PermissionError("尚未設定此平台的發布授權")
    problem = recheck(_case(db, pub["case_id"]))
    if problem:
        db.execute("UPDATE cases SET needs_review=1, review_reason=? WHERE case_id=?", (f"上線前查核：{problem}", pub["case_id"]))
        _event(db, pub_id, "上線前查核", "阻擋", problem)
        db.commit()
        raise PermissionError(f"上線前查核未通過：{problem}")
    state = C.publish(db, pub_id, poster)
    _event(db, pub_id, "發布", state)
    db.commit()
    return state


def report_manual_publication(db, pub_id, platform_ref, url, evidence):
    """人工刊登後回報。有網址或截圖證據才標為已驗證。"""
    pub = db.execute("SELECT * FROM publications WHERE pub_id=?", (pub_id,)).fetchone()
    if pub["state"] != "待發布":
        raise ValueError("只有待發布的刊登可以回報完成")
    version = _case(db, pub["case_id"])["version"]
    db.execute("UPDATE publications SET state='已發布', platform_ref=?, url=?, published_case_version=?, published_at=? WHERE pub_id=?", (platform_ref, url, version, C.now(), pub_id))
    _event(db, pub_id, "人工回報", "已發布", url)
    if evidence:
        C.mark_verified(db, pub_id, evidence)
        _event(db, pub_id, "驗證", "發布已驗證", evidence=evidence)
    C.add_task(db, f"刊登:{pub_id}", "刊登", case_id=pub["case_id"], pub_id=pub_id)
    db.execute("UPDATE tasks SET state='完成', evidence=?, done_at=? WHERE idempotency_key=?", (evidence or url, C.now(), f"刊登:{pub_id}"))
    db.commit()


# ---------- 來源辨識與客戶 ----------
def tracking_code(db, case_id, platform, campaign_id=None, base_url=""):
    """每個案件、平台、活動固定一個代碼，重跑不會變。"""
    code = "T" + C._h(case_id or "", platform, campaign_id or "")[:8].upper()
    url = f"{base_url}{'&' if '?' in base_url else '?'}src={code}" if base_url else ""
    db.execute("INSERT OR IGNORE INTO tracking_links (code,case_id,platform,campaign_id,url,created_at) VALUES (?,?,?,?,?,?)", (code, case_id, platform, campaign_id, url, C.now()))
    db.commit()
    return code


def capture_inquiry(db, channel, handle, event_key, code=None, summary="", name=None, case_id=None, source_platform=None, campaign_id=None):
    """記錄詢問。有代碼算直接追蹤；沒有代碼但人工填來源算人工補登；都沒有就是未知。不憑姓名合併。"""
    kind = "未知"
    if code:
        link = db.execute("SELECT * FROM tracking_links WHERE code=?", (code,)).fetchone()
        if link:
            case_id, source_platform, campaign_id, kind = link["case_id"], link["platform"], link["campaign_id"], "直接追蹤"
    elif source_platform:
        kind = "人工補登"
    customer_id, inquiry_id, created = C.record_inquiry(db, channel, handle, event_key, case_id, source_platform, campaign_id, summary, name, kind)
    if created:
        db.execute("UPDATE customers SET source_platform=COALESCE(source_platform,?), source_campaign=COALESCE(source_campaign,?) WHERE customer_id=?", (source_platform, campaign_id, customer_id))
        if case_id:
            watch_case(db, customer_id, case_id)
    db.commit()
    return customer_id, inquiry_id, created


def backfill_source(db, inquiry_id, source_platform, campaign_id=None):
    """無法直接辨識來源時人工補登。"""
    db.execute("UPDATE inquiries SET source_platform=?, campaign_id=?, source_kind='人工補登' WHERE inquiry_id=? AND source_kind='未知'", (source_platform, campaign_id, inquiry_id))
    row = db.execute("SELECT customer_id FROM inquiries WHERE inquiry_id=?", (inquiry_id,)).fetchone()
    db.execute("UPDATE customers SET source_platform=COALESCE(source_platform,?), source_campaign=COALESCE(source_campaign,?) WHERE customer_id=?", (source_platform, campaign_id, row["customer_id"]))
    db.commit()


def mark_inquiry_valid(db, inquiry_id, is_valid, judged_by=None):
    db.execute("INSERT OR REPLACE INTO inquiry_quality (inquiry_id,is_valid,judged_by,at) VALUES (?,?,?,?)", (inquiry_id, 1 if is_valid else 0, judged_by, C.now()))
    db.commit()


def watch_case(db, customer_id, case_id):
    db.execute("INSERT OR IGNORE INTO customer_cases VALUES (?,?,?)", (customer_id, case_id, C.now()))
    db.commit()


def next_question(db, customer_id):
    """逐步確認需求：一次只問下一個還不知道的項目。"""
    row = db.execute("SELECT * FROM customers WHERE customer_id=?", (customer_id,)).fetchone()
    for field, question in NEEDS_ORDER:
        if not row[field]:
            return field, question
    return None, None


def update_needs(db, customer_id, **needs):
    allowed = {f for f, _ in NEEDS_ORDER}
    bad = set(needs) - allowed
    if bad:
        raise ValueError(f"未知的需求欄位：{bad}")
    for field, value in needs.items():
        db.execute(f"UPDATE customers SET {field}=? WHERE customer_id=?", (value, customer_id))
    db.execute("UPDATE customers SET stage='需求確認' WHERE customer_id=? AND stage='新詢問'", (customer_id,))
    db.commit()


def set_contact_preference(db, customer_id, contact_pref=None, subscribed=None):
    if contact_pref is not None:
        db.execute("UPDATE customers SET contact_pref=? WHERE customer_id=?", (contact_pref, customer_id))
    if subscribed is not None:
        db.execute("UPDATE customers SET subscribed=? WHERE customer_id=?", (1 if subscribed else 0, customer_id))
    db.commit()


def stop_contact(db, customer_id):
    """停止聯絡：取消尚未完成的追蹤，之後不再建立。"""
    db.execute("UPDATE customers SET do_not_contact=1, subscribed=0 WHERE customer_id=?", (customer_id,))
    db.execute("UPDATE contact_points SET consent='停止聯絡' WHERE customer_id=?", (customer_id,))
    db.execute("UPDATE tasks SET state='取消', last_error='客戶停止聯絡' WHERE customer_id=? AND state IN ('待辦','執行中') AND kind IN ('客戶追蹤','回覆新詢問','未成交追蹤')", (customer_id,))
    db.commit()


def add_referral(db, new_customer_id, referred_by):
    if new_customer_id == referred_by:
        raise ValueError("不能轉介紹自己")
    db.execute("UPDATE customers SET referred_by=? WHERE customer_id=?", (referred_by, new_customer_id))
    db.commit()


def send_message(db, customer_id, platform, message_key, sender, today=None):
    """發訊息的唯一入口：停止聯絡、未訂閱、未授權都不送；同一 message_key 只送一次。"""
    row = db.execute("SELECT do_not_contact,subscribed FROM customers WHERE customer_id=?", (customer_id,)).fetchone()
    if row["do_not_contact"]:
        return "拒絕：客戶已停止聯絡"
    if not row["subscribed"]:
        return "拒絕：客戶未訂閱"
    if not is_authorized(db, platform, "發訊息", today):
        return "拒絕：未設定發訊息授權"
    task_id, _ = C.add_task(db, f"訊息:{message_key}:{customer_id}", "發訊息", platform, due=C.now()[:10], customer_id=customer_id)
    return C.run_task(db, task_id, lambda _task: sender(customer_id))


# ---------- 預約、諮詢、委託 ----------
def book_appointment(db, customer_id, case_id, at, mode, place, prep, owner=None):
    """預約需有時間、方式／地點與準備事項。現場勘查一律註明不含室內。"""
    if not (at and mode and place and prep):
        raise ValueError("預約需要時間、方式、地點與準備事項")
    if "勘查" in mode and SURVEY_NOTE not in prep:
        prep = f"{prep}。{SURVEY_NOTE}"
    appt_id = C.book(db, customer_id, case_id, at, mode, place, prep)
    if case_id:
        watch_case(db, customer_id, case_id)
    C.add_task(db, f"預約:{appt_id}", "預約提醒", f"{at} {mode}", due=at[:10], customer_id=customer_id, case_id=case_id, owner=owner)
    db.commit()
    return appt_id


def _follow(db, customer_id, key, reason, due, owner=None):
    row = db.execute("SELECT do_not_contact FROM customers WHERE customer_id=?", (customer_id,)).fetchone()
    if row["do_not_contact"]:
        return None
    return C.add_task(db, key, "未成交追蹤", reason, due=due, customer_id=customer_id, owner=owner)[0]


def record_consultation(db, appt_id, outcome, owner, note="", lost_reason=None, service=None, today=None):
    """諮詢結果回寫。outcome：委託／未成交／未到／取消。"""
    appt = db.execute("SELECT * FROM appointments WHERE appt_id=?", (appt_id,)).fetchone()
    if not appt:
        raise ValueError("找不到預約")
    today = today or C.now()[:10]
    customer_id = appt["customer_id"]
    if outcome in ("未到", "取消"):
        db.execute("UPDATE appointments SET state=?, outcome=? WHERE appt_id=?", (outcome, note, appt_id))
        _follow(db, customer_id, f"改約:{appt_id}", "重新確認預約", today, owner)
        db.commit()
        return None
    db.execute("UPDATE appointments SET state='已完成', outcome=? WHERE appt_id=?", (f"{outcome}：{note}", appt_id))
    if outcome == "委託":
        return create_mandate(db, customer_id, appt["case_id"], service, owner, today)
    if outcome == "未成交":
        if lost_reason not in LOST_ROUTES:
            raise ValueError(f"未成交原因需為：{'、'.join(LOST_ROUTES)}")
        segment, days, step = LOST_ROUTES[lost_reason]
        due = (datetime.date.fromisoformat(today) + datetime.timedelta(days=days)).isoformat()
        db.execute("UPDATE customers SET stage='未成交', lost_reason=?, segment=? WHERE customer_id=?", (lost_reason, segment, customer_id))
        _follow(db, customer_id, f"分流:{customer_id}:{lost_reason}:{due}", step, due, owner)
        db.commit()
        return segment
    raise ValueError("諮詢結果需為：委託、未成交、未到或取消")


def create_mandate(db, customer_id, case_id, service, owner, today=None):
    today = today or C.now()[:10]
    mandate_id = "M" + C._h(customer_id, case_id or "")
    db.execute("INSERT OR IGNORE INTO mandates (mandate_id,customer_id,case_id,service,signed_at) VALUES (?,?,?,?,?)", (mandate_id, customer_id, case_id, service, today))
    db.execute("UPDATE customers SET stage='委託', owner=COALESCE(owner,?) WHERE customer_id=?", (owner, customer_id))
    db.commit()
    return mandate_id


def advance_mandate(db, mandate_id, stage, note, next_step, next_due, owner=None):
    """委託進度。每一步都要有下一步與期限；結案除外。"""
    if stage not in MANDATE_STAGES:
        raise ValueError(f"未知的委託階段：{stage}")
    if stage != "結案" and not (next_step and next_due):
        raise ValueError("委託進度需要下一步與期限")
    row = db.execute("SELECT * FROM mandates WHERE mandate_id=?", (mandate_id,)).fetchone()
    db.execute("INSERT INTO mandate_events (mandate_id,at,stage,note,next_step,next_due) VALUES (?,?,?,?,?,?)", (mandate_id, C.now(), stage, note, next_step, next_due))
    result = stage if stage in ("得標", "未得標") else row["result"]
    result_at = C.now()[:10] if stage in ("得標", "未得標") else row["result_at"]
    db.execute("UPDATE mandates SET stage=?, result=?, result_at=? WHERE mandate_id=?", (stage, result, result_at, mandate_id))
    customer_stage = {"投標": "投標", "投標準備": "投標", "結案": "結案"}.get(stage, "後續服務" if stage not in ("委託簽約",) else "委託")
    db.execute("UPDATE customers SET stage=? WHERE customer_id=?", (customer_stage, row["customer_id"]))
    if next_step:
        C.add_task(db, f"委託:{mandate_id}:{stage}:{next_due}", "委託進度", next_step, due=next_due, customer_id=row["customer_id"], case_id=row["case_id"], owner=owner)
    db.commit()


# ---------- 收費條件 ----------
FEE_SEED = (
    ("fee-apply", "聲請點交", "50,000 元", "服務項目 01–05", "網站 services.py", "確認中", "網站與收費表一致，生效日待確認"),
    ("fee-package", "包辦點交", "120,000 元", "服務項目 01–11", "網站 services.py", "確認中", "網站與收費表一致，生效日待確認"),
    ("fee-full-rate", "全程代標費率", "2%～5%", "依案件難易評估", "網站 services.py", "確認中", "費率一致，生效日待確認"),
    ("fee-full-base", "全程代標計算基準", None, None, "衝突", "待確認", "網站寫「標價」；fees.md 寫「該拍次法院公告底價」"),
    ("fee-full-under-6m", "600 萬元以下案件", None, None, "衝突", "待確認", "網站寫「最低 12 萬元」；fees.md 寫「另議」"),
    ("fee-advance", "尾款代墊用語", None, None, "衝突", "待確認", "網站寫「協助代墊尾款」；fees.md 寫「保證代墊尾款」。依規則不得保證"),
    ("fee-no-win", "未得標是否收費", None, None, "待提供", "待確認", "未經確認不得對外使用"),
    ("fee-promo", "優惠期間", None, None, "待提供", "待確認", "目前未取得"),
    ("fee-loan", "貸款條件", None, None, "待提供", "待確認", "不保證貸款成數；利率與成數須附日期"),
)


def seed_fee_terms(db):
    db.executemany("INSERT OR IGNORE INTO fee_terms (term_id,item,value,condition,source,status,note) VALUES (?,?,?,?,?,?,?)", FEE_SEED)
    db.commit()


def fee_for_public_use(db, term_id):
    """只有已確認且在生效期間內的條件可以對外使用。"""
    row = db.execute("SELECT * FROM fee_terms WHERE term_id=?", (term_id,)).fetchone()
    today = C.now()[:10]
    if not row or row["status"] != "已確認" or not row["effective_from"] or row["effective_from"] > today or (row["effective_to"] and row["effective_to"] < today):
        return None
    return row["value"]


def confirm_fee(db, term_id, value, condition, effective_from, confirmed_by, effective_to=None):
    db.execute("UPDATE fee_terms SET value=?, condition=?, effective_from=?, effective_to=?, status='已確認', note=? WHERE term_id=?", (value, condition, effective_from, effective_to, f"{confirmed_by} 於 {C.now()[:10]} 確認", term_id))
    db.commit()


# ---------- 成效 ----------
UNAVAILABLE = "未取得"
DEFINITIONS = {
    "有效詢問": "由人工判定為有效的詢問（inquiry_quality.is_valid=1）",
    "每有效詢問成本": "費用 ÷ 有效詢問筆數",
    "每預約成本": "費用 ÷ 預約筆數",
    "每委託成本": "費用 ÷ 委託筆數",
    "歸屬": "平台與活動依客戶首次來源；案件依詢問、預約、委託紀錄的案件",
}


def _cost_per(cost, count):
    return round(cost / count, 1) if cost and count else UNAVAILABLE


def performance(db, dimension, key):
    """dimension：platform／campaign／case。沒有資料一律回傳未取得，不填假數字。"""
    if dimension == "platform":
        stats = db.execute("SELECT SUM(s.impressions) i,SUM(s.clicks) c,SUM(s.cost) k,GROUP_CONCAT(DISTINCT s.data_origin) o,COUNT(*) n FROM ad_stats s JOIN campaigns m USING(campaign_id) WHERE m.platform=?", (key,)).fetchone()
        customers = "SELECT customer_id FROM customers WHERE source_platform=?"
    elif dimension == "campaign":
        stats = db.execute("SELECT SUM(impressions) i,SUM(clicks) c,SUM(cost) k,GROUP_CONCAT(DISTINCT data_origin) o,COUNT(*) n FROM ad_stats WHERE campaign_id=?", (key,)).fetchone()
        customers = "SELECT customer_id FROM customers WHERE source_campaign=?"
    elif dimension == "case":
        stats = db.execute("SELECT SUM(impressions) i,SUM(clicks) c,SUM(cost) k,GROUP_CONCAT(DISTINCT data_origin) o,COUNT(*) n FROM ad_stats WHERE case_id=?", (key,)).fetchone()
        customers = None
    else:
        raise ValueError("dimension 需為 platform、campaign 或 case")
    if dimension == "case":
        where_i, where_a, where_m, args = "case_id=?", "case_id=?", "case_id=?", (key,)
    else:
        sub = f"customer_id IN ({customers})"
        where_i, where_a, where_m, args = sub, sub, sub, (key,)
    one = lambda sql: db.execute(sql, args).fetchone()[0]
    inquiries = one(f"SELECT COUNT(*) FROM inquiries WHERE {where_i}")
    judged = one(f"SELECT COUNT(*) FROM inquiries JOIN inquiry_quality USING(inquiry_id) WHERE {where_i}")
    valid = one(f"SELECT COUNT(*) FROM inquiries JOIN inquiry_quality USING(inquiry_id) WHERE is_valid=1 AND {where_i}")
    booked = one(f"SELECT COUNT(*) FROM appointments WHERE {where_a}")
    consulted = one(f"SELECT COUNT(*) FROM appointments WHERE state='已完成' AND {where_a}")
    mandates = one(f"SELECT COUNT(*) FROM mandates WHERE {where_m}")
    bids = one(f"SELECT COUNT(*) FROM mandates WHERE result IS NOT NULL AND {where_m}")
    won = one(f"SELECT COUNT(*) FROM mandates WHERE result='得標' AND {where_m}")
    has_crm = inquiries or booked or mandates
    show = lambda value: value if has_crm else UNAVAILABLE
    has_ads = stats["n"] > 0
    cost = stats["k"] if has_ads else None
    return {
        "範圍": f"{dimension}:{key}",
        "曝光": stats["i"] if has_ads and stats["i"] is not None else UNAVAILABLE,
        "點擊": stats["c"] if has_ads and stats["c"] is not None else UNAVAILABLE,
        "費用": cost if cost is not None else UNAVAILABLE,
        "詢問": show(inquiries),
        "有效詢問": valid if judged else UNAVAILABLE,
        "預約": show(booked), "實際諮詢": show(consulted), "委託": show(mandates), "投標結果": show(bids), "得標": show(won),
        "每有效詢問成本": _cost_per(cost, valid), "每預約成本": _cost_per(cost, booked), "每委託成本": _cost_per(cost, mandates),
        "資料性質": stats["o"] if has_ads and stats["o"] else UNAVAILABLE,
    }


def daily_board(db, today=None):
    """首頁待辦，沿用 core.dashboard，排除已停止聯絡的客戶。"""
    board = C.dashboard(db, today)
    stopped = {r[0] for r in db.execute("SELECT customer_id FROM customers WHERE do_not_contact=1")}
    board["今日需回覆與追蹤"] = [t for t in board["今日需回覆與追蹤"] if t["customer_id"] not in stopped]
    return board
