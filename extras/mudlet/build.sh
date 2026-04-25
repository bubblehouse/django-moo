#!/usr/bin/env bash
# Build djangomoo.mpackage from the source files.
#
# Mudlet packages are zip archives with .mpackage extension. The package
# extracts to <Mudlet profile dir>/djangomoo/ on install, so the relative
# paths inside the zip are referenced by lua modules at runtime.
set -euo pipefail

cd "$(dirname "$0")"
out="djangomoo.mpackage"
rm -f "$out"
zip -q -r "$out" config.lua djangomoo.xml icon.png lua/
echo "built $out ($(wc -c < "$out") bytes)"
