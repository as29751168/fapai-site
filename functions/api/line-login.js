// 轉到 LINE 登入頁。需要環境變數 LINE_CHANNEL_ID、LINE_CHANNEL_SECRET
// bot_prompt=aggressive：登入時同一頁問要不要加 LINE@ 好友（登入頻道已連結 @635nftwk）
// state 自帶簽章（時間＋回跳頁＋HMAC），不靠 cookie：手機從 LINE 內建瀏覽器跳到 Safari 時 cookie 會不見
const b64u = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
export async function sign(secret, payload) {
  const k = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return b64u(await crypto.subtle.sign("HMAC", k, new TextEncoder().encode(payload))).slice(0, 32);
}
// 2026-11-25 Anna：LINE 登入停用，改成加 LINE@；舊網址一律轉到 LINE@（KV leads 既有資料保留不刪）
export async function onRequestGet() {
  return Response.redirect("https://lin.ee/Y2bGSIB", 302);
}
/* 原登入流程（停用保留）
export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  let next = url.searchParams.get("next") || "/";
  if (!next.startsWith("/") || next.startsWith("//")) next = "/";
  const payload = Date.now().toString(36) + "." + b64u(new TextEncoder().encode(next));
  const state = payload + "." + (await sign(env.LINE_CHANNEL_SECRET, payload));
  const redirect = `${url.origin}/api/line-callback`;
  const q = new URLSearchParams({
    response_type: "code", client_id: env.LINE_CHANNEL_ID, redirect_uri: redirect,
    state, scope: "profile openid", bot_prompt: "aggressive",
  });
  return new Response(null, {
    status: 302,
    headers: { Location: "https://access.line.me/oauth2/v2.1/authorize?" + q, "Cache-Control": "no-store" },
  });
}

*/
