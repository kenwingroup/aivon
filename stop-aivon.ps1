# Dung AIVON - giet theo chu port 7979 truoc (nhanh, khong phu thuoc WMI), roi don python cua venv nay.
$killed = $false
Get-NetTCPConnection -LocalPort 7979 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
  Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
  Write-Host "  - Da tat PID $($_.OwningProcess) (chu port 7979)"
  $killed = $true
}
# LUU Y: python cua venv chi la LAUNCHER - no re-exec Python goc lam tien trinh CON
# (con nay moi giu port). Vi vay chi loc theo COMMANDLINE, KHONG loc theo duong dan exe
# (se bo sot thang con vi exe cua no la Python goc, khong phai venv).
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue | Where-Object {
  $_.CommandLine -like '*aivon*server\main.py*'
} | ForEach-Object {
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
  Write-Host "  - Da tat python PID $($_.ProcessId)"
  $killed = $true
}
if (-not $killed) { Write-Host '  (Khong thay server nao dang chay)' }
exit 0
