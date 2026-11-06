"""內容草稿與發布前檢查。不憑空補資料，也不會對任何平台發布。"""
import re

BRAND = "104法拍網｜法拍服務團隊"
CONTACTS = "黃先生 Pitt 0918-313-888／林小姐 Anna 0986-678-928"
DISCLAIMER = "本案件資訊整理自法院公開拍賣公告，僅提供法拍資訊及代拍服務。案件狀態、底價、拍賣日期及是否仍可投標，均以法院最新公告為準。"
SEIZED_NOTICE = "本案已查封，無法看室內，現場僅能了解周邊與外觀。"
POSTER_FORMATS = {"4:3橫式": (2000, 1500), "FB 4:5直式": (1080, 1350)}
USABLE_RIGHTS = ("自有", "授權", "法院公告附件")
# 「保證金」是法拍術語，檢查前會先排除
BANNED = ("保證", "穩賺", "撿便宜", "超安心", "完全避開風險", "全台最低", "第一名", "可看室內", "可進屋", "貸款成數一定", "無虞")
ROUND_CN = "零一二三四五六七八九十"


def wan(yuan):
    """元轉萬元文字，不做進位：12622000 → 1,262.2"""
    value = yuan / 10000
    text = f"{value:,.2f}".rstrip("0").rstrip(".")
    return text


def round_text(rnd):
    return f"第{ROUND_CN[rnd]}拍" if rnd and rnd <= 10 else "拍次待確認"


def roc(iso):
    if not iso:
        return "日期待確認"
    y, m, d = iso.split("-")
    return f"{int(y) - 1911}/{int(m)}/{int(d)}"


def _core_lines(case):
    lines = [
        f"案號：{case['case_no'] or '待確認'}",
        f"地址：{case['address'] or '待確認'}",
        f"{round_text(case['round'])}｜拍賣日 {roc(case['auction_date'])}",
    ]
    if case["official_floor_price"]:
        lines.append(f"本次法院公告底價：{wan(case['official_floor_price'])} 萬元")
    else:
        lines.append("本次法院公告底價：待確認")
    if case["deposit"]:
        lines.append(f"保證金：{wan(case['deposit'])} 萬元（以法院公告為準）")
    lines.append(f"點交情形：{case['delivery'] or '待確認'}")
    if case["estimated_price"]:
        lines.append(f"下一拍參考：約 {wan(case['estimated_price'])} 萬元（預估，非法院公告）")
    return lines


def build_post(case, cta="想了解這件，歡迎預約諮詢"):
    """FB／LINE 短文草稿。只使用案件主檔已有的資料。"""
    return "\n".join([
        f"【{case['title'] or case['address'] or '法拍案件'}】", *_core_lines(case), "",
        SEIZED_NOTICE, "", f"{cta}：{CONTACTS}", BRAND, "", DISCLAIMER,
    ])


def poster_spec(case, media_rows, fmt):
    """海報規格。沒有可用照片權限就不產生，也不憑空生成建築、室內或公設。"""
    if fmt not in POSTER_FORMATS:
        raise ValueError(f"未核定的海報格式：{fmt}")
    usable = [m for m in media_rows if m["usage_right"] in USABLE_RIGHTS]
    if not usable:
        return None, "缺照片使用權限，不得製作"
    width, height = POSTER_FORMATS[fmt]
    return {
        "format": fmt, "width": width, "height": height, "photo": usable[0]["url"],
        "colors": "深藍、白、香檳金", "lines": _core_lines(case),
        "contacts": CONTACTS, "brand": BRAND, "footer": "資料以法院最新公告為準",
    }, ""


def check_content(case, text):
    """發布前檢查，回傳問題清單；空清單才算通過。"""
    issues = []
    clean = text.replace("保證金", "")
    for word in BANNED:
        if word in clean:
            issues.append(f"禁用字詞：{word}")
    required = (
        ("案號", case["case_no"]), ("拍次", round_text(case["round"]) if case["round"] else None),
        ("拍賣日期", roc(case["auction_date"]) if case["auction_date"] else None),
        ("點交情形", case["delivery"]),
    )
    for name, value in required:
        if not value:
            issues.append(f"案件缺{name}")
        elif value not in text:
            issues.append(f"內容未列{name}")
    if not case["official_floor_price"]:
        issues.append("案件缺正式公告底價")
    elif wan(case["official_floor_price"]) not in text:
        issues.append("內容未列正式公告底價或金額不符")
    if case["estimated_price"]:
        est = wan(case["estimated_price"])
        if re.search(rf"底價[^\n]{{0,12}}{re.escape(est)}", text):
            issues.append("預估價格被寫成底價")
        if est in text and not re.search(r"預估[,，、]?\s*非(法院|正式)?公告", text):
            issues.append("預估價格未標示非法院公告")
    for name, phrase in (("已查封提醒", "已查封"), ("無法看室內提醒", "無法看室內"), ("法院公告優先文字", "以法院最新公告為準"), ("Pitt 聯絡資訊", "0918-313-888"), ("Anna 聯絡資訊", "0986-678-928"), ("品牌名稱", BRAND)):
        if phrase not in text:
            issues.append(f"缺{name}")
    return issues
