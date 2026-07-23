const SCHEDULES = Object.freeze({
  "27 0 * * 1-5": { session: "premarket", target: "08:37" },
  "32 0 * * 1-5": { session: "premarket", target: "08:37" },
  "57 5 * * 1-5": { session: "fund_action", target: "14:07" },
  "2 6 * * 1-5": { session: "fund_action", target: "14:07" },
  "27 8 * * 1-5": { session: "postmarket", target: "16:37" },
  "32 8 * * 1-5": { session: "postmarket", target: "16:37" },
  "27 1 * * 6,0": { session: "weekend_news", target: "09:37" },
  "32 1 * * 6,0": { session: "weekend_news", target: "09:37" }
});

export function scheduleForCron(cron) {
  return SCHEDULES[cron] ?? null;
}

function githubHeaders(env) {
  return {
    Accept: "application/vnd.github+json",
    Authorization: `Bearer ${env.GITHUB_TOKEN}`,
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "stock-quant-scheduler"
  };
}

export async function dispatchWorkflow(env, schedule, fetchImpl = fetch) {
  const base = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/${env.WORKFLOW_FILE}`;
  const headers = githubHeaders(env);

  const enableResponse = await fetchImpl(`${base}/enable`, {
    method: "PUT",
    headers
  });
  if (![204, 409].includes(enableResponse.status)) {
    throw new Error(`GitHub workflow enable failed: HTTP ${enableResponse.status}`);
  }

  const dispatchResponse = await fetchImpl(`${base}/dispatches`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({
      ref: env.GITHUB_REF || "main",
      inputs: {
        session: schedule.session,
        scheduled_run: "true",
        delivery_target: schedule.target,
        delivery_tolerance_minutes: "5",
        silent_failure: "true"
      }
    })
  });
  if (dispatchResponse.status !== 204) {
    throw new Error(`GitHub workflow dispatch failed: HTTP ${dispatchResponse.status}`);
  }
}

export async function dispatchWithRetry(
  env,
  schedule,
  fetchImpl = fetch,
  sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)),
  maxAttempts = 3
) {
  let lastError;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      await dispatchWorkflow(env, schedule, fetchImpl);
      return;
    } catch (error) {
      lastError = error;
      if (attempt < maxAttempts) {
        await sleep(1000 * 2 ** (attempt - 1));
      }
    }
  }
  throw lastError;
}

export async function notifySchedulerFailure(env, schedule, error, fetchImpl = fetch) {
  if (!env.DINGTALK_WEBHOOK) {
    return;
  }
  const payload = {
    msgtype: "markdown",
    markdown: {
      title: "量化调度器故障",
      text: [
        "# 量化调度器故障",
        `- 任务：${schedule.session}`,
        `- 目标时间：${schedule.target}（北京时间）`,
        `- 原因：${error.message || String(error)}`,
        "- 状态：外部调度已重试 3 次，GitHub 报告任务仍未成功启动。"
      ].join("\n")
    }
  };
  const response = await fetchImpl(await signedDingTalkUrl(env), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(`DingTalk scheduler alert failed: HTTP ${response.status}`);
  }
}

async function signedDingTalkUrl(env) {
  if (!env.DINGTALK_SECRET) {
    return env.DINGTALK_WEBHOOK;
  }
  const timestamp = Date.now();
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(env.DINGTALK_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    encoder.encode(`${timestamp}\n${env.DINGTALK_SECRET}`)
  );
  const sign = btoa(String.fromCharCode(...new Uint8Array(signature)));
  const url = new URL(env.DINGTALK_WEBHOOK);
  url.searchParams.set("timestamp", String(timestamp));
  url.searchParams.set("sign", sign);
  return url.toString();
}

async function handleManualTrigger(request, env) {
  if (request.headers.get("Authorization") !== `Bearer ${env.SCHEDULER_ADMIN_TOKEN}`) {
    return new Response("Unauthorized", { status: 401 });
  }
  const url = new URL(request.url);
  const session = url.searchParams.get("session");
  const target = url.searchParams.get("target");
  const allowed = new Set(["premarket", "fund_action", "postmarket", "weekend_news"]);
  if (!allowed.has(session) || !/^\d{2}:\d{2}$/.test(target || "")) {
    return new Response("Invalid session or target", { status: 400 });
  }
  await dispatchWithRetry(env, { session, target });
  return Response.json({ ok: true, session, target });
}

export default {
  async scheduled(controller, env, ctx) {
    const schedule = scheduleForCron(controller.cron);
    if (!schedule) {
      throw new Error(`Unknown cron: ${controller.cron}`);
    }
    ctx.waitUntil(
      dispatchWithRetry(env, schedule).catch((error) =>
        notifySchedulerFailure(env, schedule, error)
      )
    );
  },

  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/health") {
      return Response.json({ ok: true, scheduler: "stock-quant-scheduler" });
    }
    if (url.pathname === "/trigger" && request.method === "POST") {
      return handleManualTrigger(request, env);
    }
    return new Response("Not found", { status: 404 });
  }
};
