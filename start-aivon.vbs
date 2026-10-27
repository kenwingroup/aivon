' ============================================
'  AIVON - chạy NGẦM (ẩn cửa sổ cmd)
'  Double-click file này (hoặc start-aivon.bat) để bật server ở chế độ nền.
'  Log ghi vào server\aivon.log. Dừng bằng stop-aivon.bat.
' ============================================
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")
Set procEnv = sh.Environment("PROCESS")
procEnv("PYTHONUTF8") = "1"
procEnv("PATH") = root & "\.tools\nodejs;" & root & "\.tools;" & root & "\.venv\Scripts;" & procEnv("PATH")

' QUAN TRỌNG: mọi lệnh đều cd /d vào root trước - KHÔNG dựa vào working directory
' kế thừa (CurrentDirectory không đáng tin tuỳ nơi gọi, từng làm bước stop chết
' im lặng với lỗi 'stop-aivon.bat is not recognized').

' Tắt instance cũ trước (ẩn, chờ xong). Output ghi server\stop-last.log để soi khi trục trặc.
' GỌI BẰNG ĐƯỜNG DẪN TUYỆT ĐỐI: tên trần "stop-aivon.bat" bị cmd từ chối tìm theo thư mục
' hiện tại khi môi trường có NoDefaultCurrentDirectoryInExePath (đường dẫn có "\" thì không sao).
sh.Run "cmd /c cd /d """ & root & """ && call """ & root & "\stop-aivon.bat"" > server\stop-last.log 2>&1", 0, True

' Chạy server ẩn (0 = cửa sổ ẩn, False = không chờ). Output -> server\aivon.log
sh.Run "cmd /c cd /d """ & root & """ && .venv\Scripts\python.exe server\main.py > server\aivon.log 2>&1", 0, False
