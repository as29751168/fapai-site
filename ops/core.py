"""法拍行銷與客戶經營核心（SQLite；不改動既有爬蟲與網站建置）。
原則：價格分離、去重、重跑不重複、發布失敗不算完成、未授權不產生廣告支出、缺資料不造假。"""
import hashlib, json, os, re, sqlite3, datetime

HERE = os.path.dirname(__file__)
STATUS_MAP = {"待標中": "待拍", "開標日期已過・待確認": "待確認", "流標・待下一拍公告": "流標", "停拍（可能再拍）": "停拍"}
PLATFORMS = ("自有網站", "House-Info", "買屋網", "FB廣告", "FB粉專", "LINE@", "FB社團")
TRANSIENT = ("timeout", "429", "503", "連線")      # 暫時性錯誤：有限次重試
MAX_RETRY = 3


def now(): return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
def _h(*p): return hashlib.sha1("|".join(p).encode()).hexdigest()[:12]


def connect(path=":memory:"):
    c = sqlite3.connect(path); c.row_factory = sqlite3.Row
    c.executescript(open(os.path.join(HERE, "schema.sql"), encoding="utf-8").read())
    return c


# ---------- 解析 ----------
def roc_date(s):
    m = re.match(r"(\d{2,3})/(\d{1,2})/(\d{1,2})$", s or "")
    return f"{int(m[1]) + 1911:04d}-{int(m[2]):02d}-{int(m[3]):02d}" if m else None


def money(s):
    """'1329 萬'、'1.2億'、'12,300,000' → 元；無法解析回傳 None"""
    m = re.search(r"([\d.,]+)\s*(億|萬)?", s or "")
    if not m: return None
    try: v = float(m[1].replace(",", ""))
    except ValueError: return None
    return int(round(v * (100000000 if m[2] == "億" else 10000 if m[2] == "萬" else 1)))


def official_price_for_round(record_text, rnd):
    """只從「拍賣紀錄」（法院公告來源）取指定拍次底標價；取不到就回傳 None（不拿售價頂替）"""
    cn = "零一二三四五六七八九十"
    for ln in (record_text or "").splitlines():
        m = re.match(r"第(.{1,2})拍\s+\S+\s+底標價[：:]\s*(.+)", ln.strip())
        if m and rnd and (m[1] == cn[rnd] if rnd <= 10 else False):
            return money(m[2])
    return None


def norm_addr(a):
    """物件識別：取「路名最後2字＋路／街／大道＋門牌」之後的部分，去掉縣市區與社區名，讓不同來源的同一地址得到相同鍵"""
    a = re.sub(r"【[^】]*】|\s+", "", a or "")
    m = re.search(r"(?:路|街|大道)(?=(?:[一-鿿]段)?\d)", a)
    return a[max(0, m.start() - 2):] if m else a


def ping(v):
    try: return float(re.sub(r"[^\d.]", "", v or "") or "nan")
    except ValueError: return None


# ---------- 案件主檔 ----------
def _fields_from_104(x):
    inf = x.get("資訊") or {}
    rnd = int(inf["拍次"]) if str(inf.get("拍次", "")).isdigit() else None
    return {
        "case_no": inf.get("案號", ""), "object_key": norm_addr(x.get("地址")),
        "title": x.get("地址"), "address": x.get("地址"), "area": (x.get("區域") or "").split("-")[0],
        "ptype": x.get("類型"), "ping_total": ping(inf.get("總登記坪數")), "ping_main": ping(inf.get("主建物")),
        "ping_attached": ping(inf.get("附屬建物")), "ping_land": ping(inf.get("土地登記總坪數")),
        "floor": inf.get("所在樓層"), "parking": inf.get("車位") or inf.get("停車位"),
        "round": rnd, "auction_date": roc_date(inf.get("開標日期")),
        "official_floor_price": official_price_for_round(inf.get("拍賣紀錄"), rnd),
        "listing_price_raw": x.get("價格"),
        "delivery": (re.search(r"點交情形→(不點交|部分點交|點交)", inf.get("筆錄") or "") or [None, "待確認"])[1],
        "status": STATUS_MAP.get(x.get("狀態"), "待確認"),
    }


TRACKED = ("round", "auction_date", "official_floor_price", "estimated_price", "delivery", "status", "address", "court")


def upsert_case(db, fields, source, source_id, court=""):
    """匯入／更新一件案件。先以平台編號比對，再以（執行機關,案號,物件識別）比對；同一件重匯入不會新增。
    回傳 (case_id, 'new'|'changed'|'same')"""
    f = dict(fields); f["court"] = court or f.get("court", "")
    row = db.execute("SELECT case_id FROM case_alias WHERE source=? AND source_id=?", (source, source_id)).fetchone()
    if not row:
        row = db.execute("SELECT case_id FROM cases WHERE court=? AND case_no=? AND object_key=?",
                         (f["court"], f["case_no"], f["object_key"])).fetchone()
    ts = now()
    # 關鍵資料查核：缺案號或缺正式底價 → 待確認並阻擋自動發布（不自行補值）
    miss = [n for n, v in (("案號", f.get("case_no")), ("法院公告底價", f.get("official_floor_price")), ("拍次", f.get("round")), ("開標日期", f.get("auction_date"))) if not v]
    if f["status"] == "待拍" and miss: f["needs_review"], f["review_reason"] = 1, "缺：" + "、".join(miss)
    else: f["needs_review"], f["review_reason"] = 0, None
    if not row:
        cid = "C" + _h(f["court"], f["case_no"], f["object_key"], source, source_id if not f["case_no"] else "")
        cols = list(f) + ["case_id", "source", "verified_at", "created_at", "updated_at"]
        db.execute(f"INSERT INTO cases ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                   [*f.values(), cid, source, ts, ts, ts])
        db.execute("INSERT OR IGNORE INTO case_alias VALUES (?,?,?)", (source, source_id, cid))
        db.execute("INSERT INTO case_history (case_id,at,field,old,new,version,source) VALUES (?,?,?,?,?,1,?)", (cid, ts, "建檔", None, f["status"], source))
        return cid, "new"
    cid = row["case_id"]
    db.execute("INSERT OR IGNORE INTO case_alias VALUES (?,?,?)", (source, source_id, cid))
    cur = dict(db.execute("SELECT * FROM cases WHERE case_id=?", (cid,)).fetchone())
    changes = {k: (cur.get(k), f.get(k)) for k in TRACKED if k in f and f[k] not in (None, "") and cur.get(k) != f[k]}
    # 正式底價不可被空值或預估價覆蓋；estimated_price 只接受人工設定，不由匯入改動
    changes.pop("estimated_price", None)
    ver = cur["version"] + (1 if changes else 0)
    sets = {k: f[k] for k in f if k != "estimated_price" and f[k] is not None}
    sets.update(version=ver, verified_at=ts, updated_at=ts)
    db.execute(f"UPDATE cases SET {','.join(k + '=?' for k in sets)} WHERE case_id=?", [*sets.values(), cid])
    for k, (o, n) in changes.items():
        db.execute("INSERT INTO case_history (case_id,at,field,old,new,version,source) VALUES (?,?,?,?,?,?,?)", (cid, ts, k, str(o), str(n), ver, source))
    return cid, ("changed" if changes else "same")


def import_104(db, items, court_of=None):
    """匯入 site/data.json['104'] 的物件。court_of(x)->執行機關，未提供則留空並標待確認（不猜）。"""
    out = {"new": 0, "changed": 0, "same": 0}
    for x in items:
        _, r = upsert_case(db, _fields_from_104(x), "104法拍網", x["編號"], court_of(x) if court_of else "")
        out[r] += 1
    db.commit(); return out


def set_estimated_price(db, case_id, price, who):
    cur = db.execute("SELECT estimated_price FROM cases WHERE case_id=?", (case_id,)).fetchone()[0]
    if cur == price: return                      # 沒變就不重複寫紀錄
    db.execute("UPDATE cases SET estimated_price=? WHERE case_id=?", (price, case_id))
    db.execute("INSERT INTO case_history (case_id,at,field,old,new,version,source) VALUES (?,?,?,?,?,0,?)", (case_id, now(), "estimated_price", None if cur is None else str(cur), str(price), "人工:" + who))
    db.commit()


# ---------- 任務（冪等＋有限重試） ----------
def add_task(db, key, kind, reason="", due=None, **ref):
    """同一 idempotency_key 只會有一筆；回傳 (task_id, created)"""
    try:
        cur = db.execute("INSERT INTO tasks (idempotency_key,kind,reason,case_id,customer_id,pub_id,owner,due,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                         (key, kind, reason, ref.get("case_id"), ref.get("customer_id"), ref.get("pub_id"), ref.get("owner"), due, now()))
        return cur.lastrowid, True
    except sqlite3.IntegrityError:
        return db.execute("SELECT task_id FROM tasks WHERE idempotency_key=?", (key,)).fetchone()[0], False


def run_task(db, task_id, fn):
    """執行任務。已完成者不重跑；暫時性錯誤最多重試 MAX_RETRY 次；登入／權限／資料錯誤直接轉人工。fn 回傳完成證據字串。"""
    t = db.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
    if t["state"] in ("完成", "待人工", "失敗"): return t["state"]
    db.execute("UPDATE tasks SET state='執行中', attempts=attempts+1 WHERE task_id=?", (task_id,))
    try:
        ev = fn(dict(t))
        if not ev: raise ValueError("缺少完成證據")   # 沒證據不算完成
        db.execute("UPDATE tasks SET state='完成', evidence=?, done_at=?, last_error=NULL WHERE task_id=?", (str(ev), now(), task_id))
        st = "完成"
    except Exception as ex:
        msg = str(ex); transient = any(k in msg.lower() for k in TRANSIENT)
        att = db.execute("SELECT attempts FROM tasks WHERE task_id=?", (task_id,)).fetchone()[0]
        st = ("待辦" if att < MAX_RETRY else "失敗") if transient else "待人工"
        db.execute("UPDATE tasks SET state=?, last_error=? WHERE task_id=?", (st, msg, task_id))
    db.commit(); return st


# ---------- 刊登 ----------
def register_publication(db, case_id, platform, platform_ref="", url="", asset_id=None):
    assert platform in PLATFORMS, platform
    pid = "P" + _h(case_id, platform, platform_ref)
    db.execute("INSERT OR IGNORE INTO publications (pub_id,case_id,asset_id,platform,platform_ref,url) VALUES (?,?,?,?,?,?)", (pid, case_id, asset_id, platform, platform_ref, url))
    db.commit(); return pid


def can_publish(db, case_id):
    c = db.execute("SELECT needs_review,review_reason,status FROM cases WHERE case_id=?", (case_id,)).fetchone()
    if c["needs_review"]: return False, "待確認：" + (c["review_reason"] or "")
    if c["status"] != "待拍": return False, "案件狀態為" + c["status"]
    return True, ""


def publish(db, pub_id, poster):
    """poster(pub)->(platform_ref,url)；失敗標為「失敗」，不得標成已發布。上線前再查核關鍵資料。"""
    p = db.execute("SELECT * FROM publications WHERE pub_id=?", (pub_id,)).fetchone()
    if p["state"] in ("已發布", "發布已驗證"): return p["state"]      # 重送不重複發布
    ok, why = can_publish(db, p["case_id"])
    if not ok:
        db.execute("UPDATE publications SET state='失敗', last_error=? WHERE pub_id=?", (why, pub_id)); db.commit(); return "失敗"
    try:
        ref, url = poster(dict(p))
        ver = db.execute("SELECT version FROM cases WHERE case_id=?", (p["case_id"],)).fetchone()[0]
        db.execute("UPDATE publications SET state='已發布', platform_ref=?, url=?, published_case_version=?, published_at=?, last_error=NULL WHERE pub_id=?", (ref, url, ver, now(), pub_id))
        st = "已發布"
    except Exception as ex:
        db.execute("UPDATE publications SET state='失敗', last_error=?, retries=retries+1 WHERE pub_id=?", (str(ex), pub_id)); st = "失敗"
    db.commit(); return st


def mark_verified(db, pub_id, evidence):
    if not evidence: raise ValueError("驗證需要證據（截圖或網址檢查結果）")
    db.execute("UPDATE publications SET state='發布已驗證', verified_at=? WHERE pub_id=? AND state='已發布'", (now(), pub_id)); db.commit()


def find_affected(db):
    """停拍／撤回／拍定／流標，或案件版本高於已發布版本 → 建立更新／下架任務（每通路每案件版本一筆，重跑不重複）。"""
    made = []
    rows = db.execute("""SELECT p.pub_id,p.platform,p.case_id,p.published_case_version pv,c.version cv,c.status,c.address
                         FROM publications p JOIN cases c USING(case_id)
                         WHERE p.state IN ('已發布','發布已驗證','待更新','待下架')""").fetchall()
    for r in rows:
        if r["status"] in ("停拍", "撤回", "拍定", "流標"):
            kind, newstate = "下架", "待下架"
            # 停拍可能再拍，仍先下架／暫停，待人工決定是否保留
        elif (r["pv"] or 0) < r["cv"]:
            kind, newstate = "更新", "待更新"
        else: continue
        tid, created = add_task(db, f"{kind}:{r['pub_id']}:v{r['cv']}", kind, f"{r['status']}／案件版本{r['pv']}→{r['cv']}", case_id=r["case_id"], pub_id=r["pub_id"])
        db.execute("UPDATE publications SET state=? WHERE pub_id=? AND state NOT IN ('已下架')", (newstate, r["pub_id"]))
        if created: made.append((r["platform"], r["address"], kind))
    db.commit(); return made


# ---------- 廣告支出授權 ----------
def authorize_spend(db, platform, cap_total, valid_from, valid_to, granted_by, note=""):
    db.execute("INSERT INTO spend_authorizations (platform,cap_total,valid_from,valid_to,granted_by,note) VALUES (?,?,?,?,?,?)", (platform, cap_total, valid_from, valid_to, granted_by, note)); db.commit()


def activate_campaign(db, campaign_id, today=None):
    """沒有有效授權就拒絕啟用——不會產生實際廣告支出"""
    today = today or now()[:10]
    c = db.execute("SELECT * FROM campaigns WHERE campaign_id=?", (campaign_id,)).fetchone()
    a = db.execute("SELECT * FROM spend_authorizations WHERE platform=? AND valid_from<=? AND valid_to>=? ORDER BY id DESC", (c["platform"], today, today)).fetchone()
    if not a:
        db.execute("UPDATE campaigns SET state='待授權' WHERE campaign_id=?", (campaign_id,)); db.commit()
        raise PermissionError("尚未設定有效的廣告支出授權")
    db.execute("UPDATE campaigns SET state='進行中', spend_cap=? WHERE campaign_id=?", (a["cap_total"], campaign_id)); db.commit()


# ---------- 客戶 ----------
def record_inquiry(db, channel, handle, event_key, case_id=None, source_platform=None, campaign_id=None, summary="", name=None, source_kind="未知"):
    """同一 event_key 重送不重複建客戶／詢問。客戶僅以（管道,帳號）辨識，不憑姓名合併。"""
    ex = db.execute("SELECT inquiry_id,customer_id FROM inquiries WHERE event_key=?", (event_key,)).fetchone()
    if ex: return ex["customer_id"], ex["inquiry_id"], False
    cp = db.execute("SELECT customer_id FROM contact_points WHERE channel=? AND handle=?", (channel, handle)).fetchone()
    if cp: cid = cp["customer_id"]
    else:
        cid = "U" + _h(channel, handle)
        db.execute("INSERT INTO customers (customer_id,display_name,created_at) VALUES (?,?,?)", (cid, name, now()))
        db.execute("INSERT INTO contact_points (channel,handle,customer_id) VALUES (?,?,?)", (channel, handle, cid))
    iid = "Q" + _h(event_key)
    db.execute("INSERT INTO inquiries VALUES (?,?,?,?,?,?,?,?,?)", (iid, cid, case_id, source_platform, campaign_id, source_kind, event_key, summary, now()))
    add_task(db, f"回覆:{iid}", "回覆新詢問", summary, due=now()[:10], customer_id=cid, case_id=case_id)
    db.commit(); return cid, iid, True


def add_interaction(db, customer_id, channel, summary, owner, next_step, next_due):
    """每次互動必須有下一步與期限"""
    if not (next_step and next_due): raise ValueError("每次互動都需要下一步與日期")
    db.execute("INSERT INTO interactions (customer_id,at,channel,summary,owner,next_step,next_due) VALUES (?,?,?,?,?,?,?)", (customer_id, now(), channel, summary, owner, next_step, next_due))
    add_task(db, f"追蹤:{customer_id}:{next_due}:{next_step}", "客戶追蹤", next_step, due=next_due, customer_id=customer_id, owner=owner)
    db.commit()


def book(db, customer_id, case_id, at, mode, place, prep):
    aid = "A" + _h(customer_id, case_id or "", at)
    db.execute("INSERT OR IGNORE INTO appointments (appt_id,customer_id,case_id,at,mode,place,prep) VALUES (?,?,?,?,?,?,?)", (aid, customer_id, case_id, at, mode, place, prep))
    db.execute("UPDATE customers SET stage='預約' WHERE customer_id=?", (customer_id,)); db.commit(); return aid


# ---------- 儀表板：沒有資料就顯示「未取得」，不填假數字 ----------
def dashboard(db, today=None):
    today = today or now()[:10]
    q = lambda s, *a: db.execute(s, a).fetchall()
    d = {
        "今日需回覆與追蹤": [dict(r) for r in q("SELECT customer_id,kind,reason,due FROM tasks WHERE state IN ('待辦','執行中') AND customer_id IS NOT NULL AND due<=?", today)],
        "今日預約": [dict(r) for r in q("SELECT appt_id,customer_id,at,mode FROM appointments WHERE state='已預約' AND substr(at,1,10)=?", today)],
        "即將投標(7日內)": [dict(r) for r in q("SELECT case_id,address,auction_date,round FROM cases WHERE status='待拍' AND auction_date BETWEEN ? AND date(?,'+7 day')", today, today)],
        "待更新／待下架": [dict(r) for r in q("SELECT p.platform,c.address,p.state FROM publications p JOIN cases c USING(case_id) WHERE p.state IN ('待更新','待下架')")],
        "待補資料": [dict(r) for r in q("SELECT case_id,address,review_reason FROM cases WHERE needs_review=1")],
        "自動化異常": [dict(r) for r in q("SELECT task_id,kind,state,last_error FROM tasks WHERE state IN ('待人工','失敗')")],
    }
    n = db.execute("SELECT COUNT(*) FROM ad_stats").fetchone()[0]
    inq = db.execute("SELECT COUNT(*) FROM inquiries").fetchone()[0]
    perf = {"曝光": "未取得", "點擊": "未取得", "花費": "未取得", "每有效詢問成本": "未取得"}
    if n:
        s = db.execute("SELECT SUM(impressions) i,SUM(clicks) c,SUM(cost) k FROM ad_stats").fetchone()
        perf.update({"曝光": s["i"], "點擊": s["c"], "花費": s["k"]})
        if s["k"] is not None and inq: perf["每有效詢問成本"] = round(s["k"] / inq, 1)   # 分母＝詢問筆數（含全部來源）
    perf["詢問(依來源)"] = {f"{r[0] or '未知'}／{r[1]}": r[2] for r in db.execute("SELECT source_platform,source_kind,COUNT(*) FROM inquiries GROUP BY 1,2")} or "未取得"
    d["成效"] = perf
    return d


if __name__ == "__main__":
    import sys
    db = connect(sys.argv[2] if len(sys.argv) > 2 else "ops/ops.db")
    if sys.argv[1] == "import":
        print(import_104(db, json.load(open("site/data.json", encoding="utf-8"))["104"]))
    elif sys.argv[1] == "dashboard":
        print(json.dumps(dashboard(db), ensure_ascii=False, indent=1))
    elif sys.argv[1] == "affected":
        print(find_affected(db))
