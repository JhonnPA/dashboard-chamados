"""
Upload/atualização do dashboard.html numa pasta do Google Drive
restrita ao domínio da empresa.
"""

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import config


def obter_ultima_modificacao(file_id, creds):
    """Data da última alteração do arquivo no Drive (texto ISO, ex:
    '2026-10-01T17:42:10.123Z'). É uma consulta leve: não lê o conteúdo."""
    drive_service = build("drive", "v3", credentials=creds)
    arquivo = drive_service.files().get(
        fileId=file_id, fields="modifiedTime", supportsAllDrives=True
    ).execute()
    return arquivo["modifiedTime"]


def enviar_para_drive(caminho_local, creds):
    """Atualiza o conteúdo do dashboard.html na pasta configurada em
    config.DRIVE_FOLDER_ID.

    Importante: contas de serviço do Google não têm cota de armazenamento
    própria, então elas NÃO conseguem criar arquivos novos no Drive - só
    atualizar arquivos que já existem (criados por uma pessoa real, cujo
    armazenamento é usado). Por isso, o arquivo dashboard.html precisa ser
    criado manualmente uma vez na pasta antes de rodar o script pela
    primeira vez.
    """

    if not config.DRIVE_FOLDER_ID:
        raise RuntimeError("DRIVE_FOLDER_ID não configurado no arquivo .env.")

    drive_service = build("drive", "v3", credentials=creds)

    query = (
        f"name = '{config.DASHBOARD_HTML_FILE}' and "
        f"'{config.DRIVE_FOLDER_ID}' in parents and trashed = false"
    )
    resultado = drive_service.files().list(q=query, fields="files(id, name)").execute()
    arquivos_existentes = resultado.get("files", [])

    if not arquivos_existentes:
        raise RuntimeError(
            f"O arquivo '{config.DASHBOARD_HTML_FILE}' ainda não existe na pasta do Drive "
            f"(ID: {config.DRIVE_FOLDER_ID}).\n"
            "Contas de serviço não têm cota de armazenamento e não conseguem criar arquivos "
            "novos no Drive, só atualizar arquivos existentes.\n"
            "SOLUÇÃO: crie manualmente um arquivo vazio chamado "
            f"'{config.DASHBOARD_HTML_FILE}' dentro dessa pasta do Drive (pela sua conta "
            "pessoal/da empresa) e rode o script de novo."
        )

    media = MediaFileUpload(caminho_local, mimetype="text/html", resumable=True)
    file_id = arquivos_existentes[0]["id"]
    drive_service.files().update(fileId=file_id, media_body=media).execute()
    print(f"Dashboard atualizado no Google Drive (arquivo existente: {file_id}).")