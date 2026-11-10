#!/bin/bash
# ============================================================
# AIVON - one-line install for macOS, no "cannot be opened" block
#
#   curl -fsSL https://raw.githubusercontent.com/kenwingroup/aivon/main/packaging/macos/get-aivon.sh | bash
#
# Downloads the same AivonOS-macOS.dmg the website links to, copies AIVON.app into
# Applications, then runs its first-time install right here in this Terminal window.
# Why no Gatekeeper prompt: macOS only checks files a browser saved (they carry a quarantine
# flag), and the app is not signed with an Apple Developer ID yet. A file curl downloads
# carries no such flag.
# ============================================================
set -euo pipefail

URL="https://github.com/kenwingroup/aivon/releases/download/desktop/AivonOS-macOS.dmg"
[ "$(uname -s)" = "Darwin" ] || { echo "This installer is for macOS. On Linux run ./install.sh from the repo."; exit 1; }

TMP="$(mktemp -d)"
MNT=""
cleanup() { [ -n "${MNT}" ] && hdiutil detach -quiet "${MNT}" 2>/dev/null; rm -rf "${TMP}"; }
trap cleanup EXIT

echo ""
echo "  AIVON: dang tai bo cai... (downloading)"
curl -fL --progress-bar -o "${TMP}/AivonOS-macOS.dmg" "${URL}"
MNT="$(hdiutil attach -nobrowse -readonly "${TMP}/AivonOS-macOS.dmg" | awk -F'\t' '/\/Volumes\//{print $NF}')"
[ -d "${MNT}/AIVON.app" ] || { echo "The disk image has no AIVON.app"; exit 1; }

# /Applications when it is writable (an admin account), else ~/Applications.
DEST="/Applications"
[ -w "${DEST}" ] || { DEST="${HOME}/Applications"; mkdir -p "${DEST}"; }
# Replace only the app bundle; the brain lives in ~/AivonOS and is never touched here.
rm -rf "${DEST}/AIVON.app"
cp -R "${MNT}/AIVON.app" "${DEST}/"
xattr -dr com.apple.quarantine "${DEST}/AIVON.app" 2>/dev/null || true
echo "  Da chep AIVON vao ${DEST} (copied to ${DEST})"

APP="${DEST}/AIVON.app"
if [ -d "${HOME}/AivonOS/.git" ] && [ -x "${HOME}/AivonOS/.venv/bin/python" ]; then
  echo "  Aivon da cai san, dang mo... (already installed, opening)"
  open "${APP}"
  exit 0
fi
# First install in THIS window. stdin is the curl pipe, so give the installer the keyboard
# back: install.sh asks for the Aivon admin account and may ask for the Mac password.
bash "${APP}/Contents/Resources/bootstrap.sh" < /dev/tty
