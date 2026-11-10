# ============================================================
# AIVON - one-line install for Windows, no red SmartScreen screen
#
#   irm https://raw.githubusercontent.com/kenwingroup/aivon/main/packaging/windows/get-aivon.ps1 | iex
#
# Downloads the same AivonOS-Setup.exe the website links to and opens its wizard.
# Why this avoids "Windows protected your PC": SmartScreen checks files the BROWSER saved
# (they carry a "downloaded from the Internet" mark) and the .exe is not code-signed yet.
# A file PowerShell downloads itself carries no such mark. Claude Code, Antigravity and Grok
# install the same way. Once the .exe is signed (desktop-installers.yml, WINDOWS_CERT_*), the
# normal download stops warning too and this script stays as a shortcut.
#
# Everything runs inside & { } so nothing leaks into the person's PowerShell session.
# ASCII only: Windows PowerShell 5.1 reads text without BOM in the ANSI codepage.
# ============================================================
& {
  $ErrorActionPreference = "Stop"
  $ProgressPreference = "SilentlyContinue"   # the PS 5.1 progress bar makes downloads 10x slower
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  $url = "https://github.com/kenwingroup/aivon/releases/download/desktop/AivonOS-Setup.exe"
  $out = Join-Path $env:TEMP "AivonOS-Setup.exe"
  Write-Host ""
  Write-Host "  AIVON: dang tai bo cai... (downloading the installer)" -ForegroundColor Cyan
  try {
    Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing
  } catch {
    Write-Host "  Khong tai duoc bo cai: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Kiem tra mang Internet roi chay lai lenh." -ForegroundColor Red
    return
  }
  Write-Host "  Da tai xong, dang mo trinh cai dat AIVON... (opening the setup wizard)" -ForegroundColor Green
  Start-Process -FilePath $out
}
