// 2026-11-25 站內轉換：LINE@ 按鈕點擊次數
// POST /api/click  {p: 頁面路徑, t: "line@"|"ask"|"login"}  → KV LEADS 的 c:<日期>:<t>:<路徑> 加 1
// GET  /api/click  （標頭 Authorization: Bearer <ADMIN_KEY>）→ 下載 CSV：日期、按鈕、頁面、次數
function same(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}
const NOSTORE = { "Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow" };
const TYPES = new Set(["line@", "ask", "login"]);

export async function onRequestPost({ request, env }) {
  try {
    const b = JSON.parse((await request.text()).slice(0, 500) || "{}");
    const t = TYPES.has(b.t) ? b.t : "";
    const p = typeof b.p === "string" && b.p.startsWith("/") ? b.p.slice(0, 120) : "";
    if (!t || !p || !env.LEADS) return new Response(null, { status: 204, headers: NOSTORE });
    const day = new Date(Date.now() + 8 * 3600e3).toISOString().slice(0, 10);   // 台北日期
    const k = `c:${day}:${t}:${p}`;
    const n = parseInt((await env.LEADS.get(k)) || "0", 10) || 0;
    await env.LEADS.put(k, String(n + 1), { expirationTtl: 400 * 86400 });
  } catch (e) {}
  return new Response(null, { status: 204, headers: NOSTORE });
}

export async function onRequestGet({ request, env }) {
  const auth = request.headers.get("Authorization") || "";
  const key = auth.startsWith("Bearer ") ? auth.slice(7) : "";
  if (!env.ADMIN_KEY || !same(key, env.ADMIN_KEY)) return new Response("Forbidden", { status: 403, headers: NOSTORE });
  const rows = [["日期", "按鈕", "頁面", "次數"]];
  let cursor;
  do {
    const l = await env.LEADS.list({ prefix: "c:", cursor });
    for (const k of l.keys) {
      const [, day, t, ...rest] = k.name.split(":");
      rows.push([day, t, rest.join(":"), (await env.LEADS.get(k.name)) || "0"]);
    }
    cursor = l.list_complete ? null : l.cursor;
  } while (cursor);
  const csv = "﻿" + rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\r\n");
  return new Response(csv, { headers: { ...NOSTORE, "Content-Type": "text/csv; charset=utf-8" } });
}
