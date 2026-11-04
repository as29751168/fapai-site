"""每週拍定・停拍・撤回・流標：從 toro591 讀取法院開標結果（只取文字資料，不取照片與連結）-> data/results.json"""
import re, json, html, time, datetime, requests

HOST = "https://www.toro591.com"
KEEP_DAYS = 14

def roc_to_date(s):
    m = re.match(r"(\d+)/(\d+)/(\d+)", s or "")
    return datetime.date(int(m[1]) + 1911, int(m[2]), int(m[3])) if m else None

def fetch(max_pages=12):
    s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (fapai-site daily sync)"
    s.get(f"{HOST}/decide-house.php", timeout=40)
    today = datetime.date.today(); cutoff = today - datetime.timedelta(days=KEEP_DAYS)
    out, old_pages = [], 0
    for p in range(1, max_pages + 1):
        h = s.post(f"{HOST}/house_ajax2.php", files={k: (None, str(v)) for k, v in {"i": 1, "page": p, "page_size": 12, "layout": "product"}.items()},
                   headers={"X-Requested-With": "XMLHttpRequest", "Referer": f"{HOST}/decide-house.php", "Origin": HOST}, timeout=60).text
        boxes = re.findall(r'<a class="product-box".*?</a>', h, flags=re.S)
        if not boxes: break
        recent = 0
        for b in boxes:
            g = lambda pat: html.unescape(re.sub(r"<[^>]+>", "", (re.search(pat, b, flags=re.S) or [None, ""])[1])).strip()
            top = g(r'<div class="product-top">(.*?)</div>')
            m = re.match(r"(\d+/\d+/\d+)｜\s*(\S+)", top)
            if not m: continue
            d = roc_to_date(m[1])
            if d and d >= cutoff: recent += 1
            tag = g(r"<span>([^<]*拍[^<]*|[^<]*應買[^<]*)</span></div>")
            rd, _, dj = tag.partition("｜")
            typ = g(r'<div class="product-type">(.*?)</div>')
            addr = g(r'<div class="product-address">(.*?)</div>')
            base = g(r'<div class="product-price1"><span>底價</span>(.*?)</div>')
            win = g(r'<div class="product-price\d"><span>拍定價</span>(.*?)</div>')
            out.append({"date": m[1], "status": m[2], "round": rd, "deliver": dj, "type": typ, "addr": addr, "base": base, "win": win})
        # 列表由新到舊；整頁都比期限舊就停止（未來日期的撤回／停拍排在前面，不影響）
        old_pages = old_pages + 1 if recent == 0 else 0
        if old_pages >= 2: break
        time.sleep(0.5)
    return [x for x in out if (roc_to_date(x["date"]) or today) >= cutoff]


# ---- 桃園：透明房訊公開的「開標結果」頁（不需登入；本公司資料）----
import urllib.parse
OLD = "http://www.104woo.com.tw/tom1/house/lin2_k_index00a.asp"
_STATUS = {"得標": "拍定", "承受": "承受"}

def _clean(t):
    t = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", "", t)
    t = html.unescape(re.sub(r"<[^>]+>", "|", t))
    return re.sub(r"\s*\|\s*(\|\s*)*", "|", t)

def fetch_court(court="桃園法院", prefix="桃園市", days=8):
    q = lambda x: urllib.parse.quote(x, encoding="big5")
    s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (fapai-site daily sync)"
    out, today = [], datetime.date.today()
    for k in range(days):
        d = today - datetime.timedelta(days=k)
        u = (f"{OLD}?endDay0={d:%Y/%m/%d}&acity={q(court)}&sel_ect0={q('不限')}&asblo=all&achange1=all&achange2=all&achange3=all&achange4=all&achange5=all&achange6=all&achange7=0")
        try: t = _clean(s.get(u, timeout=40).content.decode("big5", "ignore"))
        except Exception: continue
        for chunk in re.split(r"\|\d+\.\|", t)[1:]:
            p = [x.strip() for x in chunk.split("|") if x.strip()]
            if len(p) < 8 or not re.match(r"\d+/\d+", p[1]): continue
            status = p[3]
            base = next((x.split("：", 1)[1] for x in p if x.startswith("底價：")), "")
            dj = next((x for x in p if x in ("點交", "不點交", "有點交", "部份點交", "依現況點交", "詳如備註")), "")
            size = next((x for x in p if x.startswith(("建坪：", "地坪：")) ), "")
            addr, typ = p[-2], p[-1]
            if addr.endswith("號") or "地號" in addr or True:
                out.append({"date": f"{d.year - 1911}/{d.month:02d}/{d.day:02d}", "status": _STATUS.get(status, status), "round": re.sub(r"^(.)拍", lambda m: str("一二三四五六七八九十".index(m[1]) + 1) + "拍" if m[1] in "一二三四五六七八九十" else m[0], p[2]), "deliver": dj,
                            "type": "｜".join(filter(None, [typ, size.replace("：", " ")])), "addr": prefix + addr, "base": base, "win": "", "land": typ == "土地"})
        time.sleep(0.4)
    return out

if __name__ == "__main__":
    xs = fetch()
    json.dump({"更新時間": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "items": xs}, open("data/results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    import collections; print(len(xs), "筆", dict(collections.Counter(x["status"] for x in xs)))
