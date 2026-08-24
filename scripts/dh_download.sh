#!/usr/bin/env bash
set -euo pipefail

download_and_extract() {
    local type="$1"
    local name="$2"
    local dest="$3"

    mkdir -p "$dest"

    dhcli download \
        -p mars-features-coverage \
        "$type" \
        -n "$name" \
        -d "$dest"

    tar -xzf "$dest"/*.tar.gz \
        -C "$dest" \
        --strip-components=1

    rm -f "$dest"/*.tar.gz
}

download_and_extract artifact coverage-artifacts data/artifacts
download_and_extract artifact coverage-metadata data/metadata
download_and_extract dataitem coverage-summary data/artifacts