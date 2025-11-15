#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${ROOT_DIR}/.env"

if [ -f "$ENV_FILE" ]; then
  echo "Loading env vars from $ENV_FILE"
  set -a
  source "$ENV_FILE"
  set +a
else
  echo "No .env file found at $ENV_FILE, assuming env vars are already set"
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ARTIFACT_BUCKET_NAME="${PROJECT_NAME}-${ENV}-${ACCOUNT_ID}-${REGION}-artifacts"

GIT_SHA="${GITSHA:-$(git rev-parse HEAD)}"
ZIP_NAME="app-${GIT_SHA}.zip"

echo "Forcing update of lambda code whether it wants to or not..."
aws lambda update-function-code \
  --function-name "${PROJECT_NAME}-${ENV}-app" \
  --s3-bucket "$ARTIFACT_BUCKET_NAME" \
  --s3-key "$ZIP_NAME" \
  --publish \
  --region "${REGION}" >/dev/null
aws lambda wait function-updated --function-name "${PROJECT_NAME}-${ENV}-app" --region "$REGION"
aws lambda wait function-active  --function-name "${PROJECT_NAME}-${ENV}-app" --region "$REGION"
