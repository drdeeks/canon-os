"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { DEFAULT_QUEUE_NAME, createRabbitMqJobQueue } = require("../src/queue/job-queue");

test("RabbitMQ publisher declares a durable queue and waits for a broker confirm", async () => {
  const calls = [];
  const channel = {
    async assertQueue(name, options) {
      calls.push(["assertQueue", name, options]);
    },
    sendToQueue(name, body, options) {
      calls.push(["sendToQueue", name, JSON.parse(body.toString("utf8")), options]);
      return true;
    },
    async waitForConfirms() {
      calls.push(["waitForConfirms"]);
    },
    async close() {
      calls.push(["channel.close"]);
    },
  };
  const connection = {
    async createConfirmChannel() {
      calls.push(["createConfirmChannel"]);
      return channel;
    },
    async close() {
      calls.push(["connection.close"]);
    },
  };
  const queue = createRabbitMqJobQueue({
    url: "amqp://test",
    connect: async (url) => {
      calls.push(["connect", url]);
      return connection;
    },
  });
  const job = { id: "job-123", job_type: "content.generate", payload: { prompt: "Canon" } };

  await queue.enqueue(job);
  await queue.close();

  assert.deepEqual(calls, [
    ["connect", "amqp://test"],
    ["createConfirmChannel"],
    ["assertQueue", DEFAULT_QUEUE_NAME, { durable: true }],
    ["sendToQueue", DEFAULT_QUEUE_NAME, job, {
      contentType: "application/json",
      contentEncoding: "utf-8",
      deliveryMode: 2,
      messageId: "job-123",
      timestamp: calls[3][3].timestamp,
      type: "content.generate",
    }],
    ["waitForConfirms"],
    ["channel.close"],
    ["connection.close"],
  ]);
  assert.equal(typeof calls[3][3].timestamp, "number");
});

test("RabbitMQ publisher requires a connection URL", () => {
  assert.throws(() => createRabbitMqJobQueue({ url: "" }), /RABBITMQ_URL is required/);
});
