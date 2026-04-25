#!/usr/bin/env bash
# Build djangomoo_mapper_bridge.mpackage from the source XML and config.lua.
#
# Mudlet packages are zip archives with .mpackage extension. This script
# runs from the directory it lives in so paths stay simple.
set -euo pipefail

cd "$(dirname "$0")"
out="djangomoo_mapper_bridge.mpackage"
rm -f "$out"
zip -q "$out" config.lua djangomoo_mapper_bridge.xml
echo "built $out ($(wc -c < "$out") bytes)"
