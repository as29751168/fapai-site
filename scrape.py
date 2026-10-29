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

if __name__ == "__main__":
    data = {"更新時間": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M"),
            "104": s104()}
    clear_images()
    json.dump(data, open("site/data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(data["104"]), "筆 104")
