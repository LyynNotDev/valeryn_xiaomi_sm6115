#!/usr/bin/env bash
# Backward-compatible entry point for POCO M3 (citrus).
set -Eeuo pipefail
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec env DEVICE=citrus "${SOURCE_DIR}/build-chime.sh" "$@"
