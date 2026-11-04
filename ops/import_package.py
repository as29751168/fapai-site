"""匯入「上架包」(xlsx + 案件與圖片對照.csv + posters/) 為草稿：建案件、預估價、海報素材、刊登任務。
不會對任何平台發布。用法：python3 -m ops.import_package <資料夾> [db路徑]"""
import csv, os, sys, openpyxl
from . import core as C


def run(db, folder):
    ws = openpyxl.load_workbook(os.path.join(folder, [f for f in os.listdir(folder) if f.endswith(".xlsx")][0]))["Sheet1"]
    hdr = [c.value for c in ws[1]]
    xl = {r[2]: dict(zip(hdr, r)) for r in ws.iter_rows(min_row=2, values_only=True)}
    out = []
    for r in csv.DictReader(open(os.path.join(folder, "案件與圖片對照.csv"), encoding="utf-8-sig")):
        x = xl[r["案號"]]
        addr = r["完整地址"]
        f = {"case_no": r["案號"], "object_key": C.norm_addr(addr), "title": x["房屋案名"], "address": addr, "area": x["縣市"] + x["鄉鎮市區"],
             "ptype": x["房屋類型"], "ping_total": x["總登記坪數"], "round": int(x["法拍屋拍次"]), "auction_date": C.roc_date(x["法拍屋開標日期"]),
             "official_floor_price": int(round(float(r["本次公告底價萬元"]) * 10000)),   # 包內明定：本次正式公告底價
             "listing_price_raw": f"{x['出售總價(萬)']}萬", "delivery": r["點交"], "status": "待拍", "floor": x["建物所在樓層"], "parking": x["車位"]}
        cid, st = C.upsert_case(db, f, "上架包", r["案號"])
        # 預估價：只有「下一拍八折預估／非正式公告」才寫入 estimated_price；第三拍正式底價者不寫
        if "預估" in r["價格性質"]:
            C.set_estimated_price(db, cid, int(round(float(r["海報主打價格萬元"]) * 10000)), "上架包")
        poster = os.path.join(folder, r["海報檔案"])
        aid = "S" + C._h(cid, r["海報檔案"])
        db.execute("INSERT OR IGNORE INTO assets (asset_id,case_id,kind,platform_format,case_version,template_version,file_ref,review_state,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                   (aid, cid, "海報", "4:3橫式", db.execute("SELECT version FROM cases WHERE case_id=?", (cid,)).fetchone()[0], "上架包3-9", poster, "待審", C.now()))
        pubs = [C.register_publication(db, cid, p, "", "", aid) for p in ("House-Info", "自有網站")]
        ok, why = C.can_publish(db, cid)
        out.append((r["原清單序號"], r["案號"], r["社區"], st, "可發布(待人工授權)" if ok else why, os.path.exists(poster)))
    db.commit(); return out


if __name__ == "__main__":
    db = C.connect(sys.argv[2] if len(sys.argv) > 2 else "ops/ops.db")
    for o in run(db, sys.argv[1]): print(o)
