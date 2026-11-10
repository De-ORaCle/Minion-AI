' Minion AI - Silent Launcher
' Launches the Minion desktop app with pythonw (no terminal or command prompt window)
Set fso = CreateObject("Scripting.FileSystemObject")
projectDir = fso.GetParentFolderName(WScript.ScriptFullName)

Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = projectDir
WshShell.Run "pythonw.exe app.py", 0, False
