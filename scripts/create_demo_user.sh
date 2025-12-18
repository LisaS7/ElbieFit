#!/usr/bin/env bash
set -euo pipefail

# ====== Params =======
# Expected from deploy_stack.sh or environment:
#   ENV, REGION, USER_POOL_ID
#
# Optional:
#   DEMO_USERNAME
#
# Required:
#   DEMO_USER_PASSWORD

if [[ -z "$REGION" ]]; then
  echo "REGION is not set"
  exit 1
fi

if [[ -z "$USER_POOL_ID" ]]; then
  echo "USER_POOL_ID is not set"
  exit 1
fi

if [[ -z "$DEMO_USER_PASSWORD" ]]; then
  echo "DEMO_USER_PASSWORD is not set (put it in .env or CI secrets)"
  exit 1
fi

DEMO_USERNAME="${DEMO_USERNAME:-demo@elbiefit.co.uk}"

# ====== Functions =======
user_exists() {
  aws cognito-idp admin-get-user \
    --region "$REGION" \
    --user-pool-id "$USER_POOL_ID" \
    --username "$DEMO_USERNAME" \
    --no-cli-pager >/dev/null 2>&1
}

create_user() {
  aws cognito-idp admin-create-user \
    --region "$REGION" \
    --user-pool-id "$USER_POOL_ID" \
    --username "$DEMO_USERNAME" \
    --message-action SUPPRESS \
    --user-attributes \
      Name=email,Value="$DEMO_USERNAME" \
      Name=email_verified,Value=true \
    --no-cli-pager >/dev/null
}

set_permanent_password() {
  aws cognito-idp admin-set-user-password \
    --region "$REGION" \
    --user-pool-id "$USER_POOL_ID" \
    --username "$DEMO_USERNAME" \
    --password "$DEMO_USER_PASSWORD" \
    --permanent \
    --no-cli-pager >/dev/null
}

get_user_sub() {
  aws cognito-idp admin-get-user \
    --region "$REGION" \
    --user-pool-id "$USER_POOL_ID" \
    --username "$DEMO_USERNAME" \
    --query "UserAttributes[?Name=='sub'].Value | [0]" \
    --output text \
    --no-cli-pager
}

# ====== Main =======
echo -e "\n\n--------------- PROVISION DEMO USER (${ENV}) ------------------"
echo "Demo username: ${DEMO_USERNAME}" 1>&2

if user_exists; then
  echo "Demo user already exists" 1>&2
else
  echo "Creating demo user..." 1>&2
  create_user
  echo "Demo user created" 1>&2
fi

echo "Setting permanent password..." 1>&2
set_permanent_password
echo "Password set" 1>&2

DEMO_USER_SUB=$(get_user_sub)

if [[ -z "$DEMO_USER_SUB" || "$DEMO_USER_SUB" == "None" ]]; then
  echo "Failed to get demo user sub" 1>&2
  exit 1
fi

echo "DEMO_USER_SUB=${DEMO_USER_SUB}"
