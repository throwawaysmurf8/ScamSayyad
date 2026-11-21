' Starts the Athar Al Anaq dashboard in the background (no window), for this computer only.
' Put a shortcut to this file in the Windows Startup folder so it runs at every log-in;
' then the dashboard is always ready at http://localhost:8501.
' To stop it: Task Manager > Details > end "pythonw.exe" (or restart the computer without the shortcut).
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = folder
shell.Run """" & folder & "\.venv\Scripts\pythonw.exe"" -m streamlit run app.py --server.address localhost --server.headless true", 0, False
