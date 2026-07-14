#!/usr/bin/env sh
set -eu

mkdir -p bin
CLANG_MODULE_CACHE_PATH="${CLANG_MODULE_CACHE_PATH:-/private/tmp/redcard-clang-cache}" \
  swiftc tools/LocalOverlay.swift -o bin/redcard-local-overlay
