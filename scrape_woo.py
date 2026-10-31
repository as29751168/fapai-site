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
    json.dump(P, open("site/photos.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    return items, pics, extra
