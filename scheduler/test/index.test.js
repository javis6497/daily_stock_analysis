import test from "node:test";
import assert from "node:assert/strict";

import {
  dispatchWithRetry,
  dispatchWorkflow,
  notifySchedulerFailure,
  scheduleForCron
} from "../src/index.js";

test("maps redundant UTC cron triggers to Beijing report slots", () => {
  assert.deepEqual(scheduleForCron("27 0 * * 1-5"), {
    session: "premarket",
    target: "08:37"
  });
  assert.deepEqual(scheduleForCron("2 6 * * 1-5"), {
    session: "fund_action",
    target: "14:07"
  });
  assert.equal(scheduleForCron("0 0 * * *"), null);
});

test("enables and dispatches the core workflow with resilient inputs", async () => {
  const calls = [];
  const fakeFetch = async (url, options) => {
    calls.push({ url, options });
    return { status: url.endsWith("/enable") ? 204 : 204 };
  };
  const env = {
    GITHUB_OWNER: "owner",
    GITHUB_REPO: "repo",
    GITHUB_REF: "main",
    WORKFLOW_FILE: "daily-report.yml",
    GITHUB_TOKEN: "secret"
  };

  await dispatchWorkflow(env, { session: "premarket", target: "08:37" }, fakeFetch);

  assert.equal(calls.length, 2);
  assert.equal(calls[0].options.method, "PUT");
  assert.equal(calls[1].options.method, "POST");
  const payload = JSON.parse(calls[1].options.body);
  assert.equal(payload.inputs.scheduled_run, "true");
  assert.equal(payload.inputs.silent_failure, "true");
  assert.equal(payload.inputs.delivery_target, "08:37");
});

test("retries a failed GitHub dispatch", async () => {
  let dispatchAttempts = 0;
  const fakeFetch = async (url) => {
    if (url.endsWith("/enable")) {
      return { status: 204 };
    }
    dispatchAttempts += 1;
    return { status: dispatchAttempts === 1 ? 503 : 204 };
  };
  const env = {
    GITHUB_OWNER: "owner",
    GITHUB_REPO: "repo",
    GITHUB_REF: "main",
    WORKFLOW_FILE: "daily-report.yml",
    GITHUB_TOKEN: "secret"
  };

  await dispatchWithRetry(
    env,
    { session: "premarket", target: "08:37" },
    fakeFetch,
    async () => {}
  );

  assert.equal(dispatchAttempts, 2);
});

test("sends a DingTalk watchdog alert after dispatch retries are exhausted", async () => {
  const calls = [];
  const fakeFetch = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, status: 200 };
  };

  await notifySchedulerFailure(
    { DINGTALK_WEBHOOK: "https://example.com/robot" },
    { session: "premarket", target: "08:37" },
    new Error("GitHub unavailable"),
    fakeFetch
  );

  const payload = JSON.parse(calls[0].options.body);
  assert.equal(payload.msgtype, "markdown");
  assert.match(payload.markdown.text, /GitHub unavailable/);
});
