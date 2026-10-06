@echo off
REM Ajuste o caminho abaixo para onde você salvou a pasta do projeto no seu PC
cd /d "C:\Dashboard_Chamados"

REM Quando o log passa de ~1 MB, guarda o antigo como .old e começa um novo
for %%A in (log_execucao.txt) do if %%~zA GTR 1048576 move /y log_execucao.txt log_execucao.old.txt >nul

python main.py >> log_execucao.txt 2>&1

REM Repassa o código de saída para o Agendador de Tarefas mostrar falhas
exit /b %errorlevel%
