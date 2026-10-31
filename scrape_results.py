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

if __name__ == "__main__":
    xs = fetch()
    json.dump({"更新時間": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "items": xs}, open("data/results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    import collections; print(len(xs), "筆", dict(collections.Counter(x["status"] for x in xs)))
