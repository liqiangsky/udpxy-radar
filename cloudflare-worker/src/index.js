/**
 * Cloudflare Worker 定时心跳
 * 每分钟 ping HF Spaces，唤醒实例并触发 cron 任务
 *
 * 部署: npx wrangler deploy
 */

const HF_SPACE_URL = "https://wuliao666-iptv-server.hf.space";
const HEARTBEAT_PATH = "/api/cron/heartbeat";

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(triggerHeartbeat(env));
  },

  async fetch(request, env, ctx) {
    ctx.waitUntil(triggerHeartbeat(env));
    return new Response("Heartbeat triggered", { status: 200 });
  },
};

async function triggerHeartbeat(env) {
  try {
    const url = `${HF_SPACE_URL}${HEARTBEAT_PATH}`;
    console.log(`[heartbeat] POST ${url}`);

    const headers = { "Content-Type": "application/json" };
    const token = env.CALLBACK_TOKEN || "";
    if (token) {
      headers["X-Callback-Token"] = token;
    }

    const res = await fetch(url, {
      method: "POST",
      headers: headers,
    });

    const body = await res.json();
    console.log(`[heartbeat] ${res.status} -> triggered: ${body.triggered}, tasks: ${JSON.stringify(body.tasks)}`);
  } catch (e) {
    console.error(`[heartbeat] 失败: ${e.message}`);
  }
}
