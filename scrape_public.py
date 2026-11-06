"""用透明房訊公開的每日開標清單（不需登入）校正 104法拍網物件資料：拍次、開標日期、底價、狀態。
比對依據：案號尾碼（如「宇156447」）＋區，其次地址；每日清單範圍：過去 8 天～未來 45 天。"""
import re, json, html, time, datetime, urllib.parse, concurrent.futures as cf, requests

OLD = "http://www.104woo.com.tw/tom1/house/lin2_k_index00a.asp"
COURTS = ["台北市", "新北市", "基隆市", "高雄市", "台北法院", "士林法院", "新北法院", "桃園法院", "基隆法院", "新竹法院", "苗栗法院", "台中法院", "宜蘭法院", "台南法院", "高雄法院", "橋頭法院", "屏東法院"]
NUMS = "一二三四五六七八九十"
CLOSED = re.compile(r"停拍|撤|得標|拍定|承受|流標")   # 這些狀態的場次不會開標

def _clean(t):
    t = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", "", t)
    t = html.unescape(re.sub(r"<[^>]+>", "|", t))
    return re.sub(r"\s*\|\s*(\|\s*)*", "|", t)

def _rnd(s): return re.sub(r"^(.)拍", lambda m: (str(NUMS.index(m[1]) + 1) + "拍") if m[1] in NUMS else m[0], s)

def day_rows(court, d, sess):
    q = lambda x: urllib.parse.quote(x, encoding="big5")
    u = f"{OLD}?endDay0={d:%Y/%m/%d}&acity={q(court)}&sel_ect0={q('不限')}&asblo=all&achange1=all&achange2=all&achange3=all&achange4=all&achange5=all&achange6=all&achange7=0"
    for i in range(3):
        try: t = _clean(sess.get(u, timeout=40).content.decode("big5", "ignore")); break
        except Exception: time.sleep(1 + i); t = ""
    rows = []
    for chunk in re.split(r"\|\d+\.\|", t)[1:]:
        p = [x.strip() for x in chunk.split("|") if x.strip()]
        if len(p) < 8 or not re.match(r"\d+/\d+", p[1]): continue
        get = lambda pre: next((x.split("：", 1)[1] for x in p if x.startswith(pre + "：")), "")
        rows.append({"court": court, "date": d, "name": p[0], "round": _rnd(p[2]), "status": p[3], "base": get("底價"), "win": get("標價"),
                     "deliver": next((x for x in p if x in ("點交", "不點交", "有點交", "部份點交", "依現況點交", "詳如備註")), ""), "addr": p[-2], "type": p[-1]})
    return rows

def collect(back=8, ahead=45, workers=4):
    today = datetime.date.today(); days = [today + datetime.timedelta(days=k) for k in range(-back, ahead + 1)]
    jobs = [(c, d) for c in COURTS for d in days if d.weekday() < 5]
    out = []
    def run(j):
        s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (fapai-site daily sync)"
        time.sleep(0.15); return day_rows(j[0], j[1], s)
    with cf.ThreadPoolExecutor(workers) as ex:
        for r in ex.map(run, jobs): out += r
    seen, uniq = set(), []
    for r in out:
        k = (r["date"], r["name"], r["addr"], r["round"], r["status"])
        if k not in seen: seen.add(k); uniq.append(r)
    return uniq

def _suffix(case): m = re.match(r"\d+(.+)", case or ""); return m[1] if m else ""
def _district(area): m = re.search(r"[區鄉鎮市]", area[2:]) ; return area[2:2 + (m.start() + 1 if m else 0)] if len(area) > 2 else ""
def _key(title):
    m = re.findall(r"([一-鿿]+(?:路|街|大道)[^號]*?號)", title or "")
    return m[-1] if m else ""

def apply(items, rows=None, today=None):
    """校正 items；回傳 (items, 統計)。拍定／承受／撤回的物件移除；停拍保留並標註；流標且無新日期者標註待公告。"""
    today = today or datetime.date.today()
    rows = rows if rows is not None else collect()
    if len(rows) < 2000:   # 來源異常（抓到太少）：不動資料，避免誤判
        return items, {"skipped": len(rows)}
    by_suf, rows_by_dist = {}, {}
    for r in rows:
        by_suf.setdefault(r["name"].split("_")[-1], []).append(r)
        rows_by_dist.setdefault(r["addr"][:3], []).append(r)
    def core(addr):   # 去掉縣市／區，取到「號」為止，例如「三民路95巷9號」
        m = re.match(r"^(?:.{2,3}[市縣])?(?:.{1,3}?[區鄉鎮市])?(.+?(?:地號|號))", addr)
        return m[1] if m else ""
    stat = {"updated": 0, "removed": 0, "stopped": 0, "flow": 0, "unmatched": 0}
    kept = []
    for x in items:
        inf = x.setdefault("資訊", {})
        dist = _district(x["區域"]); suf = _suffix(inf.get("案號", ""))
        title = re.sub(r"[\s　]", "", x["地址"])
        cands = []
        if suf and not suf.startswith("國"):
            cs = by_suf.get(suf, [])
            cands = [r for r in cs if (not dist) or dist in r["addr"]] or ([r for r in cs] if len({r["addr"] for r in cs}) == 1 else [])
        if not cands and dist:
            cands = [r for r in rows_by_dist.get(dist[:3], []) if r["addr"].startswith(dist) and (c := core(r["addr"])) and len(c) >= 5 and c in title]
        if not cands:
            stat["unmatched"] += 1; stat.setdefault("ids", []).append(x["編號"])
            m = re.match(r"(\d+)/(\d+)/(\d+)", inf.get("開標日期", ""))
            try: dd = datetime.date(int(m[1]) + 1911, int(m[2]), int(m[3])) if m else None
            except ValueError: dd = None
            if dd and (today - dd).days > 21:   # 開標日期已過很久、公開清單查無新場次：標註待確認
                x["狀態"] = "開標日期已過・待確認"; inf["銷售狀態"] = "待確認"; stat["stale"] = stat.get("stale", 0) + 1
            kept.append(x); continue
        cands.sort(key=lambda r: r["date"]); last = cands[-1]
        st = last["status"]; fut = [r for r in cands if r["date"] >= today and not CLOSED.search(r["status"])]
        if fut:   # 還有仍有效的未開標場次：以最近一場為準；已停拍或撤回的未來場次不算
            r = fut[0]
            inf["拍次"] = re.sub(r"拍", "", r["round"]); inf["開標日期"] = f"{r['date'].year - 1911}/{r['date'].month}/{r['date'].day}"
            if r["base"]:
                x["價格"] = "售" + r["base"]; inf["銷售狀態"] = "待標中"
            x["狀態"] = "待標中"; stat["updated"] += 1; kept.append(x); continue
        if st in ("得標", "拍定", "承受") or st.startswith("撤"):
            stat["removed"] += 1; continue          # 已拍定或撤回：不再顯示
        if st.startswith("停拍"):
            x["狀態"] = "停拍（可能再拍）"; inf["銷售狀態"] = "停拍"; stat["stopped"] += 1; kept.append(x); continue
        if st == "流標":
            x["狀態"] = "流標・待下一拍公告"; inf["銷售狀態"] = "流標"; stat["flow"] += 1; kept.append(x); continue
        kept.append(x)
    return kept, stat
