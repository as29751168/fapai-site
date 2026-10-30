# 購屋流程、服務費用頁（由 learn.py 載入）
STAGES = [
 ("階段一", "評估與委託", "了解物件，確認需求", [
   ("01", "確認案件", "挑選物件、勘查外觀及周邊，檢視法院公告與筆錄"),
   ("02", "預約諮詢", "說明法拍流程及案件條件，分析成本、稅費與貸款"),
   ("03", "委託簽約", "確認服務內容與費用，簽訂代標委託合約")]),
 ("階段二", "投標與繳款", "確認出價，備妥資金", [
   ("04", "投標準備", "現場調查、行情與融資評估，備妥保證金，買方確認出價"),
   ("05", "正式投標", "核對投標文件與委任資料，陪同或依委託金額代理投標"),
   ("06", "得標繳款", "安排自有資金、融資或代墊，於規定期限內繳足價金")]),
 ("階段三", "產權與交屋", "完成登記，處理交接", [
   ("07", "產權登記", "領取法院權利移轉證書，辦理相關稅費與移轉登記"),
   ("08", "點交處理", "點交：向法院聲請辦理。不點交：協商，必要時訴訟執行"),
   ("09", "完成交屋", "確認騰空與現場屋況，辦理鑰匙、水電及管理交接")]),
]
PROCESS_NOTE = "未得標：依程序領回保證金，可再評估其他物件。交屋時程：依占用現況及法院程序評估。拍賣、繳款與點交依法院公告及相關規定辦理；融資與代墊須依個案條件評估。"

FEE_COLS = [("聲請點交", "50,000 元", "服務項目 01–05"), ("包辦點交", "120,000 元", "服務項目 01–11"), ("全程代標", "標價的 2–5%", "服務項目 01–19，600 萬元以下另議，依案件難易評估")]
FEE_ROWS = [
 ("追蹤法院核發權利移轉證書", "", 1), ("協助產權過戶", "相關代書費、稅費另計，詳見附註一", 1), ("撰擬點交聲請狀", "", 1),
 ("向法院遞交點交書狀", "", 1), ("持續追蹤點交進度", "", 1),
 ("保證代墊尾款", "", 2), ("協調轄區警員到場", "", 2), ("安排鎖匠與搬家公司待命", "", 2), ("協同法院協調現住人交屋時間", "", 2),
 ("處理原債務人戶籍及營業登記遷移", "包含原債務人戶籍中的幽靈人口遷移", 2), ("協助恢復水、電與瓦斯", "", 2),
 ("投標前案件調查", "現場訪查、法院筆錄核對、債權與水電調查；確認附屬增建是否在拍賣範圍、車位是否遭占用；查核第三人租約陳報與拍定後點交條件", 3),
 ("標價評估與投標準備", "投標現場陪同及最終標價建議、投標文件準備；核對投標書、委任狀及保證金票據；了解周邊競標情形，比對市價及法拍成交紀錄", 3),
 ("協調原屋主搬遷條件", "協商搬遷，配合法院點交程序進行", 3), ("全程承辦點交程序", "", 3),
 ("提供點交保固書", "限服務費 5% 的案件適用，詳見附註二", 3), ("保證於約定期限內和諧交屋", "", 3),
 ("處理遺留神明、神主牌及祖先牌位", "協助寄託廟宇管理", 3), ("有價遺留物清點與保管", "以貨櫃屋或倉庫存放，通知權利人領取；未領取時，依法聲請拍賣", 3),
]
FEE_NOTES = ["服務費不含：過戶代書費、貸款設定代書費、過戶契約、規費及貸款手續費。", "點交保固書適用於服務費 5% 的案件。", "不點交、部分點交及持分案件，服務費另議。"]

def process_page():
    h = '<nav class="bc"><a href="/">首頁</a> › 法拍屋購屋流程</nav><h1>法拍屋購屋流程：9 步驟看懂</h1><p>從挑選案件到交屋，分成三個階段。我們全程協助，每一步都清楚告訴你在做什麼。</p>'
    for tag, name, sub, steps in STAGES:
        h += f'<section class="box"><h2>{e(tag)}｜{e(name)}</h2><p style="color:#666">{e(sub)}</p><ol style="padding-left:0;list-style:none">'
        for n, t, d in steps:
            h += f'<li style="margin:10px 0"><b style="display:inline-block;background:#1f3a4d;color:#fff;border-radius:50%;width:30px;height:30px;line-height:30px;text-align:center;margin-right:8px">{n}</b><b>{e(t)}</b>：{e(d)}</li>'
        h += '</ol></section>'
    h += f'<p style="color:#666;font-size:13px">{e(PROCESS_NOTE)}</p>'
    h += (f'<section class="box"><h2>想了解費用？</h2><p><a class="btn" href="/fees">服務費用與收費標準</a><a class="btn line" href="{e(LINKS["LINE"])}" target="_blank" rel="noopener">LINE 諮詢</a></p></section>')
    return page(f"法拍屋購屋流程 9 步驟｜{NAME}", "法拍屋從確認案件、投標、繳款到點交交屋，9 個步驟說明。黃先生 Pitt、林小姐 Anna 全程協助。", "/process", h, _article_ld("法拍屋購屋流程 9 步驟", "法拍屋購屋流程說明", "/process"))

def fees_page():
    mark = lambda lvl, col: "✓" if lvl <= col + 1 and ((col == 0 and lvl == 1) or (col == 1 and lvl <= 2) or col == 2) else "—"
    th = "".join(f'<th style="text-align:center">{e(n)}<br><span style="font-size:20px;color:#d62828">{e(p)}</span><br><span style="font-size:12px;font-weight:400;color:#666">{e(s)}</span></th>' for n, p, s in FEE_COLS)
    rows = ""
    for i, (t, d, lvl) in enumerate(FEE_ROWS, 1):
        sub = f'<br><span style="font-size:13px;color:#666">{e(d)}</span>' if d else ""
        rows += f'<tr><td><b>{i:02d}</b>　{e(t)}{sub}</td>' + "".join(f'<td style="text-align:center">{mark(lvl, c)}</td>' for c in range(3)) + '</tr>'
    h = ('<nav class="bc"><a href="/">首頁</a> › 服務費用</nav><h1>法拍代標服務費用與收費標準</h1><p>三種方案，清楚列出每一項服務內容。實際費用依案件條件確認，歡迎先諮詢。</p>'
         f'<section class="box" style="overflow-x:auto"><table style="min-width:560px"><tr><th>服務項目</th>{th}</tr>{rows}</table></section>'
         '<section class="box"><h2>費用附註</h2><ol>' + "".join(f"<li>{e(n)}</li>" for n in FEE_NOTES) + '</ol></section>'
         f'<section class="box"><h2>聯絡我們</h2><p><b>黃先生 Pitt</b>　<a href="tel:0918313888">{PHONE_P}</a><br><b>林小姐 Anna</b>　<a href="tel:0986678928">{PHONE_A}</a></p>'
         f'<p><a class="btn line" href="{e(LINKS["LINE"])}" target="_blank" rel="noopener">LINE 諮詢</a><a class="btn" href="/process">購屋流程</a></p></section>')
    return page(f"法拍代標服務費用與收費標準｜{NAME}", "聲請點交 50,000 元、包辦點交 120,000 元、全程代標為標價 2–5%，列出 19 項服務內容與附註。", "/fees", h)

def svc_teaser():
    return ('<section class="box" id="svc"><h2>代標流程與服務費用</h2><p>9 個步驟看懂法拍，三種服務方案清楚標價。</p>'
            '<p><a class="btn" href="/process">購屋流程</a><a class="btn" href="/fees">服務費用</a></p></section>')

DRAWER = DRAWER.replace('<a href="/learn">法拍小教室</a>', '<a href="/process">購屋流程</a><a href="/fees">服務費用</a><a href="/learn">法拍小教室</a>')
_extras_base = extras_index
def extras_index():
    return svc_teaser() + _extras_base()
_write_learn_base = write_learn
def write_learn(urls):
    _write_learn_base(urls)
    write("site/process.html", process_page()); urls.append(("/process", 0.8))
    write("site/fees.html", fees_page()); urls.append(("/fees", 0.8))
