# 為每個物件產生分享用封面圖 site/og/<編號>.jpg（LINE/FB 分享預覽）
import json, os, re, html
from playwright.sync_api import sync_playwright

D = json.load(open("site/data.json", encoding="utf-8"))
os.makedirs("site/og", exist_ok=True)

def area(x): return x["區域"].split("-")[0]
def deliver(x):
    m = re.search(r"點交情形→([^●\n]+)", x.get("資訊", {}).get("筆錄", ""))
    v = m.group(1).strip() if m else ""
    return "不點交" if v.startswith("不點交") else "點交" if v.startswith("點交") else ""
def short_addr(x):
    a = re.sub(r"【[^】]*】", "", x["地址"]).strip()
    return a[:22]

TPL = """<html><body style="margin:0;width:1200px;height:630px;overflow:hidden;font-family:'Noto Sans CJK TC','Noto Sans CJK HK',sans-serif;background:radial-gradient(circle at 85% 15%,#24406b,#0b1626 70%);position:relative;color:#fff">
<div style="position:absolute;left:50px;top:34px;font-size:30px;font-weight:700;letter-spacing:2px">透明房訊｜104法拍網</div>
<div style="position:absolute;right:50px;top:30px;background:#ff7a1a;color:#fff;font-size:34px;font-weight:900;padding:6px 24px;border-radius:30px">法拍屋</div>
<div style="position:absolute;left:46px;top:100px;font-size:118px;font-weight:900;line-height:1.1;color:#ff7a1a;-webkit-text-stroke:12px #fff;paint-order:stroke fill;text-shadow:0 7px 0 rgba(0,0,0,.35)">{{rnd}}</div>
<div style="position:absolute;left:50px;top:268px;font-size:50px;font-weight:900;line-height:1.25;width:1100px">{{addr}}</div>
<div style="position:absolute;left:50px;top:350px;font-size:34px;font-weight:700;color:#f5c542">{{meta}}</div>
<div style="position:absolute;left:50px;top:420px;background:#fff;color:#0b1626;border-radius:30px;padding:8px 34px;font-size:78px;font-weight:900;line-height:1.2"><span style="font-size:36px;color:#666;margin-right:12px">底價</span><span style="color:#d62828">{{price}}</span></div>
<div style="position:absolute;left:50px;top:560px;font-size:32px;font-weight:800;color:#18d6c0">{{foot}}</div>
</body></html>"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1200, "height": 630})
    n = 0
    for x in D["104"]:
        inf = x.get("資訊", {})
        r = inf.get("拍次", "")
        rnd = f"第{r}拍" if r.isdigit() else "法拍屋"
        d = deliver(x)
        if d: rnd += f"｜{d}"
        meta = " ・ ".join(filter(None, [area(x), x.get("類型", ""), x.get("格局坪數", ""), ("開標 " + inf["開標日期"]) if inf.get("開標日期") else ""]))
        price = re.sub(r"^售", "", x.get("價格", "")) or "洽詢"
        t = TPL
        for k, v in dict(rnd=rnd, addr=short_addr(x), meta=meta, price=price, foot="tomin104.com　雙人顧問・代標諮詢").items():
            t = t.replace("{{" + k + "}}", html.escape(v))
        pg.set_content(t)
        pg.screenshot(path=f"site/og/{x['編號']}.jpg", type="jpeg", quality=82)
        n += 1
    b.close()
print("og:", n)
