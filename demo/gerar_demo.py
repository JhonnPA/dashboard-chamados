"""
Gera um dashboard de DEMONSTRAÇÃO com dados 100% fictícios, e os prints
usados no README (docs/img/).

    python demo/gerar_demo.py

Não lê a planilha nem usa nenhuma credencial: nomes, sistemas, descrições,
tickets e links são todos inventados aqui. Usa o mesmo src/dashboard.py da
produção, então o visual é idêntico ao dashboard real.

Os prints são tirados com o Microsoft Edge em modo headless (Windows).
"""

import random
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

PASTA_PROJETO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PASTA_PROJETO))

from src.dashboard import gerar_dashboard_html  # noqa: E402

ARQUIVO_DEMO = PASTA_PROJETO / "demo" / "dashboard_demo.html"
PASTA_IMAGENS = PASTA_PROJETO / "docs" / "img"

# Semente fixa: os dados (e os prints) saem sempre iguais
random.seed(42)

RESPONSAVEIS = ["Ana Ribeiro", "Bruno Carvalho", "Camila Duarte"]
DEVS = ["Diego Moreira", "Elisa Farias", "Fábio Nunes", "Gabriela Torres",
        "Henrique Prado", "Isabela Rocha", "João Mendes"]
# Peso de cada sistema (alguns concentram mais chamados, como na vida real)
SISTEMAS = {"Portal do Cliente": 45, "ERP": 25, "App Mobile": 15,
            "Financeiro": 10, "Integrações": 5}
PROBLEMAS = [
    "Erro ao gerar relatório de {x}",
    "Solicitação de acesso ao módulo de {x}",
    "Lentidão na tela de {x}",
    "Falha na importação de {x}",
    "Ajuste de cadastro de {x}",
    "Dúvida sobre o fluxo de {x}",
    "Correção de dados em {x}",
    "Erro ao salvar {x}",
]
ASSUNTOS = ["pedidos", "faturas", "clientes", "contratos", "estoque",
            "usuários", "notas fiscais", "pagamentos"]
# (mês, quantidade de chamados): volume crescendo, como numa equipe real
MESES = [("05/2026", 210), ("06/2026", 260), ("07/2026", 330),
         ("08/2026", 310), ("09/2026", 345), ("10/2026", 120)]


def _status(indice_mes):
    # Meses antigos: quase tudo resolvido. Mês atual: mais coisa em aberto.
    idade = len(MESES) - 1 - indice_mes
    chance_aberto = {0: 0.35, 1: 0.10}.get(idade, 0.02)
    sorteio = random.random()
    if sorteio < chance_aberto * 0.7:
        return "Em andamento"
    if sorteio < chance_aberto:
        return "Pendente"
    return "Resolvido"


def gerar_dados():
    linhas = []
    ticket = 500000
    for indice_mes, (mes, quantidade) in enumerate(MESES):
        for _ in range(quantidade):
            ticket += random.randint(1, 40)
            status = _status(indice_mes)
            linhas.append({
                "Ticket ID": str(ticket),
                "Responsável": random.choices(RESPONSAVEIS, weights=[50, 35, 15])[0],
                "Sistema": random.choices(list(SISTEMAS), weights=list(SISTEMAS.values()))[0],
                "Dev Responsável": random.choices(DEVS, weights=[22, 18, 16, 14, 12, 10, 8])[0],
                "Descrição": random.choice(PROBLEMAS).format(x=random.choice(ASSUNTOS)),
                "Status": status,
                "Mes_Referencia": mes,
                "Link TFS": f"https://example.com/tickets/{ticket}",
            })
    return pd.DataFrame(linhas)


def _edge():
    candidatos = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ]
    for caminho in candidatos:
        if caminho.exists():
            return str(caminho)
    return shutil.which("msedge")


def tirar_print(nome, largura, altura, hash_filtros="", rolar_ate_tabela=False):
    """Abre o dashboard de demo no Edge headless e salva um PNG."""
    html = ARQUIVO_DEMO.read_text(encoding="utf-8")
    if rolar_ate_tabela:
        html = html.replace("</body>", (
            "<script>addEventListener('load',()=>{const c=document.querySelector('.conteudo');"
            "c.scrollTop=c.scrollHeight;});</script></body>"
        ))
    temporario = ARQUIVO_DEMO.with_name(f"_print_{nome}.html")
    temporario.write_text(html, encoding="utf-8")

    destino = PASTA_IMAGENS / f"{nome}.png"
    subprocess.run([
        _edge(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
        f"--window-size={largura},{altura}", "--virtual-time-budget=15000",
        f"--screenshot={destino}", temporario.as_uri() + hash_filtros,
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    temporario.unlink()
    print(f"  print salvo: {destino.relative_to(PASTA_PROJETO)}")


def main():
    df = gerar_dados()
    print(f"{len(df)} chamados fictícios gerados.")
    gerar_dashboard_html(df, caminho_saida=str(ARQUIVO_DEMO))

    if not _edge():
        print("Microsoft Edge não encontrado: prints não gerados.")
        return

    PASTA_IMAGENS.mkdir(parents=True, exist_ok=True)
    tirar_print("visao-geral", 1600, 1000)
    tirar_print("filtro-mes-dev", 1600, 1000, hash_filtros="#mes=09%2F2026&dev=Elisa%20Farias")
    tirar_print("chamados-em-aberto", 1600, 1000, rolar_ate_tabela=True)


if __name__ == "__main__":
    main()
