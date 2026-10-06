"""
Configurações centrais do projeto.

Segredos (tokens, IDs) ficam no arquivo .env, que não é versionado — veja
.env.example. Aqui ficam só as configurações não sensíveis.
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

PASTA_PROJETO = Path(__file__).resolve().parent

# Carrega o .env da pasta do projeto, independente de onde o script é chamado
load_dotenv(PASTA_PROJETO / ".env")

# --- Horário de execução automática ---
# Fuso de Campo Grande (MS): UTC-4 o ano todo (sem horário de verão desde
# 2019). Calculado aqui, sem depender do fuso configurado no Windows.
FUSO_HORARIO = timezone(timedelta(hours=-4), "Campo Grande")
# Segunda (0) a sexta (4), das 9h às 17h
DIAS_EXECUCAO = range(0, 5)
HORA_INICIO = 9
HORA_FIM = 17

# Guarda a data da última modificação da planilha já processada, para só
# rodar a pipeline de novo quando alguém alterar a planilha
ESTADO_FILE = PASTA_PROJETO / ".estado_pipeline.json"


def agora():
    """Data/hora atual no fuso de Campo Grande."""
    return datetime.now(FUSO_HORARIO)

# Caminho do arquivo JSON da conta de serviço (baixado do Google Cloud)
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

# Nome exato da planilha no Google Drive (como aparece na aba do navegador)
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "")

# Nome da aba onde o resultado consolidado será escrito
CONSOLIDATED_SHEET_NAME = "Consolidado"

# Padrão de nome das abas mensais (ex: "Chamados - 07/2026")
SHEET_PATTERN = r"Chamados\s*-\s*(\d{2})/(\d{4})"

# Nome do arquivo HTML do dashboard, gerado na mesma pasta do script
DASHBOARD_HTML_FILE = "dashboard.html"

# ID da pasta do Google Drive onde o dashboard.html será enviado/atualizado.
# Essa pasta deve ser compartilhada com o e-mail da conta de serviço (Editor)
# e com acesso restrito ao domínio da empresa (não público).
# O ID é o trecho da URL depois de "/folders/" ao abrir a pasta no navegador.
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "")

# --- PythonAnywhere (hospedagem com link fixo, sem precisar baixar) ---
# Deixe em branco no .env para desativar esse envio.
PYTHONANYWHERE_USERNAME = os.getenv("PYTHONANYWHERE_USERNAME", "")
PYTHONANYWHERE_API_TOKEN = os.getenv("PYTHONANYWHERE_API_TOKEN", "")
# Caminho remoto onde o dashboard.html será salvo no PythonAnywhere.
PYTHONANYWHERE_CAMINHO_REMOTO = os.getenv(
    "PYTHONANYWHERE_CAMINHO_REMOTO", f"/home/{PYTHONANYWHERE_USERNAME}/dashboard.html"
)

# Escopos de acesso necessários para a conta de serviço
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
