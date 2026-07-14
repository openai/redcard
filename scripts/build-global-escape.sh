#!/usr/bin/env sh
set -eu

mkdir -p bin
CLANG_MODULE_CACHE_PATH="${CLANG_MODULE_CACHE_PATH:-/private/tmp/redcard-clang-cache}" \
  swiftc tools/GlobalEscape.swift -o bin/redcard-global-escape
