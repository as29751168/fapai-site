"""法拍地圖用：物件地址 -> 座標（國土測繪中心門牌定位，免金鑰）
讀 site/data.json，結果快取在 data/geo.json：{地址: [經度, 緯度, 精準度]}
精準度 2＝門牌精準、1＝同路段推估、0＝只到行政區（地圖上畫空心圖釘）
每天只查新地址，舊的直接用快取。"""
import json, os, re, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://api.nlsc.gov.tw/idc/TextQueryMap/"
HDR = {"Referer": "https://maps.nlsc.gov.tw/", "Origin": "https://maps.nlsc.gov.tw", "User-Agent": "Mozilla/5.0 (tomin104.com map)"}
P = "data/geo.json"
FW = str.maketrans("０１２３４５６７８９－", "0123456789-")


def norm(s):
    s = (s or "").translate(FW).replace("臺", "台").replace(" ", "")
    s = re.sub(r"[^市縣區鄉鎮]{1,4}?[里村]\d+鄰", "", s)          # 拿掉「紅梅里19鄰」
    s = re.sub(r"(?<=[區鄉鎮市])[^區鄉鎮市路街道段巷弄號\d]{1,3}[里村](?=[^\d])", "", s)
    s = re.sub(r"(\d+)-(\d+)號", r"\1之\2號", s)
    return s


def query_addr(x):
    """完整地址切到「號」為止（樓層不送）"""
    a = ((x.get("資訊") or {}).get("完整地址") or "").translate(FW).replace("臺", "台")
    a = re.sub(r"[^\u4e00-\u9fff0-9A-Za-z\-]", "", a)          # 拿掉 ❶、？等符號
    m = re.match(r"(.*?\d+(?:[-之]\d+)?號)", a)
    return m.group(1) if m else a


def road_of(a):
    m = re.match(r"(.*?(?:路|街|大道|道)(?:[一二三四五六七八九十]+段)?)", a)
    return m.group(1) if m else ""


def ask(q):
    url = API + urllib.parse.quote(q)
    for i in range(3):
        try:
            t = urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=20).read().decode("utf-8", "ignore")
            return [(c, tuple(map(float, l.split(",")))) for c, l in re.findall(r"<CONTENT>(.*?)</CONTENT>.*?<LOCATION>([\d.]+,[\d.]+)</LOCATION>", t, flags=re.S)]
        except Exception:
            time.sleep(2 + i * 2)
    return None


_last = [0.0]
def osm(q):
    """國土測繪連不上時的備援（OpenStreetMap Nominatim，每秒最多 1 次）"""
    try:
        time.sleep(max(0, 1.1 - (time.time() - _last[0]))); _last[0] = time.time()
        u = "https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=tw&q=" + urllib.parse.quote(q)
        r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "tomin104.com fapai map"}), timeout=20).read())
        if r: return [round(float(r[0]["lon"]), 6), round(float(r[0]["lat"]), 6), 1]
        rd = road_of(norm(q))
        if rd and rd != q: return osm(rd)
    except Exception:
        pass
    return None


def locate(q):
    nq = norm(q)
    if not nq: return None
    res = ask(q)
    if res is None: return osm(q)                   # 國土測繪查詢失敗：改用 OSM 推估（路段等級），之後 GEO_RETRY 可再精準化
    nodist = not re.match(r".{2,3}[市縣].{1,3}?[區鄉鎮市]", nq)    # 新竹市、嘉義市常省略「區」
    def same(c):
        c = norm(c)
        return c == nq or (nodist and re.sub(r"^(.{2}市).{1,2}區", r"\1", c) == nq)
    for c, (lon, lat) in res:
        if same(c): return [round(lon, 6), round(lat, 6), 2]
    rd = road_of(nq)
    if rd:
        for c, (lon, lat) in res:
            if norm(c).startswith(rd) or (nodist and re.sub(r"^(.{2}市).{1,2}區", r"\1", norm(c)).startswith(rd)): return [round(lon, 6), round(lat, 6), 1]
        r2 = ask(rd) or []
        for c, (lon, lat) in r2:
            if norm(c).startswith(rd) or (nodist and re.sub(r"^(.{2}市).{1,2}區", r"\1", norm(c)).startswith(rd)): return [round(lon, 6), round(lat, 6), 1]
    dist = re.match(r"(.{2,3}[市縣].{1,3}?[區鄉鎮市])", nq) or re.match(r"(.{2}市)", nq)
    if dist:
        for c, (lon, lat) in (ask(dist.group(1)) or [])[:1]:
            return [round(lon, 6), round(lat, 6), 0]
    return [0, 0, -1]                               # 查不到：記下來避免每天重查


def main(max_new=3000):
    geo = json.load(open(P, encoding="utf-8")) if os.path.exists(P) else {}
    items = json.load(open("site/data.json", encoding="utf-8"))["104"]
    cur = {q for q in map(query_addr, items) if q}
    geo = {k: v for k, v in geo.items() if k in cur}                    # 只留目前物件的地址
    retry = os.environ.get("GEO_RETRY") == "1"                           # GEO_RETRY=1：重查不精準的地址
    todo = sorted(q for q in cur if q not in geo or (retry and geo[q][2] < 2))[:max_new]
    print("法拍地圖定位：快取", len(geo), "筆，新查詢", len(todo), "筆")
    def job(q):
        time.sleep(0.15)
        return q, locate(q)
    with ThreadPoolExecutor(4) as ex:
        for i, (q, v) in enumerate(ex.map(job, todo), 1):
            if v: geo[q] = v
            if i % 100 == 0:
                print(" ", i); json.dump(geo, open(P, "w", encoding="utf-8"), ensure_ascii=False)
    os.makedirs("data", exist_ok=True)
    json.dump(geo, open(P, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    c = {k: sum(1 for v in geo.values() if v[2] == k) for k in (2, 1, 0, -1)}
    print("定位結果：門牌精準", c[2], "／路段推估", c[1], "／行政區", c[0], "／查無", c[-1])


if __name__ == "__main__":
    main()
