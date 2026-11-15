"""每日抓取：104法拍網物件列表 -> site/data.json"""
import json, os, re, shutil, time, datetime, urllib.request, html as H
from urllib.parse import urljoin, unquote

UA = {"User-Agent": "Mozilla/5.0 (fapai-site daily sync)"}
S104 = "http://www.xn--104-yz0f900ahup.tw/HouseSale/"

def get(url):
    for i in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "ignore")
        except Exception as e:
            err = e; time.sleep(3)
    raise err

def txt(s): return H.unescape(re.sub(r"<[^>]+>", "", s)).strip()

MASKED_NAME = re.compile(r"[一-鿿](?:[O○〇＊*ＯΟО]{2}|[O○〇＊*ＯΟО](?![A-Za-z])[一-鿿]?|０{2}(?![０-９]))")   # 法院遮罩的姓名，如 陳O恩、蔡OO、梁００

def mask_names(items):
    """筆錄公開前移除遮罩姓名（物件頁與 data.json 共用）"""
    for x in items:
        inf = x.get("資訊") or {}
        if inf.get("筆錄"): inf["筆錄"] = MASKED_NAME.sub("（姓名已隱去）", inf["筆錄"])

def clear_images():
    """不使用 104法拍屋.tw 的照片：每次執行都清掉網站內舊照片"""
    shutil.rmtree("site/img", ignore_errors=True)

def detail(hid):
    """讀取物件的結構化資料（案號、拍次、開標日期、坪數、屋齡、樓層…），不取文字說明與聯絡人"""
    try:
        h = get(f"http://www.xn--104-yz0f900ahup.tw/{hid}.htm")
    except Exception:
        return {}
    info = {}
    for k, v in re.findall(r'<li id="cphCenter_li(?:CaseNum|MgmtPingSu|UnitPrice)"><span>(.*?)：</span>(.*?)</li>', h, flags=re.S):
        info[txt(k)] = txt(v)
    for k, v in re.findall(r'detail-house-key"><h4>(.*?)</h4></div>\s*<span>：</span>\s*<div[^>]*class="detail-house-value"[^>]*>(.*?)</div>', h, flags=re.S):
        k, v = txt(k), txt(v)
        if k and v and k != "瀏覽人次": info[k] = v
    full = "".join(txt(re.search(rf'"{k}":\s*"([^"]*)"', h)[1]) for k in ("addressRegion", "addressLocality", "streetAddress") if re.search(rf'"{k}":\s*"([^"]*)"', h))
    if "號" in full or "地號" in full: info["完整地址"] = full
    m = re.search(r"【法院筆錄】(.*?)(?=<font|<iframe|$)", h, flags=re.S)
    if m:
        lines = [txt(x) for x in re.split(r"<br\s*/?>", m.group(1))]
        lines = [x for x in lines if x]
        sched = [x for x in lines if re.match(r"第.{1,2}拍", x)]
        notes = [x for x in lines if x not in sched]
        if notes: info["筆錄"] = "\n".join(notes)
        if sched: info["拍賣紀錄"] = "\n".join(sched)
    time.sleep(0.3)
    return info

def s104(max_pages=40):
    out, seen = [], set()
    for p in range(1, max_pages + 1):
        h = get(f"{S104}?p={p}")
        cards = h.split('class="cssObject"')[1:]
        new = 0
        for c in cards:
            m = re.search(r'sku" content="(HH\d+)"', c)
            if not m or m.group(1) in seen: continue
            hid = m.group(1); seen.add(hid); new += 1
            g = lambda pat: (re.search(pat, c, flags=re.S) or [None, ""])[1]
            cells = [txt(x) for x in re.findall(r'<div class="cssCaseItem">([^<]*)</div>', c)]
            prices = [txt(x) for x in re.findall(r'<div class="css(?:OriginalPrice|ReductionMoney|NowMoney)">(.*?)</div>', c)]
            out.append({"來源": "104法拍網", "編號": hid, "地址": H.unescape(g(r'itemprop="name" content="([^"]*)"')),
                        "區域": H.unescape(g(r'itemprop="description" content="([^"]*)"')),
                        "類型": cells[0] if cells else "", "格局坪數": cells[1] if len(cells) > 1 else "",
                        "原價": prices[0] if len(prices) > 1 else "", "價格": prices[-1] if prices else "",
                        "狀態": g(r"alt='([^']*)' /></div><div class=\"cssListImg"), "圖片": "",
                        "資訊": detail(hid)})
        if not new: break
        time.sleep(1)
    return out

def track(items):
    """記錄每件物件首次出現日與價格／拍次變動（data/seen.json），用於「本週新增」「降價降拍」"""
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")
    p = "data/seen.json"
    first_run = not os.path.exists(p)
    seen = {} if first_run else json.load(open(p, encoding="utf-8"))
    def num(t):
        m = re.search(r"([\d.,]+)\s*(億|萬)?", t or "")
        if not m: return 0
        return int(float(m.group(1).replace(",", "")) * (100000000 if m.group(2) == "億" else 10000 if m.group(2) == "萬" else 1))
    twin_of = {v["twin"]: v for v in seen.values() if v.get("twin")}   # 透明房訊編號 -> 同一物件的 House-Info 紀錄
    for x in items:
        i, pr = x["編號"], num(x["價格"])
        r = (x.get("資訊") or {}).get("拍次", "")
        rd = int(r) if r.isdigit() else 0
        s0 = seen.get(i)
        if s0 is None and x.get("inherit") in seen and not seen[x["inherit"]].get("twin"):
            seen[x["inherit"]]["twin"] = i; twin_of[i] = seen[x["inherit"]]
        x.pop("inherit", None)
        if s0 is None and i in twin_of:   # HO 停用後改由透明房訊提供的同一物件：沿用原上架日，不算本週新增
            t = twin_of[i]
            s0 = seen[i] = {"first": t.get("first", ""), "price": t.get("price", pr), "round": t.get("round", rd)}
            for k in ("old", "changed"):
                if t.get(k): s0[k] = t[k]
        if s0 is None:
            s0 = seen[i] = {"first": "" if first_run else today, "price": pr, "round": rd}
        else:
            ch = False
            if pr and s0["price"] and pr < s0["price"]:
                s0["old"], s0["price"], ch = s0["price"], pr, True
            if rd > s0.get("round", 0):
                s0["round"], ch = rd, True
            if ch: s0["changed"] = today
        x["新增日"], x["異動日"], x["降價前"] = s0["first"], s0.get("changed", ""), s0.get("old", 0)
    # 下架偵測：今天沒出現的物件記下 gone 日期（拍定／停拍／撤回都會從列表消失）；抓取量異常偏少時不判定，避免誤判
    cur = {x["編號"] for x in items}
    srcs = {k[:2] for k in cur}   # 整個來源停用（例如 HO 不續約）時，該來源不列入比例計算，照常判定下架
    active = [k for k, v in seen.items() if "gone" not in v and k[:2] in srcs]
    if not first_run and active and len(cur) >= 0.8 * len(active):
        for k, v in seen.items():
            if k not in cur and "gone" not in v: v["gone"] = today
    for x in items:
        v = seen[x["編號"]]; v.pop("gone", None)
        inf = x.get("資訊") or {}
        v.update({"addr": x["地址"], "area": x["區域"], "ptxt": x["價格"], "rd": inf.get("拍次", ""), "date": inf.get("開標日期", ""), "type": x.get("類型", ""), "full": inf.get("完整地址", "")})
        if x.get("twin"): v["twin"] = x.pop("twin")
    os.makedirs("data", exist_ok=True)
    json.dump(seen, open(p, "w", encoding="utf-8"), ensure_ascii=False)

def ho_items():
    """House-Info（104法拍屋.tw）物件；預設不讀 HO（廠商要求），網站也不能因此變空：
    - 預設、HO_OFF=1 或 data/ho_status.json 的 off=true：不讀 HO，沿用最後一次抓好的 HO 物件快照（見下方說明）
    - 只有設定 HO_ON=1 才會讀 HO，且：
    - 抓取失敗或件數不到上次的一半：沿用上次的 HO 物件（價格拍次仍由公開資料校正），連續 3 次（每天跑 2 次，約一天半）都這樣就自動停用 HO；要恢復就刪掉 data/ho_status.json"""
    p = "data/ho_status.json"
    st = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    # 2026-11-15 House-Info 廠商要求停止程式讀取它的網站（伺服器效能）；Anna 也確認資料以透明房訊為準。
    # 預設不抓 HO；除非廠商同意且設定 HO_ON=1 才會再讀。
    try: prev = [x for x in json.load(open("site/data.json", encoding="utf-8"))["104"] if x["編號"].startswith("HH")]
    except Exception: prev = []
    if os.environ.get("HO_ON") != "1" or os.environ.get("HO_OFF") == "1" or st.get("off"):
        # 不讀 HO：沿用最後一次抓好的 HO 物件（快照）。拍次、日期、底價、狀態之後照常由透明房訊公開開標清單每天校正；
        # 拍定／撤回會被校正程式拿掉；「待確認」（開標日過了、公開清單查無新場次）照下架規則（流標留著、停拍留三個月）
        # 留到開標日後 90 天才拿掉，因為沒有其他來源能確認。
        def old(x):
            m = re.fullmatch(r"(\d+)/(\d+)/(\d+)", (x.get("資訊") or {}).get("開標日期", ""))
            if not m: return False
            try: d = datetime.date(int(m[1]) + 1911, int(m[2]), int(m[3]))
            except ValueError: return False
            return (datetime.date.today() - d).days > 90
        keep = [x for x in prev if not ((x.get("資訊") or {}).get("銷售狀態") == "待確認" and old(x))]
        print("House-Info 不讀取（廠商要求），沿用最後一次的 HO 物件", len(keep), "件（拿掉開標日超過 90 天的待確認", len(prev) - len(keep), "件）")
        return keep
    try: cur = s104()
    except Exception as e: print("House-Info 抓取失敗：", e); cur = []
    if prev and len(cur) < 0.5 * len(prev):
        st["fail"] = st.get("fail", 0) + 1
        if st["fail"] >= 3:
            st["off"] = True; out = []
            print("House-Info 連續", st["fail"], "次抓不到，自動停用，改用透明房訊")
        else:
            out = prev; print("House-Info 只抓到", len(cur), "件，沿用上次", len(prev), "件（第", st["fail"], "次）")
    else:
        st["fail"] = 0; out = cur
    os.makedirs("data", exist_ok=True)
    json.dump(st, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    return out

if __name__ == "__main__":
    data = {"更新時間": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M"),
            "104": ho_items()}
    clear_images()
    try:
        import scrape_woo
        data["104"], np, ne = scrape_woo.sync(data["104"])
        print("透明房訊：照片更新", np, "件；新增物件", ne, "件")
        print("法院現場照新增", scrape_woo.court_sync(data["104"]), "件")
    except Exception as e:
        print("透明房訊同步失敗（略過）：", e)
    try:  # 每週拍定・停拍・撤回：法院開標結果文字資料（toro591，不取照片與連結）
        import scrape_results
        rs = scrape_results.fetch()
        if rs:
            json.dump({"更新時間": data["更新時間"], "items": rs}, open("data/results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("開標結果", len(rs), "筆")
    except Exception as e:
        print("開標結果同步失敗（略過）：", e)
    try:  # 桃園開標結果：透明房訊公開頁（不需登入）
        import scrape_results
        ty = [x for x in scrape_results.fetch_court() if x["status"] != "待標" and not x["land"]]
        if ty:
            json.dump({"更新時間": data["更新時間"], "items": ty}, open("data/results_tyd.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("桃園開標結果", len(ty), "筆")
    except Exception as e:
        print("桃園開標結果同步失敗（略過）：", e)
    try:  # 用透明房訊公開的每日開標清單校正拍次、日期、底價與狀態
        import scrape_public
        data["104"], st = scrape_public.apply(data["104"])
        print("公開資料校正：", {k: v for k, v in st.items() if k != "ids"})
    except Exception as e:
        print("公開資料校正失敗（略過）：", e)
    try:  # 人工更正（data/overrides.json）：{編號: {欄位: 值}}，避免每日抓取又被蓋回
        ov = json.load(open("data/overrides.json", encoding="utf-8"))
        for x in data["104"]:
            x.update(ov.get(x["編號"], {}))
    except Exception as e:
        print("overrides 略過：", e)
    mask_names(data["104"])
    track(data["104"])
    json.dump(data, open("site/data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(data["104"]), "筆 104")
