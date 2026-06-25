#!/bin/sh
# One-shot: register the MinIO server, create the private bucket, then exit.
# Run by the `createbuckets` service (minio/mc) after MinIO is healthy.
set -e

# Point mc at our MinIO using the root credentials from the environment.
mc alias set local "http://minio:9000" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

# Create the bucket if it doesn't already exist (idempotent across restarts).
mc mb --ignore-existing "local/$MINIO_BUCKET"

# Keep it PRIVATE — files are only ever served through the authenticated API
# (or short-lived presigned URLs), never via public bucket access.
mc anonymous set none "local/$MINIO_BUCKET"

echo "Bucket '$MINIO_BUCKET' ready (private)."
exit 0
