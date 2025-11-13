ARTIFACT_BUCKET_NAME="$1"

GIT_SHA="${GITSHA:-$(git rev-parse HEAD)}"
ZIP_NAME="app-${GIT_SHA}.zip"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TMP_DIR="$ROOT_DIR/tmp"
BUILD_DIR="$ROOT_DIR/build"
ZIP_PATH="${TMP_DIR}/${ZIP_NAME}"


create_zip() {
echo "Creating zip file..."

VENVDIR="${ROOT_DIR}/.venv"
if [ -x "${VENVDIR}/bin/python" ]; then
  PY="${VENVDIR}/bin/python"
else
  echo "❌ No venv at ${VENVDIR}. Create one with: python3.12 -m venv .venv" >&2
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
