#!/bin/bash

# ====== Params =======
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="eu-west-2"
BUCKET="elbiefit-eu-west-2-cloudformation-templates"
PROJECT_NAME="elbiefit"
ENV="dev"

ARTIFACT_BUCKET_NAME="${PROJECT_NAME}-${ENV}-${ACCOUNT_ID}-${REGION}-artifacts"
ASSETS_BUCKET_NAME="${PROJECT_NAME}-${ENV}-${ACCOUNT_ID}-${REGION}-frontend"

GIT_SHA="${GITSHA:-$(git rev-parse HEAD)}"
ZIP_NAME="app-${GIT_SHA}.zip"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TMP_DIR="$ROOT_DIR/tmp"
BUILD_DIR="$ROOT_DIR/build"

# ====== Functions ======
get_status() {
  aws cloudformation describe-stacks \
    --region "$REGION" \
    --stack-name $1 \
    --query "Stacks[0].StackStatus" \
    --output text 2>/dev/null || echo "STACK_NOT_FOUND"
}

deploy_stack() {
  local stack_name=$1
  local template_name=$2
  shift 2

  status=$(get_status "$stack_name")

  if [[ "$status" == "ROLLBACK_COMPLETE" ]]; then
    echo "Deleting stack $stack_name in ROLLBACK_COMPLETE state..."
    aws cloudformation delete-stack \
      --region "$REGION" \
      --stack-name "$stack_name"

    echo "Waiting for stack deletion to complete..."
    aws cloudformation wait stack-delete-complete \
      --region "$REGION" \
      --stack-name "$stack_name"

    echo "Re-deploying stack $stack_name..."
    aws cloudformation deploy \
    --template-file "$template_name" \
    --stack-name "$stack_name" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides ProjectName="$PROJECT_NAME" EnvName="$ENV" \
    --region "$REGION" \
    "$@"
  else
    aws cloudformation deploy \
      --template-file "$template_name" \
      --stack-name "$stack_name" \
      --capabilities CAPABILITY_NAMED_IAM \
      --parameter-overrides ProjectName="$PROJECT_NAME" EnvName="$ENV" \
      --region "$REGION" \
      "$@"

  fi

}

create_zip() {
  # --- export and install dependencies using uv ---
mkdir -p "$TMP_DIR" "$BUILD_DIR"
echo "Exporting dependencies from uv.lock..."
uv export --no-hashes -q -o "$TMP_DIR/requirements.txt"

echo "Installing dependencies into build folder..."
rm -rf "$BUILD_DIR"/*
pip install -r "$TMP_DIR/requirements.txt" --target "$BUILD_DIR" >/dev/null

# --- copy FastAPI app code ---
echo "Copying FastAPI app code..."
# Adjust "app" if your module lives elsewhere
rsync -a \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude '.venv' \
  --exclude 'tmp' \
  --exclude 'build' \
  "$ROOT_DIR/app/" "$BUILD_DIR/app/"


# --- zip it up ---
 echo "Creating zip archive ${ZIP_NAME}..."
  (
    cd "$BUILD_DIR"
    zip -r9 "$TMP_DIR/$ZIP_NAME" . >/dev/null
  )

  # sanity check
  test -s "$TMP_DIR/$ZIP_NAME" || { echo "❌ Zip not created"; exit 1; }
}

load_zip() {
  local ZIP_PATH="$TMP_DIR/$ZIP_NAME"
  echo "☁️  Uploading to s3://${ARTIFACT_BUCKET_NAME}/${ZIP_NAME}"
aws s3 cp "$ZIP_PATH" "s3://${ARTIFACT_BUCKET_NAME}/${ZIP_NAME}" --region "$REGION"


# --- verify upload ---
aws s3 ls "s3://${ARTIFACT_BUCKET_NAME}/${ZIP_NAME}" --region "$REGION"
echo "Upload ${ZIP_NAME} complete"
}


# ====== Main =======
deploy_stack "$PROJECT_NAME-$ENV-s3" "infra/s3.yaml"
deploy_stack "$PROJECT_NAME-$ENV-data" "infra/data.yaml"
deploy_stack "$PROJECT_NAME-$ENV-iam" "infra/iam.yaml" \
  ArtifactBucketName="$ARTIFACT_BUCKET_NAME" \
  AssetsBucketName="$ASSETS_BUCKET_NAME"

# --- sort out the zip before setting up the lambda---
create_zip
load_zip


deploy_stack "$PROJECT_NAME-$ENV-app" "infra/app.yaml" \
  GitSha="$GIT_SHA"

API_URL=$(aws cloudformation list-exports \
  --query "Exports[?Name=='${PROJECT_NAME}-${ENV}-ApiGatewayUrl'].Value" \
  --output text)


echo "API Gateway URL: ${API_URL}"

deploy_stack "$PROJECT_NAME-$ENV-cognito" "infra/cognito.yaml" \
  ApiGatewayUrl="$API_URL"


# ====== Grab App Env Variables =======
USER_POOL_ID=$(aws cloudformation list-exports \
  --query "Exports[?Name=='${PROJECT_NAME}-${ENV}-UserPoolId'].Value" \
  --output text)

COGNITO_ISSUER=$(aws cloudformation list-exports \
  --query "Exports[?Name=='elbiefit-${ENV}-IssuerUrl'].Value" \
  --output text)

# aka user pool client id
COGNITO_AUDIENCE=$(aws cloudformation list-exports \
  --query "Exports[?Name=='${PROJECT_NAME}-${ENV}-UserPoolClientId'].Value" \
  --output text)

DDB_TABLE_NAME=$(aws cloudformation list-exports \
  --query "Exports[?Name=='elbiefit-${ENV}-DynamoTableName'].Value" \
  --output text)

# Build cognito domain
COGNITO_DOMAIN="elbiefit-${ENV}-${ACCOUNT_ID}-auth.auth.${REGION}.amazoncognito.com"


if [[ -z "$USER_POOL_ID" || -z "$COGNITO_AUDIENCE" ]]; then
  echo "Failed to resolve Cognito exports. Check the cognito stack outputs."
  exit 1
fi


# ====== Set Env Vars =======
aws lambda update-function-configuration \
  --no-cli-pager \
  --function-name "elbiefit-${ENV}-app" \
  --environment "Variables={\
ENV_NAME=${ENV},\
LOG_LEVEL=DEBUG,\
DDB_TABLE_NAME=${DDB_TABLE_NAME},\
COGNITO_ISSUER=${COGNITO_ISSUER},\
COGNITO_AUDIENCE=${COGNITO_AUDIENCE},\
COGNITO_DOMAIN=${COGNITO_DOMAIN}}"

echo "✅ Environment variables set for Lambda elbiefit-${ENV}-app:"
echo "------------------------------------------------------------"
echo "ENV_NAME=${ENV}"
echo "LOG_LEVEL=DEBUG"
echo "DDB_TABLE_NAME=${DDB_TABLE_NAME}"
echo "COGNITO_ISSUER=${COGNITO_ISSUER}"
echo "COGNITO_AUDIENCE=${COGNITO_AUDIENCE}"
echo "COGNITO_DOMAIN=${COGNITO_DOMAIN}"
echo "------------------------------------------------------------"
