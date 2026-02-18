#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC="${ROOT_DIR}/openapi/openapi.json"
OUT="${ROOT_DIR}/generated"

# Remove generated code
rm -rf "${OUT}"
mkdir -p "${OUT}"

# Generate SDK
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "${ROOT_DIR}:/local" \
  openapitools/openapi-generator-cli generate \
  -i /local/openapi/openapi.json \
  -g python \
  -o /local/generated \
  --package-name neurolinker_sdk_gen


# Copy generated code to src/neurolinker_sdk/_generated (which will be the package installed by pip)
rm -rf "${ROOT_DIR}/src/neurolinker_sdk/_generated"
mkdir -p "${ROOT_DIR}/src/neurolinker_sdk/_generated"
cp -R "${OUT}/neurolinker_sdk_gen/"* "${ROOT_DIR}/src/neurolinker_sdk/_generated/"

# modify imports into the wrapper to not require neurolinker_sdk_gen
grep -RIl "neurolinker_sdk_gen" "${ROOT_DIR}/src/neurolinker_sdk/_generated" \
  | xargs sed -i 's/neurolinker_sdk_gen/neurolinker_sdk._generated/g'

