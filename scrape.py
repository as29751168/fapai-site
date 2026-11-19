"""每日抓取：104法拍網物件列表 -> site/data.json"""
import json, os, re, shutil, time, datetime, urllib.request, html as H
from urllib.parse import urljoin, unquote

UA = {"User-Agent": "Mozilla/5.0 (fapai-site daily sync)"}
# 2026-11-19：已刪除讀 104法拍屋.tw（House-Info 前台）的程式；物件資料只用透明房訊（CLAUDE.md、廠商 11/15 要求）

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
        v.update({"addr": x["地址"], "area": x["區域"], "ptxt": x["價格"], "rd": inf.get("拍次", ""), "date": inf.get("開標日期", ""), "type": x.get("類型", ""), "full": inf.get("完整地址", ""),
                  "comm": re.sub(r"[（(].*$", "", inf.get("社區/大樓") or "").strip()})
        if x.get("twin"): v["twin"] = x.pop("twin")
    os.makedirs("data", exist_ok=True)
    json.dump(seen, open(p, "w", encoding="utf-8"), ensure_ascii=False)

def ho_items():
    """House-Info（104法拍屋.tw）物件；預設不讀 HO（廠商要求），網站也不能因此變空：
    - 預設、HO_OFF=1 或 data/ho_status.json 的 off=true：不讀 HO，沿用最後一次抓好的 HO 物件快照（見下方說明）
    - （11/19 起讀取程式已刪除，以下 HO_ON 說明作廢）
    - 抓取失敗或件數不到上次的一半：沿用上次的 HO 物件（價格拍次仍由公開資料校正），連續 3 次（每天跑 2 次，約一天半）都這樣就自動停用 HO；要恢復就刪掉 data/ho_status.json"""
    p = "data/ho_status.json"
    st = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    # 2026-11-15 House-Info 廠商要求停止程式讀取它的網站（伺服器效能）；Anna 也確認資料以透明房訊為準。
    # 預設不抓 HO；除非廠商同意且設定 HO_ON=1 才會再讀。
    try: prev = [x for x in json.load(open("site/data.json", encoding="utf-8"))["104"] if x["編號"].startswith("HH")]
    except Exception: prev = []
    if True:   # 2026-11-19：一律不讀 HO（讀取程式已刪除），只沿用舊快照；有透明房訊同一件的由 scrape_woo 換掉
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
    try:  # 2026-11-19：停用 toro591（CLAUDE.md 禁用）。校正與開標結果都只用透明房訊公開的每日開標清單
        import scrape_public
        rows = scrape_public.collect()
        data["104"], st = scrape_public.apply(data["104"], rows)
        print("公開資料校正：", {k: v for k, v in st.items() if k != "ids"})
        today = datetime.date.today(); res = []
        for r in rows:
            if r["date"] > today or r["date"] < today - datetime.timedelta(days=8) or not r["status"] or r["status"] == "待標": continue
            stt = {"得標": "拍定", "承受": "承受"}.get(r["status"], r["status"])
            res.append({"date": f"{r['date'].year - 1911}/{r['date'].month:02d}/{r['date'].day:02d}", "status": stt, "round": r["round"],
                        "deliver": r["deliver"], "type": r["type"], "addr": r["addr"], "base": r["base"], "win": r["win"], "land": r["type"] == "土地"})
        res = [x for x in res if not x["land"]]
        if len(rows) >= 2000:
            json.dump({"更新時間": data["更新時間"], "來源": "透明房訊公開開標清單", "items": res}, open("data/results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            if os.path.exists("data/results_tyd.json"): os.remove("data/results_tyd.json")   # 已併入 results.json
            print("開標結果（透明房訊）", len(res), "筆")
    except Exception as e:
        print("公開資料校正失敗（略過）：", e)
    # 2026-11-19：11/15 以前從 House-Info 抓的 HH 舊資料，逐欄換成透明房訊資料；透明房訊沒有的欄位留白，不沿用 House-Info
    KEEP = {"拍次", "開標日期", "銷售狀態", "法拍件", "完整地址"}   # 這幾欄由透明房訊公開開標清單每天校正
    hh_fix = 0
    for x in data["104"]:
        tw = x.pop("_tw", None)
        if not x["編號"].startswith("HH"): continue
        inf = x.setdefault("資訊", {})
        if inf.get("_透明房訊") and not tw: continue   # 之前已換過、這次沒比對到：保持留白
        new_inf = {k: v for k, v in inf.items() if k in KEEP}
        if tw:
            new_inf["案號"] = f'{tw["court"]} {tw["case"]}'.strip()
            if tw.get("deliver"): new_inf["筆錄"] = f'●點交情形→{tw["deliver"]}●（依透明房訊開標清單，實際以法院公告為準）'
        new_inf["_透明房訊"] = "1"
        x["資訊"] = new_inf; x["格局坪數"] = ""
        if new_inf.get("完整地址"): x["地址"] = new_inf["完整地址"]   # 拿掉 House-Info 案名裡的【社區名】等字
        hh_fix += 1
    print("HH 舊資料換成透明房訊欄位：", hh_fix, "件")
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
