# 法拍小教室、客戶評價、人物圖區塊（由 build.py 載入）
LEARN = [
 ("what-is-foreclosure-auction", "法拍屋是什麼？從投標到交屋 6 個步驟",
  "法拍屋是法院因債務人還不出錢，依強制執行程序公開拍賣的不動產。買法拍屋的流程大致如下。",
  [("1. 查詢公告", "在法院或透明房訊查到物件的拍賣公告，記下案號、拍次、開標日期、底價與點交情形。"),
   ("2. 查產權與現場", "調閱謄本、看現場有沒有人居住、有沒有欠管理費或漏水，再決定出價。"),
   ("3. 投標", "開標前備齊投標單、保證金與證件，在規定時間內投入標櫃。"),
   ("4. 開標", "開標當天由法院公布最高價者得標。"),
   ("5. 繳清價金", "得標後依通知期限繳清價金，法院核發權利移轉證書。"),
   ("6. 點交與過戶", "若為點交物件，可聲請法院協助點交；再憑證書辦理過戶與貸款。")]),
 ("delivery-or-not", "點交與不點交差在哪？新手最該先看這一項",
  "點交是指得標後，若現場有人占用，法院可協助強制遷出；不點交則要自己處理。",
  [("點交", "法院公告載明點交，得標人繳清價金後，可聲請法院執行點交，成本與時間較可預期。"),
   ("不點交", "公告載明不點交，現場若有占用人，得標人需自行協商或另提訴訟，時間與費用較難預估。"),
   ("怎麼看", "物件頁的「法院筆錄」會列出點交情形。拍賣公告上的記載才是依據。"),
   ("提醒", "不點交不代表不能買，但價格應反映風險，也建議先請專業人員評估。")]),
 ("auction-rounds", "第一拍、第二拍、第三拍：底價怎麼變？",
  "法拍屋流標後會降價再拍，所以拍次越後面，底價通常越低。",
  [("第一拍", "底價依法院鑑定或核定的市價，通常最高。"),
   ("第二拍", "第一拍沒人應買時，依規定可減價再拍，一般為前一拍的八折。"),
   ("第三拍", "再流標會再減價，一般為前一拍的八折。"),
   ("第三拍之後", "仍無人應買時，債權人可能同意停止拍賣，或依法院裁定續拍，實際以公告為準。"),
   ("怎麼用", "拍次越後面不代表越好買，要一起看點交情形、屋況與市場行情。")]),
 ("how-to-bid", "第一次投標要準備什麼？",
  "投標前把文件與保證金備齊，可以避免開標當天被判為無效標。",
  [("證件與印章", "攜帶身分證明文件與印章，委託他人投標須備委任文件。"),
   ("保證金", "依拍賣公告載明的金額與方式繳交，常見為銀行本票或支票，金額與格式以公告為準。"),
   ("投標單", "填寫案號、出價與投標人資料，填錯或塗改可能無效。"),
   ("投標時間", "在公告時間前投入指定標櫃，逾時不受理。"),
   ("出價", "價格不得低於底價，建議先評估行情與後續成本再出價。")]),
 ("risks", "買法拍屋常見的 5 個風險",
  "法拍屋價格較低，主要是因為多了一些不確定因素。事先查清楚，就能把風險降到可控。",
  [("現場占用", "不點交或有第三人主張權利時，需要時間處理。"),
   ("欠繳費用", "管理費、水電瓦斯可能有欠款，需向社區與公司確認。"),
   ("屋況", "法拍通常無法進屋勘查，漏水、壁癌、結構問題要用外觀與周邊資訊推估。"),
   ("租賃關係", "現場有承租人時，需看公告是否載明租約情形。"),
   ("貸款成數", "法拍屋貸款成數與一般交易不同，先與銀行確認再投標。")]),
]
LEARN_NOTE = "本文為一般資訊，非法律或投資建議，實際內容請以法院拍賣公告為準。"

def _article_ld(t, desc, path):
    return {"@context": "https://schema.org", "@type": "Article", "headline": t, "description": desc,
            "author": {"@type": "Organization", "name": NAME}, "publisher": {"@type": "Organization", "name": NAME},
            "mainEntityOfPage": SITE + path, "inLanguage": "zh-TW"}

def learn_article(slug_, t, lead, secs):
    path = f"/learn/{slug_}"
    body = (f'<nav class="bc"><a href="/">首頁</a> › <a href="/learn">法拍小教室</a> › {e(t)}</nav><h1>{e(t)}</h1><p>{e(lead)}</p>'
            + "".join(f'<section class="box"><h2>{e(a)}</h2><p>{e(b)}</p></section>' for a, b in secs)
            + f'<p style="color:#666;font-size:13px">{e(LEARN_NOTE)}</p>'
            + '<section class="box"><h2>想標這間？我們陪你</h2><p>黃先生 Pitt 與林小姐 Anna 夫妻雙人顧問，協助產權調查、現場勘查與代標。</p>'
            + f'<p><a class="btn line" href="{e(LINKS["LINE"])}" target="_blank" rel="noopener">LINE 諮詢</a><a class="btn" href="/member#ask">委託代標留言</a></p></section>'
            + '<section class="box"><h2>更多文章</h2><ul>' + "".join(f'<li><a href="/learn/{s}">{e(tt)}</a></li>' for s, tt, _, _ in LEARN if s != slug_) + '</ul></section>')
    return page(f"{t}｜法拍小教室｜{NAME}", lead, path, body, _article_ld(t, lead, path))

def learn_index():
    body = ('<h1>法拍小教室</h1><p>用白話說明法拍屋的流程、點交、拍次與風險。</p><div class="grid">'
            + "".join(f'<a class="card" href="/learn/{s}"><div class="b"><h3>{e(t)}</h3><div class="m">{e(l)}</div></div></a>' for s, t, l, _ in LEARN)
            + f'</div><p style="color:#666;font-size:13px">{e(LEARN_NOTE)}</p>')
    return page(f"法拍小教室｜法拍屋流程、點交、拍次｜{NAME}", "用白話說明法拍屋流程、點交與不點交、拍次降價與投標準備。", "/learn", body)

def write_learn(urls):
    write("site/learn.html", learn_index()); urls.append(("/learn", 0.7))
    for s, t, l, secs in LEARN:
        write(f"site/learn/{s}.html", learn_article(s, t, l, secs)); urls.append((f"/learn/{s}", 0.6))

def _reviews():
    try: return json.load(open("reviews.json", encoding="utf-8"))
    except Exception: return []

def extras_index():
    h = ('<section class="box" id="learn"><h2>法拍小教室</h2><ul>'
         + "".join(f'<li><a href="/learn/{s}">{e(t)}</a></li>' for s, t, _, _ in LEARN) + '</ul></section>')
    rv = _reviews()
    if rv:
        h += '<section class="box" id="reviews"><h2>客戶評價</h2><div class="grid">' + "".join(
            f'<div class="card"><div class="b"><p>{e(r.get("text", ""))}</p><div class="m">— {e(r.get("name", "客戶"))}{("｜" + e(r["case"])) if r.get("case") else ""}</div></div></div>' for r in rv[:6]) + '</div></section>'
    return h

def team3_box():
    return ('<section class="box team"><img src="/brand/team3.jpg" alt="黃先生 Pitt 與林小姐 Anna 拿著鑰匙" width="585" height="800" loading="lazy" onerror="this.parentNode.remove()">'
            '<div><h2>想標這間？我們陪你</h2><p>產權調查、現場勘查、出價策略，由兩位顧問一起把關。</p>'
            f'<p><a class="btn line" href="{e(LINKS["LINE"])}" target="_blank" rel="noopener">LINE 詢問</a> <a class="btn" href="tel:0918313888">電話洽詢</a></p></div></section>')
