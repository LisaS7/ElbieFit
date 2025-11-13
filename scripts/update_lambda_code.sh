ARTIFACT_BUCKET_NAME="$1"
ZIP_NAME="$2"

echo "Forcing update of lambda code whether it wants to or not..."
aws lambda update-function-code \
  --function-name "${PROJECT_NAME}-${ENV}-app" \
  --s3-bucket "$ARTIFACT_BUCKET_NAME" \
  --s3-key "$ZIP_NAME" \
  --publish \
  --region eu-west-2 >/dev/null
aws lambda wait function-updated --function-name "${PROJECT_NAME}-${ENV}-app" --region "$REGION"
aws lambda wait function-active  --function-name "${PROJECT_NAME}-${ENV}-app" --region "$REGION"
