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

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TMP_DIR="$ROOT_DIR/tmp"
BUILD_DIR="$ROOT_DIR/build"
ZIP_PATH="${TMP_DIR}/${ZIP_NAME}"



# --- Zip code ---

create_zip() {
echo "Creating zip file..."

VENVDIR="${ROOT_DIR}/.venv"
if [ -x "${VENVDIR}/bin/python" ]; then
  PY="${VENVDIR}/bin/python"
else
  echo "⚠️ No venv at ${VENVDIR}, falling back to system Python"
  PY="$(command -v python3 || command -v python)"
fi
if [ -z "$PY" ]; then
  echo "❌ Could not find a Python interpreter" >&2
  exit 1
fi


  # --- export and install dependencies using uv ---
mkdir -p "$TMP_DIR" "$BUILD_DIR"
echo "Exporting dependencies from uv.lock..."
uv pip compile "${ROOT_DIR}/pyproject.toml" -o "${TMP_DIR}/requirements.txt" -q

echo "Installing dependencies into build folder..."
rm -rf "$BUILD_DIR"/*
uv pip install \
  --python "$PY" \
  --target "$BUILD_DIR" \
  --python-platform x86_64-manylinux2014 \
  --python-version 3.12 \
  --only-binary :all: \
  -r "${TMP_DIR}/requirements.txt" \
  -q

# --- copy FastAPI app code ---
echo "Copying FastAPI app code..."
# Adjust "app" if your module lives elsewhere
rsync -a \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude '.venv' \
  --exclude 'tmp' \
  --exclude 'build' \
  "${ROOT_DIR}/app/" "${BUILD_DIR}/app/"

# --- add the static files ---
  echo "Copying static assets..."
if [ -d "${ROOT_DIR}/static" ]; then
  rsync -a "${ROOT_DIR}/static/" "${BUILD_DIR}/static/"
else
  echo "⚠️ No static directory found at ${ROOT_DIR}/static, skipping"
fi



# --- zip it up ---
 echo "Creating zip archive ${ZIP_NAME}..."
  (
    cd "$BUILD_DIR"
    zip -r9 "$ZIP_PATH" . >/dev/null
  )

  # sanity check
  test -s "$ZIP_PATH" || { echo "❌ Zip not created"; exit 1; }
}

load_zip() {
  echo "☁️  Uploading..."
aws s3 cp "${ZIP_PATH}" "s3://${ARTIFACT_BUCKET_NAME}/${ZIP_NAME}" --region "$REGION"


# --- verify upload ---
printf "\nS3 file uploaded:   "
aws s3 ls "s3://${ARTIFACT_BUCKET_NAME}/${ZIP_NAME}" --region "$REGION"
}

create_zip
load_zip

"${SCRIPT_DIR}/update_lambda_code.sh" "$ENV_ARG"
