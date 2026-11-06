-- 002：行銷與客戶經營增量。只新增欄位與資料表，不刪改既有資料。
-- 回復方式：備份資料庫後還原，或不呼叫 workflow.migrate（既有 core.py 不依賴這些欄位）。

-- A. 案件主檔：標別
ALTER TABLE cases ADD COLUMN lot TEXT;

-- B. 素材審閱與刊登
ALTER TABLE assets ADD COLUMN check_result TEXT;
ALTER TABLE assets ADD COLUMN reviewed_by TEXT;
ALTER TABLE assets ADD COLUMN reviewed_at TEXT;
ALTER TABLE publications ADD COLUMN campaign_id TEXT;

CREATE TABLE IF NOT EXISTS publication_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, pub_id TEXT NOT NULL REFERENCES publications(pub_id),
  at TEXT NOT NULL, action TEXT NOT NULL, result TEXT NOT NULL, detail TEXT, evidence TEXT
);
-- 正式發布、發訊息的授權；沒有有效授權就只能停在草稿或待發布
CREATE TABLE IF NOT EXISTS publish_authorizations (
  id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT NOT NULL, action TEXT NOT NULL,
  valid_from TEXT NOT NULL, valid_to TEXT NOT NULL, granted_by TEXT NOT NULL, note TEXT
);
-- 來源辨識：每個廣告或物件連結一個案件代碼
CREATE TABLE IF NOT EXISTS tracking_links (
  code TEXT PRIMARY KEY, case_id TEXT REFERENCES cases(case_id), platform TEXT NOT NULL,
  campaign_id TEXT, url TEXT, created_at TEXT, UNIQUE (case_id, platform, campaign_id)
);

-- C. 客戶
ALTER TABLE customers ADD COLUMN source_platform TEXT;
ALTER TABLE customers ADD COLUMN source_campaign TEXT;
ALTER TABLE customers ADD COLUMN contact_pref TEXT;
ALTER TABLE customers ADD COLUMN subscribed INTEGER NOT NULL DEFAULT 0;
ALTER TABLE customers ADD COLUMN do_not_contact INTEGER NOT NULL DEFAULT 0;
ALTER TABLE customers ADD COLUMN segment TEXT;
-- 有效詢問由人工判定；沒有紀錄=未判定。獨立成表，因為 core.py 以欄位順序寫入 inquiries
CREATE TABLE IF NOT EXISTS inquiry_quality (
  inquiry_id TEXT PRIMARY KEY REFERENCES inquiries(inquiry_id),
  is_valid INTEGER NOT NULL, judged_by TEXT, at TEXT
);

CREATE TABLE IF NOT EXISTS customer_cases (   -- 一位客戶可關注多個案件
  customer_id TEXT NOT NULL REFERENCES customers(customer_id),
  case_id TEXT NOT NULL REFERENCES cases(case_id), at TEXT,
  PRIMARY KEY (customer_id, case_id)
);
CREATE TABLE IF NOT EXISTS mandates (         -- 委託與投標服務
  mandate_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(customer_id),
  case_id TEXT REFERENCES cases(case_id), service TEXT, signed_at TEXT,
  stage TEXT NOT NULL DEFAULT '委託簽約', result TEXT, result_at TEXT,
  UNIQUE (customer_id, case_id)
);
CREATE TABLE IF NOT EXISTS mandate_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, mandate_id TEXT NOT NULL REFERENCES mandates(mandate_id),
  at TEXT, stage TEXT, note TEXT, next_step TEXT, next_due TEXT
);
-- 服務費與條件集中管理；有衝突就標待確認，不自行決定
CREATE TABLE IF NOT EXISTS fee_terms (
  term_id TEXT PRIMARY KEY, item TEXT NOT NULL, value TEXT, condition TEXT, source TEXT,
  effective_from TEXT, effective_to TEXT, status TEXT NOT NULL DEFAULT '待確認', note TEXT
);

-- D. 任務
ALTER TABLE tasks ADD COLUMN next_step TEXT;
ALTER TABLE tasks ADD COLUMN module TEXT;
