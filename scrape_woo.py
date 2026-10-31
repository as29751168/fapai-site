"""每日同步：透明房訊(104woo.com.tw)林小姐 Anna 的物件 -> 照片 site/photos.json，並補上 104法拍網列表沒有的物件"""
import json, re, time, datetime, urllib.request, urllib.parse, html as H

MOBILE = "0986678928"
BASE = "https://www.104woo.com.tw"
CITIES = ["台北市", "新北市", "桃園市"]
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

def get_text(path):
    try:
        h = urllib.request.urlopen(urllib.request.Request(BASE + path, headers={"User-Agent": UA["User-Agent"]}), timeout=40).read().decode("utf-8", "ignore")
    except Exception:
        return ""
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", h, flags=re.S)
    return re.sub(r"[ \t\r　]+", " ", H.unescape(re.sub(r"<[^>]+>", "\n", h)))

def norm(s): return re.sub(r"[\s　]|<[^>]*>", "", s or "")

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

def market(city, lo=0, hi=200000, out=None):
    """列出透明房訊某縣市全部物件：單次最多回 30 筆，滿了就把價格區間對半切"""
    out = {} if out is None else out
    items = query(city, lo, hi)
    for it in items: out[it["NO"]] = it
    if len(items) >= 30 and hi - lo > 1:
        mid = (lo + hi) // 2
        market(city, lo, mid, out); market(city, mid, hi, out)
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
    for c in CITIES:
        for it in post_items(c):
            if it.get("MOBILE") == MOBILE: allc[it["NO"]] = it
    return list(allc.values())

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
    d = get_text(f"/Sales/{MOBILE}/{c['NO']}")
    g = lambda pat: (re.search(pat, d) or [None, ""])[1]
    total = g(r"總坪數\s*([\d.]+)"); age = g(r"屋齡\s*(\d+)"); fl = g(r"(\d+/\d+)樓"); dj = g(r"●點交情形→([^●\n]+)●")
    bid = c.get("BID_DATE") or ""
    bm = re.match(r"(\d{4})/(\d+)/(\d+)", bid)
    roc = f"{int(bm[1]) - 1911}/{int(bm[2])}/{int(bm[3])}" if bm else ""
    ann = c.get("houseSize")
    info = {"拍次": str(rnd) if rnd else "", "開標日期": roc, "銷售狀態": c.get("NOW_STATUS") or "待標", "法拍件": "是"}
    if total: info["總登記坪數"] = total + "坪"
    if total and pv: info["每坪單價"] = f"{pv / float(total):.2f}萬/坪"
    if age: info["屋齡"] = age + "年"
    if fl: info["所在樓層"] = fl
    if c.get("COMMUMITY"): info["社區/大樓"] = c["COMMUMITY"]
    if dj: info["筆錄"] = f"●點交情形→{dj}●"
    if bm and rnd and pv: info["拍賣紀錄"] = f"第{rnd}拍 {int(bm[2]):02d}/{int(bm[3]):02d} 底標價：{pv:g} 萬"
    typ = c.get("TYPE") or ""
    return {"來源": "透明房訊", "編號": f"HW{c['NO']}", "地址": t, "區域": f"{city}{dist}-{typ}", "類型": typ,
            "格局坪數": f"{ann}坪" if ann else "", "原價": "", "價格": f"售{ptxt}" if ptxt else "",
            "狀態": "待標中", "圖片": "", "資訊": info}

def sync(items):
    """回傳 (合併後 items, photos 更新數, 新增物件數)；失敗時原樣回傳"""
    cs = fetch_all()
    if not cs: return items, 0, 0
    P = {}
    try: P = json.load(open("site/photos.json", encoding="utf-8"))
    except Exception: pass
    pics = added = extra = 0
    for c in cs:
        if re.search(r"撤", c.get("NOW_STATUS") or ""): continue   # 撤件/撤回不上；停拍仍上架
        s = norm(c.get("ADDRESS"))
        hit = next((x for x in items if len(s) >= 5 and s in norm(x["地址"])), None) if s else None
        if hit: key = hit["編號"][2:]
        else:
            x = to_item(c); items.append(x); key = x["編號"][2:]; extra += 1; time.sleep(0.3)
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
    return items, pics, extra


# ---- 法院現場照（依案號直接找檔案；不需登入）----
import os, concurrent.futures as cf
_MONTHS = [f"{y}{m:02d}" for y in (114, 115) for m in range(1, 13)]

def _ok(path):
    u = BASE + "/" + urllib.parse.quote(path, safe="/")
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, method="HEAD", headers={"User-Agent": "Mozilla/5.0"}), timeout=15)
        return r.status == 200 and r.headers.get("content-type", "").startswith("image")
    except Exception:
        return False

def _all(prefix, c):
    out = []
    for n in range(1, 13):
        p = f"{prefix}/{c}-{n}.jpg"
        if _ok(p): out.append(p)
        elif n > 2 and not out: break
    return out

def _probe(x):
    c = x["資訊"]["案號"]
    o = _all("wwwphoto/street/judbp/wkw", c)
    if o: return x["編號"], o
    a = x["區域"][:2]
    for ct in (["tyd"] if a == "桃園" else ["tpd", "sld"] if a == "台北" else ["pcd", "sld", "tpd"]):
        for m in _MONTHS:
            if _ok(f"wwwphoto/street/{ct}/{m}/{c}-1.jpg"):
                return x["編號"], _all(f"wwwphoto/street/{ct}/{m}", c)
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
