#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# --- Load env ---

ENV_ARG="${1:-}"
if [[ "$ENV_ARG" != "dev" && "$ENV_ARG" != "prod" ]]; then
  echo "Usage: $0 [dev|prod]"
  exit 1
fi

ENV_FILE="${ROOT_DIR}/.env.${ENV_ARG}"
if [ ! -f "$ENV_FILE" ]; then
  echo "Env file not found: $ENV_FILE"
  exit 1
fi

echo "Loading env vars from $ENV_FILE"
set -a
source "$ENV_FILE"
set +a

if [[ "${ENV:-}" != "$ENV_ARG" ]]; then
  echo "ENV mismatch: ENV='${ENV:-}' but argument='$ENV_ARG'"
  exit 1
fi

# --- Params ---

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ARTIFACT_BUCKET_NAME="${PROJECT_NAME}-${ENV}-${ACCOUNT_ID}-${REGION}-artifacts"

GIT_SHA="${GITSHA:-$(git rev-parse HEAD)}"
ZIP_NAME="app-${GIT_SHA}.zip"


echo "ARTIFACT_BUCKET_NAME=$ARTIFACT_BUCKET_NAME"
echo "ZIP_NAME=$ZIP_NAME"

# --- Update lambda ---

echo "Forcing update of lambda code whether it wants to or not..."
aws lambda update-function-code \
  --function-name "${PROJECT_NAME}-${ENV}-app" \
  --s3-bucket "$ARTIFACT_BUCKET_NAME" \
  --s3-key "$ZIP_NAME" \
  --publish \
  --region "${REGION}" >/dev/null
aws lambda wait function-updated --function-name "${PROJECT_NAME}-${ENV}-app" --region "$REGION"
aws lambda wait function-active  --function-name "${PROJECT_NAME}-${ENV}-app" --region "$REGION"


# ---- Confirmation -----

echo ""
echo "✅ Lambda update complete"

aws lambda get-function \
  --function-name "${PROJECT_NAME}-${ENV}-app" \
  --query "{Function:Configuration.FunctionName,LastModified:Configuration.LastModified,CodeSha256:Configuration.CodeSha256}" \
  --output table
