# Configura a execucao automatica do Dashboard de Chamados.
# Precisa ser executado como ADMINISTRADOR:
#   powershell -ExecutionPolicy Bypass -File C:\Dashboard_Chamados\configurar_agendamento.ps1
#
# O que faz:
#   1. Ajusta o fuso do Windows para Campo Grande/MS ("Central Brazilian
#      Standard Time" = UTC-4, sem horario de verao) e liga a sincronizacao
#      automatica do relogio pela internet.
#   2. Configura a tarefa "Dashboard de Chamados" no Agendador:
#      seg-sex, a cada 10 minutos, das 9h as 17h, sem abrir janela.
#      O main.py so processa algo quando a planilha foi alterada.
#
# Para mudar o intervalo ou o horario, ajuste as variaveis abaixo.

$NomeTarefa   = "Dashboard de Chamados"
$PastaProjeto = "C:\Dashboard_Chamados"
$Inicio       = "09:00"
$IntervaloMin = 10
$DuracaoHoras = 8     # 9h + 8h = ultima execucao as 17h

$ErrorActionPreference = "Stop"

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Write-Host "Execute este script como ADMINISTRADOR." -ForegroundColor Red
    exit 1
}

# ---------- 1. Fuso horario e sincronizacao do relogio ----------
Write-Host "`n[1/2] Relogio do Windows" -ForegroundColor Cyan
tzutil /s "Central Brazilian Standard Time"
Set-Service w32time -StartupType Automatic
Start-Service w32time -ErrorAction SilentlyContinue
w32tm /config /manualpeerlist:"time.windows.com,0x9 a.ntp.br,0x9" /syncfromflags:manual /update | Out-Null
Restart-Service w32time
Start-Sleep -Seconds 2
w32tm /resync /force | Out-Null
Write-Host ("  Fuso: " + (Get-TimeZone).DisplayName)
Write-Host ("  Hora local agora: " + (Get-Date -Format "dd/MM/yyyy HH:mm:ss") + "  (deve ser o horario de Campo Grande)")

# ---------- 2. Tarefa agendada ----------
Write-Host "`n[2/2] Tarefa agendada '$NomeTarefa'" -ForegroundColor Cyan
$gatilho = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $Inicio
$repeticao = New-ScheduledTaskTrigger -Once -At $Inicio `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervaloMin) `
    -RepetitionDuration (New-TimeSpan -Hours $DuracaoHoras -Minutes 1)
$gatilho.Repetition = $repeticao.Repetition

# conhost --headless: roda o .bat sem abrir a janela preta a cada execucao
$acao = New-ScheduledTaskAction -Execute "C:\Windows\System32\conhost.exe" `
    -Argument "--headless cmd.exe /c `"$PastaProjeto\rodar_diario.bat`"" `
    -WorkingDirectory $PastaProjeto

$opcoes = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

if (Get-ScheduledTask -TaskName $NomeTarefa -ErrorAction SilentlyContinue) {
    Set-ScheduledTask -TaskName $NomeTarefa -Trigger $gatilho -Action $acao -Settings $opcoes | Out-Null
} else {
    Register-ScheduledTask -TaskName $NomeTarefa -Trigger $gatilho -Action $acao -Settings $opcoes `
        -Description "Atualiza o Dashboard de Chamados quando a planilha muda (seg-sex, 9h-17h)" | Out-Null
}

$t = Get-ScheduledTask -TaskName $NomeTarefa
Write-Host ("  Dias: seg-sex | a cada " + $IntervaloMin + " min, das " + $Inicio + " por " + $DuracaoHoras + "h")
Write-Host ("  Proxima execucao: " + (Get-ScheduledTaskInfo -TaskName $NomeTarefa).NextRunTime)
Write-Host "`nPronto." -ForegroundColor Green
