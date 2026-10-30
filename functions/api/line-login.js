// 轉到 LINE 登入頁。需要環境變數 LINE_CHANNEL_ID
export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  let next = url.searchParams.get("next") || "/";
  if (!next.startsWith("/") || next.startsWith("//")) next = "/";
  const state = crypto.randomUUID();
  const redirect = `${url.origin}/api/line-callback`;
  const q = new URLSearchParams({
    response_type: "code", client_id: env.LINE_CHANNEL_ID, redirect_uri: redirect,
    state, scope: "profile openid",
  });
  return new Response(null, {
    status: 302,
    headers: {
      Location: "https://access.line.me/oauth2/v2.1/authorize?" + q,
      "Set-Cookie": `ls=${state}|${encodeURIComponent(next)}; Path=/; Max-Age=600; HttpOnly; Secure; SameSite=Lax`,
    },
  });
}
