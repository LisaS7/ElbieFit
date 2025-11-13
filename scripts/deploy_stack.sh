#!/bin/bash

# ====== Params =======
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${ROOT_DIR}/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "Env file not found: $ENV_FILE"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

ARTIFACT_BUCKET_NAME="${PROJECT_NAME}-${ENV}-${ACCOUNT_ID}-${REGION}-artifacts"
ASSETS_BUCKET_NAME="${PROJECT_NAME}-${ENV}-${ACCOUNT_ID}-${REGION}-frontend"

GIT_SHA="${GITSHA:-$(git rev-parse HEAD)}"

ZIP_NAME="app-${GIT_SHA}.zip"
TMP_DIR="$ROOT_DIR/tmp"
BUILD_DIR="$ROOT_DIR/build"
ZIP_PATH="${TMP_DIR}/${ZIP_NAME}"

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



# ====== Main =======
echo -e "\n\n--------------- DEPLOY S3/DB/IAM ------------------"
deploy_stack "${PROJECT_NAME}-${ENV}-s3" "infra/s3.yaml"
deploy_stack "${PROJECT_NAME}-${ENV}-data" "infra/data.yaml"
deploy_stack "${PROJECT_NAME}-${ENV}-iam" "infra/iam.yaml" \
  ArtifactBucketName="$ARTIFACT_BUCKET_NAME" \
  AssetsBucketName="$ASSETS_BUCKET_NAME"


echo -e "\n\n--------------- DEPLOY CODE ------------------"
echo "Summoning the code deploy script..."
./scripts/deploy_code.sh


echo -e "\n\n--------------- DEPLOY APP ------------------"
deploy_stack "${PROJECT_NAME}-${ENV}-app" "infra/app.yaml" \
  GitSha="$GIT_SHA"

API_URL=$(aws cloudformation list-exports \
  --query "Exports[?Name=='${PROJECT_NAME}-${ENV}-ApiGatewayUrl'].Value" \
  --output text)

echo "API Gateway URL: ${API_URL}"

# LAMBDA PUSH HERE
./scripts/update_lambda_code.sh


echo -e "\n\n--------------- DEPLOY COGNITO ------------------"
deploy_stack "${PROJECT_NAME}-${ENV}-cognito" "infra/cognito.yaml" \
  ApiGatewayUrl="${API_URL}"


# ====== Grab App Env Variables =======
USER_POOL_ID=$(aws cloudformation list-exports \
  --query "Exports[?Name=='${PROJECT_NAME}-${ENV}-UserPoolId'].Value" \
  --output text)

COGNITO_ISSUER=$(aws cloudformation list-exports \
  --query "Exports[?Name=='${PROJECT_NAME}-${ENV}-IssuerUrl'].Value" \
  --output text)

# aka user pool client id
COGNITO_AUDIENCE=$(aws cloudformation list-exports \
  --query "Exports[?Name=='${PROJECT_NAME}-${ENV}-UserPoolClientId'].Value" \
  --output text)

DDB_TABLE_NAME=$(aws cloudformation list-exports \
  --query "Exports[?Name=='${PROJECT_NAME}-${ENV}-DynamoTableName'].Value" \
  --output text)

# Build cognito domain
COGNITO_DOMAIN="${PROJECT_NAME}-${ENV}-${ACCOUNT_ID}-auth"
COGNITO_REDIRECT_URI="${API_URL}/auth/callback"

if [[ -z "$USER_POOL_ID" || -z "$COGNITO_AUDIENCE" ]]; then
  echo "Failed to resolve Cognito exports. Check the cognito stack outputs."
  exit 1
fi


# ====== Set Env Vars =======
echo -e "\n\n--------------- ENV VARS ------------------"
aws lambda update-function-configuration \
  --no-cli-pager \
  --function-name "${PROJECT_NAME}-${ENV}-app" \
  --environment "Variables={\
ENV_NAME=${ENV},\
LOG_LEVEL=DEBUG,\
DDB_TABLE_NAME=${DDB_TABLE_NAME},\
COGNITO_REDIRECT_URI=${COGNITO_REDIRECT_URI}, \
COGNITO_ISSUER=${COGNITO_ISSUER},\
COGNITO_AUDIENCE=${COGNITO_AUDIENCE},\
COGNITO_DOMAIN=${COGNITO_DOMAIN}}" > /dev/null

echo "✅ Environment variables set for Lambda ${PROJECT_NAME}-${ENV}-app:"
echo "------------------------------------------------------------"
echo "ENV_NAME=${ENV}"
echo "LOG_LEVEL=DEBUG"
echo "DDB_TABLE_NAME=${DDB_TABLE_NAME}"
echo "COGNITO_REDIRECT_URI=${COGNITO_REDIRECT_URI}"
echo "COGNITO_ISSUER=${COGNITO_ISSUER}"
echo "COGNITO_AUDIENCE=${COGNITO_AUDIENCE}"
echo "COGNITO_DOMAIN=${COGNITO_DOMAIN}"
echo "------------------------------------------------------------"
