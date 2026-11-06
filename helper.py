# 法拍小幫手（內部工作頁 /helper，由 build.py 載入；noindex、不進 sitemap）
# 每日待辦：7 天內開標、本週新增、異動待更新、停拍／流標待下架、上架檢查（缺資料鎖住不產文）
# 產文：每案 FB 粉專／FB 社團／LINE 文案，內含案件代碼、UTM、必要聲明
# 新詢問速記：產生可貼到 Google 試算表的客戶列與 D1/D3/D7/D14 追蹤任務

BROKER = "財欣不動產"   # 經紀業名稱：不動產經紀業管理條例第 21 條，廣告須註明
UTM_SOURCES = [  # (utm_source, utm_medium, 顯示名稱)
    ("fb_page", "social", "FB 粉專"), ("fb_group", "social", "FB 社團"), ("line", "message", "LINE"),
    ("houseinfo", "listing", "House-Info"), ("104woo", "listing", "買屋網"), ("myhomes", "listing", "我家網"), ("gbp", "profile", "Google 商家"), ("yt", "social", "YouTube"),
]
NEED = ["案號", "拍次", "開標日期", "底價", "點交情形", "完整地址"]

def utm(path, source, medium, campaign, content=""):
    q = {"utm_source": source, "utm_medium": medium, "utm_campaign": campaign}
    if content: q["utm_content"] = content
    return f"{SITE}{path}?{urllib.parse.urlencode(q)}"

def _campaign(x): return f'{x["編號"]}_{_today():%Y%m}'

def missing_of(x):
    inf = x.get("資訊", {})
    have = {"案號": inf.get("案號"), "拍次": round_of(x), "開標日期": date_key(x) != 99999999,
            "底價": price_num(x["價格"]) > 0, "點交情形": deliver_of(x), "完整地址": inf.get("完整地址")}
    return [k for k in NEED if not have[k]]

def case_copy(x, source, medium):
    inf = x.get("資訊", {})
    addr = inf.get("完整地址") or x["地址"]
    link = utm(f'/h/{x["編號"]}', source, medium, _campaign(x), "post")
    head = f'【{area_of(x)}法拍｜{x["類型"].split("_")[0]}｜代碼 {x["編號"]}】'
    lines = [head, addr + (f'（{x["地址"]}）' if x["地址"] != addr else ""),
             f'第{round_of(x)}拍｜開標 {inf.get("開標日期", "")}｜法院底價 {re.sub(r"^售", "", x["價格"])}',
             f'點交情形：{deliver_of(x)}｜{x["格局坪數"]}', ""]
    if source == "line":
        lines += [f"詳情：{link}", "", f"有興趣請直接回覆「{x['編號']}」，我們會說明公告重點與代標流程。"]
    else:
        lines += [f"👉 物件資料與法院筆錄：{link}", "",
                  f"想問這間：加 LINE 傳「{x['編號']}」 {LINKS['LINE']}",
                  f"或來電 林小姐 Anna {PHONE_A}／黃先生 Pitt {PHONE_P}"]
    lines += ["", "法拍屋原則上無法進屋看室內，我們可協助周邊、外觀勘查與公告解讀。",
              f"※ 資料以法院公告為準。經紀業：{BROKER}｜{NAME}"]
    if source != "line": lines += ["", f"#法拍屋 #{area_of(x)[:2]}法拍 #{area_of(x)} #法拍屋代標"]
    return "\n".join(lines)

def _row(x, copy=True):
    inf = x.get("資訊", {})
    miss = missing_of(x)
    ok = copy and not miss and x["狀態"] == "待標中"
    btn = ""
    if ok:
        btn = ('<div class="hb">' + "".join(f'<button type="button" data-c="{x["編號"]}|{s}">{n}</button>'
               for s, n in (("fb_page", "粉專文"), ("fb_group", "社團文"), ("line", "LINE 文"))) +
               f'<button type="button" data-u="{x["編號"]}">追蹤連結</button></div>')
    elif copy:
        why = ("缺：" + "、".join(miss)) if miss else f'狀態「{x["狀態"]}」'
        btn = f'<div class="hw">🔒 不產文（{e(why)}）</div>'
    return (f'<li><b>{e(x["編號"])}</b> {e(area_of(x))}｜<a href="/h/{e(x["編號"])}" target="_blank">{e(inf.get("完整地址") or x["地址"])}</a>'
            f'<br><span>第{round_of(x) or "?"}拍・開標 {e(inf.get("開標日期", "—"))}・{e(x["價格"])}・{e(deliver_of(x) or "點交未明")}・{e(x["狀態"])}</span>{btn}</li>')

def _sec(i, title, tip, xs, cap=60, copy=True):
    more = f'<p class="hm">另有 {len(xs) - cap} 筆，請到 <a href="/list">物件列表</a> 查看。</p>' if len(xs) > cap else ""
    body = ("<ol>" + "".join(_row(x, copy) for x in xs[:cap]) + "</ol>" + more) if xs else "<p>目前沒有。</p>"
    return f'<section class="box" id="{i}"><h2>{title}（{len(xs)}）</h2><p class="hm">{tip}</p>{body}</section>'

HELPER_CSS = """<style>.hc{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin:10px 0}.hc a{background:#1f3a4d;color:#fff;border-radius:10px;padding:10px;text-decoration:none;display:block}.hc b{font-size:1.6rem;color:#e6c98f;display:block}
.box ol{padding-left:1.4em}.box li{margin:10px 0;line-height:1.5}.box li span{color:#666;font-size:.9rem}.hb button,#hf button{background:#c9a86a;color:#1f3a4d;border:0;border-radius:6px;padding:6px 10px;margin:4px 6px 0 0;font-weight:700;cursor:pointer}
.hw{color:#a4442d;font-size:.85rem}.hm{color:#666;font-size:.88rem}#hf label{display:block;margin-top:8px;font-weight:700}#hf input,#hf select,#hf textarea{width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;font-size:15px;box-sizing:border-box}
#hf textarea{font-family:monospace;font-size:13px}#ht{position:fixed;left:50%;bottom:20px;transform:translateX(-50%);background:#1f3a4d;color:#fff;padding:8px 16px;border-radius:20px;display:none;z-index:99}</style>"""

HELPER_JS = r"""<script>(function(){var C=window.HC,U=window.HU,S=window.HS;
function toast(t){var h=document.getElementById('ht');h.textContent=t;h.style.display='block';setTimeout(function(){h.style.display='none'},1600)}
function cp(t,m){(navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(function(){toast(m||'已複製')},function(){window.prompt('請手動複製',t)})}
document.addEventListener('click',function(ev){var b=ev.target;if(b.dataset.c){var k=b.dataset.c.split('|');cp(C[k[0]][k[1]],'已複製'+b.textContent+'，發布後記得回貼網址')}
if(b.dataset.u){var s=document.getElementById('us').value.split('|');cp(U(b.dataset.u,s[0],s[1]),'已複製追蹤連結（'+s[2]+'）')}});
var f=document.getElementById('hf');function g(i){return(document.getElementById(i).value||'').trim()}
function day(n){var d=new Date();d.setDate(d.getDate()+n);return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}
f.onsubmit=function(ev){ev.preventDefault();
 var ok=[(g('fp')||g('fl'))?'':'聯絡方式',(g('fc')||g('fa'))?'':'案件代碼或區域',(g('fb')||g('ft'))?'':'預算或時程'].filter(Boolean);
 var id='C'+day(0).replace(/-/g,'')+'-'+String(Date.now()).slice(-4),code=g('fc').toUpperCase();
 var cust=[id,day(0),g('fs'),code,g('fn'),g('fl'),g('fp'),g('fa'),g('fb'),g('ft'),g('fo'),ok.length?'待補':'有效詢問',ok.join('、'),'否'].join('\t');
 var T=[[1,'傳公告重點（點交、底價、拍次日期）＋邀約電話'],[3,'邀約實體諮詢或周邊勘查（說明只看周邊／外觀）'],[7,'確認保證金與資金；不適合此案則推薦 2 個替代案'],[14,'未成交原因分流＋徵求同意加入精選推播（附「回覆停止」）']];
 var tasks=T.map(function(t){return [id+'-D'+t[0],id,code,g('fo'),day(t[0]),'D'+t[0]+' '+t[1],'待辦'].join('\t')}).join('\n');
 document.getElementById('fr').value='【客戶表】\n客戶ID\t建立日\t來源\t案件代碼\t姓名\tLINE名稱\t電話\t區域\t預算\t時程\t負責人\t狀態\t缺少\t拒絕行銷\n'+cust+'\n\n【任務表】\n任務ID\t客戶ID\t案件代碼\t負責人\t到期日\t動作\t狀態\n'+tasks;
 document.getElementById('fw').textContent=ok.length?'⚠ 還不算有效詢問，缺：'+ok.join('、'):'✓ 有效詢問（聯絡方式＋案件／區域＋預算／時程）';
 var r=C[code];document.getElementById('fx').textContent=r?'已找到案件 '+code+'：'+r.t:(code?'⚠ 網站上找不到代碼 '+code+'，請確認或改填區域':'');};
document.getElementById('fy').onclick=function(){cp(document.getElementById('fr').value,'已複製，貼到試算表 A 欄即可分欄')};
})()</script>"""

def helper_page():
    live = [x for x in ITEMS if x["狀態"] == "待標中"]
    soon = [x for x in upcoming(7) if x["狀態"] == "待標中"]
    new = [x for x in new_items() if x["狀態"] == "待標中"]
    chg = [x for x in changed_items()]
    down = [x for x in ITEMS if x["狀態"].startswith(("停拍", "流標"))]
    gaps = [x for x in live if missing_of(x)]
    unk = [x for x in ITEMS if "待確認" in x["狀態"]]
    copyable = {x["編號"]: x for x in soon + new + chg if x["狀態"] == "待標中" and not missing_of(x)}
    hc = {k: {"t": (x.get("資訊", {}).get("完整地址") or x["地址"]), **{s: case_copy(x, s, m) for s, m, _ in UTM_SOURCES[:3]}} for k, x in copyable.items()}
    for x in ITEMS:
        hc.setdefault(x["編號"], {"t": x.get("資訊", {}).get("完整地址") or x["地址"]})
    cards = [("soon", "7 天內開標", soon), ("new", "本週新增", new), ("chg", "降價・降拍待更新", chg), ("down", "停拍・流標待下架", down), ("gap", "待補資料", gaps)]
    opts = "".join(f'<option value="{s}|{m}|{n}">{n}</option>' for s, m, n in UTM_SOURCES)
    body = (f'<h1>法拍小幫手</h1><p class="hm">內部工作頁，資料更新：{e(UPDATED)}（每日 11:00、16:30 自動更新）。此頁不會被搜尋引擎收錄。'
            f'所有文案發布前須經紀人審閱；價格、拍次、點交一律以法院公告為準。</p>'
            '<div class="hc">' + "".join(f'<a href="#{i}"><b>{len(xs)}</b>{t}</a>' for i, t, xs in cards) + "</div>"
            f'<p class="hm">待標中 {len(live)} 筆；開標日已過待確認 {len(unk)} 筆（不產文，等開標結果）。'
            f'追蹤連結來源：<select id="us">{opts}</select>　<a href="/post">本週精選貼文草稿 ›</a></p>'
            + _sec("soon", "① 7 天內開標", "優先推：發粉專＋LINE 精選；有詢問的客戶確認保證金。", soon)
            + _sec("new", "② 本週新增", "上架到買屋網／House-Info、發粉專或社團（社團請手動）。", new)
            + _sec("chg", "③ 降價・降拍待更新", "已刊登的平台要改拍次與價格，並回頭通知關注此案的客戶。", chg)
            + _sec("down", "④ 停拍・流標待下架", "到各平台下架或標註；已關注的客戶改推替代案。", down, copy=False)
            + _sec("gap", "⑤ 待補資料（上架檢查未過）", "缺" + "、".join(NEED) + "任一項就鎖住不產文，請先到法院公告核對補齊。", gaps)
            + '<section class="box" id="ask"><h2>⑥ 新詢問速記</h2><p class="hm">接到詢問 2 小時內回覆。填完按「產生」，複製後貼到 Google 試算表（客戶表、任務表），會自動排 D1／D3／D7／D14 追蹤。'
              '不要用姓名合併客戶，以電話或 LINE 比對。客戶表示不要推播時，把「拒絕行銷」改成「是」。</p><form id="hf">'
              '<label>來源</label><select id="fs">' + "".join(f'<option>{n}</option>' for _, _, n in UTM_SOURCES) + '<option>電話</option><option>轉介紹</option><option>其他</option></select>'
              '<label>案件代碼（例：HH2512789）</label><input id="fc"><p id="fx" class="hm"></p>'
              '<label>姓名</label><input id="fn"><label>LINE 名稱</label><input id="fl"><label>電話</label><input id="fp" inputmode="tel">'
              '<label>想找的區域</label><input id="fa"><label>預算</label><input id="fb"><label>購買時程</label><input id="ft">'
              '<label>負責人</label><select id="fo"><option>Anna</option><option>Pitt</option></select>'
              '<p><button type="submit">產生</button><button type="button" id="fy">複製</button></p><p id="fw" class="hm"></p>'
              '<textarea id="fr" rows="9" readonly></textarea></form></section>'
            + '<div id="ht"></div>'
            + f'<script>window.HC={jd(hc)};window.HU=function(id,s,m){{var d=new Date(Date.now()+288e5);return {jd(SITE)}+"/h/"+id+"?utm_source="+s+"&utm_medium="+m+"&utm_campaign="+id+"_"+d.toISOString().slice(0,7).replace("-","")+"&utm_content=post"}};</script>'
            + HELPER_JS)
    return page("法拍小幫手｜" + NAME, "內部工作頁", "/helper", body, None, None, HELPER_CSS, "", False).replace("index,follow", "noindex,nofollow")
