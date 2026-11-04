' wsl_keepalive.vbs — keep the Ubuntu WSL distro (and therefore tailscaled) running after a Windows logon,
' with NO console window (window style 0). Registered as the logon task "WSL Keepalive" by the
' claude-remote-control skill (2026-09-19). A bare wsl.exe in a scheduled task flashes a console.
CreateObject("WScript.Shell").Run "wsl.exe -d Ubuntu --exec /bin/sh -c ""exec sleep infinity""", 0, False
