#!/bin/bash
# ============================================================
# Build dist/AivonOS-macOS.dmg: "AIVON.app" plus a shortcut to Applications, so the
# person drags the app across like any other Mac app.
#
#   bash packaging/macos/build-dmg.sh          # needs macOS (hdiutil)
#   NO_DMG=1 bash packaging/macos/build-dmg.sh # any OS: only assemble the .app (tests use it)
#
# The app stays tiny: launcher.sh + bootstrap.sh + icon. The first launch clones the newest
# Aivon into ~/AivonOS (see bootstrap.sh), so this .dmg never goes stale.
# Not signed with an Apple Developer ID: macOS asks once to allow it under
# System Settings > Privacy & Security > Open Anyway (QUICKSTART explains it).
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HERE="${ROOT}/packaging/macos"
DIST="${ROOT}/dist"
VERSION="$(tr -d ' \r\n' < "${ROOT}/VERSION")"
STAGE="${DIST}/dmg-stage"
APP="${STAGE}/AIVON.app"

rm -rf "${STAGE}"
mkdir -p "${APP}/Contents/MacOS" "${APP}/Contents/Resources"

cp "${HERE}/launcher.sh" "${APP}/Contents/MacOS/aivon"
cp "${HERE}/bootstrap.sh" "${APP}/Contents/Resources/bootstrap.sh"
cp "${ROOT}/packaging/assets/aivon.icns" "${APP}/Contents/Resources/aivon.icns"
chmod +x "${APP}/Contents/MacOS/aivon" "${APP}/Contents/Resources/bootstrap.sh"

cat > "${APP}/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>AIVON</string>
    <key>CFBundleDisplayName</key><string>AIVON</string>
    <key>CFBundleIdentifier</key><string>vn.minhvu.aivon</string>
    <key>CFBundleVersion</key><string>${VERSION}</string>
    <key>CFBundleShortVersionString</key><string>${VERSION}</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleExecutable</key><string>aivon</string>
    <key>CFBundleIconFile</key><string>aivon</string>
    <key>LSMinimumSystemVersion</key><string>11.0</string>
    <key>LSUIElement</key><true/>
    <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

if [ "${NO_DMG:-0}" = "1" ]; then
  echo "Assembled ${APP} (NO_DMG=1, no .dmg built)"
  exit 0
fi

# Ad-hoc signature: not a Developer ID, but it gives the bundle a valid seal so macOS reports
# "unidentified developer" (allowed once in Settings) instead of "damaged".
codesign --force --deep --sign - "${APP}" || echo "codesign skipped"

ln -s /Applications "${STAGE}/Applications"
# The Aivon star as the icon of the mounted disk (Finder sidebar and desktop) instead of the
# generic drive. Needs the volume's "custom icon" flag, which can only be set on a writable
# image: build read-write, flag it, then compress. Missing SetFile only loses the icon.
cp "${ROOT}/packaging/assets/aivon.icns" "${STAGE}/.VolumeIcon.icns"
rm -f "${DIST}/AivonOS-macOS.dmg" "${DIST}/rw.dmg"
hdiutil create -volname "AIVON" -srcfolder "${STAGE}" -ov -format UDRW "${DIST}/rw.dmg"
MNT="$(hdiutil attach -nobrowse -readwrite "${DIST}/rw.dmg" | awk -F'\t' '/\/Volumes\//{print $NF}')"
if SETFILE="$(xcrun --find SetFile 2>/dev/null)" && [ -n "${MNT}" ]; then
  "${SETFILE}" -a C "${MNT}" && echo "Volume icon set"
else
  echo "SetFile not found: disk image keeps the generic icon"
fi
[ -n "${MNT}" ] && hdiutil detach "${MNT}"
hdiutil convert "${DIST}/rw.dmg" -format UDZO -o "${DIST}/AivonOS-macOS.dmg"
rm -f "${DIST}/rw.dmg"
rm -rf "${STAGE}"
echo "Built ${DIST}/AivonOS-macOS.dmg"
