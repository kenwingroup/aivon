#!/bin/bash
# Double-click in Finder to start AIVON and open the dashboard.
cd "$(dirname "$0")" || exit 1
bash "bin/aivon-start.sh"
echo ""
echo "AIVON is running at http://127.0.0.1:7979"
echo "This window can be closed - the server keeps running in the background."
