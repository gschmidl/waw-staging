# Starts a DOSBox Staging test instance after a delay (so the user can finish typing) and records its PID.
#   run_staging.ps1 -Exe <dosbox.exe> -Conf <file.conf> -PidFile <file> [-Delay 30]
param(
    [Parameter(Mandatory = $true)][string]$Exe,
    [Parameter(Mandatory = $true)][string]$Conf,
    [Parameter(Mandatory = $true)][string]$PidFile,
    [int]$Delay = 30
)
Start-Sleep -Seconds $Delay
$p = Start-Process -FilePath $Exe -ArgumentList @('--noprimaryconf', '-conf', "`"$Conf`"") -WorkingDirectory (Split-Path $Exe) -PassThru
Set-Content -Path $PidFile -Value $p.Id
"started PID $($p.Id)"
# Staging rejects window positions outside the primary display, so move the window to the left monitor ourselves.
& python -I (Join-Path $PSScriptRoot 'move_window.py') $p.Id -2400 60
