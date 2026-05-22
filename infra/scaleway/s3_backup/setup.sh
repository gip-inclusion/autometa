#!/usr/bin/env bash
# Deploy the s3_backup Scaleway Function + daily cron trigger.
# Run from repo root. Requires: scw CLI configured, jq, and S3_ACCESS_KEY/S3_SECRET_KEY env vars set to the Scaleway Object Storage credentials with read access on matometa and write access on matometa-backup.

set -euo pipefail

: "${S3_ACCESS_KEY:?set S3_ACCESS_KEY (Scaleway Object Storage access key)}"
: "${S3_SECRET_KEY:?set S3_SECRET_KEY (Scaleway Object Storage secret key)}"

REGION="${REGION:-fr-par}"
NAMESPACE_NAME="${NAMESPACE_NAME:-nova}"
FUNCTION_NAME="${FUNCTION_NAME:-s3-backup}"
SOURCE_BUCKET="${SOURCE_BUCKET:-matometa}"
BACKUP_BUCKET="${BACKUP_BUCKET:-matometa-backup}"
SCHEDULE="${SCHEDULE:-0 3 * * *}"

cd "$(dirname "$0")"

echo "→ Building zip"
rm -f s3_backup.zip
zip -q s3_backup.zip handler.py config.py requirements.txt

echo "→ Ensuring namespace '$NAMESPACE_NAME'"
NS_ID=$(scw function namespace list region="$REGION" -o json | jq -r ".[] | select(.name==\"$NAMESPACE_NAME\") | .id" | head -n1)
if [ -z "$NS_ID" ]; then
  NS_ID=$(scw function namespace create name="$NAMESPACE_NAME" region="$REGION" -o json | jq -r .id)
  echo "  created namespace $NS_ID"
fi

echo "→ Deploying function '$FUNCTION_NAME'"
scw function deploy \
  namespace-id="$NS_ID" \
  name="$FUNCTION_NAME" \
  runtime=python313 \
  zip-file=s3_backup.zip \
  region="$REGION"

FN_ID=$(scw function function list namespace-id="$NS_ID" region="$REGION" -o json | jq -r ".[] | select(.name==\"$FUNCTION_NAME\") | .id")

echo "→ Setting handler, env vars, memory, timeout, privacy"
scw function function update "$FN_ID" \
  region="$REGION" \
  handler=handler.handle \
  memory-limit=512 \
  timeout=900s \
  privacy=private \
  environment-variables.SOURCE_BUCKET="$SOURCE_BUCKET" \
  environment-variables.BACKUP_BUCKET="$BACKUP_BUCKET" \
  secret-environment-variables.0.key=S3_ACCESS_KEY \
  secret-environment-variables.0.value="$S3_ACCESS_KEY" \
  secret-environment-variables.1.key=S3_SECRET_KEY \
  secret-environment-variables.1.value="$S3_SECRET_KEY"

echo "→ Waiting for function to reach 'ready' status"
until [ "$(scw function function get "$FN_ID" region="$REGION" -o json | jq -r .status)" = "ready" ]; do
  sleep 5
done

echo "→ Ensuring cron trigger ($SCHEDULE)"
CRON_ID=$(scw function cron list function-id="$FN_ID" region="$REGION" -o json | jq -r ".[] | select(.name==\"${FUNCTION_NAME}-daily\") | .id")
if [ -z "$CRON_ID" ]; then
  scw function cron create \
    function-id="$FN_ID" \
    schedule="$SCHEDULE" \
    name="${FUNCTION_NAME}-daily" \
    args='{}' \
    region="$REGION"
else
  scw function cron update "$CRON_ID" schedule="$SCHEDULE" region="$REGION"
fi

echo "✅ Done. Test invocation:"
echo "   scw function function get $FN_ID region=$REGION"
