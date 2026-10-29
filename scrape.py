"""每日抓取：鑫創法拍(toro591)首頁兩張表 + 104法拍網物件列表 -> site/data.json"""
import json, re, time, datetime, urllib.request, html as H
from urllib.parse import urljoin, unquote

UA = {"User-Agent": "Mozilla/5.0 (fapai-site daily sync)"}
TORO = "https://www.toro591.com/"
S104 = "http://www.xn--104-yz0f900ahup.tw/HouseSale/"

def get(url):
    for i in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "ignore")
        except Exception as e:
            err = e; time.sleep(3)
    raise err

def txt(s): return H.unescape(re.sub(r"<[^>]+>", "", s)).strip()

def toro():
    h = get(TORO)
    h = re.sub(r"<!--.*?-->", "", h, flags=re.S)
    out = []
    for t_i, tb in enumerate(re.findall(r"<table.*?</table>", h, flags=re.S)):
        kind = "新增/復拍" if t_i == 0 else "拍定/停拍/撤回/流標"
        heads = [txt(x) for x in re.findall(r"<th[^>]*>(.*?)</th>", tb, flags=re.S)]
        for tr in re.findall(r"<tr[^>]*clickable-row.*?</tr>", tb, flags=re.S):
            m = re.search(r"window\.open\('([^']+)'", tr)
            cells = [txt(x) for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
            if not m or not cells: continue
            row = dict(zip(heads, cells))
            row["來源"] = "鑫創法拍"; row["分類"] = kind; row["連結"] = urljoin(TORO, m.group(1))
            out.append(row)
    return out

def toro_all(page_size=50):
    """鑫創全部物件：呼叫其網站列表所用的 house_ajax.php（與瀏覽器相同），分頁讀完"""
    import uuid
    out, page, pages = [], 1, 1
    while page <= pages and page < 200:
        bd = uuid.uuid4().hex
        fields = dict(city="", area="", h="", a="", c="", p="", page=str(page), page_size=str(page_size), layout="product")
        body = "".join(f'--{bd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in fields.items()) + f"--{bd}--\r\n"
        req = urllib.request.Request(TORO + "house_ajax.php", body.encode(), {**UA, "Content-Type": f"multipart/form-data; boundary={bd}"})
        h = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
        pages = int((re.search(r'id="pages" value="(\d+)"', h) or [0, 1])[1])
        for c in h.split('class="product-box"')[1:]:
            g = lambda pat: txt((re.search(pat, c, flags=re.S) or [None, ""])[1])
            href = (re.search(r'href="([^"]+)"', c) or [None, ""])[1]
            top = g(r'class="product-top">(.*?)</div>')
            date, _, status = top.partition("｜")
            tp, _, area = g(r'class="product-type">(.*?)</div>').partition("｜")
            img = (re.search(r'<img[^>]+src="([^"]+)"', c) or [None, ""])[1]
            out.append({"來源": "鑫創法拍", "地址": g(r'class="product-address">(.*?)</div>'), "拍賣日": date.strip(), "狀態": status.strip(),
                        "拍次點交": g(r"<span>(\d拍[^<]*)</span>"), "類型": tp, "坪數": area,
                        "底價": g(r'class="product-price1"><span>底價</span>(.*?)</div>'),
                        "圖片": urljoin(TORO, img), "連結": urljoin(TORO, href)})
        page += 1; time.sleep(1)
    return out

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
                        "狀態": g(r"alt='([^']*)' /></div><div class=\"cssListImg"), "圖片": g(r'data-original="([^"]+)"'),
                        "連結": f"http://www.xn--104-yz0f900ahup.tw/{hid}.htm"})
        if not new: break
        time.sleep(1)
    return out

if __name__ == "__main__":
    data = {"更新時間": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M"),
            "鑫創": toro(), "鑫創全部": toro_all(), "104": s104()}
    json.dump(data, open("site/data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(data["鑫創"]), "週更;", len(data["鑫創全部"]), "筆 鑫創全部;", len(data["104"]), "筆 104")
