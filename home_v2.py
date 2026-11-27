"""tomin104 首頁（2026-11-27 Anna 說「推」上線；原本是 v2 預覽）
- 主角 Pitt & Anna（Q 版）＋透明房訊實拍照；第一屏雙北桃園 3～14 天內開標倒數（開標前 2 天不打廣告、要留時間看房）
- 本人頁 /team/pitt、/team/anna，含 Person 結構化資料
- 舊首頁由 build.py 備份在 /home-old（不收錄）"""
import json, re, os, datetime, html, urllib.parse
SITE = "https://tomin104.com"
LINE = "https://lin.ee/Y2bGSIB"
YT = "https://youtube.com/@anna-n9999"
FB = "https://www.facebook.com/share/1CnLq9vuJd/?mibextid=wwXIfr"
e = lambda s: html.escape(str(s or ""), quote=True)
TW = ("台北", "新北", "桃園")

def build(D, P, write, TODAY, OLD_LD=(), CLICK_JS=""):
    OLD_LD = list(OLD_LD)

    def open_date(x):
        m = re.fullmatch(r"(\d+)/(\d+)/(\d+)", (x.get("資訊") or {}).get("開標日期", ""))
        return datetime.date(int(m[1]) + 1911, int(m[2]), int(m[3])) if m else None
    def real_photo(x):
        """實拍照：跳過海報（Media/… 的 png 多半是我們自己的海報，上面可能是舊底價），用現場照"""
        v = P.get(x["編號"][2:], []) or []
        if isinstance(v, str): v = [v]
        st = [p for p in v if p.startswith("wwwphoto/")]          # 法院／透明房訊現場照，沒有海報字
        v = st or [p for p in v[1:] if not p.lower().endswith(".png")]   # 沒有就跳過第一張（多半是海報）
        return ["https://www.104woo.com.tw/" + urllib.parse.quote(p, safe="/") for p in v]
    def price(x): return re.sub(r"^售", "", x.get("價格", ""))
    def name(x):
        a = (x.get("資訊") or {}).get("完整地址") or x["地址"]
        return re.sub(r"^(台北市|新北市|桃園市)", "", a)

    soon = []
    for x in D["104"]:
        d = open_date(x)
        if x["區域"][:2] in TW and d and 3 <= (d - TODAY).days <= 14 and real_photo(x):   # 11/27 營運總管：開標前 2 天不打廣告，且要留時間看房
            soon.append((d, x))
    soon.sort(key=lambda t: (t[0], TW.index(t[1]["區域"][:2])))
    cnt = {c: sum(1 for _, x in soon if x["區域"][:2] == c) for c in TW}

    def card(d, x):
        inf = x.get("資訊") or {}
        n = (d - TODAY).days
        left = "今天開標" if n == 0 else f"還有 <b>{n}</b> 天"
        ph = real_photo(x)
        per = inf.get("每坪單價", "")
        rd = inf.get("拍次", "")
        dj = "點交" if "點交" in (inf.get("點交情形") or inf.get("筆錄", "")[:200]) and "不點交" not in (inf.get("筆錄", "")[:200]) else ""
        q = urllib.parse.quote(f"我想問 {name(x)}（{x['編號']}）同社區的實登行情")
        return (f'<article class="tk" data-c="{e(x["區域"][:2])}">'
                f'<a class="tk-img" href="/h/{e(x["編號"])}"><img loading="lazy" src="{e(ph[0])}" alt="{e(name(x))} 實拍照">'
                f'<span class="tk-left">{left}</span></a>'
                f'<div class="tk-body"><p class="tk-date">{d.month}/{d.day}（{"一二三四五六日"[d.weekday()]}）開標'
                + (f'<span class="tk-rd">第{e(rd)}拍</span>' if rd else "") + '</p>'
                f'<h3><a href="/h/{e(x["編號"])}">{e(name(x))}</a></h3>'
                f'<p class="tk-meta">{e(x["區域"].replace("-", "｜"))}｜{e(inf.get("總登記坪數") or x.get("格局坪數", ""))}</p>'
                f'<div class="tk-price"><div><small>底價</small><b>{e(price(x))}</b></div>'
                + (f'<div><small>每坪</small><b class="sm">{e(per.replace("萬/坪", " 萬"))}</b></div>' if per else "") + '</div>'
                '<p class="tk-see">想投標請先到現場看房</p>'
                f'<a class="tk-ask" href="{LINE}" target="_blank" rel="noopener">問同社區實登差價 →</a>'
                '</div></article>')

    TOP = ('<header class="hd"><div class="wrap hd-in"><a class="logo" href="/"><img src="/home/assets/pitt_anna.webp" alt="" width="44" height="44">'
           '<span><b>Pitt &amp; Anna</b><small>104法拍網團隊</small></span></a>'
           '<nav><a href="/list">找物件</a><a href="/#countdown">3～14 天內開標</a><a href="/learn">法拍小教室</a><a href="/fees">收費</a><a href="/team/pitt">認識我們</a></nav>'
           f'<a class="hd-line" href="{LINE}" target="_blank" rel="noopener">LINE@ 問物件</a></div></header>')
    FOOT = ('<footer class="ft"><div class="wrap"><p><b>Pitt &amp; Anna 104法拍網團隊</b>｜你的法拍購屋夥伴</p>'
            '<p>黃先生 Pitt <a href="tel:0918313888">0918-313-888</a>　林小姐 Anna <a href="tel:0986678928">0986-678-928</a>　'
            f'<a href="{LINE}" target="_blank" rel="noopener">LINE@</a>　<a href="{YT}" target="_blank" rel="noopener">YouTube</a>　<a href="{FB}" target="_blank" rel="noopener">粉絲專頁</a></p>'
            '<p class="ft-s">經紀業：財欣不動產管理顧問有限公司｜物件資料來源：透明房訊，每日更新；拍賣條件以法院公告為準，遇停拍、撤回、拍定即失效。</p></div></footer>')
    CSS = """
    *{box-sizing:border-box}body{margin:0;font-family:"Noto Sans TC","Microsoft JhengHei",sans-serif;color:#18222d;background:#fff;line-height:1.6}
    a{color:inherit}.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
    .hand{font-family:"LXGW WenKai TC","Noto Sans TC",sans-serif}
    .hd{position:sticky;top:0;z-index:9;background:#fff;border-bottom:3px solid #12324f}
    .hd-in{display:flex;align-items:center;gap:18px;min-height:64px}.logo{display:flex;align-items:center;gap:10px;text-decoration:none}
    .logo img{border-radius:50%;object-fit:cover;object-position:50% 20%;background:#dbe9f7}.logo b{display:block;font-size:19px;color:#12324f;line-height:1.1}.logo small{color:#5b6875;font-size:12px}
    .hd nav{display:flex;gap:18px;margin-left:auto}.hd nav a{text-decoration:none;font-weight:700;font-size:15px}.hd nav a:hover{color:#e2553b}
    .hd-line{background:#06c755;color:#fff;text-decoration:none;font-weight:700;border-radius:999px;padding:8px 16px;font-size:15px;white-space:nowrap}
    .hero{background:#12324f;color:#fff;padding:26px 0 30px}
    .hero-top{display:flex;align-items:flex-end;gap:22px;flex-wrap:wrap}
    .hero-who{display:flex;align-items:center;gap:14px}.hero-who img{width:96px;height:96px;border-radius:18px;object-fit:cover;object-position:50% 15%;background:#dbe9f7;border:3px solid #ffd84d}
    .hero h1{margin:0;font-size:34px;line-height:1.25}.hero h1 mark{background:linear-gradient(transparent 58%,#ffd84d 58%);color:inherit;padding:0 2px}
    .hero-sub{margin:6px 0 0;color:#c8d6e5;font-size:15px}
    .hero-k{margin-left:auto;display:flex;gap:10px}.hero-k a{background:#fff;color:#12324f;text-decoration:none;border-radius:12px;padding:8px 14px;text-align:center;font-weight:700;min-width:84px}
    .hero-k a b{display:block;font-size:24px;color:#e2553b;line-height:1.1}.hero-k a small{font-size:12px;color:#5b6875}
    .cd-head{display:flex;align-items:center;gap:12px;margin:22px 0 12px;flex-wrap:wrap}.cd-head h2{margin:0;font-size:22px}
    .cd-head h2 span{background:#ffd84d;color:#12324f;border-radius:6px;padding:0 8px;margin-right:6px}
    .chips{display:flex;gap:8px;margin-left:auto}.chips button{border:2px solid #fff;background:transparent;color:#fff;border-radius:999px;padding:4px 14px;font-size:15px;font-weight:700;cursor:pointer}
    .chips button[aria-pressed=true]{background:#ffd84d;border-color:#ffd84d;color:#12324f}
    .board{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.tk{min-width:0}
    .tk{background:#fff;color:#18222d;border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
    .tk-img{position:relative;display:block;aspect-ratio:4/3;background:#e7edf3}.tk-img img{width:100%;height:100%;object-fit:cover;display:block}
    .tk-left{position:absolute;left:10px;top:10px;background:#e2553b;color:#fff;border-radius:8px;padding:3px 10px;font-weight:700;font-size:14px}.tk-left b{font-size:20px}
    .tk-body{padding:10px 14px 12px;display:flex;flex-direction:column;flex:1}
    .tk-date{margin:0;color:#e2553b;font-weight:700;font-size:14px}.tk-rd{white-space:nowrap;margin-left:8px;background:#eef3f8;color:#12324f;border-radius:6px;padding:0 6px;font-size:12px}
    .tk h3{margin:4px 0 2px;font-size:16px;line-height:1.4}.tk h3 a{text-decoration:none}.tk-meta{margin:0;color:#5b6875;font-size:13px}
    .tk-price{display:flex;gap:16px;margin:8px 0 6px;align-items:baseline}.tk-price small{display:block;color:#5b6875;font-size:12px}.tk-price b{font-size:22px;color:#12324f}.tk-price b.sm{font-size:16px}
    .tk-see{margin:0 0 6px;font-size:13px;font-weight:700;color:#12324f;background:#fff6c7;border-radius:6px;padding:3px 8px;margin-top:auto}.tk-ask{font-size:13px;font-weight:700;color:#0a8f3c;text-decoration:none;border-top:1px dashed #cfd8e1;padding-top:8px}
    .more{text-align:center;margin:18px 0 0}.more a{display:inline-block;background:#ffd84d;color:#12324f;font-weight:700;text-decoration:none;border-radius:999px;padding:10px 22px}
    .sec{padding:40px 0}.sec h2{font-size:26px;margin:0 0 6px}.sec .lead{color:#5b6875;margin:0 0 20px}
    .duo{display:grid;grid-template-columns:320px 1fr;gap:28px;align-items:center}
    .duo img{width:100%;border-radius:20px;background:#dbe9f7}
    .ppl{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}
    .pp{border:2px solid #12324f;border-radius:14px;padding:14px 16px;text-decoration:none;display:block}.pp b{font-size:18px}.pp p{margin:4px 0 0;font-size:14px;color:#3d4955}
    .pp .tel{display:inline-block;margin-top:6px;font-weight:700;color:#e2553b}
    .notes{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
    .note{background:#fff6c7;border-radius:4px;padding:18px 18px 16px;box-shadow:0 6px 14px rgba(18,50,79,.12);text-decoration:none;position:relative;transform:rotate(-1deg)}
    .note:nth-child(2){transform:rotate(1deg);background:#e3f4ff}.note:nth-child(3){background:#ffe6de}
    .note:before{content:"";position:absolute;top:-10px;left:50%;width:70px;height:20px;margin-left:-35px;background:rgba(255,255,255,.7);border:1px solid rgba(0,0,0,.06)}
    .note h3{margin:0 0 6px;font-size:21px}.note p{margin:0;font-size:15px;color:#3d4955}.note span{display:block;margin-top:10px;font-weight:700;color:#12324f}
    .cities{display:flex;flex-wrap:wrap;gap:10px}.cities a{border:2px solid #12324f;border-radius:999px;padding:6px 14px;text-decoration:none;font-weight:700}.cities a b{color:#e2553b;margin-left:4px}
    .cities a.hot{background:#12324f;color:#fff}.cities a.hot b{color:#ffd84d}
    .ask{background:#f2f6fa}.ask-in{display:flex;gap:20px;align-items:center;flex-wrap:wrap}.ask-in h2{margin:0}
    .btn-line{background:#06c755;color:#fff;text-decoration:none;font-weight:700;border-radius:999px;padding:12px 24px;font-size:17px}
    .ft{background:#12324f;color:#c8d6e5;padding:24px 0;font-size:14px}.ft a{color:#fff}.ft b{color:#fff}.ft-s{font-size:12px;opacity:.85}
    .pv{background:#e2553b;color:#fff;text-align:center;font-size:13px;padding:4px}
    @media(max-width:900px){.board{grid-template-columns:repeat(2,minmax(0,1fr))}.duo{grid-template-columns:1fr}.duo img{max-width:260px;margin:0 auto;display:block}.notes{grid-template-columns:1fr}.hd nav{display:none}.hero-k{margin-left:0}}
    @media(max-width:520px){.board{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.chips button{white-space:nowrap;padding:3px 10px;font-size:14px}.hero-sub{font-size:13px}.hero{padding:16px 0 22px}.hero-k a b{font-size:20px}.cd-head{margin:14px 0 10px}.tk-left{font-size:12px;padding:2px 7px}.tk-left b{font-size:16px}.tk-meta{font-size:12px}.tk-date{font-size:12px}.hero-k a{min-width:0;flex:1}.hero-k{width:100%}.tk h3{font-size:14px}.tk-price b{font-size:18px}.tk-price{gap:10px}.tk-body{padding:8px 10px 10px}.tk-ask{font-size:12px}.tk-see{font-size:12px;padding:2px 6px}
    .hero h1{font-size:26px}.hero-who img{width:72px;height:72px}.chips{margin-left:0}.ppl{grid-template-columns:1fr}.logo small{display:none}}
    """
    HEAD = lambda title, desc, ld, path="/": (f'<!doctype html><html lang="zh-Hant-TW"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(title)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{SITE}{path}"><meta property="og:locale" content="zh_TW"><meta property="og:type" content="website"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{SITE}{path}"><meta property="og:image" content="{SITE}/home/assets/pitt_anna.webp"><link rel="icon" href="/home/assets/favicon.svg" type="image/svg+xml"><meta name="theme-color" content="#12324f"><meta name="robots" content="index,follow,max-image-preview:large">'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=LXGW+WenKai+TC:wght@700&family=Noto+Sans+TC:wght@400;700&display=swap" rel="stylesheet">'
            f'<style>{CSS}</style>' + "".join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in ld) + '</head><body>'
            )

    city_cnt = {}
    for x in D["104"]:
        if x["區域"][:2] in ("金門", "澎湖", "連江"): continue   # 11/25 起離島不放
        city_cnt[x["區域"][:2]] = city_cnt.get(x["區域"][:2], 0) + 1
    cities = sorted(city_cnt.items(), key=lambda t: ({"台北": 0, "新北": 1, "桃園": 2}.get(t[0], 3), -t[1]))
    total = sum(city_cnt.values())
    board = "".join(card(d, x) for d, x in soon[:12])

    ORG = {"@context": "https://schema.org", "@type": "RealEstateAgent", "@id": SITE + "/#organization", "legalName": "財欣不動產管理顧問有限公司", "name": "Pitt & Anna 104法拍網團隊", "url": SITE,
           "telephone": "+886-986-678-928", "parentOrganization": {"@type": "Organization", "name": "財欣不動產管理顧問有限公司"},
           "employee": [{"@type": "Person", "name": "Pitt", "url": f"{SITE}/team/pitt"}, {"@type": "Person", "name": "Anna", "url": f"{SITE}/team/anna"}],
           "sameAs": [YT, FB]}
    home = (HEAD("Pitt & Anna 104法拍網團隊｜你的法拍購屋夥伴・雙北桃園 3～14 天內開標", "雙北桃園 3～14 天內開標的法拍屋倒數，每天依透明房訊更新。Pitt & Anna 夫妻雙人顧問，陪你看懂公告、算清總成本、一路到點交。", [ORG] + OLD_LD)
      + TOP +
      '<section class="hero" id="countdown"><div class="wrap">'
      '<div class="hero-top"><div class="hero-who"><img src="/home/assets/pitt_anna.webp" alt="Pitt 與 Anna（Q 版）">'
      '<div><h1 class="hand">你的<mark>法拍購屋夥伴</mark></h1><p class="hero-sub">Pitt &amp; Anna 夫妻雙人顧問｜看懂公告、算清總成本、陪你到點交</p></div></div>'
      f'<div class="hero-k"><a href="/list?c=台北"><b>{city_cnt.get("台北", 0)}</b><small>台北</small></a><a href="/list?c=新北"><b>{city_cnt.get("新北", 0)}</b><small>新北</small></a><a href="/list?c=桃園"><b>{city_cnt.get("桃園", 0)}</b><small>桃園</small></a></div></div>'
      f'<div class="cd-head"><h2 class="hand"><span>倒數</span>雙北桃園 3～14 天內開標</h2>'
      f'<div class="chips" role="group" aria-label="選縣市"><button aria-pressed="true" data-c="">全部 {len(soon)}</button>'
      + "".join(f'<button aria-pressed="false" data-c="{c}">{c} {cnt[c]}</button>' for c in TW) + '</div></div>'
      f'<div class="board" id="board">{board}</div>'
      f'<p class="more"><a href="/list">看全部 {len(soon)} 件 3～14 天內開標 →</a></p>'
      '</div></section>'
      '<section class="sec"><div class="wrap duo"><img src="/home/assets/pitt_anna.webp" alt="Pitt 與 Anna（Q 版）">'
      '<div><h2 class="hand">我們是 Pitt &amp; Anna</h2><p class="lead">夫妻雙人顧問。你只要決定喜不喜歡，公告、筆錄、點交、要準備多少錢，我們幫你拆清楚。</p>'
      '<div class="ppl"><a class="pp" href="/team/pitt"><b>黃先生 Pitt</b><p>產權調查、現場勘查、標價評估</p><span class="tel">0918-313-888</span></a>'
      '<a class="pp" href="/team/anna"><b>林小姐 Anna</b><p>投標諮詢、委託流程、點交與交屋協助</p><span class="tel">0986-678-928</span></a></div></div></div></section>'
      '<section class="sec" style="background:#fbfaf3"><div class="wrap"><h2 class="hand">買法拍，最常卡在這三件事</h2><p class="lead">先看懂，再決定要不要標。</p><div class="notes">'
      '<a class="note" href="/learn/delivery-or-not"><h3 class="hand">點交還是不點交？</h3><p>差在得標後法院幫不幫你把人請出去。公告的「使用情形」要看正本。</p><span>看說明 →</span></a>'
      '<a class="note" href="/learn/auction-costs-after-winning"><h3 class="hand">總共要準備多少錢？</h3><p>底價之外，還有保證金、尾款、稅費、代書費。先算清楚再出價。</p><span>看說明 →</span></a>'
      '<a class="note" href="/learn/auction-rounds"><h3 class="hand">第幾拍最划算？</h3><p>每流標一次底價通常再降，但等越久，被別人標走的機會也越高。</p><span>看說明 →</span></a>'
      '</div></div></section>'
      f'<section class="sec"><div class="wrap"><h2 class="hand">各縣市找物件</h2><p class="lead">全台 {total} 件，每天依透明房訊更新。</p><div class="cities">'
      + "".join(f'<a class="{"hot" if c in TW else ""}" href="/list?c={e(c)}">{e(c)}<b>{n}</b></a>' for c, n in cities) + '</div></div></section>'
      f'<section class="sec ask"><div class="wrap ask-in"><h2 class="hand">看到喜歡的？傳案名給我們</h2><a class="btn-line" href="{LINE}" target="_blank" rel="noopener">加入 LINE@ 問物件</a>'
      '<span>或直接打給 Anna <a href="tel:0986678928"><b>0986-678-928</b></a></span></div></section>'
      + FOOT +
      '<script>document.querySelectorAll(".chips button").forEach(function(b){b.onclick=function(){var c=b.dataset.c;'
      'document.querySelectorAll(".chips button").forEach(function(x){x.setAttribute("aria-pressed",x===b)});'
      'document.querySelectorAll("#board .tk").forEach(function(t){t.style.display=(!c||t.dataset.c===c)?"":"none"})}})</script></body></html>')
    # 倒數板放 12 件；篩選縣市時要有該縣市的件，所以板子另外補齊每縣市至少 4 件
    extra = []
    for c in TW:
        have = [x for d, x in soon[:12] if x["區域"][:2] == c]
        extra += [card(d, x) for d, x in soon[12:] if x["區域"][:2] == c][:max(0, 4 - len(have))]
    home = home.replace(f'<div class="board" id="board">{board}</div>', f'<div class="board" id="board">{board}' + "".join(extra).replace('<article class="tk"', '<article class="tk" style="display:none" data-x="1"') + '</div>')
    home = home.replace('if(!c||t.dataset.c===c)', 'if(!c||t.dataset.c===c)')
    home = home.replace('t.style.display=(!c||t.dataset.c===c)?"":"none"', 't.style.display=((!c&&!t.dataset.x)||t.dataset.c===c)?"":"none"')
    write("site/index.html", home.replace("</body>", CLICK_JS + "</body>", 1))

    PEOPLE = {
     "pitt": {"n": "Pitt", "zh": "黃先生", "tel": "0918-313-888", "t": "+886-918-313-888",
              "do": ["產權調查：謄本、筆錄、使用情形先看清楚", "現場勘查：周邊環境、社區狀況", "標價評估：底價、行情與總成本一起算"],
              "say": "法拍不是越便宜越好，要先知道買到的是什麼。看不懂的地方，交給我們拆。"},
     "anna": {"n": "Anna", "zh": "林小姐", "tel": "0986-678-928", "t": "+886-986-678-928",
              "do": ["投標諮詢：哪件適合你、要準備多少錢", "委託與投標流程：一步一步說清楚", "點交與交屋協助：得標後一路陪你"],
              "say": "你只要決定喜不喜歡，其他流程我們陪你走。先傳案名給我，我幫你看。"},
    }
    for k, p in PEOPLE.items():
        other = "anna" if k == "pitt" else "pitt"
        ld = [{"@context": "https://schema.org", "@type": "Person", "name": p["n"], "alternateName": p["zh"] + " " + p["n"],
               "jobTitle": "法拍代標顧問", "telephone": p["t"], "url": f"{SITE}/team/{k}", "image": f"{SITE}/home/assets/pitt_anna.webp",
               "worksFor": {"@type": "RealEstateAgent", "name": "Pitt & Anna 104法拍網團隊", "url": SITE,
                            "parentOrganization": {"@type": "Organization", "name": "財欣不動產管理顧問有限公司"}},
               "knowsAbout": ["法拍屋", "法院拍賣", "點交", "代標", "投標保證金"], "areaServed": "台灣", "sameAs": [YT, FB]},
              {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                  {"@type": "ListItem", "position": 1, "name": "首頁", "item": SITE + "/"},
                  {"@type": "ListItem", "position": 2, "name": f'{p["zh"]} {p["n"]}', "item": f"{SITE}/team/{k}"}]}]
        pg = (HEAD(f'{p["zh"]} {p["n"]}｜法拍代標顧問｜Pitt & Anna 104法拍網團隊', f'{p["zh"]} {p["n"]}，Pitt & Anna 104法拍網團隊法拍代標顧問。' + "、".join(d.split("：")[0] for d in p["do"]) + f'。電話 {p["tel"]}。', ld, f"/team/{k}")
          + TOP + '<section class="sec"><div class="wrap duo"><img src="/home/assets/pitt_anna.webp" alt="Pitt 與 Anna（Q 版）">'
          f'<div><p style="margin:0;color:#5b6875">首頁 › 認識我們</p><h1 class="hand" style="font-size:34px;margin:4px 0">{p["zh"]} {p["n"]}</h1>'
          f'<p class="lead">法拍代標顧問｜Pitt &amp; Anna 104法拍網團隊（夫妻雙人顧問）</p>'
          f'<p style="font-size:18px;background:#fff6c7;padding:12px 16px;border-radius:6px" class="hand">「{e(p["say"])}」</p>'
          '<h2 style="font-size:20px;margin:18px 0 6px">我負責</h2><ul>' + "".join(f"<li>{e(d)}</li>" for d in p["do"]) + '</ul>'
          f'<p><a class="btn-line" href="{LINE}" target="_blank" rel="noopener">LINE@ 問物件</a>　<a href="tel:{p["tel"].replace("-", "")}"><b>{p["tel"]}</b></a></p>'
          f'<p>服務範圍：全台（金門、澎湖、連江除外）｜品牌：透明房訊品牌深耕法拍逾 40 年</p>'
          f'<p>看我們的法拍影片：<a href="{YT}" target="_blank" rel="noopener">YouTube「我的法拍屋最新情報」</a>｜另一位顧問：<a href="/team/{other}">{PEOPLE[other]["zh"]} {PEOPLE[other]["n"]}</a></p>'
          '</div></div></section>' + FOOT + '</body></html>')
        write(f"site/team/{k}.html", pg.replace("</body>", CLICK_JS + "</body>", 1))
    print("新首頁 3～14 天內開標雙北桃園（有實拍照）", len(soon), cnt)
    return len(soon)
