"""每日同步：透明房訊(104woo.com.tw)林小姐 Anna 的物件 -> 照片 site/photos.json，並補上 104法拍網列表沒有的物件"""
import json, re, time, datetime, urllib.request, urllib.error, urllib.parse, html as H

MOBILE = "0986678928"
BASE = "https://www.104woo.com.tw"
CITIES = ["台北市", "新北市", "桃園市"]   # 他人物件對照法院照的範圍
ALL_CITIES = ["台北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣", "苗栗縣", "台中市", "彰化縣", "南投縣", "雲林縣", "嘉義市", "嘉義縣", "台南市", "高雄市", "屏東縣", "宜蘭縣", "花蓮縣", "台東縣", "澎湖縣", "金門縣", "連江縣"]   # 自家物件：買屋網有上架的全部縣市
UA = {"User-Agent": "Mozilla/5.0 (fapai-site daily sync)", "Content-Type": "application/json; charset=utf-8"}
NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

def post_items(city):
    q = urllib.parse.urlencode({"isJson": "Y", "type": "SEARCH", "cityCourt": "", "city": city, "mobile": MOBILE, "pageIndex": 1, "pageSize": 100})
    for i in range(3):
        try:
            req = urllib.request.Request(f"{BASE}/MW/SearchItems?{q}", data=b"", headers=UA, method="POST")
            return json.loads(urllib.request.urlopen(req, timeout=40).read().decode("utf-8"))["items"]
        except Exception:
            time.sleep(3)
    return []

BLOCKED = []   # 透明房訊回 403（短時間開太多頁被擋）後，這次執行就不再開物件頁，改用 data/detail.json

def get_text(path, tries=2):
    # 2026-11-27：每天一次開近千個物件頁，約 90 頁後透明房訊回 403，後面的坪數、屋齡、筆錄就全空。
    # 改成：被擋就停（不硬重試），逾時才重試一次。
    if BLOCKED: return ""
    h = ""
    for i in range(tries):
        try:
            h = urllib.request.urlopen(urllib.request.Request(BASE + path, headers={"User-Agent": UA["User-Agent"]}), timeout=40).read().decode("utf-8", "ignore")
            break
        except urllib.error.HTTPError as e:
            if e.code in (403, 429): BLOCKED.append(path); print("透明房訊回", e.code, "，這次不再開物件頁：", path); return ""
            h = ""
        except Exception:
            h = ""
        if i < tries - 1: time.sleep(5)
    if not h: return ""
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", h, flags=re.S)
    return re.sub(r"[ \t\r　]+", " ", H.unescape(re.sub(r"<[^>]+>", "\n", h)))

# 2026-11-27：每天同步都是從零重建物件，當天物件頁抓不到時坪數、屋齡、筆錄就會變空白。
# 抓到的詳細欄位存進 data/detail.json，下次抓不到就沿用上次透明房訊原文的值（抓得到一律用新的）。
DETAIL_F = "data/detail.json"
DETAIL_KEYS = ("總登記坪數", "屋齡", "所在樓層", "案號", "主建物", "附屬建物", "公共設施", "土地登記總坪數", "筆錄")
MASKED_NAME = re.compile(r"[一-鿿](?:[O○〇＊*ＯΟО]{2}|[O○〇＊*ＯΟО](?![A-Za-z])[一-鿿]?|０{2}(?![０-９]))")   # 與 scrape.py 相同：存檔前先隱去遮罩姓名
try: DETAIL = json.load(open(DETAIL_F, encoding="utf-8"))
except Exception: DETAIL = {}
DETAIL_STAT = {"沿用": 0, "仍缺": 0, "開頁": 0}

def detail_key(c):   # 拍次、開標日、底價都沒變 → 公告沒換，物件頁不用重開
    return f'{c.get("BID_COUNT") or ""}|{c.get("BID_DATE") or ""}|{c.get("TOTAL_PRICE") or ""}'

def detail_fresh(c):
    v = DETAIL.get(f"HW{c['NO']}") or {}
    return v.get("_key") == detail_key(c) and all(v.get(k) for k in ("總登記坪數", "屋齡", "筆錄"))

def detail_fill(no, info, key=""):
    old = DETAIL.get(no, {}); used = False
    for k in DETAIL_KEYS:
        if not info.get(k) and old.get(k): info[k] = old[k]; used = True
    if used: DETAIL_STAT["沿用"] += 1
    if not all(info.get(k) for k in ("總登記坪數", "屋齡", "筆錄")): DETAIL_STAT["仍缺"] += 1
    keep = {k: (MASKED_NAME.sub("（姓名已隱去）", info[k]) if k == "筆錄" else info[k]) for k in DETAIL_KEYS if info.get(k)}
    if keep: DETAIL[no] = {**keep, "_key": key}

def detail_save():
    json.dump(DETAIL, open(DETAIL_F, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
    print("物件詳細欄位：開頁", DETAIL_STAT["開頁"], "次；沿用上次", DETAIL_STAT["沿用"], "件；三欄仍缺", DETAIL_STAT["仍缺"], "件；存檔", len(DETAIL), "件", "（被擋）" if BLOCKED else "")

def norm(s): return re.sub(r"[\s　]|<[^>]*>", "", s or "")

def addr_tail(full):
    """完整地址只留路名門牌到「號」（去掉縣市、行政區、樓層），用來比對同一物件"""
    a = re.sub(r"^.{2,3}?[市縣].{1,3}?[區鄉鎮市]", "", norm(full).replace("臺", "台"))
    m = re.match(r"(.*?號)", a)
    return m.group(1) if m else ""

def photo_list(c):
    out = []
    for k in range(1, 13):
        p = c.get(f"PIC{k}")
        if not p: continue
        p = p.replace(BASE + "/", "")
        out.append(p if re.match(r"(wwwphoto|street|Media)/", p) else f"Media/{MOBILE}/{c['CITY']}/{c['FP_ID']}/{p}")
    return out

def query(city, lo, hi, mobile=""):
    p = {"isJson": "Y", "type": "SEARCH", "cityCourt": "", "city": city, "pageIndex": 1, "pageSize": 100, "price-min": lo, "price-max": hi}
    if mobile: p["mobile"] = mobile
    for i in range(3):
        try:
            req = urllib.request.Request(f"{BASE}/MW/SearchItems?{urllib.parse.urlencode(p)}", data=b"", headers=UA, method="POST")
            return json.loads(urllib.request.urlopen(req, timeout=40).read().decode("utf-8"))["items"]
        except Exception:
            time.sleep(2)
    return []

def market(city, lo=0, hi=200000, out=None, mobile=""):
    """列出透明房訊某縣市全部物件：單次最多回 30 筆，滿了就把價格區間對半切"""
    out = {} if out is None else out
    items = query(city, lo, hi, mobile)
    for it in items: out[it["NO"]] = it
    if len(items) >= 30 and hi - lo > 1:
        mid = (lo + hi) // 2
        market(city, lo, mid, out, mobile); market(city, mid, hi, out, mobile)
    return out

COURT = re.compile(r"(wwwphoto|street)/")
def court_photos(c):
    """他人物件只用法院現場照（不用其他經紀人自己上傳的照片）"""
    return [p for p in photo_list(c) if COURT.match(p)]

def district(s):
    m = re.search(r"[市縣](.{1,3}?[區鄉鎮市])", s or "")
    return m.group(1) if m else ""

def fetch_all():
    allc = {}
    for c in ALL_CITIES:
        for it in market(c, mobile=MOBILE).values():   # 單次最多 30 筆，靠價格對半切才抓得完
            if it.get("MOBILE") == MOBILE: allc[it["NO"]] = it
    return list(allc.values())

def full_notes(d):
    """從物件頁文字取出完整「拍賣公告」（點交情形＋編號段落），與 104法拍屋 的法院筆錄格式一致"""
    a = d.find("●點交情形→")
    if a < 0: return ""
    b = d.find("物件補充說明", a)
    seg = d[a:b if b > 0 else None]
    lines = [x.strip() for x in seg.splitlines() if x.strip()]
    out = []
    for x in lines:
        if out and re.fullmatch(r"\d+[‧.]", out[-1]): out[-1] += x
        else: out.append(x)
    return "\n".join(out)

def to_item(c):
    full = re.sub(r"<[^>]*>", "", c.get("FULL_ADDRESS") or "")
    city = full[:2]; m = re.search(r"[市縣](.{1,3}?[區鄉鎮市])", full); dist = m.group(1) if m else ""
    rnd = NUM.get((re.search(r"第(.)拍", c.get("BID_COUNT") or "") or [0, ""])[1], 0)
    price = c.get("TOTAL_PRICE") or ""
    try: pv = float(price)
    except Exception: pv = 0
    ptxt = (f"{pv:g}" + "萬") if pv else ""
    t = (c.get("TITLE") or c.get("ADDRESS") or "").strip()
    a = c.get("ADDRESS") or ""
    parts = t.rsplit(" ", 1)
    if len(parts) == 2 and parts[1] == a and a in parts[0]: t = parts[0].strip()
    if detail_fresh(c): d = ""   # 已存好且公告沒換 → 不開頁，直接沿用 data/detail.json
    else:
        d = get_text(f"/Sales/{MOBILE}/{c['NO']}"); DETAIL_STAT["開頁"] += 1; time.sleep(1.5)
    g = lambda pat: (re.search(pat, d) or [None, ""])[1]
    total = g(r"總坪數\s*([\d.]+)"); age = g(r"屋齡\s*(\d+)"); fl = g(r"(\d+/\d+)樓"); dj = g(r"●點交情形→([^●\n]+)●")
    bid = c.get("BID_DATE") or ""
    bm = re.match(r"(\d{4})/(\d+)/(\d+)", bid)
    roc = f"{int(bm[1]) - 1911}/{int(bm[2])}/{int(bm[3])}" if bm else ""
    ann = c.get("houseSize")
    info = {"拍次": str(rnd) if rnd else "", "開標日期": roc, "銷售狀態": c.get("NOW_STATUS") or "待標", "法拍件": "是"}
    if total: info["總登記坪數"] = total + "坪"
    if ann: info["建坪（不含公設）"] = f"{ann}坪"
    if total and pv: info["每坪單價"] = f"{pv / float(total):.2f}萬/坪"
    if age: info["屋齡"] = age + "年"
    if fl: info["所在樓層"] = fl
    if c.get("COMMUMITY"): info["社區/大樓"] = c["COMMUMITY"]
    if "號" in full: info["完整地址"] = full
    cn = g(r"案號：\s*([^\s｜|]+)") or g(r"([一-鿿]{1,3}地院\s*\d{2,3}\s*[一-鿿]{1,4}\d{3,7}(?:（[^）]{1,6}）)?)")   # 11/19：文案沒寫「案號：」時，抓「新北地院 114司執148052（金股）」這種寫法
    if cn: info["案號"] = cn
    for k, pat in (("主建物", r"主建物\s*([\d.]+)\s*坪"), ("附屬建物", r"附屬\s*([\d.]+)\s*坪"), ("公共設施", r"公設\s*([\d.]+)\s*坪"), ("土地登記總坪數", r"土地：合計約\s*([\d.]+)\s*坪")):
        v = g(pat)
        if v: info[k] = v
    fn = full_notes(d)
    if fn: info["筆錄"] = fn
    elif dj: info["筆錄"] = f"●點交情形→{dj}●"
    detail_fill(f"HW{c['NO']}", info, detail_key(c) if d else (DETAIL.get(f"HW{c['NO']}") or {}).get("_key", ""))
    total = (info.get("總登記坪數") or "").removesuffix("坪")
    if total and pv and "每坪單價" not in info: info["每坪單價"] = f"{pv / float(total):.2f}萬/坪"
    if bm and rnd and pv: info["拍賣紀錄"] = f"第{rnd}拍 {int(bm[2]):02d}/{int(bm[3]):02d} 底標價：{pv:g} 萬"
    typ = c.get("TYPE") or ""
    return {"來源": "透明房訊", "編號": f"HW{c['NO']}", "地址": t, "區域": f"{city}{dist}-{typ}", "類型": typ,
            # 2026-11-19：卡片坪數用總坪數（含公設，與買屋網、HO 一致）；houseSize 是建坪（主建＋附屬，不含公設），另存「建坪」
            "格局坪數": f"{total}坪" if total else (f"建坪{ann}坪" if ann else ""), "原價": "", "價格": f"售{ptxt}" if ptxt else "",
            "狀態": "待標中", "圖片": "", "資訊": info}

def sync(items):
    """回傳 (合併後 items, photos 更新數, 新增物件數)；失敗時原樣回傳"""
    cs = fetch_all()
    if not cs: return items, 0, 0
    P = {}
    try: P = json.load(open("site/photos.json", encoding="utf-8"))
    except Exception: pass
    pics = added = extra = replaced = 0
    try: seen = json.load(open("data/seen.json", encoding="utf-8"))
    except Exception: seen = {}
    cur = {x["編號"] for x in items}
    ho_seen = [(k, v) for k, v in seen.items() if k.startswith("HH") and k not in cur and "gone" not in v and not v.get("twin")]
    ho_ghost = {(v.get("area", "")[:2], addr_tail(v.get("full"))): k for k, v in ho_seen if len(addr_tail(v.get("full"))) >= 5}
    for c in cs:
        if re.search(r"撤", c.get("NOW_STATUS") or ""): continue   # 撤件/撤回不上；停拍仍上架
        s = norm(c.get("ADDRESS"))
        cty = norm(c.get("FULL_ADDRESS"))[:2].replace("臺", "台")   # 同路名不同縣市不可視為同一件
        ft = addr_tail(c.get("FULL_ADDRESS"))
        hit = next((x for x in items if x["區域"][:2].replace("臺", "台") == cty and ((len(s) >= 5 and s in norm(x["地址"])) or (len(ft) >= 5 and ft == addr_tail((x.get("資訊") or {}).get("完整地址"))))), None) if s or ft else None
        if hit:
            key = hit["編號"][2:]
            if hit["編號"].startswith("HH"):   # 2026-11-19：舊 House-Info 快照有透明房訊同一件 → 整筆換成透明房訊資料，舊網址轉過去
                x = to_item(c); x["inherit"] = hit["編號"]; items[items.index(hit)] = x; key = x["編號"][2:]; replaced += 1; time.sleep(0.3)
                pl = photo_list(c)
                if pl and P.get(key) != pl: P[key] = pl; pics += 1
                continue
            if hit["編號"].startswith("HW") and not detail_fresh(c):   # 自家物件：公告換了才重抓完整筆錄
                try:
                    fn = full_notes(get_text(f"/Sales/{MOBILE}/{c['NO']}"))
                    if fn: hit["資訊"]["筆錄"] = fn
                except Exception: pass
                time.sleep(1.5)
        else:
            x = to_item(c); items.append(x); key = x["編號"][2:]; extra += 1; time.sleep(0.3)
            ho = ho_ghost.get((cty, ft)) or next((k for k, v in ho_seen if len(s) >= 5 and v.get("area", "")[:2] == cty and s in norm(v.get("addr"))), None)
            if ho: x["inherit"] = ho   # HO 停用後由透明房訊接手的同一物件：舊網址轉過來、沿用上架日
        pl = photo_list(c)
        if pl and P.get(key) != pl: P[key] = pl; pics += 1
    # 其他尚無照片的物件：到透明房訊用地址對應，只取法院現場照
    try:
        mk = {}
        for city in CITIES: market(city, out=mk)
        mk = [c for c in mk.values() if c.get("MOBILE") != MOBILE and not re.search(r"撤", c.get("NOW_STATUS") or "")]
        for x in items:
            key = x["編號"][2:]
            if P.get(key): continue
            a = norm(x["地址"]); d = x["區域"][2:5]
            for c in mk:
                s = norm(c.get("ADDRESS"))
                if len(s) >= 5 and s in a and district(c.get("FULL_ADDRESS")) in d + "區":
                    pl = court_photos(c)
                    if pl: P[key] = pl; pics += 1
                    break
        print("透明房訊全部物件", len(mk), "筆")
    except Exception as e:
        print("他人物件照片同步失敗（略過）：", e)
    json.dump(P, open("site/photos.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    try: detail_save()
    except Exception as e: print("detail.json 存檔失敗（略過）：", e)
    return items, pics, extra


# ---- 法院現場照（依案號直接找檔案；不需登入）----
import os, concurrent.futures as cf
_MONTHS = [f"{y}{m:02d}" for y in (113, 114, 115) for m in range(1, 13)]

def _ok(path):
    u = BASE + "/" + urllib.parse.quote(path, safe="/")
    for i in range(3):   # 連線錯誤重試；404 代表真的沒有
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, method="HEAD", headers={"User-Agent": "Mozilla/5.0"}), timeout=20)
            return r.status == 200 and r.headers.get("content-type", "").startswith("image")
        except urllib.error.HTTPError as e:
            if e.code in (404, 403): return False
            time.sleep(1 + i)
        except Exception:
            time.sleep(1 + i)
    return False

def _all(prefix, c):
    out = []
    for n in range(1, 13):
        p = f"{prefix}/{c}-{n}.jpg"
        if _ok(p): out.append(p)
        elif n > 2 and not out: break
    return out

_ALL_COURTS = ["tpd", "sld", "pcd", "tyd", "kld", "scd", "tcd", "tnd", "ksd"]
_PLAN_CODES = ["PCD", "TPD", "SLD", "TYD", "KLD", "SCD", "TCD", "TND", "KSD"]

def _probe(x):
    c = x["資訊"]["案號"]
    o = _all("wwwphoto/street/judbp/wkw", c)
    if o: return x["編號"], o
    a = x["區域"][:2]
    first = (["kld"] if c.endswith("金") else []) + (["tyd"] if a == "桃園" else ["tpd", "sld"] if a == "台北" else ["pcd", "sld", "tpd"])
    for ct in first:
        for m in _MONTHS:
            if _ok(f"wwwphoto/street/{ct}/{m}/{c}-1.jpg"):
                return x["編號"], _all(f"wwwphoto/street/{ct}/{m}", c)
    # 沒有現場照時，改用透明房訊製作的平面圖（固定路徑）
    for pc in _PLAN_CODES:
        p = f"wwwphoto/sc4/0/{pc}/{c}_s.gif"
        if _ok(p): return x["編號"], [p]
    return x["編號"], []

def court_sync(items):
    """沒有照片的物件，用案號到透明房訊找法院現場照；找不到的 7 天後再試"""
    P = json.load(open("site/photos.json", encoding="utf-8"))
    mp = "data/photo_miss.json"
    miss = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
    today = datetime.date.today()
    todo = []
    for x in items:
        if P.get(x["編號"][2:]) or not x["資訊"].get("案號"): continue
        t = miss.get(x["編號"])
        if t and (today - datetime.date.fromisoformat(t)).days < 7: continue
        todo.append(x)
    n = 0
    with cf.ThreadPoolExecutor(48) as ex:
        for k, o in ex.map(_probe, todo):
            if o: P[k[2:]] = o; miss.pop(k, None); n += 1
            else: miss[k] = today.isoformat()
    ids = {x["編號"] for x in items}
    miss = {k: v for k, v in miss.items() if k in ids}
    json.dump(P, open("site/photos.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(miss, open(mp, "w", encoding="utf-8"), ensure_ascii=False)
    return n
