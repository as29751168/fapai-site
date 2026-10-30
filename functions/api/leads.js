// 下載名單（CSV，可用 Excel 開）：/api/leads?key=你的ADMIN_KEY
export async function onRequestGet({ request, env }) {
  const key = new URL(request.url).searchParams.get("key");
  if (!env.ADMIN_KEY || key !== env.ADMIN_KEY) return new Response("Forbidden", { status: 403 });
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
  const csv = "﻿" + rows.map((r) => r.map((c) => `"${String(c ?? "").replace(/"/g, '""')}"`).join(",")).join("\r\n");
  return new Response(csv, { headers: { "Content-Type": "text/csv; charset=utf-8", "Content-Disposition": 'attachment; filename="leads.csv"' } });
}
