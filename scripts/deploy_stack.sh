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
deploy_stack "$PROJECT_NAME-$ENV-s3" "infra/s3.yaml"
deploy_stack "$PROJECT_NAME-$ENV-data" "infra/data.yaml"
deploy_stack "$PROJECT_NAME-$ENV-iam" "infra/iam.yaml" \
  ArtifactBucketName="$ARTIFACT_BUCKET_NAME" \
  AssetsBucketName="$ASSETS_BUCKET_NAME"
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

APP_CLIENT_ID=$(aws cloudformation list-exports \
  --query "Exports[?Name=='${PROJECT_NAME}-${ENV}-UserPoolClientId'].Value" \
  --output text)

if [[ -z "$USER_POOL_ID" || -z "$APP_CLIENT_ID" ]]; then
  echo "Failed to resolve Cognito exports. Check the cognito stack outputs."
  exit 1
fi

ISSUER="https://cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID}"

echo "Cognito Issuer: $ISSUER"
echo "Cognito Audience (ClientId): $APP_CLIENT_ID"

# ====== Redeploy App Stack with Cognito Env Vars =======
deploy_stack "$PROJECT_NAME-$ENV-app" "infra/app.yaml" \
  GitSha="$GIT_SHA" \
  CognitoIssuer="$ISSUER" \
  CognitoAudience="$APP_CLIENT_ID"
