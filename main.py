"""
Ponto de entrada do projeto.

Esse é o único arquivo que você/o Agendador de Tarefas precisa executar:
    python main.py            -> execução automática (com as checagens abaixo)
    python main.py --forcar   -> roda tudo agora, sem checar horário nem alterações

O que ele faz, em ordem:
0. Checagens da execução automática (puladas com --forcar):
   - só roda de segunda a sexta, das 9h às 17h (horário de Campo Grande/MS);
   - só roda se a planilha foi alterada desde a última execução com sucesso.
1. Conecta na planilha Google Sheets.
2. Consolida todas as abas mensais ("Chamados - MM/AAAA") numa só.
3. Escreve o resultado de volta na aba "Consolidado" (se mudou algo).
4. Gera o dashboard.html com os gráficos.
5. Sobe o dashboard.html para a pasta configurada no Google Drive.
6. Publica o dashboard.html no PythonAnywhere (link fixo, sempre acessível).

Os envios (5 e 6) são independentes: se um falhar, o outro ainda é tentado.
Qualquer falha faz o script terminar com código de erro, para aparecer
como "falhou" no Agendador de Tarefas.
"""

import argparse
import json
import sys
import traceback

import config
from src.dashboard import gerar_dashboard_html
from src.drive import enviar_para_drive, obter_ultima_modificacao
from src.hospedagem import enviar_para_pythonanywhere
from src.sheets import conectar_planilha, consolidar, escrever_resultado


def _carimbo():
    return config.agora().strftime("%Y-%m-%d %H:%M:%S")


def dentro_do_horario():
    """Seg-sex, das HORA_INICIO:00 às HORA_FIM:00 (inclusive), em Campo Grande."""
    momento = config.agora()
    if momento.weekday() not in config.DIAS_EXECUCAO:
        return False
    minutos = momento.hour * 60 + momento.minute
    return config.HORA_INICIO * 60 <= minutos <= config.HORA_FIM * 60


def _ler_estado():
    try:
        return json.loads(config.ESTADO_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def _salvar_estado(modificacao):
    config.ESTADO_FILE.write_text(
        json.dumps({"ultima_modificacao_processada": modificacao, "processado_em": _carimbo()}, indent=2),
        encoding="utf-8",
    )


def main(forcar=False):
    if not forcar and not dentro_do_horario():
        print(f"[{_carimbo()}] Fora do horário (seg-sex, {config.HORA_INICIO}h-{config.HORA_FIM}h de Campo Grande). Nada a fazer.")
        return 0

    spreadsheet, creds = conectar_planilha()

    modificacao = obter_ultima_modificacao(spreadsheet.id, creds)
    if not forcar and modificacao == _ler_estado().get("ultima_modificacao_processada"):
        print(f"[{_carimbo()}] Planilha sem alterações. Nada a fazer.")
        return 0

    print(f"[{_carimbo()}] Iniciando consolidação{' (forçada)' if forcar else ''}...")
    df_final = consolidar(spreadsheet)

    if df_final is None:
        print("Nada para processar. Encerrando.")
        return 0

    escreveu = escrever_resultado(spreadsheet, df_final)
    gerar_dashboard_html(df_final, caminho_saida=config.DASHBOARD_HTML_FILE)

    envios = [
        ("Google Drive", lambda: enviar_para_drive(config.DASHBOARD_HTML_FILE, creds)),
        ("PythonAnywhere", lambda: enviar_para_pythonanywhere(config.DASHBOARD_HTML_FILE)),
    ]
    falhas = []
    for nome, enviar in envios:
        try:
            enviar()
        except Exception:
            print(f"ERRO ao enviar para {nome}:")
            traceback.print_exc(file=sys.stdout)
            falhas.append(nome)

    print(f"Concluído: {len(df_final)} linhas consolidadas na aba '{config.CONSOLIDATED_SHEET_NAME}'.")

    if falhas:
        # Não salva o estado: na próxima execução tenta de novo
        print(f"Atenção: falha no envio para {', '.join(falhas)}.")
        return 1

    # A escrita na aba "Consolidado" também altera a planilha. Relê a data
    # depois dela, para essa alteração do próprio script não contar como
    # "planilha alterada" na próxima execução.
    _salvar_estado(obter_ultima_modificacao(spreadsheet.id, creds) if escreveu else modificacao)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consolida a planilha de chamados e publica o dashboard.")
    parser.add_argument(
        "--forcar", action="store_true",
        help="roda agora, mesmo fora do horário e sem alterações na planilha",
    )
    sys.exit(main(forcar=parser.parse_args().forcar))
