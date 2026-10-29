"""由 site/data.json + site/photos.json 產生全站靜態頁面（SEO / AI 搜尋友善）
輸出：index.html、h/<編號>.html、area/<地區>.html、sitemap.xml、robots.txt、llms.txt
"""
import html, json, os, re, shutil, urllib.parse, datetime

SITE = "https://tomin104.com"          # 網站正式網址
NAME = "透明房訊｜104法拍網"
PHONE_A, PHONE_P = "0986-678-928", "0918-313-888"
LINKS = {
    "LINE": "https://line.me/ti/p/MJcPvp3nG8",
    "粉絲專頁": "https://www.facebook.com/share/1CnLq9vuJd/?mibextid=wwXIfr",
    "YouTube": "https://youtube.com/@anna-n9999?si=laOYfE2Bm2VMPYDa",
    "LINE 社群": "https://line.me/ti/g2/6-QeB1Co7tP6e-Qhln_j0swFD4q0ZIFqdSmUDQ?utm_source=invitation&utm_medium=link_copy&utm_campaign=default",
}
ADDR = ["新北市土城區金城路二段396號11樓", "桃園市桃園區莊敬路一段346號4樓"]
PHOTO_BASE = "https://www.104woo.com.tw/"

D = json.load(open("site/data.json", encoding="utf-8"))
ITEMS = sorted(D["104"], key=lambda x: {"台北": 0, "新北": 1, "桃園": 2}.get(x["區域"][:2], 3))
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
    return [PHOTO_BASE + urllib.parse.quote(p, safe="/") for p in v]
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
    m = re.search(r"底標價[：:]\s*([\d.,]+)\s*(億|萬)?", x.get("資訊", {}).get("拍賣紀錄", "").split("\n")[0])
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

CSS = """*{box-sizing:border-box}body{margin:0;font-family:"Noto Sans TC","Microsoft JhengHei",sans-serif;color:#222;background:#f6f6f4;line-height:1.6}
a{color:#1f3a4d}header.top{background:#1f3a4d;color:#fff;padding:14px 16px}header.top a{color:#fff;text-decoration:none;font-weight:700;font-size:18px}
header.top small{display:block;opacity:.8;font-weight:400;font-size:13px}
main{max-width:1100px;margin:0 auto;padding:16px}nav.bc{font-size:13px;color:#666;margin-bottom:10px}nav.bc a{color:#666}
h1{font-size:22px;line-height:1.4;margin:6px 0}h2{font-size:18px;margin:0 0 10px}
.box{background:#fff;border:1px solid #e2e2de;border-radius:8px;padding:16px;margin-bottom:16px}
.tag{display:inline-block;font-size:12px;padding:1px 8px;border-radius:10px;background:#e8eef2;color:#1f3a4d;margin-right:6px}
.price{font-size:28px;font-weight:700;color:#b3261e;margin:6px 0}.price s{font-size:15px;font-weight:400;color:#999;margin-right:8px}
table{width:100%;border-collapse:collapse;font-size:15px}td,th{padding:8px 6px;border-bottom:1px solid #eee;text-align:left;vertical-align:top}td:first-child,th{color:#666;width:120px;font-weight:400}
.gal{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px}.gal img{width:100%;height:170px;object-fit:cover;border-radius:6px;background:#e8eef2;display:block}.gal img:first-child{grid-column:1/-1;height:auto;max-height:460px}
.noimg{height:160px;background:#e8eef2;color:#6b7c88;display:flex;align-items:center;justify-content:center;border-radius:6px}
.notes{white-space:pre-line}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px}
.card{background:#fff;border:1px solid #e2e2de;border-radius:8px;overflow:hidden;text-decoration:none;color:inherit;display:block}
.card img,.card .noimg{width:100%;height:160px;object-fit:cover;display:block;border-radius:0}.card .b{padding:10px 12px}.card h3{margin:0 0 4px;font-size:15px;line-height:1.4}
.card .m{font-size:13px;color:#666}.card .p{margin-top:6px;font-size:17px;font-weight:700;color:#b3261e}.card .p s{font-size:13px;font-weight:400;color:#999;margin-right:6px}
.bar{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}#n{scroll-margin-top:70px}.bar input,.bar select{padding:9px 10px;border:1px solid #ccc;border-radius:6px;font-size:16px;background:#fff}.bar input{flex:1;min-width:180px}
.btn{display:inline-block;margin:6px 8px 0 0;padding:9px 15px;border-radius:6px;background:#1f3a4d;color:#fff!important;text-decoration:none;font-size:14px}.btn.line{background:#06c755}
.cv{position:relative}.rd{position:absolute;left:8px;top:8px;background:#b3261e;color:#fff;padding:2px 10px;border-radius:12px;font-size:13px;font-weight:700}.rd.n{background:#1f3a4d}
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
@media(max-width:640px){h1{font-size:19px}.hero2 h1{font-size:26px}.hd nav{display:none}.hd{justify-content:space-between}.hin{padding:40px 14px 30px}.tbl .rt{display:none}}"""

ORG = {
    "@context": "https://schema.org", "@type": "RealEstateAgent", "@id": SITE + "/#org",
    "name": NAME, "alternateName": ["104法拍網", "透明房訊", "一零四法拍網股份有限公司"], "url": SITE + "/",
    "telephone": ["+886-918-313-888", "+886-986-678-928", "+886-2-2270-0888", "+886-3-338-8220"],
    "address": [{"@type": "PostalAddress", "streetAddress": "金城路二段396號11樓", "addressLocality": "土城區", "addressRegion": "新北市", "addressCountry": "TW"},
                {"@type": "PostalAddress", "streetAddress": "莊敬路一段346號4樓", "addressLocality": "桃園區", "addressRegion": "桃園市", "addressCountry": "TW"}],
    "areaServed": "TW", "sameAs": list(LINKS.values())[1:3],
    "knowsAbout": ["法拍屋", "法拍屋代標", "不點交物件處理", "撤封代償", "產權調查", "法拍屋貸款"],
}

FAB = (f'<div class="fab"><a href="tel:0918313888" aria-label="電話諮詢"><svg width="26" height="26" viewBox="0 0 24 24" fill="#fff"><path d="M6.6 10.8c1.4 2.8 3.8 5.1 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1C10.6 21 3 13.4 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1l-2.3 2.2z"/></svg></a>'
       f'<a class="l" href="{LINKS["LINE"]}" target="_blank" rel="noopener" aria-label="LINE 諮詢">LINE</a></div>')

def contact_box():
    btn = "".join(f'<a class="btn{" line" if k=="LINE" else ""}" href="{e(v)}" target="_blank" rel="noopener">{e(k)}</a>' for k, v in LINKS.items())
    return f'''<section class="box" id="contact"><h2>聯絡我們</h2>
<p><b>黃先生 Pitt</b>　<a href="tel:0918313888">{PHONE_P}</a><br><b>林小姐 Anna</b>　<a href="tel:0986678928">{PHONE_A}</a></p>
<p>透明房訊雜誌社／一零四法拍網股份有限公司<br>台北 <a href="tel:0222700888">(02)2270-0888</a>　桃園 <a href="tel:033388220">(03)338-8220</a>　傳真 (02)2274-0884</p>
<p>{e(ADDR[0])}<br>{e(ADDR[1])}</p><p>服務：法拍屋評估、代標、不點交物件處理、撤封代償、產權疑難雜症排除</p><div>{btn}</div></section>'''

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
<header class="top"><div class="hd"><a class="logo" href="/">透明房訊<i>｜</i>104法拍網</a><nav><a href="/#list">物件列表</a><a href="/#areas">地區</a><a href="/#faq">常見問題</a><a href="/#contact">聯絡我們</a></nav><a class="tel" href="tel:0918313888">電話諮詢</a><a class="lg" href="/member">登入</a><button class="mb" id="mb" type="button" aria-label="選單">☰</button></div></header>{DRAWER}
{pre}<main>{body}</main>
<footer>© {e(NAME)}　資料每日更新（{e(UPDATED)}），實際拍賣內容請以法院公告為準。</footer>{FAB if fab else ""}<script src="/ui.js" defer></script></body></html>'''

DRAWER = ('<div id="dr"><div class="bk"></div><div class="pn"><button class="x" type="button" id="dx">×</button><div style="clear:both"></div>'
          '<a href="/">首頁</a><a href="/#list">物件列表</a><a href="/#n">本週新增・降價</a><a href="/#areas">各區法拍屋</a><a href="/member">會員登入／註冊</a><a href="/member#ask">委託代標留言</a><a href="/#faq">常見問題</a>'
          f'<a href="{LINKS["LINE 社群"]}" target="_blank" rel="noopener">加入 LINE 社群</a><a href="{LINKS["粉絲專頁"]}" target="_blank" rel="noopener">粉絲專頁</a></div></div>'
          '<script>(function(){var d=document.getElementById("dr");function t(v){d.classList.toggle("on",v)}document.getElementById("mb").onclick=function(){t(true)};document.getElementById("dx").onclick=function(){t(false)};d.querySelector(".bk").onclick=function(){t(false)};d.querySelectorAll("a").forEach(function(a){a.addEventListener("click",function(){t(false)})})})()</script>')

def member_page():
    body = ('<h1>會員專區・委託代標留言</h1>'
            '<section class="box"><h2>會員登入／註冊</h2><p>會員可收藏物件、接收每週新案通知與降價提醒。Google／LINE 一鍵登入即將開放，目前請先加入 LINE 社群或直接聯絡我們，專人協助建立會員資料。</p>'
            f'<p><a class="btn line" href="{e(LINKS["LINE 社群"])}" target="_blank" rel="noopener">加入 LINE 社群</a> <a class="btn" href="tel:0918313888">電話洽詢 黃先生 Pitt</a></p></section>'
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
    badge = f'<span class="rd2">{e("｜".join(filter(None, [("第%d拍" % r) if r else "拍次洽詢", dv])))}</span>'
    img = f'<img loading="lazy" src="{e(ph[0])}" alt="{e(x["地址"])} 法拍屋照片">' if ph else '<div class="noimg">照片請洽業務</div>'
    price = re.sub(r"^售", "", x["價格"])
    old = f'<s>{e(re.sub(r"^售", "", x["原價"]))}</s>' if x["原價"] else ""
    top = "｜".join(filter(None, [inf.get("開標日期", ""), x["狀態"], "新上架" if _within(x.get("新增日", "")) else "", "降價" if _within(x.get("異動日", "")) and x.get("降價前", 0) else ""]))
    text = f'{x["地址"]} {x["區域"]} {x["類型"]} {inf.get("案號","")}'
    return (f'<a class="card" href="/h/{e(x["編號"])}" data-t="{e(text)}" data-c="{e(area_of(x)[:2])}" data-a="{e(area_of(x))}" data-y="{e(x["類型"])}" data-p="{price_num(x["價格"])}" data-r="{r}" data-d="{date_key(x)}" data-j="{e(dv)}" data-f="{first_price(x)}">'
            f'<div class="ch">{e(top)}</div><div class="cv">{img}{badge}</div>'
            f'<div class="b"><div class="m">{e(x["類型"])}｜{e(x["格局坪數"])}</div><h3>{e(x["地址"])}</h3>'
            f'<div class="pr"><span>底價</span><b>{old}{e(price)}</b></div></div></a>')

def kv(rows):
    rows = [(k, v) for k, v in rows if v]
    return "<table>" + "".join(f"<tr><td>{e(k)}</td><td>{e(v)}</td></tr>" for k, v in rows) + "</table>" if rows else ""

def detail_page(x):
    inf = dict(x.get("資訊", {}))
    notes, sched = inf.pop("筆錄", ""), inf.pop("拍賣紀錄", "")
    ph = photos(x)
    area = area_of(x)
    full_title = f'{x["地址"]}｜{area}{x["類型"]}法拍屋｜{NAME}'
    desc = (f'{area}{x["類型"]}法拍屋 {x["地址"]}，{x["格局坪數"]}，{x["價格"]}。'
            + (f'案號{inf["案號"]}，' if inf.get("案號") else "") + (f'第{inf["拍次"]}拍，' if inf.get("拍次") else "")
            + (f'開標日期{inf["開標日期"]}。' if inf.get("開標日期") else "") + "提供代標、產權調查、貸款諮詢，歡迎聯絡透明房訊104法拍網。")
    gal = ('<div class="gal">' + "".join(f'<img {"fetchpriority=high " if i==0 else "loading=lazy "}src="{e(u)}" alt="{e(x["地址"])} 法拍屋照片{i+1}">' for i, u in enumerate(ph)) + "</div>") if ph else '<div class="noimg">照片請洽業務</div>'
    pr = (f'<s>{e(x["原價"])}</s>' if x["原價"] else "") + e(x["價格"])
    tags = f'<span class="tag">{e(x["狀態"])}</span>' + (f'<span class="tag">第{e(inf["拍次"])}拍</span>' if inf.get("拍次") else "") + (f'<span class="tag">開標 {e(inf["開標日期"])}</span>' if inf.get("開標日期") else "")
    top = kv([("案號", inf.get("案號")), ("類型", x["類型"]), ("總登記坪數", inf.get("總登記坪數")), ("每坪單價", inf.get("每坪單價")), ("地址", x["地址"]), ("地區", x["區域"]), ("物件編號", x["編號"])])
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
    same = [y for y in ITEMS if y is not x and area_of(y) == area][:3]
    sim = ('<section class="box"><h2>相似物件</h2><div class="grid">' + "".join(card(y) for y in same) + "</div></section>") if same else ""
    body = (f'<nav class="bc"><a href="/">首頁</a> › <a href="/area/{slug(area)}">{e(area)}法拍屋</a> › {e(x["類型"])}</nav>'
            f'<section class="box"><h1>{e(x["地址"])}</h1><div>{tags}</div><div class="price">{pr}</div>{gal}</section>'
            f'<section class="box" id="tools" data-price="{price_num(x["價格"])}" data-addr="{e(x["地址"])}" data-id="{e(x["編號"])}"></section>'
            f'<section class="box"><h2>物件資料</h2>{top}</section>'
            + (f'<section class="box"><h2>詳細資料</h2>{det}</section>' if det else "")
            + (f'<section class="box"><h2>坪數說明</h2>{size}</section>' if size else "") + srows + nsec + contact_box() + sim)
    ld = [ORG,
          {"@context": "https://schema.org", "@type": "RealEstateListing", "name": x["地址"], "url": f'{SITE}/h/{x["編號"]}', "description": desc,
           "image": ph[:6] or None, "dateModified": UPDATED.replace(" ", "T") + ":00+08:00",
           "offers": {"@type": "Offer", "price": price_num(x["價格"]), "priceCurrency": "TWD", "availability": "https://schema.org/InStock", "seller": {"@id": SITE + "/#org"}},
           "about": {"@type": "Place", "name": x["地址"], "address": {"@type": "PostalAddress", "streetAddress": x["地址"], "addressCountry": "TW"}}},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "首頁", "item": SITE + "/"},
              {"@type": "ListItem", "position": 2, "name": area + "法拍屋", "item": f"{SITE}/area/{slug(area)}"},
              {"@type": "ListItem", "position": 3, "name": x["地址"]}]}]
    for o in ld:
        for k in [k for k, v in o.items() if v is None]: del o[k]
    ask = f'我對物件 {x["編號"]}（{x["地址"]}）有興趣，想了解代標與細節。'
    cta = (f'<div class="cta"><button class="l" id="ask" type="button">LINE 詢問此物件</button><a class="t" href="tel:0918313888">打電話</a></div>'
           f'<script>document.getElementById("ask").onclick=function(){{var b=this,t={jd(ask)};try{{navigator.clipboard.writeText(t)}}catch(e){{}};b.textContent="已複製詢問文字，開啟 LINE…";setTimeout(function(){{window.open({jd(LINKS["LINE"])},"_blank");b.textContent="LINE 詢問此物件"}},500)}};</script>')
    return page(full_title, desc, f'/h/{x["編號"]}', body + cta, ld, ph[0] if ph else None, "<style>footer{padding-bottom:90px}</style>", "", False)

FAQ = [
    ("什麼是法拍屋的「點交」與「不點交」？", "點交是指拍定後，由法院協助將房屋點交給得標人；不點交則需得標人自行處理占用問題。各物件是否點交，請見該物件的「法院筆錄」與執行公告。"),
    ("法拍屋的「拍次」是什麼意思？", "拍次是法院拍賣的次數。第一拍無人應買（流標）後，法院通常會減價再拍，實際底價與日期以各物件「拍賣紀錄」及法院公告為準。"),
    ("可以委託代標嗎？需要準備什麼？", "可以。透明房訊104法拍網提供法拍屋代標、產權調查、不點交物件處理、撤封代償與貸款諮詢，請透過電話或 LINE 聯絡黃先生 Pitt 或林小姐 Anna。"),
    ("法拍屋可以看屋嗎？", "一般法拍屋查封後無法入內參觀，可依建物平面圖推斷格局，或參考同棟樓上樓下。能看屋的物件會在資料中另行註明。"),
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
        fb += [f'{i}. {area_of(x)}｜{x["地址"]}', f'   {desc}', f'   👉 {link}?utm_source=fb', ""]
        ln += [f'{i}. {area_of(x)} {x["地址"]}', f'   {desc}', f'   {link}?utm_source=line', ""]
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
    return (f'<section class="hero2">{svg}<div class="hin"><p class="eyebrow">TOMIN REALTY · 1986 年成立</p><h1>透明房訊｜法拍屋查詢與代標</h1>'
            f'<p class="sub">讓法拍更透明，讓您安心買到好房</p>'
            f'<div class="cta2"><a class="b1" href="#list">瀏覽全部物件</a><a class="b2" href="{e(LINKS["LINE"])}" target="_blank" rel="noopener">LINE 諮詢</a></div>'
            f'<div class="stats"><span><b>{len(ITEMS)}</b>筆物件</span><span><b>每日</b>更新</span><span><b>代標</b>・產權調查・貸款諮詢</span></div>'
            f'<div class="qk"><button type="button" data-c="台北">台北</button><button type="button" data-c="新北">新北</button><button type="button" data-c="桃園">桃園</button><button type="button" data-r="3+">第3拍以上</button></div></div></section>')

def hero_html():
    h = (f'<div class="hero"><a class="l" href="{e(LINKS["LINE 社群"])}" target="_blank" rel="noopener">加入 LINE 社群，搶先看新物件</a>'
         f'<a class="f" href="{e(LINKS["粉絲專頁"])}" target="_blank" rel="noopener">追蹤粉絲專頁</a>'
         f'<a href="tel:0918313888">電話諮詢 黃先生 Pitt</a><a href="tel:0986678928">電話諮詢 林小姐 Anna</a></div>')
    nw = new_items()[:6]
    if nw: h += '<h2 class="sec">本週新增</h2><div class="grid">' + "".join(card(x) for x in nw) + "</div>"
    dr = changed_items()[:6]
    if dr: h += '<h2 class="sec">降價・降拍更新</h2><div class="grid">' + "".join(card(x) for x in dr) + "</div>"
    wk = upcoming(30)[:8]
    if wk:
        rows = "".join(f'<tr><td>{e("%d拍" % round_of(x) if round_of(x) else "—")}</td><td>{e(x["資訊"].get("開標日期", ""))}</td><td><a href="/h/{e(x["編號"])}">{e(x["地址"])}</a></td><td class="rt">{e(x["價格"])}</td></tr>' for x in wk)
        h += f'<h2 class="sec">近期開標（30 天內）</h2><table class="tbl"><tr><th>拍次</th><th>開標日期</th><th>地址</th><th class="rt">底價</th></tr>{rows}</table>'
    top = sorted([x for x in ITEMS if round_of(x) >= 3], key=lambda x: (price_num(x["價格"]), date_key(x)))[:6]
    if top: h += '<h2 class="sec">第 3 拍以上精選</h2><div class="grid">' + "".join(card(x) for x in top) + "</div>"
    return h

def index_page():
    cities = sorted({area_of(x)[:2] for x in ITEMS}, key=lambda c: ({"台北": 0, "新北": 1, "桃園": 2}.get(c, 3), c))
    types = sorted({x["類型"] for x in ITEMS})
    areas = {}
    for x in ITEMS: areas.setdefault(area_of(x), []).append(x)
    opts = lambda a: "".join(f"<option>{e(i)}</option>" for i in a)
    al = "".join(f'<a href="/area/{slug(a)}">{e(a)}（{len(v)}）</a>' for a, v in sorted(areas.items(), key=lambda t: ({"台北": 0, "新北": 1, "桃園": 2}.get(t[0][:2], 3), t[0])))
    faq = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in FAQ)
    js = """<script>(function(){var $=function(i){return document.getElementById(i)},g=$('g'),n=$('n'),cards=[].slice.call(g.children),orig=cards.slice();
var F=['q','c','a','y','r','j','pr','s'];
function rk(k){return k.indexOf('台北')==0?0:k.indexOf('新北')==0?1:k.indexOf('桃園')==0?2:3}
function areas(){var c=$('c').value,seen={},o='<option value="">地區不拘</option>';cards.forEach(function(d){if((!c||d.dataset.c===c)&&!seen[d.dataset.a]){seen[d.dataset.a]=1}});Object.keys(seen).sort(function(a,b){return rk(a)-rk(b)||(a<b?-1:1)}).forEach(function(k){o+='<option>'+k+'</option>'});var cur=$('a').value;$('a').innerHTML=o;if(seen[cur])$('a').value=cur}
function f(){var k=$('q').value.trim(),c=$('c').value,a=$('a').value,y=$('y').value,r=$('r').value,j=$('j').value,pr=$('pr').value,s=$('s').value,cnt=0,lo=0,hi=1e9;if(pr){var p=pr.split('-');lo=+p[0]*10000;hi=+p[1]*10000}
cards.forEach(function(d){var D=d.dataset,p=+D.p,rr=+D.r,ok=(!k||D.t.indexOf(k)>-1)&&(!c||D.c===c)&&(!a||D.a===a)&&(!y||D.y===y)&&(!r||(r==='4'?rr>=4:r==='3+'?rr>=3:rr===+r))&&(!j||D.j===j)&&(!pr||(p>=lo&&p<hi));d.style.display=ok?'':'none';if(ok)cnt++});
var arr=s?cards.slice().sort(function(x,y){var X=x.dataset,Y=y.dataset;return s==='pa'?X.p-Y.p:s==='pd'?Y.p-X.p:s==='da'?X.d-Y.d:Y.d-X.d}):orig;arr.forEach(function(d){g.appendChild(d)});n.textContent='共 '+cnt+' 筆'}
[].forEach.call(document.querySelectorAll('.qk button'),function(b){b.addEventListener('click',function(){if(b.dataset.c){$('c').value=b.dataset.c;areas()}if(b.dataset.r){$('r').value=b.dataset.r;chipsOn()}f();$('list').scrollIntoView({behavior:'smooth'})})});
var rc=$('rc');function chipsOn(){[].forEach.call(rc.querySelectorAll('button'),function(b){b.className=b.dataset.v===$('r').value?'on':''})}rc.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;$('r').value=b.dataset.v;chipsOn();f()});
var go=$('go');function done(){if(document.activeElement)document.activeElement.blur();f();$('n').scrollIntoView({behavior:'smooth',block:'start'})}go.addEventListener('click',done);$('q').addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();done()}});
F.forEach(function(i){$(i).addEventListener('input',function(){if(i==='c')areas();f()})});
$('rs').addEventListener('click',function(){F.forEach(function(i){$(i).value=''});areas();chipsOn();f()});areas();chipsOn();f()})();</script>"""
    body = (f'<p>透明房訊／104法拍網提供全台法拍屋、金拍屋物件資訊，含拍次、開標日期、底標價與法院筆錄，並提供代標、產權調查、不點交物件處理與貸款諮詢。目前共 {len(ITEMS)} 筆物件。</p>'
            + hero_html() + '<h2 class="sec" id="list">全部法拍屋物件</h2>' +
            f'<div class="chips" id="rc"><b>拍次：</b><button type="button" data-v="" class="on">全部（{len(ITEMS)}）</button>'
            f'<button type="button" data-v="1">第1拍（{sum(1 for x in ITEMS if round_of(x)==1)}）</button><button type="button" data-v="2">第2拍（{sum(1 for x in ITEMS if round_of(x)==2)}）</button>'
            f'<button type="button" data-v="3">第3拍（{sum(1 for x in ITEMS if round_of(x)==3)}）</button><button type="button" data-v="4">第4拍以上（{sum(1 for x in ITEMS if round_of(x)>=4)}）</button></div>'
            f'<div class="bar"><input id="q" type="search" enterkeyhint="search" placeholder="搜尋地址、社區、案號…" aria-label="搜尋"><button id="go" type="button">搜尋</button><select id="c" aria-label="縣市"><option value="">縣市不拘</option>{opts(cities)}</select><select id="a" aria-label="地區"><option value="">地區不拘</option></select>'
            f'<select id="y" aria-label="類型"><option value="">類型不拘</option>{opts(types)}</select>'
            f'<input type="hidden" id="r">'
            f'<select id="j" aria-label="點交情形"><option value="">點交不拘</option><option>點交</option><option>不點交</option><option>其他</option></select>'
            f'<select id="pr" aria-label="價格"><option value="">價格不拘</option><option value="0-500">500萬以下</option><option value="500-1000">500～1000萬</option><option value="1000-2000">1000～2000萬</option><option value="2000-3000">2000～3000萬</option><option value="3000-1000000">3000萬以上</option></select>'
            f'<select id="s" aria-label="排序"><option value="">預設（雙北優先）</option><option value="pa">價格低→高</option><option value="pd">價格高→低</option><option value="da">開標日期近→遠</option><option value="dd">開標日期遠→近</option></select><button id="rs" type="button">重設</button></div>'
            f'<div id="n" class="m"></div><div class="grid" id="g">{"".join(card(x) for x in ITEMS)}</div>'
            f'<section class="box areas" id="areas"><h2>依地區找法拍屋</h2>{al}</section>'
            f'<section class="box" id="faq"><h2>法拍屋常見問題</h2>{faq}</section>' + contact_box() + js)
    ld = [ORG, {"@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": SITE + "/", "inLanguage": "zh-TW"},
          {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]},
          {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f'{SITE}/h/{x["編號"]}', "name": x["地址"]} for i, x in enumerate(ITEMS[:50])]}]
    first = next((photos(x)[0] for x in ITEMS if photos(x)), None)
    return page(f"法拍屋查詢｜法拍屋代標｜{NAME}", f"全台法拍屋、金拍屋物件查詢，含拍次、開標日期、底標價與法院筆錄；提供法拍屋代標、產權調查、不點交處理、貸款諮詢。共{len(ITEMS)}筆，每日更新。", "/", body, ld, SITE + "/og.jpg", "", hero_banner())

def area_page(a, xs):
    title = f"{a}法拍屋｜{len(xs)}筆物件｜{NAME}"
    desc = f"{a}法拍屋物件列表，共{len(xs)}筆，含拍次、開標日期、底標價與法院筆錄；提供{a}法拍屋代標、產權調查與貸款諮詢。"
    body = (f'<nav class="bc"><a href="/">首頁</a> › {e(a)}法拍屋</nav><h1>{e(a)}法拍屋（{len(xs)}筆）</h1><p>{e(desc)}</p><div class="grid">{"".join(card(x) for x in xs)}</div>' + contact_box())
    ld = [ORG, {"@context": "https://schema.org", "@type": "ItemList", "name": f"{a}法拍屋", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f'{SITE}/h/{x["編號"]}', "name": x["地址"]} for i, x in enumerate(xs)]}]
    return title, page(title, desc, f"/area/{slug(a)}", body, ld, SITE + "/og.jpg")

def write(path, s):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    open(path, "w", encoding="utf-8").write(s)

if __name__ == "__main__":
    for d in ("site/h", "site/area"): shutil.rmtree(d, ignore_errors=True)
    write("site/index.html", index_page())
    urls = [("/", 1.0), ("/member", 0.5)]
    for x in ITEMS:
        write(f'site/h/{x["編號"]}.html', detail_page(x)); urls.append((f'/h/{x["編號"]}', 0.8))
    areas = {}
    for x in ITEMS: areas.setdefault(area_of(x), []).append(x)
    for a, xs in areas.items():
        write(f"site/area/{a}.html", area_page(a, xs)[1]); urls.append((f"/area/{slug(a)}", 0.7))
    day = UPDATED[:10]
    write("site/sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "".join(f"<url><loc>{e(SITE + p)}</loc><lastmod>{day}</lastmod><priority>{pr}</priority></url>\n" for p, pr in urls) + "</urlset>\n")
    write("site/robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")
    write("site/llms.txt", f"# {NAME}\n\n> 透明房訊／一零四法拍網股份有限公司的法拍屋、金拍屋資訊網站，提供拍次、開標日期、底標價、法院筆錄，以及法拍屋代標、產權調查、不點交物件處理、撤封代償與貸款諮詢。資料每日更新（{UPDATED}）。\n\n"
          f"## 主要頁面\n- [物件列表]({SITE}/): 全部法拍屋物件與搜尋\n" + "".join(f"- [{a}法拍屋]({SITE}/area/{slug(a)}): {len(xs)}筆\n" for a, xs in sorted(areas.items())) +
          f"\n## 聯絡\n- 黃先生 Pitt：{PHONE_P}\n- 林小姐 Anna：{PHONE_A}\n- 台北 (02)2270-0888／桃園 (03)338-8220\n- 地址：{ADDR[0]}；{ADDR[1]}\n")
    write("site/post.html", post_page())
    write("site/member.html", member_page())
    write("site/404.html", page("找不到頁面｜" + NAME, "找不到這個頁面，請回到物件列表。", "/404", '<h1>找不到頁面</h1><p><a href="/">回到法拍屋物件列表</a></p>'))
    print("pages:", len(urls))
