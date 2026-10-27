# ============================================================
# AIVON - tu khoi dong cung Windows (ban sao cua bin/aivon-autostart.sh ben Mac).
# Goi qua aivon-autostart.bat, dung goi truc tiep tru khi biet minh dang lam gi.
#
# Cach lam: dat mot shortcut trong thu muc Startup cua USER (khong can quyen admin)
# tro vao start-aivon.vbs - dang nhap may la server tu chay NEN, khong bat trinh
# duyet, khong cua so den. Muon mo dashboard thi double-click "AIVON.bat".
# ============================================================
param([string]$Action = "status")

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Startup = [Environment]::GetFolderPath("Startup")
$Lnk = Join-Path $Startup "AIVON.lnk"

switch ($Action.ToLower()) {
  "install" {
    $vbs = Join-Path $Root "start-aivon.vbs"
    if (-not (Test-Path $vbs)) {
      Write-Host "Khong thay start-aivon.vbs canh script nay - dat aivon-autostart.ps1 o goc thu muc Aivon."
      exit 1
    }
    $ws = New-Object -ComObject WScript.Shell
    $s = $ws.CreateShortcut($Lnk)
    $s.TargetPath = "wscript.exe"
    $s.Arguments = "//nologo `"$vbs`""
    $s.WorkingDirectory = $Root
    $s.Description = "AIVON - tu chay nen khi dang nhap may"
    $s.Save()
    Write-Host "Da bat tu khoi dong cung Windows."
    Write-Host "Shortcut: $Lnk"
    Write-Host "Go bo: aivon-autostart.bat uninstall"
  }
  "uninstall" {
    if (Test-Path $Lnk) { Remove-Item $Lnk -Force }
    Write-Host "Da tat tu khoi dong cung Windows."
  }
  default {
    if (Test-Path $Lnk) {
      Write-Host "DANG bat tu khoi dong (shortcut: $Lnk)."
    } else {
      Write-Host "CHUA bat tu khoi dong. Bat bang: aivon-autostart.bat install"
    }
  }
}
