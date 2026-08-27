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
    local shares="${4-}"

    # Everything lands beside the destination first, so a download that fails or
    # is interrupted leaves what is already on disk untouched.
    local staged="$dest.incoming"
    rm -rf "$staged"
    mkdir -p "$staged"

    dhcli download \
        -p mars-features-coverage \
        "$type" \
        -n "$name" \
        -d "$staged"

    tar -xzf "$staged"/*.tar.gz \
        -C "$staged" \
        --strip-components=1

    rm -f "$staged"/*.tar.gz

    # Nothing already on disk is touched unless there is something to put in its
    # place, so a download that came down empty leaves the last one alone.
    if [[ -z $(ls -A "$staged" 2>/dev/null) ]]; then
        echo "nothing came down for \`$name\`, leaving $dest as it was" >&2
        rm -rf "$staged"
        return 1
    fi

    # An archive owns the directory it fills, so it replaces what is there rather
    # than merging into it. The summary shares the artifacts directory and clears
    # nothing. Either way this runs only once the download has come down whole.
    [[ -n $shares ]] || rm -rf "$dest"
    mkdir -p "$dest"
    cp -a "$staged"/. "$dest"/
    rm -rf "$staged"
}

download() {
    case "$1" in
        artifacts) download_and_extract artifact coverage-artifacts data/artifacts ;;
        metadata) download_and_extract artifact coverage-metadata data/metadata ;;
        predictions) download_and_extract artifact coverage-predictions data/predictions ;;
        summary) download_and_extract dataitem coverage-summary data/artifacts shares ;;
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
