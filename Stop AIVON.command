#!/bin/bash
# Double-click in Finder to stop AIVON.
cd "$(dirname "$0")" || exit 1
bash "bin/aivon-stop.sh"
echo ""
echo "You can close this window."
