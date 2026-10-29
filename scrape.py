"""每日抓取：104法拍網物件列表 -> site/data.json"""
import base64, zlib, json, os, re, time, datetime, urllib.request, html as H
import cv2, numpy as np
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

# 他人業務加在照片左下角的浮水印圖示（圓形標誌）；比對到就不使用該照片
WM = np.frombuffer(zlib.decompress(base64.b64decode("eNo9VP1PE2cc/xOWzRk2E/fikpksWbLExG3OmSW6ZXE/+cukvefe2kKRl5YrfUcGosMCEvEFZEyBgghSoUFeVYQWV7BStaUKyqSApS1YtLTQt7sr23OH+MnlLnnu83ye7+fz/d4pKVWePDuHEn2xZ/++Hw8fEWVpTzea+7s7Gksp4sDXn324fee27R+kbacUqnyKyjn++16ASzPl9Q9ehbyT972pVNS/tHCvTHRg14609yBPp9PrtHql5lekRFdmehpmmEfVPcYyJz16uW9gddnejB745P1tH6XlKZVqVb5GfFCnvjo3awmlGJPeYi3pjF0rLr9Lh8zumfNHdqft+FihUWvUMtVRrGJ82VlxPrgWtJe2DJ5zL/e2ldyiZwxVT2fvSL/7dOdxfaGqQEYJDE+Y+OvaotGp4fjULYcvuW63DXrp3qKrkdH7jxQHdxQUaFT5MrJm1vqYpscMF52BqH/a2j8w4vK9oZmxMmfAEUwslR5SatXoMeVZj3nAH06+GPT7bE2aTDT9KJJJNQ7PR252jb2E3t2qQr1OcuxUwGc4bZ0IRRa6tGIU4CiGoRwUbQsrETbBLA5P67VKudKWiJhOnR6KOEtFCMBQIcfjqDip/Wc94puoKR7VKim1afZBbM1hWxnKJjEcMggMx7kLwwhE0hOzGU60DqnkyiKP5fHkWChhkkMRnHuPE9ydgMBRsSnS3XtjOF+W3emoanN2eMalGAeS1yK5DTwI8VBg1BhUqFXP2k+V1k24KYByPJxMh08g2uIBIsv94jaTr26OLz2ovbzUABCCFwSqyjx44BbE6UR5OEDnUk9YJul/9FBMAr54QNYFZm7K3xEx6NrhmaFUK3E2+mq1AQZCcLWB+hmPf/5pHl8D7woFZ+YvFGhDobDN7pHxZ0LFYy6GjsyO58L4sLeCKO66mlX93NJrdNkAnxeJgOpYimHjVtGWHrcuHLFnNPfdbLrl7RZsJofKp5IbDBP8EzaPW8A5RxgwLWa1/11ccibYwq3iKEBq4xsbG8npeimKAc4YwnlDWmJ57SN97W1h42bNpNDMMmzq1Vj4YYNaDAtEoV0cFbb4Cq7H6GiIvibgS0H1lhfLLDOm6PGt+fpOivl2Q8NGj7KB9br/Tbby5QHipHvRNT9XCbDCfv/6a4shFyCcZuuc3OBvLjkz343wqRCovHFhuRIjBECk6F2h38w2ZWAEjpgiOYUTF7t67tgQuAtgCA4w1ZVs2FQoj5R3B2LrN9JxXHh7MUtt75ow1z+D+QPJiQqDwVBebhBhCIkCAiU0t+eaAQEIe1dm7mhHSXHb2mUgEuhcz3lMXxRwrcbhvJJqCUzV4PlLIj/nbev0pR6LCFDngpicdLuHM8FmTtAaLsQyxtfMYlnWVDxBv3l9BcWON0I0GY3NdVKE3OKhOKgKr0SlJHXJu+icGnRS6YQQQiAQwh6AdzwM5Nyd77FnkFL1wMhgzcl7ExLYTZTYnBoS3ZwAmHNen73ivI0gMjRVPdVFNcNLJthTkh8v/gviiUJU3BrzGiqv116quVTQcqHjJR2NDkr4kd6aJsjHMFH3ejwxNW4myXQBobkxl6BZOvbwDxTB3oL7HwBUZ43GUik63n/4l5/2fnNI7qLZJLORWDZpYA6bPAITU02LdJKGCvelX+3etevzL/crnCk2xbJJOjh+VisFsDlZmgrLUpzeYFNM1CLD9u/7dt8P3+/5TWqBJ7MsQ7PM2hOH1eqYXIU6NGT9t9on+fnQ/zVvVN8=")), np.uint8).reshape(38, 40)

def has_watermark(path):
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if im is None: return True
    H_ = im.shape[0]
    reg = im[max(0, H_ - 170):H_, 0:260]
    reg = cv2.resize(reg, (reg.shape[1] // 2, reg.shape[0] // 2), interpolation=cv2.INTER_AREA)
    if reg.shape[0] < WM.shape[0] or reg.shape[1] < WM.shape[1]: return False
    return float(cv2.matchTemplate(reg, WM, cv2.TM_CCOEFF_NORMED).max()) >= 0.67

def save_img(url, hid):
    """把照片存到網站自己的 img/ 資料夾（原站只有 http，直接引用會被瀏覽器擋掉）"""
    if not url: return ""
    path = f"site/img/{hid}.jpg"
    if not os.path.exists(path):
        try:
            os.makedirs("site/img", exist_ok=True)
            data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()
            open(path, "wb").write(data)
        except Exception:
            return ""
    if has_watermark(path):
        os.remove(path); return ""
    return f"img/{hid}.jpg"

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
                        "狀態": g(r"alt='([^']*)' /></div><div class=\"cssListImg"), "圖片": save_img(g(r'data-original="([^"]+)"'), hid),
                        "連結": f"http://www.xn--104-yz0f900ahup.tw/{hid}.htm"})
        if not new: break
        time.sleep(1)
    return out

if __name__ == "__main__":
    data = {"更新時間": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M"),
            "104": s104()}
    json.dump(data, open("site/data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(data["104"]), "筆 104")
