-- 法拍行銷與客戶經營：共用資料表（SQLite；語法相容 Cloudflare D1）
PRAGMA foreign_keys = ON;

-- A. 案件主檔
CREATE TABLE IF NOT EXISTS cases (
  case_id        TEXT PRIMARY KEY,            -- 唯一案件ID（由 執行機關+案號+物件識別 雜湊）
  court          TEXT NOT NULL DEFAULT '',    -- 執行機關；空白=待確認
  case_no        TEXT NOT NULL DEFAULT '',    -- 例：114乙184648
  object_key     TEXT NOT NULL DEFAULT '',    -- 標別／物件識別（正規化地址）
  title          TEXT, address TEXT, area TEXT, ptype TEXT,
  ping_total REAL, ping_main REAL, ping_attached REAL, ping_land REAL, floor TEXT, parking TEXT,
  round          INTEGER,                     -- 目前拍次
  auction_date   TEXT,                        -- ISO yyyy-mm-dd
  official_floor_price INTEGER,               -- 法院公告底價（元），僅來自公告
  deposit        INTEGER,                     -- 保證金
  estimated_price INTEGER,                    -- 預估價格（獨立欄位，不得當底價）
  listing_price_raw TEXT,                     -- 來源平台顯示價格原文，僅供比對
  delivery       TEXT,                        -- 點交／不點交／部分點交／待確認
  status         TEXT NOT NULL DEFAULT '待確認',  -- 待拍/停拍/撤回/拍定/流標/待確認
  needs_review   INTEGER NOT NULL DEFAULT 0,  -- 1=關鍵資料無法查核，阻擋自動發布
  review_reason  TEXT,
  source         TEXT, verified_at TEXT, version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT, updated_at TEXT,
  UNIQUE (court, case_no, object_key)
);
CREATE TABLE IF NOT EXISTS case_alias (       -- 各平台編號 → 案件ID（去重用）
  source TEXT NOT NULL, source_id TEXT NOT NULL, case_id TEXT NOT NULL REFERENCES cases(case_id),
  PRIMARY KEY (source, source_id)
);
CREATE TABLE IF NOT EXISTS case_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL REFERENCES cases(case_id),
  at TEXT NOT NULL, field TEXT NOT NULL, old TEXT, new TEXT, version INTEGER, source TEXT
);
CREATE TABLE IF NOT EXISTS case_media (        -- 照片／素材來源與使用權限
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL REFERENCES cases(case_id),
  kind TEXT, url TEXT, origin TEXT, usage_right TEXT NOT NULL DEFAULT '待確認',  -- 自有/授權/待確認/禁用
  UNIQUE (case_id, url)
);

-- B. 素材與刊登
CREATE TABLE IF NOT EXISTS assets (
  asset_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id),
  kind TEXT NOT NULL, platform_format TEXT, case_version INTEGER NOT NULL, template_version TEXT,
  body TEXT, file_ref TEXT, review_state TEXT NOT NULL DEFAULT '草稿',  -- 草稿/待審/已核可
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS publications (
  pub_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id), asset_id TEXT REFERENCES assets(asset_id),
  platform TEXT NOT NULL, platform_ref TEXT, url TEXT, published_case_version INTEGER,
  state TEXT NOT NULL DEFAULT '素材完成',   -- 素材完成/待發布/已發布/發布已驗證/失敗/待更新/待下架/已下架
  published_at TEXT, verified_at TEXT, last_error TEXT, retries INTEGER NOT NULL DEFAULT 0,
  UNIQUE (case_id, platform, platform_ref)
);
CREATE TABLE IF NOT EXISTS campaigns (
  campaign_id TEXT PRIMARY KEY, platform TEXT NOT NULL, name TEXT, case_id TEXT REFERENCES cases(case_id),
  state TEXT NOT NULL DEFAULT '草稿',        -- 草稿/待授權/進行中/暫停/結束
  spend_cap INTEGER                          -- 已授權上限（元）；NULL=未授權
);
CREATE TABLE IF NOT EXISTS spend_authorizations (
  id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT NOT NULL, cap_total INTEGER NOT NULL,
  valid_from TEXT NOT NULL, valid_to TEXT NOT NULL, granted_by TEXT NOT NULL, note TEXT
);
CREATE TABLE IF NOT EXISTS ad_stats (          -- 成效；缺資料就不寫入
  campaign_id TEXT, case_id TEXT, day TEXT, impressions INTEGER, clicks INTEGER, cost INTEGER,
  data_origin TEXT NOT NULL,                   -- 直接追蹤/人工登記/推估
  PRIMARY KEY (campaign_id, case_id, day)
);

-- C. 客戶與互動
CREATE TABLE IF NOT EXISTS customers (
  customer_id TEXT PRIMARY KEY, display_name TEXT, owner TEXT,
  budget TEXT, down_payment TEXT, purpose TEXT, buy_timing TEXT, want_areas TEXT,
  stage TEXT NOT NULL DEFAULT '新詢問',   -- 新詢問/需求確認/諮詢/預約/委託/投標/後續服務/未成交/結案
  lost_reason TEXT,                       -- 資金未備妥/暫無適合案件/仍在了解/延後購買/其他
  referred_by TEXT REFERENCES customers(customer_id), created_at TEXT
);
CREATE TABLE IF NOT EXISTS contact_points (    -- 同一客戶的聯絡方式；跨平台不憑姓名自動合併
  channel TEXT NOT NULL, handle TEXT NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(customer_id),
  consent TEXT NOT NULL DEFAULT '未確認',     -- 同意/未確認/停止聯絡
  PRIMARY KEY (channel, handle)
);
CREATE TABLE IF NOT EXISTS inquiries (
  inquiry_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(customer_id),
  case_id TEXT REFERENCES cases(case_id), source_platform TEXT, campaign_id TEXT,
  source_kind TEXT NOT NULL DEFAULT '未知',   -- 直接追蹤/人工補登/未知
  event_key TEXT UNIQUE,                      -- 重送同一事件不重複建立
  summary TEXT, at TEXT
);
CREATE TABLE IF NOT EXISTS interactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id TEXT NOT NULL REFERENCES customers(customer_id),
  at TEXT, channel TEXT, summary TEXT, owner TEXT, next_step TEXT, next_due TEXT
);
CREATE TABLE IF NOT EXISTS appointments (
  appt_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(customer_id),
  case_id TEXT REFERENCES cases(case_id), at TEXT NOT NULL, mode TEXT, place TEXT, prep TEXT,
  state TEXT NOT NULL DEFAULT '已預約', outcome TEXT   -- 已預約/已完成/取消/未到
);

-- D. 任務與自動化紀錄（idempotency_key 唯一 → 重跑不重複）
CREATE TABLE IF NOT EXISTS tasks (
  task_id INTEGER PRIMARY KEY AUTOINCREMENT, idempotency_key TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL, reason TEXT, case_id TEXT, customer_id TEXT, pub_id TEXT,
  owner TEXT, state TEXT NOT NULL DEFAULT '待辦',   -- 待辦/執行中/完成/待人工/失敗
  due TEXT, attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT, evidence TEXT,
  created_at TEXT, done_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_pub_case ON publications(case_id);
CREATE INDEX IF NOT EXISTS ix_task_state ON tasks(state, due);
