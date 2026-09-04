#!/usr/bin/env bash
set -euo pipefail

# Every name a download asks for is read from the one file the runs are settled
# from, so nothing here can drift from what the pipeline publishes.
config="$(dirname "$0")/../configs/digitalhub.yaml"
project="$(sed -n 's/^project: *//p' "$config")"

published() {
    sed -n "/^publishes:/,/^[^ #]/{s/^  $1: *//p;}" "$config"
}

usage() {
    cat <<'EOF'
usage: dh_download.sh [name ...]

Brings down what the pipelines published and unpacks it under data/.
With no name, every one of them comes down.

  coverage     the coverage measurements       -> data/analysis/coverage
  catalog      the ODE feature and set lists   -> data/_catalog
  metadata     the ODE records behind them     -> data/analysis/metadata
  selection    the features and looks kept    -> data/analysis/selection
  stats        what the filter left of it     -> data/analysis/stats
  summary      one row per feature and set     -> data/analysis/coverage
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
        -p "$project" \
        "$type" \
        -n "$name" \
        -d "$staged"

    # An artifact comes down as one archive to unpack. A dataitem comes down as
    # the file itself, so there is nothing to unpack and it is kept as it landed.
    local packed
    packed="$(find "$staged" -maxdepth 1 -name '*.tar.gz' -print -quit)"
    if [[ -n $packed ]]; then
        tar -xzf "$packed" \
            -C "$staged" \
            --strip-components=1

        rm -f "$packed"
    fi

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
        coverage) download_and_extract artifact "$(published coverage)" data/analysis/coverage ;;
        catalog) download_and_extract artifact "$(published catalog)" data/_catalog ;;
        metadata) download_and_extract artifact "$(published metadata)" data/analysis/metadata ;;
        selection) download_and_extract artifact "$(published selection)" data/analysis/selection ;;
        stats) download_and_extract artifact "$(published stats)" data/analysis/stats ;;
        summary) download_and_extract dataitem "$(published summary)" data/analysis/coverage shares ;;
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
    names=(coverage catalog metadata selection stats summary)
fi

for name in "${names[@]}"; do
    download "$name"
done
