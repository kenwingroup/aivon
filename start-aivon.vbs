' ============================================
'  AIVON - background launcher (hidden window)
'  Double-click this file (or start-aivon.bat) to start the server in background.
'  Log written to server\aivon.log. Stop with stop-aivon.bat.
' ============================================
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")
Set procEnv = sh.Environment("PROCESS")
procEnv("PYTHONUTF8") = "1"
procEnv("PATH") = root & "\.tools\nodejs;" & root & "\.tools;" & root & "\.venv\Scripts;" & procEnv("PATH")

' Stop old instance first (hidden, wait). Output written to server\stop-last.log.
sh.Run "cmd /c cd /d """ & root & """ && call """ & root & "\stop-aivon.bat"" > server\stop-last.log 2>&1", 0, True

' Run server hidden (0 = hidden window, False = do not wait). Output -> server\aivon.log
sh.Run "cmd /c cd /d """ & root & """ && .venv\Scripts\python.exe server\main.py > server\aivon.log 2>&1", 0, False

If WScript.Arguments.Count > 0 Then
  If LCase(WScript.Arguments(0)) = "/open" Then MoDashboard
End If

Sub MoDashboard()
  Dim port, url, i, http, ok, cands, c
  port = sh.ExpandEnvironmentStrings("%AIVON_PORT%")
  If port = "%AIVON_PORT%" Or port = "" Then port = "7979"
  url = "http://127.0.0.1:" & port
  ok = False
  For i = 1 To 60
    WScript.Sleep 1000
    On Error Resume Next
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    http.setTimeouts 2000, 2000, 2000, 2000
    http.Open "GET", url & "/health", False
    http.Send
    If Err.Number = 0 Then
      If http.Status = 200 Then ok = True
    End If
    Err.Clear
    On Error GoTo 0
    If ok Then Exit For
  Next
  cands = Array(sh.ExpandEnvironmentStrings("%ProgramFiles%") & "\Google\Chrome\Application\chrome.exe", _
                sh.ExpandEnvironmentStrings("%LocalAppData%") & "\Google\Chrome\Application\chrome.exe", _
                sh.ExpandEnvironmentStrings("%ProgramFiles(x86)%") & "\Microsoft\Edge\Application\msedge.exe", _
                sh.ExpandEnvironmentStrings("%ProgramFiles%") & "\Microsoft\Edge\Application\msedge.exe")
  For Each c In cands
    If fso.FileExists(c) Then
      sh.Run """" & c & """ --app=" & url, 1, False
      Exit Sub
    End If
  Next
  sh.Run url, 1, False
End Sub
