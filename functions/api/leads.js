// 下載名單（CSV，可用 Excel 開）
// 建議用標頭帶金鑰：Authorization: Bearer <ADMIN_KEY>（不會留在網址、瀏覽紀錄與日誌）
// 舊用法 /api/leads?key=... 暫時保留相容，之後改用標頭。
function same(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}
// 防 CSV 公式注入：LINE 暱稱是使用者自己取的，開頭是 = + - @ 或定位字元時前面加 '
const cell = (c) => {
  let s = String(c ?? "");
  if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;
  return `"${s.replace(/"/g, '""')}"`;
};
const NOSTORE = { "Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow" };

export async function onRequestGet({ request, env }) {
  const auth = request.headers.get("Authorization") || "";
  const key = auth.startsWith("Bearer ") ? auth.slice(7) : new URL(request.url).searchParams.get("key");
  if (!env.ADMIN_KEY || !same(key, env.ADMIN_KEY)) return new Response("Forbidden", { status: 403, headers: NOSTORE });
  const rows = [["LINE名稱", "首次登入", "最近登入", "登入次數", "從哪頁進來"]];
  let cursor;
  do {
    const l = await env.LEADS.list({ prefix: "u:", cursor });
    for (const k of l.keys) {
      const v = JSON.parse((await env.LEADS.get(k.name)) || "{}");
      rows.push([v.name, v.first, v.last, v.count, v.from]);
    }
    cursor = l.list_complete ? null : l.cursor;
  } while (cursor);
  const csv = "﻿" + rows.map((r) => r.map(cell).join(",")).join("\r\n");
  return new Response(csv, { headers: { ...NOSTORE, "Content-Type": "text/csv; charset=utf-8", "Content-Disposition": 'attachment; filename="leads.csv"' } });
}
