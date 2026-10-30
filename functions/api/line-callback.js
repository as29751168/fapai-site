// LINE 登入完成後回到這裡：驗證、取得名稱、存進名單（KV: LEADS）
export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const m = (request.headers.get("Cookie") || "").match(/(?:^|;\s*)ls=([^;]+)/);
  const [saved, nextRaw] = m ? decodeURIComponent(m[1]).split("|") : [];
  if (!code || !state || state !== saved) return new Response("登入失敗，請回上一頁重試。", { status: 400 });
  let next = decodeURIComponent(nextRaw || "/");
  if (!next.startsWith("/") || next.startsWith("//")) next = "/";

  const tok = await fetch("https://api.line.me/oauth2/v2.1/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code", code, redirect_uri: `${url.origin}/api/line-callback`,
      client_id: env.LINE_CHANNEL_ID, client_secret: env.LINE_CHANNEL_SECRET,
    }),
  }).then((r) => r.json());
  if (!tok.access_token) return new Response("登入失敗，請稍後再試。", { status: 400 });

  const p = await fetch("https://api.line.me/v2/profile", {
    headers: { Authorization: "Bearer " + tok.access_token },
  }).then((r) => r.json());
  if (!p.userId) return new Response("無法取得 LINE 資料。", { status: 400 });

  const key = "u:" + p.userId;
  const old = JSON.parse((await env.LEADS.get(key)) || "null");
  const now = new Date().toISOString();
  await env.LEADS.put(key, JSON.stringify({
    name: p.displayName, first: old ? old.first : now, last: now,
    count: (old ? old.count : 0) + 1, from: old ? old.from : next,
  }));
  const h = new Headers({ Location: next });
  h.append("Set-Cookie", "ls=; Path=/; Max-Age=0");
  h.append("Set-Cookie", "tl=1; Path=/; Max-Age=31536000; Secure; SameSite=Lax");
  return new Response(null, { status: 302, headers: h });
}
