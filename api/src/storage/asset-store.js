"use strict";

const { S3Client, HeadBucketCommand, CreateBucketCommand, PutBucketVersioningCommand, PutObjectCommand, GetObjectCommand } = require("@aws-sdk/client-s3");

function required(value, name) {
  if (!value) {
    throw new Error(`${name} is required for S3 asset storage.`);
  }
  return value;
}

function decodeFilename(metadata, fallback) {
  try {
    return metadata && metadata.filename ? decodeURIComponent(metadata.filename) : fallback;
  } catch {
    return fallback;
  }
}

function createS3AssetStore(options = {}) {
  const bucket = options.bucket || process.env.S3_BUCKET || "canon-assets";
  const client = options.client || new S3Client({
    endpoint: options.endpoint || process.env.S3_ENDPOINT,
    region: options.region || process.env.S3_REGION || "us-east-1",
    forcePathStyle: options.forcePathStyle ?? (process.env.S3_FORCE_PATH_STYLE !== "false"),
    credentials: options.credentials || {
      accessKeyId: required(process.env.S3_ACCESS_KEY, "S3_ACCESS_KEY"),
      secretAccessKey: required(process.env.S3_SECRET_KEY, "S3_SECRET_KEY"),
    },
  });
  let ready;

  async function ensureBucket() {
    if (!ready) {
      ready = (async () => {
        try {
          await client.send(new HeadBucketCommand({ Bucket: bucket }));
        } catch (error) {
          if (error.name !== "NotFound" && error.$metadata?.httpStatusCode !== 404) {
            throw error;
          }
          await client.send(new CreateBucketCommand({ Bucket: bucket }));
        }
        await client.send(new PutBucketVersioningCommand({
          Bucket: bucket,
          VersioningConfiguration: { Status: "Enabled" },
        }));
      })();
    }
    return ready;
  }

  return {
    async upload({ key, body, contentType, filename }) {
      await ensureBucket();
      await client.send(new PutObjectCommand({
        Bucket: bucket,
        Key: key,
        Body: body,
        ContentType: contentType || "application/octet-stream",
        Metadata: { filename: encodeURIComponent(filename) },
      }));
    },

    async download({ key }) {
      await ensureBucket();
      const object = await client.send(new GetObjectCommand({ Bucket: bucket, Key: key }));
      return {
        body: Buffer.from(await object.Body.transformToByteArray()),
        contentType: object.ContentType || "application/octet-stream",
        filename: decodeFilename(object.Metadata, key.split("/").pop()),
      };
    },
  };
}

function createInMemoryAssetStore() {
  const assets = new Map();
  return {
    async upload({ key, body, contentType, filename }) {
      assets.set(key, {
        body: Buffer.from(body),
        contentType: contentType || "application/octet-stream",
        filename,
      });
    },
    async download({ key }) {
      const asset = assets.get(key);
      if (!asset) {
        const error = new Error("Asset not found.");
        error.code = "ASSET_NOT_FOUND";
        throw error;
      }
      return { ...asset, body: Buffer.from(asset.body) };
    },
  };
}

module.exports = { createS3AssetStore, createInMemoryAssetStore };
