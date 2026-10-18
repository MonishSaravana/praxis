#!/usr/bin/env bash
# Deploy tools/site-auth.js as the CloudFront viewer-request function for praxis.monishsaravana.com (it is already
# attached to the distribution as praxis-site-index). The password comes from the environment, never from the repo:
#
#   PRAXIS_SITE_PASSWORD=... tools/site-auth.sh
#
# Tests the function in the DEVELOPMENT stage first (401 without credentials, pass-through with them), then publishes.
# To make the site public again, publish tools/site-index.open.js (the original, no-password function) the same way.
set -euo pipefail
: "${PRAXIS_SITE_PASSWORD:?set PRAXIS_SITE_PASSWORD}"
NAME=praxis-site-index
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/site-auth.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

HASH="$(printf '%s' "$PRAXIS_SITE_PASSWORD" | shasum -a 256 | cut -d' ' -f1)"
sed "s/__PWD_SHA256__/$HASH/" "$HERE/site-auth.js" > "$WORK/fn.js"

ETAG="$(aws cloudfront describe-function --name "$NAME" --stage DEVELOPMENT --query ETag --output text 2>/dev/null \
  || aws cloudfront describe-function --name "$NAME" --query ETag --output text)"
ETAG="$(aws cloudfront update-function --name "$NAME" --if-match "$ETAG" \
  --function-config 'Comment=praxis.monishsaravana.com basic auth + directory index,Runtime=cloudfront-js-2.0' \
  --function-code "fileb://$WORK/fn.js" --query ETag --output text)"

B64="$(printf 'praxis:%s' "$PRAXIS_SITE_PASSWORD" | base64)"
ev() { # $1 = headers json
  printf '{"version":"1.0","context":{"eventType":"viewer-request"},"viewer":{"ip":"1.2.3.4"},"request":{"method":"GET","uri":"/","querystring":{},"headers":%s,"cookies":{}}}' "$1" > "$WORK/ev.json"
}
test_fn() {
  aws cloudfront test-function --name "$NAME" --if-match "$ETAG" --stage DEVELOPMENT --event-object "fileb://$WORK/ev.json" \
    --query 'TestResult.FunctionOutput' --output text
}
ev '{}'; no_auth="$(test_fn)"
ev "{\"authorization\":{\"value\":\"Basic $B64\"}}"; with_auth="$(test_fn)"
ev '{"authorization":{"value":"Basic cHJheGlzOndyb25n"}}'; wrong_auth="$(test_fn)"
echo "$no_auth" | grep -q '"statusCode":401' || { echo "FAIL: no credentials was not rejected" >&2; exit 1; }
echo "$wrong_auth" | grep -q '"statusCode":401' || { echo "FAIL: wrong password was not rejected" >&2; exit 1; }
echo "$with_auth" | grep -q 'index.html' || { echo "FAIL: correct password did not pass" >&2; exit 1; }
echo "function tests ok (no creds -> 401, wrong -> 401, correct -> index.html)"

aws cloudfront publish-function --name "$NAME" --if-match "$ETAG" --query 'FunctionSummary.FunctionMetadata.Stage' --output text
echo "published: https://praxis.monishsaravana.com now asks for a password (any username)"
