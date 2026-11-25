"""由 site/data.json + site/photos.json 產生全站靜態頁面（SEO / AI 搜尋友善）
輸出：index.html、h/<編號>.html、area/<地區>.html、sitemap.xml、robots.txt、llms.txt
"""
import html, json, os, re, shutil, urllib.parse, datetime

SITE = "https://tomin104.com"          # 網站正式網址
NAME = "Pitt & Anna 104法拍網團隊"   # 2026-11-24 Anna 定案品牌名稱（個人名稱＋104法拍網團隊）
PHONE_A, PHONE_P = "0986-678-928", "0918-313-888"
LINKS = {
    "LINE": "https://lin.ee/Y2bGSIB",
    "粉絲專頁": "https://www.facebook.com/share/1CnLq9vuJd/?mibextid=wwXIfr",
    "YouTube": "https://youtube.com/@anna-n9999?si=laOYfE2Bm2VMPYDa",
    "LINE 社群": "https://line.me/ti/g2/6-QeB1Co7tP6e-Qhln_j0swFD4q0ZIFqdSmUDQ?utm_source=invitation&utm_medium=link_copy&utm_campaign=default",
}
# 2026-11-19 Anna「全部照改」：對外統一 Pitt & Anna｜104法拍網團隊、財欣全名；不放公司總機、土城地址（統一對外資料_20261119.md）
TEAM = NAME
COMPANY = "財欣不動產管理顧問有限公司"
SLOGAN = "你的法拍購屋夥伴"
INTRO = "Pitt & Anna｜104法拍網團隊，你的法拍購屋夥伴。透明房訊品牌深耕法拍逾 40 年，全台都有服務：投標諮詢、全程代標、點交協助，從看懂公告、評估總成本，到得標後續一路陪你。"
PHOTO_BASE = "https://www.104woo.com.tw/"

D = json.load(open("site/data.json", encoding="utf-8"))

# 2026-11-19 筆錄遮個資：法院沒遮的姓名（債務人朱○、第三人張○○…）與電話，產生頁面前一律隱去，連 data.json 一起寫回
_SUR = "陳林黃張李王吳劉蔡楊許鄭謝洪郭邱曾廖賴徐周葉蘇莊呂江何蕭羅高潘簡朱鍾游彭詹胡施沈余盧梁趙顏柯翁魏孫戴范方宋鄧杜傅侯曹薛丁卓阮馬董温溫唐藍石蔣古紀姚連馮歐程湯黎田康姜白汪鄒尤巫鐘涂龔嚴韓袁金童陸夏柳凃邵錢伍倪于譚駱熊任甘秦顧毛章史官萬俞雷粘饒闕凌崔尹孔辛武辜陶段龍韋葛池孟褚殷麥賀賈莫文管關向包丘梅華裴利全樊房佘花安左魯塗穆鮑蒲郝谷成邢"
_ROLE = r"(債務人|債權人|所有權人|所有人|承租人|出租人|占有人|佔有人|占用人|佔用人|使用人|現住人|居住人|第三人|關係人|代理人|管理人|屋主|房客|配偶|之子|之女|之妻|之夫|之父|之母|兒子|女兒|胞弟|胞兄|胞姊|胞妹|姓名|即)"
_PNAME = re.compile(_ROLE + r"(?!陳報|陳述|陳明|陳稱|陳情|管理|代理|何人|方形|全體)([" + _SUR + r"][一-鿿]{1,2}?)(?=在場|到場|稱|陳稱|陳述|表示|說明|答稱|自稱|供稱|指稱|自行|居住|使用|占用|佔用|承租|及|、|，|,|。|等人|之|（|\(|君|先生|小姐|女士|現|\d|自住|自用|自己|所有|名下|一人|夫妻|全家|與|於|向|已|仍|尚|目前|則|並|亦|在)")
_PPHONE = re.compile(r"(?<![\d,])0(?:9\d{2}[-\s]?\d{3}[-\s]?\d{3}|\d{1,2}[-)）\s]?\d{3,4}[-\s]?\d{4})(?![\d,號])")
def _hide_pii(t):
    t = _PNAME.sub(lambda m: m.group(0) if re.search(r"先|小姐|女士", m.group(2)) else m.group(1) + "（姓名已隱去）", t)
    return _PPHONE.sub("（電話已隱去）", t)
# 2026-11-19：舊資料的「格局坪數」是建坪（不含公設），有總登記坪數就改用總坪數，跟買屋網、HO 一致
_area_n = 0
for _x in D.get("104", []):
    _t = (_x.get("資訊") or {}).get("總登記坪數", "")
    if _x.get("來源") == "透明房訊" and _t and _x.get("格局坪數") != _t: _x["格局坪數"] = _t; _area_n += 1
_pii_n = 0
for _x in D.get("104", []):
    _inf = _x.get("資訊") or {}
    if _inf.get("筆錄"):
        _new = _hide_pii(_inf["筆錄"])
        if _new != _inf["筆錄"]: _inf["筆錄"] = _new; _pii_n += 1
if _pii_n or _area_n:
    json.dump(D, open("site/data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("筆錄遮個資:", _pii_n, "筆")
# 2026-11-18 Anna：開標日已過卻還寫「待標」的不能照舊顯示（HO 快照沒更新拍次）；改標「開標日期已過・待確認」並排到最後
_TODAY = datetime.date.today()
for _x in D["104"]:
    _i = _x.get("資訊") or {}
    _m = re.fullmatch(r"(\d+)/(\d+)/(\d+)", _i.get("開標日期", ""))
    if not _m or _i.get("銷售狀態") not in ("待標中", "待標"): continue
    try: _d = datetime.date(int(_m[1]) + 1911, int(_m[2]), int(_m[3]))
    except ValueError: continue
    if _d < _TODAY:
        _i["銷售狀態"] = "待確認"; _x["狀態"] = "開標日期已過・待確認"
def _age(x):
    """屋齡（年）；預售屋視為 0；查無則回傳 None"""
    v = (x.get("資訊") or {}).get("屋齡", "")
    if "預售" in v: return 0.0
    m = re.match(r"[\d.]+", v)
    return float(m[0]) if m else None
# 屋齡 10 年內的新房子排最前面（由新到舊）；其餘維持台北、新北、桃園的順序
def _order(x):
    if x.get("資訊", {}).get("銷售狀態") == "待確認": return (2, 0, 0)   # 開標日期已過、待確認者排最後
    a = _age(x)
    return (0, a, 0) if a is not None and a <= 10 else (1, 0, {"台北": 0, "新北": 1, "桃園": 2}.get(x["區域"][:2], 3))
EXCL_CITY = ("金門", "澎湖", "連江")   # 2026-11-25 Anna：金門、澎湖都不用放
EXCL_IDS = {x["編號"] for x in D["104"] if x.get("區域", "")[:2] in EXCL_CITY}
ITEMS = sorted([x for x in D["104"] if x["編號"] not in EXCL_IDS], key=_order)
UPDATED = D["更新時間"]
try:
    P = json.load(open("site/photos.json", encoding="utf-8"))
except Exception:
    P = {}

def e(s): return html.escape(str(s if s is not None else ""), quote=True)
def jd(o): return json.dumps(o, ensure_ascii=False).replace("</", "<\\/")
def photos(x):
    v = P.get(x["編號"][2:], [])
    if isinstance(v, str): v = [v]
    return [(SITE + p if p.startswith("/") else PHOTO_BASE + urllib.parse.quote(p, safe="/")) for p in v]
def is_ying(x):
    """公告應買（一買）：沒有開標日，先買先贏（2026-11-18 Anna）"""
    return "應買" in (x.get("資訊", {}).get("拍次", "") or "")
YING = "公告應買｜先買先贏"
# 照片載入失敗時自動換下一張，全部失敗就換成「照片請洽業務」（2026-11-18 Anna：卡片不可出現問號破圖）
IMG_FB = ("var a=(this.dataset.alt||'').split('|').filter(Boolean);if(a.length){this.src=a.shift();this.dataset.alt=a.join('|')}"
          "else{this.onerror=null;var d=document.createElement('div');d.className='noimg';d.textContent='照片請洽業務';this.replaceWith(d)}")
def img_fb(ph):
    return f' data-alt="{e("|".join(ph[1:4]))}" onerror="{e(IMG_FB)}"'
def price_num(s):
    m = re.search(r"([\d.,]+)\s*(億|萬)?", str(s or ""))
    if not m: return 0
    n = float(m.group(1).replace(",", ""))
    return int(n * (100000000 if m.group(2) == "億" else 10000 if m.group(2) == "萬" else 1))
def area_of(x): return x["區域"].split("-")[0]
def title_of(x):
    t = re.sub(r"^[^【]*?(?=【)", "", x["地址"]) if False else x["地址"]
    return t
def slug(s): return urllib.parse.quote(s)
def round_of(x):
    r = x.get("資訊", {}).get("拍次", "")
    return int(r) if r.isdigit() else 0
def date_key(x):
    m = re.fullmatch(r"(\d+)/(\d+)/(\d+)", x.get("資訊", {}).get("開標日期", ""))
    return int(m.group(1)) * 10000 + int(m.group(2)) * 100 + int(m.group(3)) if m else 99999999
def deliver_of(x):
    m = re.search(r"點交情形→([^●\n]+)", x.get("資訊", {}).get("筆錄", ""))
    v = m.group(1).strip() if m else ""
    return "不點交" if v.startswith("不點交") else "點交" if v.startswith("點交") else ("其他" if v else "")

def first_price(x):
    ln = x.get("資訊", {}).get("拍賣紀錄", "").split("\n")[0]
    if not re.match(r"第\s*(1|一)\s*拍", ln): return 0   # 2026-11-25 Anna：降幅算不出來就不顯示（只有本次拍次時會誤算成 0%）
    m = re.search(r"底標價[：:]\s*([\d.,]+)\s*(億|萬)?", ln)
    return price_num(m.group(1) + (m.group(2) or "")) if m else 0

def upcoming(days=7):
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date()
    out = []
    for x in ITEMS:
        m = re.fullmatch(r"(\d+)/(\d+)/(\d+)", x.get("資訊", {}).get("開標日期", ""))
        if not m: continue
        try: d = datetime.date(int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3)))
        except ValueError: continue
        if 0 <= (d - today).days <= days: out.append((d, x))
    return [x for d, x in sorted(out, key=lambda t: t[0])]

SPEC_ORDER = ["案號", "總登記坪數", "每坪單價"]
DETAIL_KEYS = ["銷售狀態", "格局", "社區/大樓", "屋齡", "車位", "座向", "所在樓層", "管理費", "管委會", "中庭", "電梯", "邊間", "增建", "是否凶宅", "無障礙環境", "法拍件", "拍次", "開標日期"]
SIZE_KEYS = ["主建物", "附屬建物", "公共設施", "停車位", "土地登記總坪數", "總坪數"]

CSS = """.crx{background:#8a8f94}.crs>.crb .crp+.crp{margin-top:6px;border-top:0;padding-top:0}.note{color:#777;font-size:.85rem;text-align:center;margin:4px 0 14px}.cr{position:relative;margin:6px 0 4px}.crt{display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;scrollbar-width:none;padding:2px}.crt::-webkit-scrollbar{display:none}.crs{flex:0 0 88%;max-width:420px;scroll-snap-align:center;border:1px solid #d9b8a8;border-radius:14px;overflow:hidden;background:#fff;color:#222;text-decoration:none;display:block}.crh{background:#cf8570;color:#fff;text-align:center;padding:8px;font-size:1rem;letter-spacing:.03em}.cri{position:relative;aspect-ratio:4/3;background:#eee}.cri img{width:100%;height:100%;object-fit:cover;display:block}.cri .noimg{display:flex;align-items:center;justify-content:center;height:100%;color:#999}.crtg{position:absolute;right:10px;bottom:10px;background:#fff;color:#b5502f;font-weight:700;border-radius:8px;padding:5px 12px;font-size:.95rem}.crb{padding:12px 16px 14px}.crct{color:#b5654a;font-size:.92rem}.crn{font-weight:700;font-size:1.05rem;margin:6px 0 10px;min-height:2.9em;line-height:1.45}.crp{display:flex;justify-content:space-between;align-items:baseline;border-top:1px solid #e3cfc4;padding-top:10px}.crp span{color:#b5654a;font-weight:700}.crp b{font-size:1.4rem}.crdots{display:flex;justify-content:center;gap:9px;margin:12px 0 4px}.crdots i{width:11px;height:11px;border-radius:50%;background:#efd8cf;display:block}.crdots i.on{background:#a4442d}.crmw{text-align:center;margin:10px 0 18px}.crmore{display:inline-flex;align-items:center;justify-content:center;width:104px;height:104px;border:1px solid #cf8570;border-radius:50%;color:#cf8570;text-decoration:none;font-family:Georgia,serif;font-size:1.3rem}
body{-webkit-user-select:none;user-select:none;-webkit-touch-callout:none}input,textarea,select{-webkit-user-select:text;user-select:text}img{-webkit-user-drag:none;user-drag:none}
*{box-sizing:border-box}body{margin:0;font-family:"Noto Sans TC","Microsoft JhengHei",sans-serif;color:#222;background:#f6f6f4;line-height:1.6}
a{color:#1f3a4d}header.top{background:#1f3a4d;color:#fff;padding:14px 16px}header.top a{color:#fff;text-decoration:none;font-weight:700;font-size:18px}
header.top small{display:block;opacity:.8;font-weight:400;font-size:13px}
main{max-width:1100px;margin:0 auto;padding:16px}nav.bc{font-size:13px;color:#666;margin-bottom:10px}nav.bc a{color:#666}
h1{font-size:22px;line-height:1.4;margin:6px 0}h2{font-size:18px;margin:0 0 10px}
.box{background:#fff;border:1px solid #e2e2de;border-radius:8px;padding:16px;margin-bottom:16px}
.tag{display:inline-block;font-size:12px;padding:1px 8px;border-radius:10px;background:#e8eef2;color:#1f3a4d;margin-right:6px}
.price{font-size:28px;font-weight:700;color:#b3261e;margin:6px 0}.price s{font-size:15px;font-weight:400;color:#999;margin-right:8px}
.gate .card.lk{filter:blur(7px);pointer-events:none;user-select:none}.gb{display:flex;flex-wrap:wrap;gap:10px;align-items:center;background:#f3f8f4;border:1px solid #cfe5d4;border-radius:10px;padding:12px 14px;margin:10px 0}.gb span{color:#555;font-size:14px}table{width:100%;border-collapse:collapse;font-size:15px}td,th{padding:8px 6px;border-bottom:1px solid #eee;text-align:left;vertical-align:top}td:first-child,th{color:#666;width:120px;font-weight:400}
.gal{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px}.gal img{width:100%;height:170px;object-fit:contain;border-radius:6px;background:#e8eef2;display:block}.gal img:first-child{grid-column:1/-1;height:auto;max-height:none;object-fit:contain}
.noimg{height:160px;background:#e8eef2;color:#6b7c88;display:flex;align-items:center;justify-content:center;border-radius:6px}
.notes{white-space:pre-line}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px}
.card{background:#fff;border:1px solid #e2e2de;border-radius:8px;overflow:hidden;text-decoration:none;color:inherit;display:block}
.card img,.card .noimg{width:100%;height:160px;object-fit:cover;display:block;border-radius:0}.card .b{padding:10px 12px}.card h3{margin:0 0 4px;font-size:15px;line-height:1.4}
.card .m{font-size:13px;color:#666}.card .p{margin-top:6px;font-size:17px;font-weight:700;color:#b3261e}.card .p s{font-size:13px;font-weight:400;color:#999;margin-right:6px}
.bar{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}#n{scroll-margin-top:70px}.bar input,.bar select{padding:9px 10px;border:1px solid #ccc;border-radius:6px;font-size:16px;background:#fff}.bar input{flex:1;min-width:180px}
.btn{display:inline-block;margin:6px 8px 0 0;padding:9px 15px;border-radius:6px;background:#1f3a4d;color:#fff!important;text-decoration:none;font-size:14px}.btn.line{background:#06c755}
.cd{margin:8px 0 0;color:var(--muted,#637581);font-size:15px}.cd b{display:inline-block;margin-left:10px;background:#9c3b32;color:#fff;border-radius:2px;padding:2px 10px;font-size:14px;font-weight:600}.cv{position:relative}.rd{position:absolute;left:8px;top:8px;background:#b3261e;color:#fff;padding:2px 10px;border-radius:12px;font-size:13px;font-weight:700}.rd.n{background:#1f3a4d}
.bar button{padding:9px 14px;border:1px solid #1f3a4d;background:#fff;color:#1f3a4d;border-radius:6px;font-size:15px;cursor:pointer}
.cta{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid #ddd;padding:8px 12px;display:flex;gap:8px;z-index:9}.cta a,.cta button{flex:1;text-align:center;padding:12px;border-radius:8px;font-size:16px;border:0;color:#fff;text-decoration:none;cursor:pointer;font-family:inherit}.cta .l{background:#06c755}.cta .t{background:#1f3a4d}
.hero{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}.hero a{padding:10px 16px;border-radius:8px;color:#fff;text-decoration:none;font-size:15px;background:#1f3a4d}.hero a.l{background:#06c755}.hero a.f{background:#1877f2}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0;align-items:center}.chips button{padding:8px 14px;border:1px solid #1f3a4d;background:#fff;color:#1f3a4d;border-radius:20px;font-size:15px;cursor:pointer;font-family:inherit}.chips button.on{background:#1f3a4d;color:#fff}
.hd{max-width:1100px;margin:0 auto;padding:10px 16px;display:flex;align-items:center;gap:14px}header.top{background:#fff;border-bottom:1px solid #e6e2d8;position:sticky;top:0;z-index:20;color:#222;padding:0}
header.top a.logo{font-family:"Noto Serif TC","Songti TC",serif;font-weight:700;font-size:19px;color:#1f3a4d;letter-spacing:1px}.logo i{color:#b8893b;font-style:normal}
.hd nav{margin-left:auto;display:flex;gap:16px;font-size:14px}.hd nav a{color:#1f3a4d;text-decoration:none;font-weight:400;font-size:14px}header.top a.tel{background:#1f3a4d;color:#fff;padding:7px 14px;border-radius:20px;font-size:14px;font-weight:400;white-space:nowrap}
.hero2{position:relative;background:linear-gradient(160deg,#16303f,#1f3a4d 55%,#2c5068);color:#fff;overflow:hidden}.hero2 .sky{position:absolute;left:0;bottom:0;width:100%;height:100%}
.hin{position:relative;max-width:1100px;margin:0 auto;padding:52px 16px 40px;text-align:center}.eyebrow{letter-spacing:3px;color:#d9b97a;font-size:13px;margin:0}
.hero2 h1{font-family:"Noto Serif TC","Songti TC",serif;font-size:34px;margin:10px 0 6px;color:#fff;letter-spacing:1px}.sub{font-size:17px;opacity:.92;margin:0 0 18px}
.cta2 a{display:inline-block;margin:4px;padding:12px 24px;border-radius:30px;text-decoration:none;font-size:16px;color:#fff}.cta2 .b1{background:#b8893b}.cta2 .b2{background:#06c755}
.stats{display:flex;justify-content:center;gap:24px;flex-wrap:wrap;margin:22px 0 12px;font-size:14px}.stats b{color:#d9b97a;font-size:21px;margin-right:4px}
.qk button{margin:4px;padding:8px 18px;border-radius:20px;border:1px solid rgba(255,255,255,.55);background:rgba(255,255,255,.08);color:#fff;font-size:15px;cursor:pointer;font-family:inherit}
h2.sec{font-family:"Noto Serif TC","Songti TC",serif;text-align:center;font-size:21px;color:#b8893b;border:1px solid #b8893b;padding:10px;margin:30px 0 16px;border-radius:2px;background:#fff}
.tbl td,.tbl th{padding:12px 6px}.tbl td:nth-child(1),.tbl td:nth-child(2),.tbl th:nth-child(1),.tbl th:nth-child(2){white-space:nowrap}.tbl th{font-weight:700;color:#b8893b;width:auto}.tbl td:first-child{color:#222;width:auto}.tbl a{color:#1f3a4d;text-decoration:none;border-bottom:1px dotted #1f3a4d}
.fab{position:fixed;right:12px;bottom:16px;display:flex;flex-direction:column;gap:10px;z-index:15}.fab a{width:52px;height:52px;border-radius:14px;background:#111;display:flex;align-items:center;justify-content:center;color:#fff;text-decoration:none;font-weight:700;font-size:13px;box-shadow:0 3px 10px rgba(0,0,0,.25)}.fab a.l{background:#06c755}
.ch{background:#1f3a4d;color:#fff;text-align:center;padding:7px;font-size:14px;font-family:"Noto Serif TC","Songti TC",serif}.rd2{position:absolute;right:10px;bottom:10px;background:#fff;color:#b3261e;padding:4px 12px;border-radius:8px;font-weight:700;font-size:14px;box-shadow:0 1px 4px rgba(0,0,0,.2)}.rd{display:none}
.card .b h3{font-family:"Noto Serif TC","Songti TC",serif;font-size:16px;margin:4px 0 10px;min-height:44px}.card .pr{display:flex;justify-content:flex-start;gap:14px;align-items:baseline;border-top:1px solid #e6e2d8;padding-top:8px;color:#b8893b}.card .pr b{font-family:"Noto Serif TC","Songti TC",serif;font-size:20px;color:#222}.card .pr s{font-size:13px;color:#999;margin-right:6px;font-weight:400}
.card .noimg{display:flex}
.card{transition:transform .15s,box-shadow .15s}.card:hover{transform:translateY(-2px);box-shadow:0 6px 16px rgba(0,0,0,.09)}
.areas a{display:inline-block;margin:3px 6px 3px 0;font-size:14px}footer{text-align:center;color:#888;font-size:13px;padding:24px}
details{border-bottom:1px solid #eee;padding:8px 0}summary{cursor:pointer;font-weight:700}
.lg{background:#18a999;color:#fff!important;padding:7px 14px;border-radius:20px;font-size:14px;text-decoration:none;white-space:nowrap}.mb{background:none;border:1px solid #1f3a4d;color:#1f3a4d;border-radius:8px;font-size:20px;line-height:1;padding:5px 10px;cursor:pointer}
#dr{position:fixed;inset:0;z-index:60;display:none}#dr.on{display:block}#dr .bk{position:absolute;inset:0;background:rgba(0,0,0,.5)}#dr .pn{position:absolute;right:0;top:0;bottom:0;width:78%;max-width:320px;background:#1a7f8a;color:#fff;padding:20px 22px;overflow:auto}#dr .pn a{display:block;color:#fff;text-decoration:none;font-size:18px;padding:14px 0;border-bottom:1px solid rgba(255,255,255,.2)}#dr .x{background:none;border:0;color:#fff;font-size:28px;float:right;cursor:pointer}
.mf label{display:block;margin:10px 0 4px;font-weight:700}.mf input,.mf select,.mf textarea{width:100%;box-sizing:border-box;padding:10px;border:1px solid #ccc;border-radius:6px;font-size:16px}
.hin .tm{display:block;margin:0 auto 6px;height:230px;width:auto;border-radius:18px;box-shadow:0 8px 24px rgba(0,0,0,.35)}
@media(min-width:900px){.hin{text-align:left;padding-right:380px;min-height:420px}.hin .tm{position:absolute;right:24px;top:24px;height:380px;margin:0}.cta2,.stats,.qk{justify-content:flex-start}}
.team{display:flex;gap:18px;align-items:center;flex-wrap:wrap}.team img{width:230px;max-width:100%;height:auto;border-radius:16px}.team ol{flex:1;min-width:230px;margin:0;padding-left:20px}.team li{margin:6px 0}
@media(max-width:640px){header.top a.logo{font-size:16px;letter-spacing:0;white-space:nowrap}header.top a.tel{display:none}.hd{gap:10px}.fab{right:10px;bottom:12px;gap:8px}.fab a{width:44px;height:44px;border-radius:12px;font-size:12px}.fab svg{width:22px;height:22px}body{padding-bottom:70px}}
@media(max-width:640px){h1{font-size:19px}.hero2 h1{font-size:26px}.hd nav{display:none}.hd{justify-content:space-between}.hin{padding:40px 14px 30px}.tbl .rt{display:none}}
/* ===== 新版外觀：沿用新首頁的深藍、香檳金、襯線標題 ===== */
:root{--navy:#18354b;--navy-deep:#112a3e;--ink:#233e50;--muted:#637581;--gold:#a78b5c;--gold-light:#d9c39c;--paper:#f8f7f3;--tint:#edf2f4;--line:#dce3e5}
html{scroll-behavior:smooth;scroll-padding-top:90px}
body{background:#fff;color:var(--ink);-webkit-font-smoothing:antialiased}
a{color:var(--navy)}
main{max-width:1200px;padding:28px 24px 40px}
h1,h2,h3{font-family:"Noto Serif TC","Songti TC","PMingLiU",serif;color:var(--navy);letter-spacing:.04em}
h1{font-size:30px;line-height:1.5}h2{font-size:22px}
.lh{margin:8px 0 6px}.ls{color:var(--muted);font-size:15px;margin:0 0 18px}
header.top{border-bottom:1px solid #edf0f1;background:#fffffff5;backdrop-filter:blur(14px)}
.hd{max-width:1200px;padding:0 24px;height:78px;gap:22px}
header.top a.logo{font-size:21px;letter-spacing:.13em;color:var(--navy)}.logo i{color:var(--gold)}
.hd nav{gap:28px}.hd nav a{font-size:14px;color:var(--ink);letter-spacing:.03em}.hd nav a:hover{color:var(--gold)}
header.top a.tel{background:transparent;color:var(--navy);border:1px solid #bfaa87;border-radius:3px;padding:9px 16px}
.lg{background:var(--gold-light);color:var(--navy)!important;border-radius:3px;padding:10px 16px;font-weight:650}
.mb{border:1px solid var(--line);border-radius:3px;color:var(--navy)}
.box{border:1px solid var(--line);border-radius:3px;box-shadow:none;padding:22px}
.tag{background:var(--tint);color:var(--navy);border-radius:2px}
.price{color:var(--navy);font-family:"Noto Serif TC","Songti TC",serif}
h2.sec{font-size:26px;text-align:left;color:var(--navy);border:0;background:none;padding:0;margin:44px 0 18px}
.chips{gap:8px;margin:14px 0}.chips button{border:1px solid #c9d4d9;border-radius:3px;color:var(--navy);padding:9px 16px;min-height:44px;transition:background .15s,color .15s}.chips button:hover{background:var(--tint)}.chips button.on{background:var(--navy);border-color:var(--navy);color:#fff}
.bar{gap:10px;margin:14px 0 8px}.bar input,.bar select{border:1px solid #cfd9de;border-radius:3px;min-height:46px;color:var(--ink)}.bar input:focus,.bar select:focus{outline:0;border-color:var(--gold)}
.bar button{border:1px solid #aebcc5;border-radius:3px;color:var(--navy);min-height:46px;padding:0 18px;transition:background .15s}.bar button:hover{background:var(--tint)}.bar #go{background:var(--navy);border-color:var(--navy);color:#fff}
#n{color:var(--muted);font-size:14px;margin:14px 0 14px}
.grid{grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:22px}
.card{border:1px solid var(--line);border-radius:3px;box-shadow:none;content-visibility:auto;contain-intrinsic-size:auto 380px;transition:transform .2s ease,box-shadow .2s ease,border-color .2s}
.card:hover{transform:translateY(-3px);box-shadow:0 10px 26px rgba(24,53,75,.10);border-color:#c9b995}
.ch{background:var(--paper);color:var(--navy);border-bottom:1px solid var(--line);font-family:inherit;font-size:13px;letter-spacing:.06em;padding:9px 10px}
.rd2{background:var(--navy);color:#fff;border-radius:2px;box-shadow:none;font-size:13px;letter-spacing:.05em;padding:4px 10px}
.card .b{padding:14px 16px 16px}.card .m{color:var(--muted);font-size:13px}.card .b h3{font-size:16px;line-height:1.55;letter-spacing:.03em}
.card .pr{border-top:1px solid var(--line);color:var(--gold)}.card .pr b{color:var(--navy);font-size:21px}
.btn{border-radius:3px;background:var(--navy)}.btn.line{background:var(--gold-light);color:var(--navy)!important}
.gb{background:var(--paper);border:1px solid var(--line);border-radius:3px}.gb .btn.line{margin:0}
.cta{border-top:1px solid var(--line)}.cta a,.cta button{border-radius:3px}.cta .l{background:var(--gold-light);color:var(--navy)}.cta .t{background:var(--navy)}
.fab a{background:var(--navy);border-radius:3px;box-shadow:0 4px 14px rgba(17,42,62,.22)}.fab a.l{background:var(--gold-light);color:var(--navy)}.fab svg{fill:#fff}
#dr .pn{background:var(--navy)}
summary{font-weight:550}details{border-bottom:1px solid var(--line)}
footer{background:var(--navy-deep);color:#9fb0bb;text-align:left;padding:30px 24px;font-size:12px;line-height:1.9}
.areas a{color:var(--navy);border-bottom:1px solid #d9c9a8;text-decoration:none;margin-right:12px}
@media(max-width:640px){main{padding:20px 16px 32px}.hd{padding:0 16px;height:68px}header.top a.logo{font-size:17px;letter-spacing:.06em}h1{font-size:24px}.grid{grid-template-columns:1fr;gap:16px}.bar input,.bar select,.bar button{font-size:16px}.chips button{font-size:15px}footer{padding:26px 16px 90px}}
header.top a.lg{font-size:14px;font-weight:650;letter-spacing:.03em}
.tg{border-radius:2px!important;font-size:12px!important;letter-spacing:.04em}.tg.l{background:var(--gold)!important}.tg.r{background:#9c3b32!important}
@media(max-width:640px){.bar{display:grid;grid-template-columns:1fr 1fr;gap:10px}.bar #q,.bar #go{grid-column:1/-1}.bar select,.bar button{width:100%;min-width:0}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.card{transition:none}}"""

ORG = {
    "@context": "https://schema.org", "@type": "RealEstateAgent", "@id": SITE + "/#org",
    "name": NAME, "alternateName": [TEAM, "104法拍網團隊"], "legalName": COMPANY, "slogan": SLOGAN, "url": SITE + "/",
    "telephone": ["+886-918-313-888", "+886-986-678-928"],
    "areaServed": "TW", "sameAs": list(LINKS.values())[1:],
    "employee": [{"@type": "Person", "name": "黃先生 Pitt", "jobTitle": "法拍代標顧問", "telephone": "+886-918-313-888"}, {"@type": "Person", "name": "林小姐 Anna", "jobTitle": "法拍代標顧問", "telephone": "+886-986-678-928"}],
    "makesOffer": [{"@type": "Offer", "name": "聲請點交", "price": "50000", "priceCurrency": "TWD"}, {"@type": "Offer", "name": "包辦點交", "price": "120000", "priceCurrency": "TWD"}, {"@type": "Offer", "name": "全程代標", "description": "2% 到 5%，300 萬元以下固定 10 萬元，超過 300 萬元至 600 萬元最低 12 萬元"}],
    "knowsAbout": ["法拍屋", "法拍屋代標", "投標諮詢", "聲請點交", "包辦點交"],
}

FAB = (f'<div class="fab"><a href="tel:0918313888" aria-label="電話諮詢"><svg width="26" height="26" viewBox="0 0 24 24" fill="#fff"><path d="M6.6 10.8c1.4 2.8 3.8 5.1 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1C10.6 21 3 13.4 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1l-2.3 2.2z"/></svg></a>'
       f'<a class="l" href="{LINKS["LINE"]}" target="_blank" rel="noopener" aria-label="LINE 諮詢">LINE</a></div>')

def contact_box():
    btn = "".join(f'<a class="btn{" line" if k=="LINE" else ""}" href="{e(v)}" target="_blank" rel="noopener">{e(k)}</a>' for k, v in LINKS.items())
    return f'''<section class="box" id="contact"><h2>聯絡我們</h2>
<p><b>黃先生 Pitt</b>　<a href="tel:0918313888">{PHONE_P}</a><br><b>林小姐 Anna</b>　<a href="tel:0986678928">{PHONE_A}</a></p>
<p>LINE@ <a href="{e(LINKS["LINE"])}" target="_blank" rel="noopener">https://lin.ee/Y2bGSIB</a>（傳「案名」或地址就能問）</p>
<p><b>{e(TEAM)}</b>｜{e(SLOGAN)}<br>全台都有服務：投標諮詢、全程代標、聲請點交／包辦點交<br>{e(COMPANY)}</p><div>{btn}</div></section>'''

def page(title, desc, path, body, jsonld=None, image=None, extra_head="", pre="", fab=True):
    url = SITE + path
    ld = "".join(f'<script type="application/ld+json">{jd(o)}</script>' for o in (jsonld or []))
    og_img = f'<meta property="og:image" content="{e(image)}"><meta name="twitter:card" content="summary_large_image">' if image else '<meta name="twitter:card" content="summary">'
    return f'''<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}"><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<meta property="og:type" content="website"><meta property="og:site_name" content="{e(NAME)}"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{e(url)}"><meta property="og:locale" content="zh_TW">{og_img}
<link rel="alternate" type="text/plain" href="{SITE}/llms.txt" title="llms.txt">{extra_head}
<style>{CSS}</style>{ld}</head><body>
<header class="top"><div class="hd"><a class="logo" href="/">Pitt &amp; Anna<i> </i>104法拍網團隊</a><nav><a href="/list">物件列表</a><a href="/list#areas">地區</a><a href="/fees">服務收費</a><a href="/#faq">常見問題</a><a href="/#contact">聯絡我們</a></nav><a class="tel" href="tel:0918313888">電話諮詢</a><a class="lg" href="https://lin.ee/Y2bGSIB" target="_blank" rel="noopener">LINE@加入</a><button class="mb" id="mb" type="button" aria-label="選單">☰</button></div></header>{DRAWER}
{pre}<main>{body}</main>
<footer>© {e(TEAM)}｜{e(COMPANY)}｜林小姐 Anna <a href="tel:0986678928">0986-678-928</a>｜黃先生 Pitt <a href="tel:0918313888">0918-313-888</a><br>物件資料來源：透明房訊，每日更新（{e(UPDATED)}），實際拍賣內容請以法院公告為準。</footer>{FAB if fab else ""}<script src="/ui.js" defer></script></body></html>'''

DRAWER = ('<div id="dr"><div class="bk"></div><div class="pn"><button class="x" type="button" id="dx">×</button><div style="clear:both"></div>'
          '<a href="/">首頁</a><a href="/list">物件列表</a><a href="/new">本週新增・降價</a><a href="/list#areas">各區法拍屋</a><a href="https://lin.ee/Y2bGSIB" target="_blank" rel="noopener">LINE@加入</a><a href="/member#ask">委託代標留言</a><a href="/fees">服務與收費</a><a href="/#faq">常見問題</a><a href="/learn">法拍小教室</a>'
          f'<a href="{LINKS["LINE 社群"]}" target="_blank" rel="noopener">加入 LINE 社群</a><a href="{LINKS["粉絲專頁"]}" target="_blank" rel="noopener">粉絲專頁</a></div></div>'
          '<script>(function(){var d=document.getElementById("dr");function t(v){d.classList.toggle("on",v)}document.getElementById("mb").onclick=function(){t(true)};document.getElementById("dx").onclick=function(){t(false)};d.querySelector(".bk").onclick=function(){t(false)};d.querySelectorAll("a").forEach(function(a){a.addEventListener("click",function(){t(false)})})})()</script>')

GATE_JS = ""   # 2026-11-25 LINE 登入停用，列表不再遮住第 13 筆以後

def member_page():
    body = ('<h1>會員專區・委託代標留言</h1>'
            '<section class="box"><h2>會員登入／註冊</h2><p>會員可收藏物件、接收每週新案通知與降價提醒。請用 LINE 加入官方好友，我們為您建立會員資料，並用 LINE 推送新案與降價提醒。</p>'
            f'<p><a class="btn line" href="{e(LINKS["LINE"])}" target="_blank" rel="noopener">LINE@加入</a><a class="btn line" href="{e(LINKS["LINE 社群"])}" target="_blank" rel="noopener">加入 LINE 社群</a> <a class="btn" href="tel:0918313888">電話洽詢 黃先生 Pitt</a></p></section>'
            '<section class="box" id="ask"><h2>委託代標・物件諮詢留言</h2><p>留下需求，我們會盡快與您聯絡。</p><form class="mf" id="mf">'
            '<label>姓名</label><input id="mn" required autocomplete="name"><label>聯絡電話</label><input id="mp" type="tel" required autocomplete="tel">'
            '<label>想了解的物件（案號／地址，可留空）</label><input id="mo"><label>需求</label><select id="mt"><option>委託代標</option><option>產權調查／不點交處理</option><option>貸款諮詢</option><option>其他</option></select>'
            '<label>預算區間／其他說明</label><textarea id="mm" rows="4"></textarea><p><button class="btn line" type="submit" style="border:0;cursor:pointer">送出並開啟 LINE</button></p></form></section>'
            f'<script>document.getElementById("mf").onsubmit=function(ev){{ev.preventDefault();var g=function(i){{return document.getElementById(i).value}};var t="【委託留言】\\n姓名："+g("mn")+"\\n電話："+g("mp")+"\\n物件："+g("mo")+"\\n需求："+g("mt")+"\\n說明："+g("mm");try{{navigator.clipboard.writeText(t)}}catch(e){{}};alert("內容已複製，請在 LINE 貼上送出，我們會盡快回覆您。");window.open({jd(LINKS["LINE"])},"_blank")}}</script>')
    return page("會員登入・委託代標留言｜" + NAME, "透明房訊會員專區與法拍屋委託代標留言，專人回覆。", "/member", body)

def card(x):
    ph = photos(x)
    inf = x.get("資訊", {})
    r = round_of(x)
    dv = deliver_of(x)
    badge = f'<span class="rd2">{e("｜".join(filter(None, [YING if is_ying(x) else ("第%d拍" % r) if r else "拍次洽詢", dv])))}</span>'
    img = f'<img loading="lazy" src="{e(ph[0])}" alt="{e(x["地址"])} 法拍屋照片"{img_fb(ph)}>' if ph else '<div class="noimg">照片請洽業務</div>'
    price = re.sub(r"^售", "", x["價格"])
    old = f'<s>{e(re.sub(r"^售", "", x["原價"]))}</s>' if x["原價"] else ""
    top = "｜".join(filter(None, ["先買先贏" if is_ying(x) else inf.get("開標日期", ""), x["狀態"], "新上架" if _within(x.get("新增日", "")) else "", "降價" if _within(x.get("異動日", "")) and x.get("降價前", 0) else ""]))
    text = f'{inf.get("完整地址","")} {x["地址"]} {x["區域"]} {x["類型"]} {inf.get("案號","")}'
    return (f'<a class="card" href="/h/{e(x["編號"])}" data-t="{e(text)}" data-c="{e(area_of(x)[:2])}" data-a="{e(area_of(x))}" data-y="{e(x["類型"])}" data-p="{price_num(x["價格"])}" data-r="{r}" data-d="{date_key(x)}" data-j="{e(dv)}" data-f="{first_price(x)}">'
            f'<div class="ch">{e(top)}</div><div class="cv">{img}{badge}</div>'
            f'<div class="b"><div class="m">{e(x["類型"])}｜{e(x["格局坪數"])}</div><h3>{e(x["地址"] if "號" in x["地址"] else inf.get("完整地址") or x["地址"])}</h3>'
            f'<div class="pr"><span>底價</span><b>{old}{e(price)}</b></div></div></a>')

def kv(rows):
    rows = [(k, v) for k, v in rows if v]
    return "<table>" + "".join(f"<tr><td>{e(k)}</td><td>{e(v)}</td></tr>" for k, v in rows) + "</table>" if rows else ""

_HAUNT_W = re.compile(r"非自然死亡|凶宅|兇宅|自殺|他殺|命案")

def _haunt_lines(notes):
    """筆錄中提到非自然死亡等字眼的「整句」（法院制式說明常寫『並無發生非自然死亡』，只截片段會誤導）。"""
    out = []
    for s in re.split(r"[。●\n]", notes or ""):
        s = s.strip()
        if _HAUNT_W.search(s) and s not in out:
            out.append(s[:160] + ("…" if len(s) > 160 else ""))
    return out[:2]

# 2026-11-24：否定句、制式提醒不算有記載。只有「曾有人自殺身亡」「疑似凶宅」這種明確肯定的句子才算
_HAUNT_NEG = re.compile(r"並無|查無|未查|未發生|未有|無發生|未曾發生|未發現|未曾|沒有|不曾|非屬|是否|有無|尚無|均無|否認|未表示|未查報|並不清楚|無從|如有|請投標人|應自行查明|自行查明|已儘量|使用情形欄|無上開|無上列|非凶宅|非兇宅|(?<![非])無[^，；]{0,40}(非自然死亡|凶宅|兇宅|自殺|他殺|命案)")
_HAUNT_POS = re.compile(r"(曾|發生|疑似|確有|係|屬|為)[^，；]{0,10}(凶宅|兇宅|自殺|他殺|命案|非自然死亡)|自殺身亡|死亡事故")

def _haunt_positive(notes):
    """筆錄裡「肯定」提到非自然死亡等事件的句子；全是否定句或制式提醒就回傳空清單"""
    out = []
    for s in _haunt_lines_all(notes):
        for c in re.split(r"[，；]", s):   # 逐小句判斷：小句有明確肯定字眼、且同一小句沒有否定或制式提醒，才算
            if _HAUNT_W.search(c) and _HAUNT_POS.search(c) and not _HAUNT_NEG.search(c): out.append(s); break
    return out

def _haunt_lines_all(notes):
    out = []
    for s in re.split(r"[。●\n]", notes or ""):
        s = s.strip()
        if _HAUNT_W.search(s) and s not in out: out.append(s)
    return out

def verify_box(addr, notes):
    """凶宅與點交查證：只寫筆錄裡有的字，查不到就照實說查不到。"""
    m = re.search(r"點交情形→([^●\n]+)", notes or "")
    dv = m.group(1).strip()[:120] if m else ""
    pos = _haunt_positive(notes)   # 2026-11-25 Anna：只有筆錄肯定記載才顯示這一列；否定句（載明無）不算
    rows = [("點交", f"法院筆錄記載：{dv}" if dv else "筆錄未載明點交情形，以法院拍賣公告為準。")]
    if pos: rows.append(("非自然死亡", "筆錄原文：" + "／".join(s[:160] for s in pos[:2])))
    rows.append(("查證依據", f"法院筆錄與拍賣公告（資料更新 {UPDATED}）；以法院最新公告為準。"))
    return (f'<section class="box" id="verify"><h2>{e(addr)}{"凶宅與點交查證" if pos else "點交查證"}</h2>' + kv(rows)
            + '</section>')   # 11/24 Anna：拿掉台灣凶宅網等外站連結

def map_query(x):
    """給 Google 地圖的乾淨地址：縣市＋行政區＋路名門牌（到「號」為止）。案名裡的「法拍屋｜坪數｜底價」、社區名都不送，避免比對到同名商家"""
    q = (x.get("資訊") or {}).get("完整地址") or ""
    if not q:
        a = re.sub(r"【[^】]*】", "", x.get("地址") or "").strip()
        a = a.split()[-1] if a.split() else a
        a = a.split("｜")[-1]
        area = area_of(x); c2, dist = area[:2], area[2:]
        city = {"新竹": "新竹市" if dist.endswith("區") else "新竹縣", "嘉義": "嘉義市" if dist.endswith("區") else "嘉義縣"}.get(c2) or _CITY_FULL.get(c2, c2)
        a = re.sub(r"^.{1,3}?[市縣](?=.{1,3}?[區鄉鎮市])", "", a)
        if dist and a.startswith(dist): a = a[len(dist):]
        q = city + dist + a
    m = re.match(r"(.*?\d+(?:[-之]\d+)?號)", q)
    return m.group(1) if m else q

def countdown(x):
    if is_ying(x):
        return '<p class="cd"><b>公告應買・先買先贏</b>（應買期間與條件以法院公告為準）</p>'
    od = _open_date(x)
    if not od: return ""
    return (f'<p class="cd" data-open="{od}">開標日期 {e(x["資訊"].get("開標日期", ""))}</p>'
            '<script>(function(){var p=document.querySelector(".cd");if(!p)return;var n=Math.ceil((new Date(p.dataset.open+"T00:00:00+08:00")-Date.now())/864e5);'
            'var t=n>1?"還有 "+n+" 天開標":n===1?"明天開標":n===0?"今天開標":"";if(t)p.innerHTML+="<b>"+t+"</b>"})()</script>')

def city_of(x):
    """物件所屬的縣市專區（CITIES 的一筆）；沒有專區時回傳 None"""
    return next((c for c in CITIES if c[0] != "greater-taipei" and area_of(x)[:2] in c[2]), None)

def community_of(x):
    """社區名：只用來源資料的「社區/大樓」欄（去掉括號裡的建商名）；不從案名的【】猜，那裡常是「頂加」「一樓」「捷運站」"""
    v = re.sub(r"[（(].*$", "", ((x.get("資訊") or {}).get("社區/大樓") or "")).strip()
    return v if len(v) >= 2 and v not in ("無社區", "不詳") else ""

def _comm(x): return community_of(x)
def _safe(s): return re.sub(r'[\\/:*?"<>|\s#%&.]', "", s or "")
def comm_key(x):
    c = community_of(x)
    return f"{area_of(x)[:2]}-{_safe(c)}" if c else ""

_CG = None
def community_groups():
    """社區頁的資料：同縣市同社區的現有物件＋近半年下架的；合計 2 件以上才做頁面，避免內容太薄"""
    global _CG
    if _CG is not None: return _CG
    g = {}
    for x in ITEMS:
        c = community_of(x)
        if c: g.setdefault(comm_key(x), {"name": c, "city": area_of(x)[:2], "cur": [], "past": []})["cur"].append(x)
    try: seen = json.load(open("data/seen.json", encoding="utf-8"))
    except Exception: seen = {}
    cur_ids = {x["編號"] for x in ITEMS}
    for k, v in seen.items():
        if k in cur_ids or not v.get("gone") or not v.get("addr") or v.get("twin") in cur_ids: continue
        try:
            if (_today() - datetime.date.fromisoformat(v["gone"])).days > 180: continue
        except ValueError: continue
        city = v.get("area", "")[:2]
        if v.get("comm"):
            g.setdefault(f"{city}-{_safe(v['comm'])}", {"name": v["comm"], "city": city, "cur": [], "past": []})["past"].append((k, v)); continue
        for grp in g.values():   # 舊紀錄沒存社區名：案名裡有寫到同縣市的社區名才算
            if grp["city"] == city and len(grp["name"]) >= 3 and grp["name"] in v["addr"]: grp["past"].append((k, v)); break
    _CG = {k: v for k, v in g.items() if k and len(v["cur"]) + len(v["past"]) >= 2}
    return _CG

def comm_links(pred, title):
    """某縣市或行政區裡有社區頁的社區連結"""
    gs = [(k, v) for k, v in community_groups().items() if pred(v)]
    if not gs: return ""
    gs.sort(key=lambda t: (-len(t[1]["cur"]), t[1]["name"]))
    return (f'<section class="box areas"><h2>{e(title)}</h2>' + "".join(f'<a href="/c/{slug(k)}">{e(v["name"])}法拍屋（{len(v["cur"])}）</a>' for k, v in gs[:40]) + '</section>')

def community_page(key, g):
    name, cur, past = g["name"], g["cur"], g["past"]
    cur = sorted(cur, key=date_key)
    areas = sorted({area_of(x) for x in cur} | {v.get("area", "").split("-")[0] for _, v in past if v.get("area")})
    a0 = areas[0] if areas else g["city"]
    t = _today(); today = (t.year - 1911) * 10000 + t.month * 100 + t.day
    md = lambda x: "/".join(str(int(v)) for v in x["資訊"]["開標日期"].split("/")[1:])
    up = [x for x in cur if today <= date_key(x) < 99999999]
    ps = sorted(p for p in (price_num(x["價格"]) for x in cur) if p > 0)
    if cur:
        title = f"{name}法拍屋｜{a0}{len(cur)}件" + (f"・最近{md(up[0])}開標" if up else "") + f"｜{NAME}"
        intro = (f"{name}（{a0}）目前有 {len(cur)} 件法拍物件" + (f"，底價 {wan(ps[0])}～{wan(ps[-1])}" if ps else "") + (f"，最近一場 {md(up[0])} 開標" if up else "")
                 + (f"；近半年另有 {len(past)} 件已下架（拍定、停拍或撤回）" if past else "") + f"。資料每日更新（{UPDATED}），拍次與底價以法院最新公告為準。")
    else:
        title = f"{name}法拍屋｜{a0}近期拍賣紀錄｜{NAME}"
        intro = f"{name}（{a0}）目前沒有待拍的法拍物件；近半年有 {len(past)} 件已下架（拍定、停拍或撤回，實際結果以法院公告為準）。有新的拍賣公告時本頁會自動更新（{UPDATED}）。"
    vrows = ""
    for x in cur:
        inf = x.get("資訊", {}); notes = inf.get("筆錄", "")
        m = re.search(r"點交情形→([^●\n]+)", notes); h = _haunt_lines(notes)
        vrows += (f'<tr><td><a href="/h/{e(x["編號"])}">{e(inf.get("完整地址") or x["地址"])}</a></td><td>{e(("第%d拍" % round_of(x)) if round_of(x) else "")} {e(inf.get("開標日期", ""))}</td>'
                  f'<td>{e(re.sub(r"^售", "", x["價格"]))}</td><td>{e(m.group(1).strip()[:60] if m else "筆錄未載明")}</td><td>{e(("筆錄原文：" + "／".join(h)) if h else ("法院筆錄未提到非自然死亡" if notes else "沒有筆錄資料"))}</td></tr>')
    vsec = ""   # 2026-11-25 Anna：不另外整理凶宅、點交判斷，以物件頁的法院筆錄全文為準
    prow = "".join(f'<tr><td>{e(v.get("gone", ""))}</td><td><a href="/h/{e(k)}">{e(v.get("addr", ""))}</a></td><td>{e(("第%s拍" % v["rd"]) if v.get("rd") else "")}</td><td>{e(re.sub(r"^售", "", v.get("ptxt", "")))}</td></tr>'
                   for k, v in sorted(past, key=lambda t: t[1].get("gone", ""), reverse=True))
    psec = (f'<section class="box"><h2>{e(name)}近半年已下架的法拍物件</h2><table class="tbl"><tr><th>下架日期</th><th>物件</th><th>最後拍次</th><th>最後底價</th></tr>{prow}</table>'
            '<p class="note">下架可能是拍定、停拍或撤回，實際結果請以法院公告為準。</p></section>') if past else ""
    cc = next((c for c in CITIES if c[0] != "greater-taipei" and g["city"] in c[2]), None)
    links = "".join(f'<a href="/area/{slug(a)}">{e(a)}法拍屋</a>' for a in areas) + (f'<a href="/{cc[0]}">{e(cc[3])}</a>' if cc else "")
    body = (f'<nav class="bc"><a href="/">首頁</a> › ' + (f'<a href="/{cc[0]}">{e(cc[3])}</a> › ' if cc else "") + f'{e(name)}法拍屋</nav>'
            f'<h1>{e(name)}法拍屋｜{e(a0)}（{len(cur)}件）</h1><p>{e(intro)}</p>'
            + (f'<h2>{e(name)}法拍物件</h2><div class="grid">{"".join(card(x) for x in cur)}</div>' if cur else "") + vsec + psec
            + f'<section class="box areas"><h2>附近法拍屋</h2>{links}</section>' + contact_box())
    desc = intro[:150]
    ld = [ORG, {"@context": "https://schema.org", "@type": "CollectionPage", "name": f"{name}法拍屋", "url": f"{SITE}/c/{slug(key)}", "description": desc, "inLanguage": "zh-TW", "dateModified": UPDATED.replace(" ", "T") + ":00+08:00"},
          {"@context": "https://schema.org", "@type": "ItemList", "name": f"{name}法拍屋", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f'{SITE}/h/{x["編號"]}', "name": x["地址"]} for i, x in enumerate(cur)]},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": ([{"@type": "ListItem", "position": 1, "name": "首頁", "item": SITE + "/"}]
              + ([{"@type": "ListItem", "position": 2, "name": cc[3], "item": f"{SITE}/{cc[0]}"}] if cc else []) + [{"@type": "ListItem", "position": 3 if cc else 2, "name": f"{name}法拍屋"}])}]
    return page(title, desc, f"/c/{slug(key)}", body, ld, SITE + "/og.jpg")
def _road(x):
    a = re.sub(r"^.{2,3}?[市縣].{1,3}?[區鄉鎮市]", "", (x.get("資訊") or {}).get("完整地址") or "")
    m = re.match(r"([^\d]{1,8}?(?:路|街|大道)(?:[一二三四五六七八九十]段)?)", a)
    return m.group(1) if m else ""

_IDX = {}
def related_box(x, comm, area):
    """相關物件（內部連結）：同社區 → 同路段 → 同區同類型 → 同區，最多 6 筆，並附區、縣市、類型專區連結"""
    rd, ty = _road(x), x.get("類型", "")
    if not _IDX:   # 一次建好索引，避免每頁掃全部物件
        for y in ITEMS:
            a = area_of(y)
            for key in (("c", a[:2], _comm(y)), ("r", a, _road(y)), ("t", a, y.get("類型")), ("a", a)):
                if all(key): _IDX.setdefault(key, []).append(y)
    pools = [("同社區", _IDX.get(("c", area[:2], comm), []) if comm else []),
             ("同路段", _IDX.get(("r", area, rd), []) if rd else []),
             ("同區同類型", _IDX.get(("t", area, ty), [])),
             ("同區", _IDX.get(("a", area), []))]
    out, why = [], {}
    for lab, ys in pools:
        for y in ys:
            if y is x or y in out or len(out) >= 6: continue
            out.append(y); why[lab] = why.get(lab, 0) + 1
    cc = city_of(x)
    links = [f'<a href="/area/{slug(area)}">{e(area)}全部法拍屋</a>']
    ck = comm_key(x)
    if ck in community_groups(): links.insert(0, f'<a href="/c/{slug(ck)}">{e(comm)}法拍屋整理</a>')
    if cc:
        links.append(f'<a href="/{cc[0]}">{e(cc[3])}</a>')
        t = next((t for t in TYPES if t[2] in ty and len(type_items(cc, t[2])) >= 3), None)
        if t: links.append(f'<a href="/{cc[0]}-{t[0]}">{e(cc[1] + t[1])}法拍屋</a>')
    head = "附近與相似物件" + (f'（{"、".join(f"{k}{v}筆" for k, v in why.items())}）' if why else "")
    grid = ('<div class="grid">' + "".join(card(y) for y in out) + "</div>") if out else ""
    return f'<section class="box"><h2>{e(head)}</h2>{grid}<p class="areas">{"".join(links)}</p></section>'

def utm(path, source, medium="", campaign="", content=""):
    """各管道連結統一加 UTM：source 用 fb_group、fb_page、marketplace、youtube、line、591、ho（對照表在 部門建議／各管道連結_UTM對照表.md）"""
    q = urllib.parse.urlencode([(k, v) for k, v in (("utm_source", source), ("utm_medium", medium), ("utm_campaign", campaign), ("utm_content", content)) if v])
    return SITE + path + ("&" if "?" in path else "?") + q

def detail_page(x):
    inf = dict(x.get("資訊", {}))
    notes, sched = inf.pop("筆錄", ""), inf.pop("拍賣紀錄", "")
    ph = photos(x)
    area = area_of(x)
    addr = inf.get("完整地址") or x["地址"]
    comm = community_of(x)
    # 2026-11-19：拿掉每頁都一樣的「凶宅點交查證」（770 頁同一句像套版關鍵字）；標題只放社區名＋法拍屋＋地址
    # 2026-11-17 Anna：免費曝光先做。標題、H1、內文都要有「社區名＋法拍屋＋區＋路名」，搜社區名才找得到
    dist, rd = (area[2:] or area), _road(x)
    loc = addr if dist in addr else f"{dist}{rd}｜{addr}"
    full_title = (f'{comm}法拍屋｜{loc}｜{NAME}' if comm else f'{loc}法拍屋｜{x["類型"]}｜{NAME}')
    h1 = (f"{comm}法拍屋｜{dist}{rd}" if rd else f"{comm}法拍屋｜{addr}") if comm else f"{addr}法拍屋"
    lead = ((f"{comm}法拍屋，位於{dist}{rd}" if comm else f"{dist}{rd}法拍屋") + f"，門牌 {addr}，{x['類型']}"
            + (f"，第{inf['拍次']}拍" if inf.get("拍次") else "") + (f"，開標日期 {inf['開標日期']}" if inf.get("開標日期") else "")
            + "。以下整理法院公告的拍賣紀錄、筆錄與點交情形，實際內容以法院公告為準。") if (comm or rd) else ""
    _dv = deliver_of(x)
    vline = ((f"點交情形：{_dv}。" if _dv in ("點交", "不點交") else ""))
    desc = (f'{comm}法拍屋，' if comm else "") + (f'{addr}法拍屋，{area}{x["類型"]}，{x["地址"]}，{x["格局坪數"]}，{x["價格"]}。'
            + (f'案號{inf["案號"]}，' if inf.get("案號") else "") + (f'第{inf["拍次"]}拍，' if inf.get("拍次") else "")
            + (f'開標日期{inf["開標日期"]}。' if inf.get("開標日期") else "") + vline + "提供代標、產權調查、貸款諮詢。")
    gal = ('<div class="gal">' + "".join(f'<img {"fetchpriority=high " if i==0 else "loading=lazy "}src="{e(u)}" alt="{e((comm + " ") if comm else "")}{e(addr)} 法拍屋照片{i+1}" onerror="this.remove()">' for i, u in enumerate(ph)) + "</div>") if ph else '<div class="noimg">照片請洽業務</div>'
    pr = (f'<s>{e(x["原價"])}</s>' if x["原價"] else "") + e(x["價格"])
    tags = f'<span class="tag">{e(x["狀態"])}</span>' + (f'<span class="tag">第{e(inf["拍次"])}拍</span>' if inf.get("拍次") else "") + (f'<span class="tag">開標 {e(inf["開標日期"])}</span>' if inf.get("開標日期") else "")
    top = kv([("案號", inf.get("案號")), ("類型", x["類型"]), ("總登記坪數", inf.get("總登記坪數")), ("每坪單價", inf.get("每坪單價")), ("地址", addr), ("案名", x["地址"] if x["地址"] != addr else ""), ("地區", re.sub(r"-0房$", "", x["區域"])), ("物件編號", x["編號"])])
    det = kv([(k, inf.get(k)) for k in DETAIL_KEYS])
    size = kv([(k, (inf.get(k) + "坪") if inf.get(k) and re.fullmatch(r"[\d.]+", inf.get(k)) else inf.get(k)) for k in SIZE_KEYS])
    srows = ""
    if sched:
        rows = []
        for ln in sched.split("\n"):
            m = re.match(r"(第.{1,2}拍)\s*([\d/]+)?\s*底標價[：:]\s*(.+)", ln)
            rows.append(f"<tr><td>{e(m.group(1))}</td><td>{e(m.group(2) or '')}</td><td>{e(m.group(3))}</td></tr>" if m else f'<tr><td colspan="3">{e(ln)}</td></tr>')
        srows = '<section class="box"><h2>拍賣紀錄（拍次／拍賣日期／底標價）</h2><table><tr><th>拍次</th><th>日期（月/日）</th><th>底標價</th></tr>' + "".join(rows) + "</table></section>"
    nsec = f'<section class="box"><h2>法院筆錄</h2><div class="notes">{e(notes)}</div></section>' if notes else ""
    sim = related_box(x, comm, area)
    cc = city_of(x)
    body = (f'<nav class="bc"><a href="/">首頁</a> › ' + (f'<a href="/{cc[0]}">{e(cc[3])}</a> › ' if cc else "") + f'<a href="/area/{slug(area)}">{e(area)}法拍屋</a> › {e(x["類型"])}</nav>'
            f'<section class="box"><h1>{e(h1)}</h1><p>{e(x["地址"])}</p>' + (f'<p>{e(lead)}</p>' if lead else "") + f'<div>{tags}</div>{countdown(x)}<div class="price">{pr}</div>{gal}</section>'
            f'<section class="box" id="tools" data-price="{price_num(x["價格"])}" data-addr="{e(x["地址"])}" data-map="{e(map_query(x))}" data-id="{e(x["編號"])}"></section>'
            f'<section class="box"><h2>物件資料</h2>{top}</section>'
            + (f'<section class="box"><h2>詳細資料</h2>{det}</section>' if det else "")
            + (f'<section class="box"><h2>坪數說明</h2>{size}</section>' if size else "") + srows + nsec + contact_box() + sim)
    ld = [ORG,
          {"@context": "https://schema.org", "@type": "RealEstateListing", "name": (f"{comm}法拍屋｜{addr}" if comm else f"{addr}法拍屋"), "url": f'{SITE}/h/{x["編號"]}', "description": desc,
           "image": ph[:6] or None, "dateModified": UPDATED.replace(" ", "T") + ":00+08:00",
           "offers": {"@type": "Offer", "price": price_num(x["價格"]), "priceCurrency": "TWD", "availability": "https://schema.org/InStock", "seller": {"@id": SITE + "/#org"}},
           "about": {"@type": "Place", "name": addr, "address": {"@type": "PostalAddress", "streetAddress": addr, "addressCountry": "TW"}}},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "首頁", "item": SITE + "/"},
              {"@type": "ListItem", "position": 2, "name": area + "法拍屋", "item": f"{SITE}/area/{slug(area)}"},
              {"@type": "ListItem", "position": 3, "name": addr}]}]
    if cc:   # 麵包屑加縣市層：首頁 › 縣市法拍屋 › 行政區法拍屋 › 物件
        bl = ld[-1]["itemListElement"]
        bl.insert(1, {"@type": "ListItem", "position": 2, "name": cc[3], "item": f"{SITE}/{cc[0]}"})
        for i, it in enumerate(bl, 1): it["position"] = i
    for o in ld:
        for k in [k for k, v in o.items() if v is None]: del o[k]
    ask = f'我對物件 {x["編號"]}（{x["地址"]}）有興趣，想了解代標與細節。'
    cta = (f'<div class="cta"><button class="l" id="ask" type="button">LINE 詢問此物件</button><a class="t" href="tel:0918313888">打電話</a></div>'
           f'<script>document.getElementById("ask").onclick=function(){{var b=this,t={jd(ask)},s="";try{{s=sessionStorage.getItem("tm_src")||""}}catch(e){{}};if(s)t+="（來源:"+s+"）";try{{navigator.clipboard.writeText(t)}}catch(e){{}};b.textContent="已複製詢問文字，開啟 LINE…";setTimeout(function(){{window.open({jd(LINKS["LINE"])},"_blank");b.textContent="LINE 詢問此物件"}},500)}};</script>')
    return page(full_title, desc, f'/h/{x["編號"]}', body + team3_box() + cta, ld, ph[0] if ph else None, "<style>footer{padding-bottom:90px}</style>", "", False)

FAQ = [
    ("什麼是法拍屋的「點交」與「不點交」？", "點交是指拍定後，由法院協助將房屋點交給得標人；不點交則需得標人自行處理占用問題。各物件是否點交，請見該物件的「法院筆錄」與執行公告。"),
    ("法拍屋的「拍次」是什麼意思？", "拍次是法院拍賣的次數。第一拍無人應買（流標）後，法院通常會減價再拍，實際底價與日期以各物件「拍賣紀錄」及法院公告為準。"),
    ("可以委託代標嗎？需要準備什麼？", "可以。Pitt & Anna｜104法拍網團隊全台都有服務，提供投標諮詢、全程代標、聲請點交／包辦點交，請透過電話或 LINE@ 聯絡黃先生 Pitt 或林小姐 Anna。"),
    ("法拍屋可以看屋嗎？", "一般法拍屋查封後無法入內參觀，可依建物平面圖推斷格局，或參考同棟樓上樓下。能看屋的物件會在資料中另行註明。"),
    ("代標服務費怎麼算？", "全程代標收取 2% 到 5%（300 萬元以下固定 10 萬元；超過 300 萬元至 600 萬元最低 12 萬元）；只需聲請點交為 50,000 元，包辦點交為 120,000 元。服務項目與附註請見「服務與收費」頁。"),
    ("法拍屋得標後多久能交屋？", "點交物件走司法程序，一般約 4 至 6 個月，有狀況會順延；不點交物件則取決於與占用人的協商，時間較難預估。"),
    ("投標保證金不夠或忘記附本票會怎樣？", "保證金未繳足、未附本票，或本票、印章有瑕疵，投標會被判為無效。投標前請逐項核對拍賣公告。"),
    ("得標後要在多久內繳尾款？可以貸款嗎？", "得標後通常需在 7 天內繳清價金。需要貸款或代墊尾款，請在投標前先告知，讓我們協助準備銀行徵信資料。"),
    ("本站資料多久更新一次？", "每天早上自動更新一次物件價格、拍次與開標日期，實際內容請以法院公告為準。"),
]

def _today():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date()

def _within(d, days=7):
    try: return 0 <= (_today() - datetime.date.fromisoformat(d)).days <= days
    except Exception: return False

def new_items(): return [x for x in ITEMS if _within(x.get("新增日", ""))]
def changed_items(): return [x for x in ITEMS if _within(x.get("異動日", ""))]
def _rank(x): return {"台北": 0, "新北": 1, "桃園": 2}.get(x["區域"][:2], 3)

def drafts():
    pool = sorted(upcoming(14), key=lambda x: (_rank(x), date_key(x)))[:5]
    if not pool: pool = sorted([x for x in ITEMS if round_of(x) >= 3], key=lambda x: (_rank(x), price_num(x["價格"])))[:5]
    nw = len(new_items())
    fb = ["【本週開標・精選法拍屋】", ""]
    ln = ["📢 本週法拍精選", ""]
    for i, x in enumerate(pool, 1):
        inf = x.get("資訊", {})
        r = round_of(x)
        desc = f'第{r}拍｜開標 {inf.get("開標日期", "")}｜底價 {re.sub(r"^售", "", x["價格"])}'
        link = f'{SITE}/h/{x["編號"]}'
        fb += [f'{i}. {area_of(x)}｜{x["地址"]}', f'   {desc}', f'   👉 {utm(link[len(SITE):], "fb_page", "social", "weekly_" + f"{_today():%Y%m}", x["編號"])}', ""]
        ln += [f'{i}. {area_of(x)} {x["地址"]}', f'   {desc}', f'   {utm(link[len(SITE):], "line", "message", "weekly_" + f"{_today():%Y%m}", x["編號"])}', ""]
    if nw:
        fb.append(f'本週新增 {nw} 筆物件，完整清單看網站 ↓')
        ln.append(f'本週新增 {nw} 筆，完整清單：')
    fb += [f'{SITE}/?utm_source=fb', "", "想了解代標、產權調查與貸款，歡迎私訊或來電 黃先生 Pitt 0918-313-888、林小姐 Anna 0986-678-928 😊", "", "#法拍屋 #法拍 #法拍屋代標 #透明房訊 #104法拍網"]
    ln += [f'{SITE}/?utm_source=line', "", "有興趣請直接回覆，或聯絡 黃先生 Pitt 0918-313-888、林小姐 Anna 0986-678-928"]
    return "\n".join(fb), "\n".join(ln)

def post_page():
    fb, ln = drafts()
    box = lambda i, t, txt: (f'<section class="box"><h2>{t}</h2><textarea id="{i}" rows="14" style="width:100%;font-size:15px;padding:10px;border:1px solid #ccc;border-radius:6px">{e(txt)}</textarea>'
                             f'<button class="btn" type="button" onclick="var t=document.getElementById(\'{i}\');t.select();try{{navigator.clipboard.writeText(t.value)}}catch(e){{document.execCommand(\'copy\')}};this.textContent=\'已複製\'">複製貼文</button></section>')
    body = ('<h1>本週貼文草稿</h1><p>每天早上自動更新。按「複製貼文」後，貼到粉絲專頁或 LINE 社群即可發佈。（此頁不會被搜尋引擎收錄）</p>'
            + box("fb", "粉絲專頁貼文", fb) + box("ln", "LINE 社群推播", ln))
    return page("貼文草稿｜" + NAME, "本週貼文草稿", "/post", body, None, None, "", "", False).replace("index,follow", "noindex,nofollow")

def hero_banner():
    import random
    rnd = random.Random(7)
    rects, x = [], -10
    while x < 1200:
        w = rnd.randint(28, 52); h = rnd.randint(70, 230)
        rects.append(f'<rect x="{x}" y="{300 - h}" width="{w}" height="{h}" fill="#fff" opacity="{rnd.choice([0.04, 0.06, 0.08, 0.1])}"/>')
        x += w + rnd.randint(3, 10)
    roof = '<path d="M880 250 L960 180 L1040 250 M900 250 V300 M1020 250 V300" fill="none" stroke="#d9b97a" stroke-width="3" opacity=".55"/>'
    svg = f'<svg class="sky" viewBox="0 0 1200 300" preserveAspectRatio="xMidYMax slice" aria-hidden="true">{"".join(rects)}{roof}</svg>'
    return (f'<section class="hero2">{svg}<div class="hin"><img class="tm" src="/brand/team1.jpg" alt="黃先生 Pitt 與林小姐 Anna 夫妻雙人法拍代標顧問" width="582" height="800" onerror="this.remove()"><p class="eyebrow">透明房訊｜法拍屋查詢與代標</p><h1>法拍怕踩雷？<br>專業代標，幫你標到對的房子</h1>'
            f'<p class="sub">兩個人把關，查得清、標得穩</p>'
            f'<div class="cta2"><a class="b1" href="#list">瀏覽全部物件</a><a class="b2" href="{e(LINKS["LINE"])}" target="_blank" rel="noopener">LINE 諮詢</a></div>'
            f'<div class="stats"><span><b>{len(ITEMS)}</b>筆物件</span><span><b>每日</b>更新</span></div>'
            f'<div class="qk">' + "".join(f'<button type="button" data-c="{e(c)}">{e(c)}</button>' for c, _ in _city_counts()) + '<button type="button" data-r="3+">第3拍以上</button></div></div></section>')

def carousel(title, xs, href, cap=12, auto=False):
    """橫向滑動卡片（一次一張，底下圓點，最後 more 按鈕）"""
    if not xs: return ""
    slides = ""
    for x in xs[:cap]:
        ph = photos(x); inf = x.get("資訊", {}); r = round_of(x); dv = deliver_of(x)
        img = f'<img loading="lazy" src="{e(ph[0])}" alt="{e(x["地址"])} 法拍屋照片"{img_fb(ph)}>' if ph else '<div class="noimg">照片請洽業務</div>'
        tag = "｜".join(filter(None, [YING if is_ying(x) else ("%d拍" % r) if r else "", dv]))
        top = "｜".join(filter(None, ["先買先贏" if is_ying(x) else inf.get("開標日期", ""), x.get("狀態", "")]))
        sub = "｜".join(filter(None, [x.get("類型", ""), inf.get("總登記坪數", "") or x.get("格局坪數", "")]))
        slides += (f'<a class="crs" href="/h/{e(x["編號"])}"><div class="crh">{e(top)}</div><div class="cri">{img}<span class="crtg">{e(tag)}</span></div>'
                   f'<div class="crb"><div class="crct">{e(sub)}</div><div class="crn">{e(x["地址"])}</div><div class="crp"><span>底價</span><b>{e(re.sub("^售", "", x["價格"]))}</b></div></div></a>')
    return (f'<h2 class="sec">{e(title)}（{len(xs)}筆）</h2><div class="cr" data-cr{" data-auto" if auto else ""}><div class="crt">{slides}</div><div class="crdots"></div></div>'
            f'<p class="crmw"><a class="crmore" href="{href}">more</a></p>')

def featured_items():
    t = _today(); tk = (t.year - 1911) * 10000 + t.month * 100 + t.day
    xs = [x for x in ITEMS if (_age(x) is not None and _age(x) <= 10) and date_key(x) >= tk and "撤" not in x.get("狀態", "")]
    return sorted(xs, key=lambda x: (date_key(x), _age(x)))

def gone_entries():
    """近 7 天從列表消失的物件（拍定／停拍／撤回；結果以法院公告為準）"""
    try: seen = json.load(open("data/seen.json", encoding="utf-8"))
    except Exception: return []
    out = [v for v in seen.values() if v.get("gone") and v.get("addr") and _within(v["gone"])]
    return sorted(out, key=lambda v: v["gone"], reverse=True)

def gone_carousel(title, es, cap=12):
    if not es: return ""
    slides = ""
    for v in es[:cap]:
        rd = v.get("rd", ""); sub = "｜".join(filter(None, [(v.get("area", "").split("-")[0]), ("最後拍次 %s拍" % rd) if rd else ""]))
        slides += (f'<div class="crs"><div class="crh">{e(v["gone"])}｜已下架</div><div class="crb"><div class="crct">{e(sub)}</div><div class="crn">{e(v["addr"])}</div>'
                   f'<div class="crp"><span>最後底價</span><b>{e(re.sub("^售", "", v.get("ptxt", "")))}</b></div></div></div>')
    return (f'<h2 class="sec">{e(title)}（{len(es)}筆）</h2><div class="cr" data-cr><div class="crt">{slides}</div><div class="crdots"></div></div>'
            '<p class="note">物件從列表下架，可能是拍定、停拍或撤回，實際結果請以法院公告為準，歡迎來電詢問。</p>')

def results_items():
    """近 7 天（含之後日期）的拍定／停拍／撤回等開標結果；資料來自法院公告彙整"""
    xs = []
    for f in ("data/results.json", "data/results_tyd.json"):   # 雙北（toro591）＋桃園（透明房訊公開頁），每日自動更新
        try: xs += json.load(open(f, encoding="utf-8"))["items"]
        except Exception: pass
    if not xs: return []
    # 桃園流標很多（多為土地）：只保留本站有上架的物件；拍定／停拍／撤回全部保留
    site = [re.sub(r"[\s　]", "", x["地址"]) for x in ITEMS]
    def on_site(x):
        m = re.search(r"([\u4e00-\u9fff]+(?:路|街|道)[^號]*號)", x.get("addr", ""))
        k = m[1] if m else ""
        k = re.sub(r"^.*?[區鄉鎮市](?=.{2,}[路街道])", "", k) if k else ""
        return bool(k) and any(k in a for a in site)
    xs = [x for x in xs if x.get("status") != "流標" or on_site(x)]
    t = _today(); keep = []
    for x in xs:
        m = re.match(r"(\d+)/(\d+)/(\d+)", x.get("date", ""))
        if not m: continue
        try: d = datetime.date(int(m[1]) + 1911, int(m[2]), int(m[3]))
        except ValueError: continue
        if (t - d).days <= 7: keep.append((d, x))
    return [x for d, x in sorted(keep, key=lambda z: z[0], reverse=True)]

def results_carousel(title, xs, cap=40):
    if not xs: return ""
    slides = ""
    for x in xs[:cap]:
        win = f'<div class="crp"><span>拍定價</span><b>{e(x["win"])}</b></div>' if x.get("win") else ""
        tag = "｜".join(filter(None, [x.get("round", ""), x.get("deliver", "")]))
        cls = "crh" if x["status"] == "拍定" else "crh crx"
        slides += (f'<div class="crs"><div class="{cls}">{e(x["date"])}｜{e(x["status"])}</div><div class="crb"><div class="crct">{e("｜".join(filter(None, [x.get("type", ""), tag])))}</div>'
                   f'<div class="crn">{e(x["addr"])}</div><div class="crp"><span>底價</span><b>{e(x.get("base", ""))}</b></div>{win}</div></div>')
    return (f'<h2 class="sec">{e(title)}（{len(xs)}筆）</h2><div class="cr" data-cr><div class="crt">{slides}</div><div class="crdots"></div></div>'
            '<p class="note">開標結果依法院公告彙整，實際內容以法院公告為準。</p>')

def hero_html():
    h = (f'<div class="hero"><a class="l" href="{e(LINKS["LINE 社群"])}" target="_blank" rel="noopener">加入 LINE 社群，搶先看新物件</a>'
         f'<a class="f" href="{e(LINKS["粉絲專頁"])}" target="_blank" rel="noopener">追蹤粉絲專頁</a>'
         f'<a href="tel:0918313888">電話諮詢 黃先生 Pitt</a><a href="tel:0986678928">電話諮詢 林小姐 Anna</a></div>')
    h += ('<section class="box team"><img src="/img/team2.jpg" alt="黃先生 Pitt 與林小姐 Anna 研究格局圖" width="583" height="800" loading="lazy" onerror="this.remove()">'
          '<div><h2>同樣價格，兩個人幫你把關</h2><ol><li><b>產權調查</b>：查清楚有沒有占用、抵押、不點交風險</li><li><b>現場勘查</b>：兩人分工看屋況與周邊</li><li><b>出價精準評估</b>：比對行情與後續成本，算出合理出價</li><li><b>一條龍服務</b>：代標、貸款、點交到交屋，一次處理</li></ol>'
          '<p><a class="btn line" href="/member#ask">委託代標留言</a> <a class="btn" href="tel:0918313888">電話洽詢</a></p></div></section>')
    h += carousel("每週精選・10年內新屋", featured_items(), "/new-house", auto=True)
    h += carousel("本週新增", sorted(new_items(), key=date_key), "/new")
    h += carousel("降價・復拍更新", sorted(changed_items(), key=date_key), "/changes")
    h += results_carousel("每週拍定・停拍・撤回・流標", results_items())
    wk = upcoming(30)[:8]
    if wk:
        rows = "".join(f'<tr><td>{e("%d拍" % round_of(x) if round_of(x) else "—")}</td><td>{e(x["資訊"].get("開標日期", ""))}</td><td><a href="/h/{e(x["編號"])}">{e(x["地址"])}</a></td><td class="rt">{e(x["價格"])}</td></tr>' for x in wk)
        h += f'<h2 class="sec">近期開標（30 天內）</h2><table class="tbl"><tr><th>拍次</th><th>開標日期</th><th>地址</th><th class="rt">底價</th></tr>{rows}</table>'
    top = sorted([x for x in ITEMS if round_of(x) >= 3], key=lambda x: (price_num(x["價格"]), date_key(x)))[:6]
    if top: h += '<h2 class="sec">第 3 拍以上精選</h2><div class="grid">' + "".join(card(x) for x in top) + "</div>"
    return h

def index_page(list_mode=False):
    cities = sorted({area_of(x)[:2] for x in ITEMS}, key=lambda c: ({"台北": 0, "新北": 1, "桃園": 2}.get(c, 3), c))
    types = sorted({x["類型"] for x in ITEMS})
    areas = {}
    for x in ITEMS: areas.setdefault(area_of(x), []).append(x)
    opts = lambda a: "".join(f"<option>{e(i)}</option>" for i in a)
    al = "".join(f'<a href="/area/{slug(a)}">{e(a)}（{len(v)}）</a>' for a, v in sorted(areas.items(), key=lambda t: ({"台北": 0, "新北": 1, "桃園": 2}.get(t[0][:2], 3), t[0])))
    faq = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in FAQ)
    js = """<script>(function(){var $=function(i){return document.getElementById(i)},g=$('g'),n=$('n'),cards=[].slice.call(g.children),orig=cards.slice();
var F=['q','c','a','y','r','j','pr','s'],TY=[],TL='',OVR=null;
function rk(k){return k.indexOf('台北')==0?0:k.indexOf('新北')==0?1:k.indexOf('桃園')==0?2:3}
function areas(){var c=$('c').value,seen={},o='<option value="">地區不拘</option>';cards.forEach(function(d){if((!c||d.dataset.c===c)&&!seen[d.dataset.a]){seen[d.dataset.a]=1}});Object.keys(seen).sort(function(a,b){return rk(a)-rk(b)||(a<b?-1:1)}).forEach(function(k){o+='<option>'+k+'</option>'});var cur=$('a').value;$('a').innerHTML=o;if(seen[cur])$('a').value=cur}
function f(){var k=$('q').value.trim(),c=$('c').value,a=$('a').value,y=$('y').value,r=$('r').value,j=$('j').value,pr=$('pr').value,s=$('s').value,cnt=0,lo=0,hi=1e9;if(pr){var p=pr.split('-');lo=+p[0]*10000;hi=+p[1]*10000}else if(OVR){lo=OVR[0]*10000;hi=OVR[1]*10000}
cards.forEach(function(d){var D=d.dataset,p=+D.p,rr=+D.r,ok=(!k||D.t.indexOf(k)>-1)&&(!c||D.c===c)&&(!a||D.a===a)&&(!y||D.y===y)&&(!r||(r==='4'?rr>=4:r==='3+'?rr>=3:rr===+r))&&(!j||D.j===j)&&((!pr&&!OVR)||(p>=lo&&p<hi))&&(!TY.length||TY.some(function(t){return D.y.indexOf(t)===0}));d.style.display=ok?'':'none';if(ok)cnt++});
var arr=s?cards.slice().sort(function(x,y){var X=x.dataset,Y=y.dataset;return s==='pa'?X.p-Y.p:s==='pd'?Y.p-X.p:s==='da'?X.d-Y.d:Y.d-X.d}):orig;arr.forEach(function(d){g.appendChild(d)});n.textContent='共 '+cnt+' 筆'+(TY.length?'（類型：'+TL+'）':'')}
[].forEach.call(document.querySelectorAll('.qk button'),function(b){b.addEventListener('click',function(){if(b.dataset.c){$('c').value=b.dataset.c;areas()}if(b.dataset.r){$('r').value=b.dataset.r;chipsOn()}f();$('list').scrollIntoView({behavior:'smooth'})})});
var rc=$('rc');function chipsOn(){[].forEach.call(rc.querySelectorAll('button'),function(b){b.className=b.dataset.v===$('r').value?'on':''})}rc.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;$('r').value=b.dataset.v;chipsOn();f()});
var go=$('go');function done(){if(document.activeElement)document.activeElement.blur();f();$('n').scrollIntoView({behavior:'smooth',block:'start'})}go.addEventListener('click',done);$('q').addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();done()}});
F.forEach(function(i){$(i).addEventListener('input',function(){if(i==='c')areas();if(i==='pr')OVR=null;if(i==='y'){TY=[];TL=''}f()})});
$('rs').addEventListener('click',function(){TY=[];TL='';OVR=null;F.forEach(function(i){$(i).value=''});areas();chipsOn();f()});var Q=new URLSearchParams(location.search);if(Q.get('c')){$('c').value=Q.get('c');areas()}var pq=Q.get('p');if(pq){var pp=pq.split('-');if([].some.call($('pr').options,function(o){return o.value===pq}))$('pr').value=pq;else if(pp.length===2&&!isNaN(pp[0])&&!isNaN(pp[1]))OVR=[+pp[0],+pp[1]]}if(Q.get('t')){TY=Q.get('t').split(',');TL=Q.get('tl')||Q.get('t')}areas();chipsOn();f()})();</script>"""
    lead = (f'<h1 class="lh">全部法拍屋物件</h1><p class="ls">共 {len(ITEMS)} 筆，含拍次、開標日期、底標價與法院筆錄，每日更新。</p><div id="list"></div>' if list_mode else
            f'<p>Pitt &amp; Anna 104法拍網團隊整理全台法拍屋、金拍屋物件資訊（資料來源：透明房訊），含拍次、開標日期、底標價與法院筆錄，並提供投標諮詢、全程代標、聲請點交／包辦點交。目前共 {len(ITEMS)} 筆物件。</p>' + hero_html() + '<h2 class="sec" id="list">全部法拍屋物件</h2>')
    body = (lead +
            f'<div class="chips" id="rc"><b>拍次：</b><button type="button" data-v="" class="on">全部（{len(ITEMS)}）</button>'
            f'<button type="button" data-v="1">第1拍（{sum(1 for x in ITEMS if round_of(x)==1)}）</button><button type="button" data-v="2">第2拍（{sum(1 for x in ITEMS if round_of(x)==2)}）</button>'
            f'<button type="button" data-v="3">第3拍（{sum(1 for x in ITEMS if round_of(x)==3)}）</button><button type="button" data-v="4">第4拍以上（{sum(1 for x in ITEMS if round_of(x)>=4)}）</button></div>'
            f'<div class="bar"><input id="q" type="search" enterkeyhint="search" placeholder="搜尋地址、社區、案號…" aria-label="搜尋"><button id="go" type="button">搜尋</button><select id="c" aria-label="縣市"><option value="">縣市不拘</option>{opts(cities)}</select><select id="a" aria-label="地區"><option value="">地區不拘</option></select>'
            f'<select id="y" aria-label="類型"><option value="">類型不拘</option>{opts(types)}</select>'
            f'<input type="hidden" id="r">'
            f'<select id="j" aria-label="點交情形"><option value="">點交不拘</option><option>點交</option><option>不點交</option><option>其他</option></select>'
            f'<select id="pr" aria-label="價格"><option value="">價格不拘</option><option value="0-500">500萬以下</option><option value="500-1000">500～1000萬</option><option value="1000-2000">1000～2000萬</option><option value="2000-3000">2000～3000萬</option><option value="3000-1000000">3000萬以上</option></select>'
            f'<select id="s" aria-label="排序"><option value="">預設</option><option value="pa">價格低→高</option><option value="pd">價格高→低</option><option value="da">開標日期近→遠</option><option value="dd">開標日期遠→近</option></select><button id="rs" type="button">重設</button></div>'
            f'<div id="n" class="m"></div><div class="grid" id="g">{"".join(card(x) for x in ITEMS)}</div>'
            f'<section class="box areas" id="areas"><h2>依地區找法拍屋</h2>' + "".join(f'<a href="/{c[0]}"><b>{e(c[3])}</b></a>' for c in CITIES) + f'<br>{al}</section>'
            + (contact_box() if list_mode else f'<section class="box" id="faq"><h2>法拍屋常見問題</h2>{faq}</section>' + extras_index() + contact_box()) + js + GATE_JS)
    ld = [ORG, {"@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": SITE + "/", "inLanguage": "zh-TW"},
          {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]},
          {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f'{SITE}/h/{x["編號"]}', "name": x["地址"]} for i, x in enumerate(ITEMS[:50])]}]
    first = next((photos(x)[0] for x in ITEMS if photos(x)), None)
    return page(f"全台法拍屋查詢｜台北・新北・桃園・台中・台南・高雄法拍屋｜{NAME}", f"全台各縣市法拍屋物件查詢，含拍次、開標日期、底標價與法院筆錄；提供法拍屋代標、產權調查、不點交處理、貸款諮詢。共{len(ITEMS)}筆，每日更新。", "/list" if list_mode else "/", body, ld, SITE + "/og.jpg", "", "" if list_mode else hero_banner())

def list_page(path, h1, desc, xs):
    title = f"{h1}｜{len(xs)}筆｜{NAME}"
    body = (f'<nav class="bc"><a href="/">首頁</a> › {e(h1)}</nav><h1>{e(h1)}（{len(xs)}筆）</h1><p>{e(desc)}</p><div class="grid">{"".join(card(x) for x in xs)}</div>' + contact_box())
    ld = [ORG, {"@context": "https://schema.org", "@type": "ItemList", "name": h1, "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f'{SITE}/h/{x["編號"]}', "name": x["地址"]} for i, x in enumerate(xs)]}]
    return page(title, desc, path, body, ld, SITE + "/og.jpg")

def wan(n): return f"{n / 100000000:.1f}".rstrip("0").rstrip(".") + "億" if n >= 100000000 else f"{n / 10000:,.0f}萬"

def area_summary(a, xs):
    """區域整理文（原 部落格草稿 寫法）：件數、類型、底價範圍、最近開標，只用資料裡有的內容。"""
    t = datetime.date.today(); today = (t.year - 1911) * 10000 + t.month * 100 + t.day
    kinds = {}
    for x in xs:
        k = (x["類型"] or "其他").split("_")[0]; kinds[k] = kinds.get(k, 0) + 1
    kind_txt = "、".join(f"{k} {v} 件" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]))
    ps = sorted(p for p in (price_num(x["價格"]) for x in xs) if p > 0)
    up = sorted((x for x in xs if today <= date_key(x) < 99999999), key=date_key)
    md = lambda x: "/".join(str(int(v)) for v in x["資訊"]["開標日期"].split("/")[1:])
    r3 = sum(1 for x in xs if round_of(x) >= 3)
    dv = sum(1 for x in xs if deliver_of(x) == "點交")
    parts = [f"整理{a}近期法拍物件，共 {len(xs)} 件（{kind_txt}）"]
    if ps: parts.append(f"底價 {wan(ps[0])}～{wan(ps[-1])}")
    if up: parts.append(f"最近一場 {md(up[0])} 開標")
    r1, r2 = sum(1 for x in xs if round_of(x) == 1), sum(1 for x in xs if round_of(x) == 2)
    rt = "、".join(t for t in [f"第一拍 {r1} 件" if r1 else "", f"第二拍 {r2} 件" if r2 else "", f"第三拍以上 {r3} 件" if r3 else ""] if t)
    if rt: parts.append(rt)
    if dv: parts.append(f"筆錄記載點交 {dv} 件")
    intro = "，".join(parts) + f"。資料每日更新（{UPDATED}），拍次與底價會變動，投標前請以法院最新公告為準。"
    soon = "".join(f'<li><a href="/h/{e(x["編號"])}">{e(md(x))}｜{e(x["地址"])}</a>｜{e("第%d拍" % round_of(x) if round_of(x) else "")} 底價 {e(re.sub(r"^售", "", x["價格"]))}</li>' for x in up[:6])
    head = f"{a[2:] or a}法拍屋｜{a}{len(xs)}件待標" + (f"・底價{wan(ps[0])}～{wan(ps[-1])}" if ps else "") + (f"・最近{md(up[0])}開標" if up else "")
    return head, intro, (f'<h2>{e(a)}近期開標</h2><ul class="soon">{soon}</ul>' if soon else "")

def area_page(a, xs):
    head, intro, soon = area_summary(a, xs)
    title = f"{head}｜{NAME}"
    desc = intro[:150]
    body = (f'<nav class="bc"><a href="/">首頁</a> › {e(a)}法拍屋</nav><h1>{e(a[2:] or a)}法拍屋｜{e(a)}法拍物件整理（{len(xs)}件）</h1><p>{e(intro)}</p>'
            f'<p>{e(a)}法拍屋代標、產權調查與點交評估，可電話或 LINE 諮詢。</p>{soon}{comm_links(lambda g, a=a: any(area_of(x) == a for x in g["cur"]), a + "社區法拍屋")}<h2>{e(a)}全部法拍物件</h2><div class="grid">{"".join(card(x) for x in xs)}</div>' + contact_box())
    ld = [ORG, {"@context": "https://schema.org", "@type": "ItemList", "name": f"{a}法拍屋", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f'{SITE}/h/{x["編號"]}', "name": x["地址"]} for i, x in enumerate(xs)]}]
    return title, page(title, desc, f"/area/{slug(a)}", body, ld, SITE + "/og.jpg")

CITIES = [
    ("taipei", "台北", ["台北"], "台北法拍屋", "台北市"),
    ("new-taipei", "新北", ["新北"], "新北法拍屋", "新北市"),
    ("taoyuan", "桃園", ["桃園"], "桃園法拍屋", "桃園市"),
    ("keelung", "基隆", ["基隆"], "基隆法拍屋", "基隆市"),
    ("hsinchu", "新竹", ["新竹"], "新竹法拍屋", "新竹市、新竹縣"),
    ("miaoli", "苗栗", ["苗栗"], "苗栗法拍屋", "苗栗縣"),
    ("taichung", "台中", ["台中"], "台中法拍屋", "台中市"),
    ("changhua", "彰化", ["彰化"], "彰化法拍屋", "彰化縣"),
    ("nantou", "南投", ["南投"], "南投法拍屋", "南投縣"),
    ("yunlin", "雲林", ["雲林"], "雲林法拍屋", "雲林縣"),
    ("chiayi", "嘉義", ["嘉義"], "嘉義法拍屋", "嘉義市、嘉義縣"),
    ("tainan", "台南", ["台南"], "台南法拍屋", "台南市"),
    ("kaohsiung", "高雄", ["高雄"], "高雄法拍屋", "高雄市"),
    ("pingtung", "屏東", ["屏東"], "屏東法拍屋", "屏東縣"),
    ("yilan", "宜蘭", ["宜蘭"], "宜蘭法拍屋", "宜蘭縣"),
    ("hualien", "花蓮", ["花蓮"], "花蓮法拍屋", "花蓮縣"),
    ("taitung", "台東", ["台東"], "台東法拍屋", "台東縣"),
    ("kinmen", "金門", ["金門"], "金門法拍屋", "金門縣"),
    ("greater-taipei", "大台北", ["台北", "新北", "基隆"], "大台北法拍屋", "台北、新北、基隆"),
]
ALL_CITY_SLUGS = [c[0] for c in CITIES]
CITIES = [c for c in CITIES if any(x["區域"][:2] in c[2] for x in ITEMS)]   # 沒有物件的縣市不產生空頁

def city_faq(kw, scope):
    return [
        (f"{kw}怎麼查詢？", f"在本頁可直接瀏覽{scope}目前的法拍屋物件，每筆都有拍次、開標日期、底標價與法院筆錄，資料每日更新。想縮小範圍可點下方各行政區。"),
        (f"{kw}可以委託代標嗎？", "可以。Pitt & Anna 104法拍網團隊全台都有服務，提供投標諮詢、全程代標、聲請點交／包辦點交，請電話或 LINE 聯絡黃先生 Pitt 或林小姐 Anna。"),
        (f"{kw}第三拍以上的物件為什麼值得注意？", "第一拍流標後，法院通常會降價再拍。第三拍以上價格往往較低，但仍須先查清產權、占用與點交情形，再評估合理出價。"),
        ("點交與不點交差在哪裡？", "點交是拍定後由法院協助將房屋點交給得標人；不點交則需得標人自行處理占用問題。各物件請看「法院筆錄」中的點交情形。"),
        ("法拍屋可以看屋嗎？", "一般查封後無法入內，可依建物平面圖推斷格局，或參考同棟其他樓層。能看屋的物件會另行註明。"),
    ]

def city_page(slug_, short, prefixes, kw, scope):
    xs = [x for x in ITEMS if area_of(x)[:2] in prefixes]
    xs.sort(key=lambda x: (-min(round_of(x), 4), date_key(x)))
    areas = {}
    for x in xs: areas.setdefault(area_of(x), []).append(x)
    n3 = sum(1 for x in xs if round_of(x) >= 3)
    title = f"{kw}｜{scope}最新法拍物件{len(xs)}筆・拍次底價｜{NAME}"
    desc = f"{kw}最新物件{len(xs)}筆，涵蓋{scope}，含拍次、開標日期、底標價與法院筆錄；提供{short}法拍屋代標、產權調查、不點交處理與貸款諮詢，每日更新。"
    al = "".join(f'<a href="/area/{slug(a)}">{e(a)}法拍屋（{len(v)}）</a>' for a, v in sorted(areas.items()))
    others = "".join(f'<a href="/{c[0]}">{e(c[3])}</a>' for c in CITIES if c[0] != slug_)
    faq = city_faq(kw, scope)
    fh = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faq)
    intro = (f'<p>{e(kw)}專區：Pitt &amp; Anna 104法拍網團隊整理{e(scope)}目前共 {len(xs)} 筆法拍屋，其中第三拍以上 {n3} 筆，資料{e(UPDATED[:10])}更新。'
             f'每筆物件都列出拍次、開標日期、底標價與法院筆錄，並由黃先生 Pitt、林小姐 Anna 提供代標與產權調查。</p>')
    body = (f'<nav class="bc"><a href="/">首頁</a> › {e(kw)}</nav><h1>{e(kw)}｜{e(scope)}最新法拍物件（{len(xs)}筆）</h1>{intro}'
            f'<section class="box areas"><h2>{e(short)}各區法拍屋</h2>{al}</section>'
            + comm_links(lambda g: g["city"] in prefixes, short + "熱門社區法拍屋")
            + (lambda cc: f'<section class="box areas"><h2>依類型找{e(short)}法拍屋</h2>' + "".join(f'<a href="/{cc[0]}-{t[0]}">{e(short + t[1])}法拍屋（{len(type_items(cc, t[2]))}）</a>' for t in TYPES if len(type_items(cc, t[2])) >= 3) + '</section>')(next(c for c in CITIES if c[0] == slug_))
            +
            f'<h2 class="sec">{e(kw)}物件列表（第三拍以上優先）</h2><div class="grid">{"".join(card(x) for x in xs)}</div>'
            f'<section class="box" id="faq"><h2>{e(kw)}常見問題</h2>{fh}</section>'
            f'<section class="box areas"><h2>其他地區</h2>{others}</section>' + know_box() + contact_box())
    ld = [ORG,
          {"@context": "https://schema.org", "@type": "CollectionPage", "name": kw, "url": f"{SITE}/{slug_}", "description": desc, "inLanguage": "zh-TW", "dateModified": UPDATED.replace(" ", "T") + ":00+08:00"},
          {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
          {"@context": "https://schema.org", "@type": "ItemList", "name": kw, "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f'{SITE}/h/{x["編號"]}', "name": x["地址"]} for i, x in enumerate(xs[:50])]},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "首頁", "item": SITE + "/"},
              {"@type": "ListItem", "position": 2, "name": kw, "item": f"{SITE}/{slug_}"}]}]
    return page(title, desc, f"/{slug_}", body, ld, SITE + "/og.jpg")

TYPES = [("townhouse", "透天", "透天"), ("shop", "店面", "店面"), ("apartment", "公寓", "公寓"), ("building", "大樓", "大樓"), ("mansion", "華廈", "華廈"), ("studio", "套房", "套房")]

def type_items(c, tk):
    return [x for x in ITEMS if area_of(x)[:2] in c[2] and tk in (x.get("類型") or "")]

def type_page(c, t):
    ts, tn, tk = t
    xs = type_items(c, tk)
    xs.sort(key=lambda x: (-min(round_of(x), 4), date_key(x)))
    kw = f"{c[1]}{tn}法拍屋"
    slug_ = f"{c[0]}-{ts}"
    n3 = sum(1 for x in xs if round_of(x) >= 3)
    title = f"{kw}｜{c[4]}{tn}最新法拍物件{len(xs)}筆｜{NAME}"
    desc = f"{kw}最新物件{len(xs)}筆，含拍次、開標日期、底標價與法院筆錄；提供{c[1]}{tn}法拍屋代標、產權調查與貸款諮詢，每日更新。"
    others = "".join(f'<a href="/{c[0]}-{o[0]}">{e(c[1] + o[1])}法拍屋</a>' for o in TYPES if o[0] != ts and len(type_items(c, o[2])) >= 3)
    faq = city_faq(kw, f"{c[4]}{tn}")[:3]
    fh = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faq)
    intro = f'<p>{e(kw)}專區：目前共 {len(xs)} 筆，其中第三拍以上 {n3} 筆，資料{e(UPDATED[:10])}更新。每筆列出拍次、開標日期、底標價與法院筆錄。</p>'
    body = (f'<nav class="bc"><a href="/">首頁</a> › <a href="/{c[0]}">{e(c[3])}</a> › {e(kw)}</nav><h1>{e(kw)}（{len(xs)}筆）</h1>{intro}'
            f'<div class="grid">{"".join(card(x) for x in xs)}</div>'
            f'<section class="box" id="faq"><h2>{e(kw)}常見問題</h2>{fh}</section>'
            f'<section class="box areas"><h2>其他類型與地區</h2><a href="/{c[0]}">{e(c[3])}</a>{others}</section>' + know_box() + contact_box())
    ld = [ORG,
          {"@context": "https://schema.org", "@type": "CollectionPage", "name": kw, "url": f"{SITE}/{slug_}", "description": desc, "inLanguage": "zh-TW"},
          {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
          {"@context": "https://schema.org", "@type": "ItemList", "name": kw, "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f'{SITE}/h/{x["編號"]}', "name": x["地址"]} for i, x in enumerate(xs[:50])]},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "首頁", "item": SITE + "/"},
              {"@type": "ListItem", "position": 2, "name": c[3], "item": f"{SITE}/{c[0]}"},
              {"@type": "ListItem", "position": 3, "name": kw, "item": f"{SITE}/{slug_}"}]}]
    return page(title, desc, f"/{slug_}", body, ld, SITE + "/og.jpg")

FEE_ITEMS = [
 ("追蹤法院核發權利移轉證書", "", 1), ("協助產權過戶", "相關代書費、稅費另計，詳見附註一", 1), ("撰擬點交聲請狀", "", 1), ("向法院遞交點交書狀", "", 1), ("持續追蹤點交進度", "", 1),
 ("協助代墊尾款", "", 2), ("協調轄區警員到場", "", 2), ("安排鎖匠與搬家公司待命", "", 2), ("協同法院協調現住人交屋時間", "", 2), ("處理原債務人戶籍及營業登記遷移", "包含原債務人戶籍中的幽靈人口遷移", 2), ("協助恢復水、電與瓦斯", "", 2),
 ("投標前案件調查", "現場訪查、法院筆錄核對、債權與水電調查；確認附屬增建是否在拍賣範圍、車位是否遭占用；查核第三人租約陳報與拍定後點交條件", 3),
 ("標價評估與投標準備", "投標現場陪同及最終標價建議、投標文件準備；核對投標書、委任狀及保證金票據；了解周邊競標情形，比對市價及法拍成交紀錄", 3),
 ("協調原屋主搬遷條件", "協商搬遷，配合法院點交程序進行", 3), ("全程承辦點交程序", "", 3), ("提供點交保固書", "限服務費 5% 的案件適用，詳見附註二", 3), ("協助於約定期限內和諧交屋", "", 3),
 ("處理遺留神明、神主牌及祖先牌位", "協助寄託廟宇管理", 3), ("有價遺留物清點與保管", "以貨櫃屋或倉庫存放，通知權利人領取；未領取時，依法聲請拍賣", 3)]

def fees_page():
    cols = [("聲請點交", "50,000", "元", "服務項目 01–05", 1), ("包辦點交", "120,000", "元", "服務項目 01–11", 2), ("全程代標", "2–5%", "依案件難易評估", "服務項目 01–19；300 萬元以下固定 10 萬元；超過 300 萬元至 600 萬元最低 12 萬元", 3)]
    th = "".join(f'<th style="text-align:center;color:#123;font-weight:700"><div>{e(n)}</div><div style="font-size:22px">{p}</div><div style="font-weight:400;color:#666;font-size:13px">{e(u)}<br>{e(s)}</div></th>' for n, p, u, s, _ in cols)
    rows = ""
    for i, (t, sub, lv) in enumerate(FEE_ITEMS, 1):
        cells = "".join(f'<td style="text-align:center">{"●" if lv <= c[4] else "—"}</td>' for c in cols)
        rows += f'<tr><td style="width:auto;color:#123"><b>{i:02d}　{e(t)}</b>' + (f'<div style="color:#666;font-size:13px;font-weight:400">{e(sub)}</div>' if sub else "") + f'</td>{cells}</tr>'
    notes = ["服務費不含：過戶代書費、貸款設定代書費、過戶契稅、規費及貸款手續費。", "點交保固書適用於服務費 5% 的案件。", "不點交、部分點交及持分案件，服務費另議，不適用 300 萬元以下固定 10 萬元。"]
    nh = "<ol>" + "".join(f"<li>{e(n)}</li>" for n in notes) + "</ol>"
    body = (f'<nav class="bc"><a href="/">首頁</a> › 服務與收費</nav><h1>服務費用與收費標準</h1><p>三種服務方案，依您的委託需求選擇。</p>'
            f'<section class="box" style="text-align:center"><img src="/img/fees-chart.jpg" alt="Pitt &amp; Anna 104法拍網團隊服務費用與收費標準：聲請點交 50,000 元、包辦點交 120,000 元、全程代標 2–5%" width="1200" height="1870" loading="eager" style="width:100%;max-width:900px;height:auto;border-radius:8px"></section>'
            f'<section class="box"><details><summary>文字版服務項目</summary><table><tr><th style="width:auto">服務項目</th>{th}</tr>{rows}</table></details></section>'
            f'<section class="box"><h2>費用附註</h2>{nh}</section>' + know_box() + contact_box())
    desc = "Pitt & Anna 104法拍網團隊代標服務收費：聲請點交 50,000 元、包辦點交 120,000 元、全程代標 2% 到 5%（300 萬元以下固定 10 萬元；超過 300 萬元至 600 萬元最低 12 萬元），並列出各方案服務項目與費用附註。"
    ld = [ORG, {"@context": "https://schema.org", "@type": "Service", "name": "法拍屋代標服務", "provider": {"@id": SITE + "/#org"}, "areaServed": "TW", "description": desc}]
    return page(f"服務與收費｜法拍屋代標費用｜{NAME}", desc, "/fees", body, ld, SITE + "/og.jpg")

def know_box():
    items = [("what-is-foreclosure-auction", "法拍屋是什麼？流程"), ("delivery-or-not", "點交與不點交"), ("how-long-to-move-in", "得標後多久交屋"), ("deposit-invalid", "投標保證金"), ("proxy-bid-process", "委託代標怎麼進行")]
    return '<section class="box areas"><h2>法拍知識與服務</h2>' + "".join(f'<a href="/learn/{s}">{e(t)}</a>' for s, t in items) + '<a href="/process">購屋流程</a><a href="/fees">服務與收費</a><a href="/about">關於我們</a>' + ('<a href="/promo">年前上車｜2 萬代標券</a>' if _today() <= PROMO_END else '') + '</section>'

ABOUT_FAQ = [
    ("這個網站是誰在經營？", "由 Pitt & Anna｜104法拍網團隊經營（財欣不動產管理顧問有限公司），網站每日更新法拍物件的拍次、開標日期、底標價與法院筆錄，實際內容以法院公告為準。"),
    ("誰負責代標服務？", "由黃先生 Pitt 與林小姐 Anna 夫妻雙人顧問負責，提供產權調查、現場勘查、標價評估、點交與交屋協助。"),
    ("怎麼聯絡？服務哪些地區？", f"黃先生 Pitt {PHONE_P}、林小姐 Anna {PHONE_A}，或傳「案名」或地址到 LINE@ https://lin.ee/Y2bGSIB。全台都有服務。"),
]

def about_page():
    fh = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in ABOUT_FAQ)
    body = ('<nav class="bc"><a href="/">首頁</a> › 關於我們</nav><h1>關於 Pitt & Anna｜104法拍網團隊</h1>'
            f'<p>{e(INTRO)}</p><p>本站每天更新法拍物件，實際內容以法院拍賣公告為準。</p>'
            '<section class="box"><h2>我們的團隊</h2><p>黃先生 Pitt 與林小姐 Anna 夫妻雙人顧問，協助產權調查、現場勘查、標價評估、投標、點交與交屋。</p></section>'
            '<section class="box"><h2>我們提供的服務</h2><ul><li>聲請點交：50,000 元</li><li>包辦點交：120,000 元</li><li>全程代標：2% 到 5%（300 萬元以下固定 10 萬元；超過 300 萬元至 600 萬元最低 12 萬元）</li></ul><p><a href="/fees">查看完整服務項目與收費附註</a></p></section>'
            f'<section class="box"><h2>聯絡我們</h2><ul><li>林小姐 Anna：{e(PHONE_A)}</li><li>黃先生 Pitt：{e(PHONE_P)}</li><li>LINE@：<a href="{e(LINKS["LINE"])}" target="_blank" rel="noopener">https://lin.ee/Y2bGSIB</a></li><li>服務範圍：全台都有服務</li><li>{e(COMPANY)}</li></ul></section>'
            f'<section class="box" id="faq"><h2>常見問題</h2>{fh}</section>' + know_box() + contact_box())
    ld = [ORG, {"@context": "https://schema.org", "@type": "AboutPage", "name": "關於 Pitt & Anna｜104法拍網團隊", "url": SITE + "/about", "inLanguage": "zh-TW"},
          {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in ABOUT_FAQ]}]
    return page(f"關於我們｜Pitt & Anna 104法拍網團隊｜{SLOGAN}", "Pitt & Anna｜104法拍網團隊，你的法拍購屋夥伴：全台都有服務，提供投標諮詢、全程代標、聲請點交／包辦點交。財欣不動產管理顧問有限公司。", "/about", body, ld, SITE + "/og.jpg")

try: SOLD = json.load(open("data/sold.json", encoding="utf-8"))   # 透明房訊開標結果：拍定／承受／撤回
except Exception: SOLD = {}

def gone_page(k, v):
    """已從列表消失的物件：保留網址（不讓 Google、FB 舊連結變 404），標示已下架並導到同社區／同區現有物件。
    2026-11-19：有社區名的下架頁保留收錄並放進 sitemap（社區名＋凶宅／法拍的查詢拍完還是有人搜）；沒社區名的才 noindex"""
    addr, area = v.get("addr", ""), (v.get("area", "").split("-")[0])
    x = {"編號": k, "地址": addr, "區域": v.get("area", ""), "類型": v.get("type", ""), "資訊": {"社區/大樓": v.get("comm") or next((g["name"] for g in community_groups().values() if (k, v) in g["past"]), "")}}
    rows = kv([("案名／地址", addr), ("地區", area), ("最後拍次", ("第%s拍" % v["rd"]) if v.get("rd") else ""), ("最後開標日期", v.get("date", "")),
               ("最後底價", re.sub(r"^售", "", v.get("ptxt", ""))), ("下架日期", v.get("gone", ""))])
    sd = SOLD.get(k) or {}
    tag = "已" + sd["status"] if sd.get("status") else "已下架"
    gone_msg = (f"這筆物件依透明房訊開標結果，已於 {sd.get('date', '')} {sd['status']}，實際結果以法院公告為準。" if sd.get("status")
                else "這筆物件已從列表下架，可能已拍定、停拍或撤回，實際結果請以法院公告為準。")
    body = (f'<nav class="bc"><a href="/">首頁</a> › <a href="/area/{slug(area)}">{e(area)}法拍屋</a> › {tag}物件</nav>'
            f'<section class="box"><h1>{e(addr)}（{tag}）</h1><p>{e(gone_msg)}下面可以看同社區與附近其他現有物件，歡迎 LINE@ 或電話詢問。</p>{rows}'
            f'<p><a class="btn line" href="{e(LINKS["LINE"])}" target="_blank" rel="noopener">LINE 詢問</a> <a class="btn" href="tel:0918313888">電話洽詢</a> <a class="btn" href="/area/{slug(area)}">看{e(area)}現有物件</a></p></section>'
            + related_box(x, _comm(x), area))
    comm = _comm(x)
    if not comm:   # 下架頁來源欄常沒有社區名，改從案名的【】取；排除「頂加」「捷運」「店面」這類不是社區名的字
        m = re.search(r"【([^】]{2,12})】", addr)
        if m and not re.search(r"樓|頂|加蓋|增建|捷運|站|店|車位|透天|邊間|電梯|公園|學區|近|坪|景觀|兇|凶|法拍|點交|持分|別墅|土地|廠|整棟|全棟", m.group(1)): comm = m.group(1)
    if comm:
        return page(f"{comm}法拍屋｜{addr}（{tag}）｜{NAME}", f"{comm}（{addr}）法拍物件已下架，可能已拍定、停拍或撤回，結果以法院公告為準；可查看{comm}與{area}其他現有法拍屋。", f"/h/{k}", body)
    return page(f"{addr}（已下架）｜{area}法拍屋｜{NAME}", f"{addr}已從法拍物件列表下架，結果以法院公告為準；可查看{area}其他現有法拍屋。", f"/h/{k}", body).replace("index,follow,max-image-preview:large,max-snippet:-1", "noindex,follow")

GONE_URLS = []
def write_gone(cur_ids, keep_days=365):   # 2026-11-21 Google 建議轉址與舊網址至少保留 1 年
    """下架物件：有透明房訊同一物件（HO 停用後）就 301 轉址過去，其餘產生已下架頁；回傳 (已下架頁數, 轉址數)"""
    try: seen = json.load(open("data/seen.json", encoding="utf-8"))
    except Exception: return 0, 0
    red, n = [], 0
    for k in EXCL_IDS - set(seen): red.append(f'/h/{k} / 301')
    for k, v in seen.items():
        if k in EXCL_IDS or str(v.get("area", ""))[:2] in EXCL_CITY:
            red.append(f'/h/{k} / 301'); continue   # 金門、澎湖、連江：轉首頁，不留 404
        if k in cur_ids or not v.get("addr"): continue
        if v.get("twin") in cur_ids:
            red.append(f'/h/{k} /h/{v["twin"]} 301'); continue
        if not v.get("gone"): continue
        try:
            if (_today() - datetime.date.fromisoformat(v["gone"])).days > keep_days: continue
        except ValueError: continue
        html = gone_page(k, v); write(f"site/h/{k}.html", html); n += 1
        if "noindex" not in html[:3000]: GONE_URLS.append((f"/h/{k}", 0.4, v.get("gone", "")))
    write("site/_redirects", "# 自動產生：House-Info 舊物件網址轉到透明房訊同一物件\n" + "".join(r + "\n" for r in red[:1900]))
    return n, len(red)

def lastmod(x):
    """物件最後變動日（新增或降價降拍），沒有紀錄就不寫，避免每天都報全部更新"""
    d = max(x.get("新增日") or "", x.get("異動日") or "")
    return d if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) else ""

WRITTEN = set()
def write(path, s):
    WRITTEN.add(os.path.normpath(path))
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    open(path, "w", encoding="utf-8").write(s)

# ---------- 新首頁（preview-home）動態區塊：隨每日資料自動更新 ----------
def _open_date(x):
    m = re.fullmatch(r"(\d+)/(\d+)/(\d+)", x.get("資訊", {}).get("開標日期", ""))
    if not m: return ""
    try: return datetime.date(int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3))).isoformat()
    except ValueError: return ""

def _live_pick(n=6):
    """本週新增優先，各縣市最多取兩筆（需有照片）；不足再用 7 天內開標補滿"""
    pool = [x for x in new_items() if photos(x)]
    pool.sort(key=lambda x: (x.get("新增日", ""), ), reverse=True)
    out, per = [], {}
    for x in pool:
        c = x["區域"][:2]
        if per.get(c, 0) < 2:
            out.append(x); per[c] = per.get(c, 0) + 1
    for x in pool + [y for y in upcoming(7) if photos(y)]:
        if len(out) >= n: break
        if x not in out: out.append(x)
    out = out[:n]
    out.sort(key=lambda x: (_rank(x), x.get("新增日", "")))
    return out

def _live_card(x):
    inf = x.get("資訊", {})
    ph = photos(x)
    od = _open_date(x)
    price = re.sub(r"^售", "", x["價格"])
    old = f'<s>{e(re.sub(r"^售", "", x["原價"]))}</s>' if x.get("原價") else ""
    tag = "新上架" if _within(x.get("新增日", "")) else ""
    r = round_of(x)
    meta = "｜".join(filter(None, [x["區域"].split("-")[0], x["類型"].split("_")[0], x["格局坪數"]]))
    od_txt = re.sub(r"^\d+/", "", inf.get("開標日期", ""))
    lo = f'<p class="live-open is-soon">{YING}</p>' if is_ying(x) else f'<p class="live-open" data-open="{od}">{e(od_txt)} 開標</p>'
    return (f'<a class="live-card" href="/h/{e(x["編號"])}">'
            f'<div class="live-img"><img loading="lazy" decoding="async" width="400" height="300" src="{e(ph[0])}" alt="{e(x["地址"])} 法拍屋照片"{img_fb(ph)}>'
            f'{"<span class=live-tag>"+tag+"</span>" if tag else ""}</div>'
            f'<div class="live-body">{lo}'
            f'<h3>{e(x["地址"])}</h3><p class="live-meta-line">{e(meta)}{"｜公告應買" if is_ying(x) else ("｜第%d拍" % r) if r else ""}</p>'
            f'<p class="live-price"><span>底價</span><b>{old}{e(price)}</b></p></div></a>')

def home_live_html():
    total = len(ITEMS)
    tri = ITEMS
    cnt = dict(_city_counts())
    new_n, soon_n = len(new_items()), len(upcoming(7))
    idx = [[x["區域"][:2], x["類型"].split("_")[0], round(price_num(x["價格"]) / 10000)] for x in tri]
    chips = "".join(f'<a href="/list?c={c}">{c}<b>{n}</b></a>' for c, n in cnt.items())
    day = UPDATED[5:10].replace("-", "/")
    return ('<!--LIVE:start-->'
            '<section class="live-strip" id="live" aria-labelledby="live-title"><div class="container">'
            '<a class="resume-link" id="resume-link" href="/list" hidden></a>'
            '<div class="live-head"><div><p class="eyebrow">LIVE / 最新案件</p><h2 id="live-title">本週新增法拍物件</h2></div>'
            f'<p class="live-stats">資料更新 {day}　上架 <b data-total>{total}</b> 筆・本週新增 <b>{new_n}</b> 筆・7 天內開標 <b>{soon_n}</b> 筆</p></div>'
            f'<div class="live-chips" aria-label="依縣市瀏覽">{chips}<a class="chip-all" href="/list">全部 {total} 筆 →</a></div>'
            f'<div class="live-grid">{"".join(_live_card(x) for x in _live_pick())}</div>'
            f'<p class="live-more"><a class="button button-navy" href="/list">瀏覽全部 {total} 筆法拍物件 <span aria-hidden="true">↗</span></a></p>'
            f'<script type="application/json" id="live-index">{jd(idx)}</script>'
            '</div></section><!--LIVE:end-->')

def _city_counts():
    """各縣市件數，台北／新北／桃園在前，其餘依件數多到少"""
    c = {}
    for x in ITEMS: c[x["區域"][:2]] = c.get(x["區域"][:2], 0) + 1
    return sorted(c.items(), key=lambda t: ({"台北": 0, "新北": 1, "桃園": 2}.get(t[0], 3), -t[1], t[0]))

_CITY_FULL = {"台北": "台北市", "新北": "新北市", "桃園": "桃園市", "台中": "台中市", "台南": "台南市", "高雄": "高雄市", "基隆": "基隆市", "苗栗": "苗栗縣", "彰化": "彰化縣", "南投": "南投縣", "雲林": "雲林縣", "屏東": "屏東縣", "宜蘭": "宜蘭縣", "花蓮": "花蓮縣", "台東": "台東縣", "澎湖": "澎湖縣", "金門": "金門縣", "連江": "連江縣"}

def _home_regions(t):
    """首頁找屋的縣市按鈕與諮詢表單選項：跟著實際有物件的縣市產生"""
    names = [_CITY_FULL.get(c, c) for c, _ in _city_counts()]
    st = "flex:0 0 auto;font-size:16px;min-height:40px;padding:0 14px"
    tabs = "".join('<button type="button" data-region="%s" aria-pressed="%s" style="%s">%s</button>' % (e(n), "true" if i == 0 else "false", st, e(n)) for i, n in enumerate(names))
    t = re.sub(r'<div class="region-tabs"([^>]*)>.*?</div>', lambda m: '<div class="region-tabs"' + m[1] + ' style="display:flex;flex-wrap:wrap">' + tabs + "</div>", t, count=1, flags=re.S)
    opts = "".join("<option>%s</option>" % e(n) for n in names) + "<option>其他地區／尚未決定</option>"
    return re.sub(r'(<select id="inquiry-region">).*?(</select>)', lambda m: m[1] + opts + m[2], t, count=1, flags=re.S)

def write_home():
    """新首頁：由 tpl/home.html 產生 site/index.html（資產在 site/home/）"""
    t = open("tpl/home.html", encoding="utf-8").read()
    t = _home_regions(t)
    blk = home_live_html()
    if "<!--LIVE:start-->" in t:
        t = re.sub(r"<!--LIVE:start-->.*?<!--LIVE:end-->", lambda m: blk, t, flags=re.S)
    else:
        t = t.replace('<nav class="quick-routes', blk + '\n    <nav class="quick-routes', 1)
    t = re.sub(r'(data-total>)\d+', lambda m: m.group(1) + str(len(ITEMS)), t)
    t = t.replace('<meta name="robots" content="noindex,nofollow,noarchive">', '<meta name="robots" content="index,follow,max-image-preview:large">')
    t = re.sub(r'\s*<div class="preview-note">.*?</div>', '', t, count=1, flags=re.S)
    t = t.replace("https://tomin104.com/preview-home/assets/", SITE + "/home/assets/").replace("https://tomin104.com/preview-home/", SITE + "/")
    t = t.replace('"./', '"/home/')
    t = re.sub(r"\s*<!--PROMO:start-->.*?<!--PROMO:end-->", "", t, flags=re.S)
    t = t.replace('<a class="skip-link" href="#main">跳至主要內容</a>', '<a class="skip-link" href="#main">跳至主要內容</a>' + promo_banner(), 1)
    write("site/index.html", t)

# ---------- 活動頁：年前上車｜2 萬代標券（2026-11-18 Anna 同意上線；活動至 2027/2/5 除夕） ----------
PROMO_END = datetime.date(2026, 11, 18)   # 2026-11-19 Anna：代標券全面取消（原訂至 2027/2/5）；過期後首頁橫幅、連結自動消失，活動頁改取消公告、不收錄
PROMO_CLAIM = "https://lin.ee/z4MUUbK"   # 領券
PROMO_LINE = "https://lin.ee/Y2bGSIB"    # 加 LINE@ 好友
PROMO_COMPANY = "財欣不動產管理顧問有限公司"
# 活動辦法全文：照定稿，一字不刪（來源：00_法拍事業部/01_營運總管/年前上車_上線素材_20261118.md）
PROMO_RULES = [
    "活動期間：即日起至 2027/2/5（除夕）23:59 止，以簽訂委託書之日期為準。",
    "名額：優惠券限量 30 張，送完即止，以 LINE@ 領取紀錄為準；額滿即停止領取，已領取者於活動期間內仍可使用。",
    "參加方式：加入 104法拍網 LINE@（@635nftwk）並領取「全程代標服務折 20,000 元」優惠券，於簽訂委託時出示，始得使用。未領券者不適用。",
    "適用範圍：限「全程代標服務」。單純聲請點交、包辦點交等其他服務不適用。",
    "折抵方式：得標並收取服務費時，自服務費中折抵新台幣 20,000 元；未得標不收取服務費，亦不予折抵。優惠券不得兌換現金、不找零。",
    "每一案件限用一張，每張限用一次，不得轉讓、不得與其他優惠併用。",
    "服務費依委託書約定之收費標準計算；優惠內容以委託書記載為準。",
    "法院拍賣之底價、拍次、開標日期、點交與否等，均以法院公告為準。本公司提供專業評估與投標協助，不保證得標，亦不保證投資報酬。",
    "本公司保留修改、暫停或終止本活動之權利，如有變更，以 LINE@ 公告為準。",
]
PROMO_SIGN = "財欣不動產管理顧問有限公司｜Pitt 0918-313-888｜Anna 0986-678-928"
PROMO_CSS = ("<style>.pm{max-width:760px;margin:0 auto}.pm-hero{text-align:center;background:#fbf7ef;border:1px solid #e6d6b4;border-radius:10px;padding:22px 16px 18px;margin-bottom:16px}"
             ".pm-hero .eb{color:#8a6a2f;font-size:14px;letter-spacing:.08em;margin:0 0 6px}.pm-hero h1{font-size:clamp(26px,7vw,40px);line-height:1.25;margin:0 0 10px;color:#18354b}"
             ".pm-hero .lead{font-size:17px;line-height:1.7;margin:0 0 6px;color:#222}.pm-tag{display:inline-block;background:#fff;border:1px solid #d9b97a;color:#18354b;border-radius:999px;padding:6px 14px;font-weight:700;margin:6px 0 4px}"
             ".pm-cta{display:flex;flex-direction:column;gap:10px;margin:16px auto 4px;max-width:420px}.pm-cta a{display:block;text-align:center;text-decoration:none;font-weight:700;font-size:18px;border-radius:8px;padding:15px 12px}"
             ".pm-cta .c1{background:#06c755;color:#fff}.pm-cta .c2{background:#18354b;color:#fff}.pm-cta small{display:block;font-weight:400;font-size:13px;opacity:.9;margin-top:2px}"
             ".pm-img{margin:0 0 16px;text-align:center}.pm-img img{width:100%;max-width:560px;height:auto;border-radius:10px;border:1px solid #e6d6b4}"
             ".pm-rules ol{padding-left:1.4em;margin:8px 0 12px}.pm-rules li{line-height:1.8;margin:0 0 8px}.pm-sign{font-weight:700;color:#18354b;line-height:1.8}"
             ".pm-contact a{display:inline-block;margin:6px 10px 0 0;padding:10px 14px;border:1px solid #18354b;border-radius:6px;text-decoration:none;color:#18354b;font-weight:700}"
             ".pm-upd{color:#666;font-size:13px;margin:10px 0 0}.pm-end{background:#fff3cd;border:1px solid #e0c36a;border-radius:8px;padding:10px 14px;font-weight:700}"
             ".pm-tbl{width:100%;border-collapse:collapse;margin-top:10px;font-size:15px}.pm-tbl th,.pm-tbl td{border:1px solid #e2e2de;padding:8px 10px;text-align:left;vertical-align:top;line-height:1.6}.pm-tbl th{background:#f6f2ea;color:#18354b;white-space:nowrap;width:7.5em}"
             "@media(max-width:480px){.pm-tbl th{white-space:normal;width:5.5em}}"
             "@media(min-width:640px){.pm-cta{flex-direction:row}.pm-cta a{flex:1}}</style>")

PROMO_UPDATED = "2026-11-18"   # 活動內容更新日（改活動辦法時一起改）
PROMO_FAQ = [
    ("年前上車 2 萬代標券到什麼時候？", "活動至 2027/2/5（除夕）23:59 止，以簽訂委託書之日期為準；優惠券限量 30 張，送完即止。"),
    ("怎麼領 2 萬代標券？", "加入 104法拍網 LINE@（@635nftwk）領取「全程代標服務折 20,000 元」優惠券，簽訂委託時出示才能使用；未領券者不適用。"),
    ("沒有得標也會折 2 萬嗎？", "不會。得標並收取服務費時，才自服務費中折抵新台幣 20,000 元；未得標不收取服務費，亦不予折抵。"),
    ("聲請點交、包辦點交可以用這張券嗎？", "不行。優惠限「全程代標服務」，單純聲請點交、包辦點交等其他服務不適用。"),
    ("委託代標保證得標嗎？", "不保證。本公司提供專業評估與投標協助，不保證得標，亦不保證投資報酬；底價、拍次、開標日期、點交與否等，均以法院公告為準。"),
]

def promo_page():
    claim = e(PROMO_CLAIM); line = e(PROMO_LINE)
    ended = _today() > PROMO_END
    url = SITE + "/promo"
    cta = (f'<div class="pm-cta"><a class="c1" href="{claim}" target="_blank" rel="noopener">領取 2 萬代標券<small>LINE@ 領券（限量 30 名）</small></a>'
           f'<a class="c2" href="{line}" target="_blank" rel="noopener">加 LINE@ 好友<small>@635nftwk・傳「活動」也能領</small></a></div>')
    answer = (f"{PROMO_COMPANY}（104法拍網，黃先生 Pitt、林小姐 Anna）推出「年前上車｜2 萬代標券」：委託全程代標，得標並收取服務費時折抵新台幣 20,000 元。"
              "加入 LINE@（@635nftwk）領券、簽訂委託時出示即可使用；限量 30 張，送完即止，活動至 2027/2/5（除夕）23:59 止，以簽訂委託書之日期為準。")
    rows = [("主辦", PROMO_COMPANY), ("優惠內容", "全程代標服務折抵新台幣 20,000 元"), ("適用服務", "限「全程代標服務」"),
            ("不適用", "單純聲請點交、包辦點交等其他服務"), ("什麼時候折", "得標並收取服務費時，自服務費中折抵；未得標不收取服務費，亦不予折抵"),
            ("名額", "限量 30 張，送完即止，以 LINE@ 領取紀錄為準"), ("活動期間", "即日起至 2027/2/5（除夕）23:59 止，以簽訂委託書之日期為準"),
            ("怎麼領", "加入 LINE@（@635nftwk）領券，簽訂委託時出示"), ("使用限制", "每一案件限用一張，每張限用一次，不得轉讓、不得與其他優惠併用；不得兌換現金、不找零"),
            ("收費依據", "服務費依委託書約定之收費標準計算；優惠內容以委託書記載為準"),
            ("資料來源與更新日", f"{PROMO_COMPANY}活動辦法定稿；更新日 {PROMO_UPDATED}")]
    tbl = '<table class="pm-tbl">' + "".join(f"<tr><th>{e(k)}</th><td>{e(v)}</td></tr>" for k, v in rows) + "</table>"
    faq = "".join(f"<details open><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in PROMO_FAQ)
    notice = '<p class="pm-end">本活動已取消，不再發放代標券。服務與收費請見<a href="/fees">服務與收費</a>，有問題歡迎 LINE@ 詢問。</p>' if ended else ""
    body = ('<nav class="bc"><a href="/">首頁</a> › 年前上車活動</nav><div class="pm">' + notice +
            '<section class="pm-hero"><p class="eb">104法拍網・限時活動</p><h1>年前上車｜2 萬代標券</h1>'
            '<p class="lead">委託全程代標，得標收費時折 20,000 元</p>'
            '<p class="pm-tag">限量 30 名｜至 2027/2/5 除夕</p>' + ("" if ended else cta) +
            f'<p class="pm-upd">最後更新：{PROMO_UPDATED}</p></section>'
            f'<section class="box pm-ans"><h2>活動重點</h2><p>{e(answer)}</p>{tbl}</section>'
            '<figure class="pm-img"><img src="/img/promo/nianqian-4x5.jpg" width="1080" height="1350" alt="年前上車｜2 萬代標券：委託全程代標，得標收費時折 20,000 元，限量 30 名，至 2027/2/5 除夕" loading="lazy"></figure>'
            '<section class="box pm-rules" id="rules"><h2>※ 活動辦法</h2><ol>' + "".join(f"<li>{e(r)}</li>" for r in PROMO_RULES) + '</ol>'
            f'<p class="pm-sign">{e(PROMO_SIGN)}</p></section>'
            f'<section class="box" id="faq"><h2>常見問題</h2>{faq}</section>'
            f'<section class="box pm-contact" id="contact"><h2>主辦與聯絡</h2><p class="pm-sign">{e(PROMO_COMPANY)}</p>'
            f'<p><a href="tel:0918313888">黃先生 Pitt {PHONE_P}</a><a href="tel:0986678928">林小姐 Anna {PHONE_A}</a><a href="{line}" target="_blank" rel="noopener">LINE@ @635nftwk（lin.ee/Y2bGSIB）</a></p>'
            + ("" if ended else cta) + '</section>'
            '<section class="box areas"><h2>延伸閱讀</h2><a href="/fees">服務與收費</a><a href="/process">購屋流程</a><a href="/learn/proxy-bid-process">委託代標怎麼進行</a><a href="/about">關於我們</a></section></div>')
    desc = "年前上車｜2 萬代標券：委託全程代標，得標並收取服務費時折抵 20,000 元，限量 30 張，至 2027/2/5（除夕）。加 LINE@ @635nftwk 領券。主辦：" + PROMO_COMPANY
    org = {"@context": "https://schema.org", "@type": "Organization", "@id": url + "#org", "name": PROMO_COMPANY, "alternateName": "104法拍網", "url": SITE + "/",
           "telephone": ["+886-918-313-888", "+886-986-678-928"],
           "sameAs": [PROMO_LINE]}
    svc = {"@context": "https://schema.org", "@type": "Service", "name": "法拍屋全程代標服務", "serviceType": "法拍屋代標", "areaServed": "TW", "provider": {"@id": url + "#org"},
           "offers": {"@type": "Offer", "name": "年前上車｜2 萬代標券", "url": url,
                      "description": "委託全程代標，得標並收取服務費時自服務費中折抵新台幣 20,000 元；未得標不收取服務費，亦不予折抵。限量 30 張，以簽訂委託書之日期為準。",
                      "priceSpecification": {"@type": "PriceSpecification", "price": "-20000", "priceCurrency": "TWD", "description": "自服務費中折抵新台幣 20,000 元"},
                      "validFrom": "2026-11-18", "validThrough": "2027-02-05T23:59:00+08:00", "inventoryLevel": {"@type": "QuantitativeValue", "value": 30},
                      "availability": "https://schema.org/LimitedAvailability", "seller": {"@id": url + "#org"}}}
    bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "首頁", "item": SITE + "/"}, {"@type": "ListItem", "position": 2, "name": "年前上車活動", "item": url}]}
    fq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in PROMO_FAQ]}
    return page(f"年前上車｜2 萬代標券｜全程代標得標折 20,000 元・限量 30 名・至 2027/2/5｜{NAME}", desc, "/promo", body, [org, svc, bc, fq], SITE + "/img/promo/nianqian-4x5.jpg", PROMO_CSS) if not ended else page("年前上車活動已取消｜" + NAME, "年前上車代標券活動已取消。", "/promo", '<nav class="bc"><a href="/">首頁</a> › 活動</nav><h1>年前上車活動已取消</h1>' + notice).replace("index,follow,max-image-preview:large,max-snippet:-1", "noindex,follow")

def promo_banner():
    """首頁最上方活動橫幅：活動期間（至 2027/2/5）才出現，過期自動消失"""
    if _today() > PROMO_END: return ""
    href = e("/promo?utm_source=tomin104&utm_medium=home_banner&utm_campaign=nianqian2w")
    return ('<!--PROMO:start--><a class="promo-bar" href="' + href + '" style="display:block;background:#18354b;color:#fff;text-align:center;text-decoration:none;'
            'padding:10px 12px;font-size:clamp(14px,3.9vw,16px);line-height:1.5;font-weight:700;border-bottom:3px solid #d9b97a">'
            '<span style="color:#f1d48f">年前上車｜2 萬代標券</span>（限量 30 名，至 2/5 除夕）'
            '<span style="display:inline-block;margin-left:6px;background:#d9b97a;color:#18354b;border-radius:999px;padding:2px 12px;font-size:14px">看活動辦法 →</span></a><!--PROMO:end-->')

exec(compile(open("learn.py", encoding="utf-8").read(), "learn.py", "exec"))
exec(compile(open("helper.py", encoding="utf-8").read(), "helper.py", "exec"))

if __name__ == "__main__":
    for d in ("site/h", "site/area"): shutil.rmtree(d, ignore_errors=True)
    write("site/list.html", index_page(True))
    urls = [("/", 1.0), ("/list", 0.9), ("/member", 0.5)]
    for x in ITEMS:
        write(f'site/h/{x["編號"]}.html', detail_page(x)); urls.append((f'/h/{x["編號"]}', 0.8, lastmod(x)))
    ng, nr = write_gone({x["編號"] for x in ITEMS}); urls += GONE_URLS
    areas = {}
    for x in ITEMS: areas.setdefault(area_of(x), []).append(x)
    shutil.rmtree("site/c", ignore_errors=True)
    for ck, cg in community_groups().items():
        write(f"site/c/{ck}.html", community_page(ck, cg))
        if cg["cur"]: urls.append((f"/c/{slug(ck)}", 0.8))   # 2026-11-19 沒有待拍物件的社區頁先不送 sitemap
    for a, xs in areas.items():
        write(f"site/area/{a}.html", area_page(a, xs)[1])
        if len(xs) >= 3: urls.append((f"/area/{slug(a)}", 0.7))   # 2026-11-19 不到 3 件的區域頁內容太少，先不送 sitemap
    for c in CITIES:
        write(f"site/{c[0]}.html", city_page(*c)); urls.append((f"/{c[0]}", 0.9))
        if c[0] != "greater-taipei":
            for t in TYPES:
                if len(type_items(c, t[2])) >= 3:
                    write(f"site/{c[0]}-{t[0]}.html", type_page(c, t)); urls.append((f"/{c[0]}-{t[0]}", 0.8))
    write("site/new.html", list_page("/new", "本週新增法拍屋", "最近 7 天新上架的法拍屋，含拍次、開標日期與底標價。", new_items())); urls.append(("/new", 0.8))
    write("site/changes.html", list_page("/changes", "降價・降拍更新法拍屋", "最近 7 天價格下降或拍次往後的法拍屋。", changed_items())); urls.append(("/changes", 0.8))
    write("site/new-house.html", list_page("/new-house", "10年內新屋法拍屋", "屋齡 10 年以內的法拍屋，由新到舊排列，含拍次、開標日期與底標價。", sorted([x for x in ITEMS if _age(x) is not None and _age(x) <= 10], key=lambda x: (_age(x), date_key(x))))); urls.append(("/new-house", 0.8))
    write("site/fees.html", fees_page()); urls.append(("/fees", 0.8))
    write("site/about.html", about_page()); urls.append(("/about", 0.7))
    write("site/promo.html", promo_page())
    if _today() <= PROMO_END: urls.append(("/promo", 0.8))
    write_learn(urls)
    day = UPDATED[:10]
    write("site/sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "".join(f"<url><loc>{e(SITE + u[0])}</loc>" + (f"<lastmod>{u[2] if len(u) > 2 else day}</lastmod>" if len(u) < 3 or u[2] else "") + f"<priority>{u[1]}</priority></url>\n" for u in urls) + "</urlset>\n")
    write("site/robots.txt", "".join(f"User-agent: {b}\nAllow: /\n\n" for b in ["*", "Googlebot", "Bingbot", "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "PerplexityBot", "Google-Extended", "Applebot-Extended"]) + f"Sitemap: {SITE}/sitemap.xml\n")
    write("site/llms.txt", f"# {NAME}\n\n> Pitt & Anna｜104法拍網團隊（財欣不動產管理顧問有限公司）的法拍屋、金拍屋資訊網站，提供拍次、開標日期、底標價、法院筆錄；全台都有服務：投標諮詢、全程代標、聲請點交／包辦點交。資料每日更新（{UPDATED}）。\n\n"
          f"## 主要頁面\n- [物件列表]({SITE}/list): 全部法拍屋物件與搜尋\n" + "".join(f"- [{c[3]}]({SITE}/{c[0]}): {c[4]}法拍屋最新物件\n" for c in CITIES) + "".join(f"- [{a}法拍屋]({SITE}/area/{slug(a)}): {len(xs)}筆\n" for a, xs in sorted(areas.items())) +
          f"\n## 服務與收費\n- [服務與收費]({SITE}/fees): 聲請點交 50,000 元；包辦點交 120,000 元；全程代標 2% 到 5%（300 萬元以下固定 10 萬元；超過 300 萬元至 600 萬元最低 12 萬元）；不點交、部分點交、持分案件另議\n- [購屋流程]({SITE}/process): 法拍屋 9 個步驟\n- [關於我們]({SITE}/about): 黃先生 Pitt 與林小姐 Anna 夫妻雙人代標顧問\n- [年前上車｜2 萬代標券]({SITE}/promo): 財欣不動產管理顧問有限公司活動，委託全程代標、得標收費時折抵 20,000 元，限量 30 張，至 2027/2/5（除夕）23:59，加 LINE@ @635nftwk 領券\n"
          + "\n## 法拍小教室\n" + "".join(f"- [{t}]({SITE}/learn/{s}): {l}\n" for s, t, l, _ in LEARN)
          + "\n## 類型專區\n" + "".join(f"- [{c[1]}{t[1]}法拍屋]({SITE}/{c[0]}-{t[0]})\n" for c in CITIES if c[0] != "greater-taipei" for t in TYPES if len(type_items(c, t[2])) >= 3)
          + f"\n## 聯絡\n- 黃先生 Pitt：{PHONE_P}\n- 林小姐 Anna：{PHONE_A}\n- LINE@：https://lin.ee/Y2bGSIB\n- 服務範圍：全台都有服務\n- {COMPANY}\n")
    write_home()
    write("site/post.html", post_page())
    write("site/helper.html", helper_page())
    write("site/member.html", member_page())
    # 2026-11-25 舊的縣市／類型頁（這次沒產生的）刪掉，301 到該縣市頁或首頁，避免留著舊品牌、舊按鈕
    live_c = {c[0] for c in CITIES}; red = []
    for fn in sorted(os.listdir("site")):
        stem = fn[:-5] if fn.endswith(".html") else ""
        base = next((c for c in sorted(ALL_CITY_SLUGS, key=len, reverse=True) if stem == c or stem.startswith(c + "-")), None)
        if not base or os.path.normpath("site/" + fn) in WRITTEN: continue
        os.remove("site/" + fn); red.append(f"/{stem} " + (f"/{base}" if base in live_c else "/") + " 301")
    if red: open("site/_redirects", "a", encoding="utf-8").write("".join(r + "\n" for r in red))
    print("舊縣市／類型頁轉址:", len(red))
    write("site/404.html", page("找不到頁面｜" + NAME, "找不到這個頁面，請回到物件列表。", "/404", '<h1>找不到頁面</h1><p><a href="/list">回到法拍屋物件列表</a></p>'))
    print("pages:", len(urls), "已下架頁:", ng, "轉址:", nr)
