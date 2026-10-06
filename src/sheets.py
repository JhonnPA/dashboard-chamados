"""
Tudo relacionado a ler e escrever na planilha Google Sheets.
"""

import re

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

import config

SHEET_PATTERN = re.compile(config.SHEET_PATTERN)


def conectar_planilha():
    """Autentica com a conta de serviço e abre a planilha configurada.

    Retorna (spreadsheet, creds) — as credenciais são reaproveitadas
    depois para o upload no Google Drive.
    """
    if not config.SPREADSHEET_NAME:
        raise RuntimeError("SPREADSHEET_NAME não configurado no arquivo .env.")

    creds = Credentials.from_service_account_file(config.CREDENTIALS_FILE, scopes=config.SCOPES)
    client = gspread.authorize(creds)
    return client.open(config.SPREADSHEET_NAME), creds


def _ler_aba_como_dataframe(aba):
    """Lê a aba como tabela bruta e monta o dataframe manualmente, ignorando
    colunas sem cabeçalho (nome em branco). Usamos isso em vez de
    aba.get_all_records() porque esse método do gspread quebra quando existe
    mais de uma coluna com cabeçalho vazio (comum em planilhas com colunas
    extras de formatação/dropdown sem uso)."""

    valores = aba.get_all_values()
    if not valores:
        return pd.DataFrame()

    cabecalho = valores[0]
    linhas = valores[1:]

    df = pd.DataFrame(linhas, columns=cabecalho)

    # Remove colunas sem nome (cabeçalho vazio ou só espaços)
    colunas_validas = [c for c in df.columns if c.strip() != ""]
    df = df[colunas_validas]

    # Se ainda sobrar algum nome de coluna duplicado, mantém só a primeira
    # ocorrência (evita erro de colunas ambíguas mais adiante)
    df = df.loc[:, ~df.columns.duplicated()]

    return df


def consolidar(spreadsheet):
    """Percorre as abas mensais (ex: 'Chamados - 07/2026') e junta tudo
    em um único dataframe."""

    todas_as_tabelas = []

    for aba in spreadsheet.worksheets():
        match = SHEET_PATTERN.match(aba.title.strip())
        if not match:
            continue  # ignora abas que não são de meses (ex: a própria "Consolidado")

        mes, ano = match.groups()
        df = _ler_aba_como_dataframe(aba)

        if df.empty:
            continue

        # Descarta linhas sem Ticket ID: são linhas em branco que já vêm com
        # formatação/dropdown pré-aplicado, mas não são chamados de verdade.
        if "Ticket ID" in df.columns:
            df = df[df["Ticket ID"].astype(str).str.strip() != ""]

        if df.empty:
            continue

        df["Mes_Referencia"] = f"{mes}/{ano}"
        df["Planilha_Origem"] = aba.title
        todas_as_tabelas.append(((int(ano), int(mes)), df))
        print(f"  -> Lida: '{aba.title}' ({len(df)} linhas)")

    if not todas_as_tabelas:
        print("Nenhuma aba encontrada com o padrão configurado em SHEET_PATTERN.")
        return None

    # Ordena por data (e não pela ordem das abas na planilha), para que o
    # keep="last" abaixo mantenha sempre a ocorrência do mês mais recente
    todas_as_tabelas = [df for _, df in sorted(todas_as_tabelas, key=lambda t: t[0])]

    total_lido = sum(len(t) for t in todas_as_tabelas)
    df_final = pd.concat(todas_as_tabelas, ignore_index=True)

    if "Ticket ID" in df_final.columns:
        duplicados = df_final[df_final.duplicated(subset=["Ticket ID"], keep=False)]
        if not duplicados.empty:
            ids_duplicados = sorted(duplicados["Ticket ID"].unique().tolist())
            print(f"  ATENÇÃO: {len(ids_duplicados)} Ticket ID(s) aparecem em mais de uma linha: {ids_duplicados}")
            print("  (só a última ocorrência de cada um é mantida no consolidado)")

        df_final = df_final.drop_duplicates(subset=["Ticket ID"], keep="last")

    print(f"  Diagnóstico: {total_lido} linhas lidas ao todo -> {len(df_final)} linhas após remover duplicados.")

    return df_final


def escrever_resultado(spreadsheet, df_final):
    """Escreve o dataframe consolidado na aba de destino, sobrescrevendo
    o conteúdo anterior.

    Se a aba já tem exatamente o mesmo conteúdo, não escreve nada e retorna
    False. Isso importa para a execução automática: escrever na aba conta
    como "alteração na planilha" e faria a pipeline rodar de novo à toa."""

    # Substitui células vazias (NaN) por texto vazio ANTES de converter para
    # string. O pandas mantém NaN mesmo depois de um astype(str) direto, o
    # que quebra o envio para o Google (JSON não aceita NaN).
    df_limpo = df_final.fillna("").astype(str)

    valores = [df_limpo.columns.values.tolist()] + df_limpo.values.tolist()
    total_linhas, total_colunas = len(valores), len(df_limpo.columns)

    try:
        aba_consolidada = spreadsheet.worksheet(config.CONSOLIDATED_SHEET_NAME)
        if aba_consolidada.get_all_values() == valores:
            print(f"  Aba '{config.CONSOLIDATED_SHEET_NAME}' já está atualizada (nada a escrever).")
            return False
    except gspread.exceptions.WorksheetNotFound:
        aba_consolidada = spreadsheet.add_worksheet(
            title=config.CONSOLIDATED_SHEET_NAME, rows=total_linhas, cols=total_colunas,
        )

    # Escreve por cima primeiro e só depois corta o que sobrou da versão
    # anterior. Assim, se o envio falhar no meio, a aba não fica vazia
    # (como aconteceria com um clear() antes do update()).
    aba_consolidada.update(valores, "A1")
    aba_consolidada.resize(rows=total_linhas, cols=total_colunas)
    return True