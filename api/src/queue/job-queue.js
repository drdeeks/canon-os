"use strict";

const amqp = require("amqplib");

const DEFAULT_QUEUE_NAME = "canon.jobs";

function createRabbitMqJobQueue(options = {}) {
  const url = options.url || process.env.RABBITMQ_URL;
  const queueName = options.queueName || process.env.RABBITMQ_QUEUE || DEFAULT_QUEUE_NAME;
  const connect = options.connect || amqp.connect;

  if (typeof url !== "string" || url.trim() === "") {
    throw new Error("RABBITMQ_URL is required to configure the job queue.");
  }

  let connectionPromise;
  let channelPromise;

  async function getChannel() {
    if (!channelPromise) {
      connectionPromise = connect(url);
      channelPromise = connectionPromise
        .then((connection) => connection.createConfirmChannel())
        .then(async (channel) => {
          await channel.assertQueue(queueName, { durable: true });
          return channel;
        });
      channelPromise.catch(() => {
        connectionPromise = undefined;
        channelPromise = undefined;
      });
    }
    return channelPromise;
  }

  return {
    async enqueue(job) {
      const channel = await getChannel();
      const accepted = channel.sendToQueue(queueName, Buffer.from(JSON.stringify(job)), {
        contentType: "application/json",
        contentEncoding: "utf-8",
        deliveryMode: 2,
        messageId: job.id,
        timestamp: Math.floor(Date.now() / 1000),
        type: job.job_type,
      });
      if (!accepted) {
        await new Promise((resolve) => channel.once("drain", resolve));
      }
      await channel.waitForConfirms();
    },

    async close() {
      if (!channelPromise || !connectionPromise) {
        return;
      }
      const channel = await channelPromise;
      const connection = await connectionPromise;
      await channel.close();
      await connection.close();
    },

    queueName,
  };
}

module.exports = { DEFAULT_QUEUE_NAME, createRabbitMqJobQueue };
