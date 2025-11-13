#!/bin/bash
set -euo pipefail

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
