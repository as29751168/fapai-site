// LINE 登入完成後回到這裡：驗證、取得名稱、存進名單（KV: LEADS）
import { sign } from "./line-login.js";
const fromB64u = (s) => new TextDecoder().decode(Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0)));
const safeNext = (n) => (typeof n === "string" && n.startsWith("/") && !n.startsWith("//") ? n : "/");

// 出錯也放行：客人照樣回原頁看全部物件，只是名單沒記到；原因另存 KV（err:時間）方便查
async function letIn(env, next, why) {
  try { await env.LEADS.put("err:" + new Date().toISOString(), String(why).slice(0, 80), { expirationTtl: 2592000 }); } catch (e) {}
  const h = new Headers({ Location: next });
  h.append("Set-Cookie", "tl=1; Path=/; Max-Age=31536000; Secure; SameSite=Lax");
  return new Response(null, { status: 302, headers: h });
}

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state") || "";
  // 驗 state：時間＋回跳頁＋簽章，10 分鐘內有效（不靠 cookie）
  let next = "/", ok = false;
  const parts = state.split(".");
  if (parts.length === 3) {
    try {
      const age = Date.now() - parseInt(parts[0], 36);
      ok = age >= 0 && age < 600000 && (await sign(env.LINE_CHANNEL_SECRET, parts[0] + "." + parts[1])) === parts[2];
      if (ok) next = safeNext(fromB64u(parts[1]));
    } catch (e) { ok = false; }
  }
  // 客人按取消或 LINE 回錯誤：直接回原頁，不顯示錯誤
  if (url.searchParams.get("error")) return new Response(null, { status: 302, headers: { Location: ok ? next : "/" } });
  if (!code || !ok) return letIn(env, next, "state:" + (code ? "bad" : "nocode"));

  const tok = await fetch("https://api.line.me/oauth2/v2.1/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code", code, redirect_uri: `${url.origin}/api/line-callback`,
      client_id: env.LINE_CHANNEL_ID, client_secret: env.LINE_CHANNEL_SECRET,
    }),
  }).then((r) => r.json()).catch(() => ({ error: "fetch" }));
  if (!tok.access_token) return letIn(env, next, "token:" + (tok.error || "unknown") + ":" + (tok.error_description || ""));

  const p = await fetch("https://api.line.me/v2/profile", {
    headers: { Authorization: "Bearer " + tok.access_token },
  }).then((r) => r.json());
  if (!p.userId) return letIn(env, next, "profile:" + (p.message || "unknown"));

  // 有沒有加 LINE@ 好友（登入頻道沒連結官方帳號時查不到，就留空）
  let friend = "";
  try {
    const fr = await fetch("https://api.line.me/friendship/v1/status", {
      headers: { Authorization: "Bearer " + tok.access_token },
    }).then((r) => (r.ok ? r.json() : null));
    if (fr && typeof fr.friendFlag === "boolean") friend = fr.friendFlag ? "是" : "否";
  } catch (e) {}

  const key = "u:" + p.userId;
  const old = JSON.parse((await env.LEADS.get(key)) || "null");
  const now = new Date().toISOString();
  await env.LEADS.put(key, JSON.stringify({
    name: p.displayName, first: old ? old.first : now, last: now,
    count: (old ? old.count : 0) + 1, from: old ? old.from : next,
    friend: friend || (old && old.friend) || "",
  }));
  const h = new Headers({ Location: next });
  h.append("Set-Cookie", "ls=; Path=/; Max-Age=0");
  h.append("Set-Cookie", "tl=1; Path=/; Max-Age=31536000; Secure; SameSite=Lax");
  return new Response(null, { status: 302, headers: h });
}
