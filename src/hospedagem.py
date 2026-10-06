"""
Envio do dashboard.html para o PythonAnywhere via API de arquivos, para que
fique hospedado num link sempre acessível (sem precisar baixar o arquivo
toda vez nem depender de uma máquina da empresa sempre ligada).
"""

import requests

import config

# Evita que a tarefa agendada fique travada para sempre se a rede cair
TIMEOUT_SEGUNDOS = 60


def enviar_para_pythonanywhere(caminho_local):
    """Envia o conteúdo do dashboard.html para o caminho configurado no
    PythonAnywhere, sobrescrevendo a versão anterior."""

    if not config.PYTHONANYWHERE_USERNAME or not config.PYTHONANYWHERE_API_TOKEN:
        print("PythonAnywhere não configurado (usuário/token em branco) - pulando envio.")
        return

    api_base = f"https://www.pythonanywhere.com/api/v0/user/{config.PYTHONANYWHERE_USERNAME}/"
    caminho_remoto = f"files/path{config.PYTHONANYWHERE_CAMINHO_REMOTO}"

    with open(caminho_local, "rb") as arquivo:
        resposta = requests.post(
            api_base + caminho_remoto,
            files={"content": arquivo},
            headers={"Authorization": f"Token {config.PYTHONANYWHERE_API_TOKEN}"},
            timeout=TIMEOUT_SEGUNDOS,
        )

    if resposta.status_code not in (200, 201):
        raise RuntimeError(
            f"Falha ao publicar no PythonAnywhere: {resposta.status_code} - {resposta.text[:500]}"
        )

    print(f"Dashboard publicado no PythonAnywhere ({resposta.status_code}).")
