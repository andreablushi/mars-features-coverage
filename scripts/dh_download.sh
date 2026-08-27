#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
usage: dh_download.sh [name ...]

Brings down what the pipelines published and unpacks it under data/.
With no name, every one of them comes down.

  artifacts    the coverage measurements       -> data/artifacts
  metadata     the ODE records behind them     -> data/metadata
  predictions  what each strategy would keep   -> data/predictions
  summary      one row per feature and set     -> data/artifacts
EOF
}

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

download() {
    case "$1" in
        artifacts) download_and_extract artifact coverage-artifacts data/artifacts ;;
        metadata) download_and_extract artifact coverage-metadata data/metadata ;;
        predictions) download_and_extract artifact coverage-predictions data/predictions ;;
        summary) download_and_extract dataitem coverage-summary data/artifacts ;;
        *)
            echo "nothing is published under \`$1\`" >&2
            usage >&2
            exit 1
            ;;
    esac
}

if [[ ${1-} == -h || ${1-} == --help ]]; then
    usage
    exit 0
fi

names=("$@")
if [[ ${#names[@]} -eq 0 ]]; then
    names=(artifacts metadata predictions summary)
fi

for name in "${names[@]}"; do
    download "$name"
done
