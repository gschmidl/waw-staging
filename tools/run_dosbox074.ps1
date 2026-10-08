# Starts a DOSBox 0.74 test instance on the left monitor after a delay and records its PID.
#   run_dosbox074.ps1 -Exe <DOSBox.exe> -Conf <file.conf> -PidFile <file> [-Delay 30]
param(
    [Parameter(Mandatory = $true)][string]$Exe,
    [Parameter(Mandatory = $true)][string]$Conf,
    [Parameter(Mandatory = $true)][string]$PidFile,
    [int]$Delay = 30
)
Start-Sleep -Seconds $Delay
$env:SDL_VIDEO_WINDOW_POS = '-2300,120'
$p = Start-Process -FilePath $Exe -ArgumentList @('-noconsole', '-conf', "`"$Conf`"") -WorkingDirectory (Split-Path $Exe) -PassThru
Set-Content -Path $PidFile -Value $p.Id
"started PID $($p.Id)"
# Staging rejects window positions outside the primary display, so move the window to the left monitor ourselves.
& python -I (Join-Path $PSScriptRoot 'move_window.py') $p.Id -2400 60
