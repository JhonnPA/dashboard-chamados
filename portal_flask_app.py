"""
Este arquivo vai DENTRO do PythonAnywhere (não roda no seu PC).

Ele serve o dashboard.html protegido por usuário/senha (HTTP Basic Auth) -
ou seja, ao acessar o link, o navegador pede login antes de mostrar
qualquer coisa.

Como usar: cole este conteúdo no arquivo "flask_app.py" que o PythonAnywhere
cria automaticamente quando você configura um novo web app Flask.

Usuário e senha NÃO ficam no código: crie um arquivo ".env" na mesma pasta
do flask_app.py no PythonAnywhere com:
    DASHBOARD_USUARIO=...
    DASHBOARD_SENHA=...
e instale a dependência pelo console Bash de lá:
    pip install --user python-dotenv

Proteções:
- Acesso por http:// é redirecionado para https:// ANTES de pedir a senha
  (senão o navegador enviaria usuário/senha sem criptografia).
- Bloqueio temporário de um IP após várias senhas erradas seguidas.
- Cabeçalhos de segurança em todas as respostas (HSTS, sem cache, sem
  exibição dentro de outros sites).
"""

import hmac
import os
import time
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, Response, redirect, request

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

app = Flask(__name__)

USUARIO = os.environ.get("DASHBOARD_USUARIO", "")
SENHA = os.environ.get("DASHBOARD_SENHA", "")
if not USUARIO or not SENHA:
    raise RuntimeError("Defina DASHBOARD_USUARIO e DASHBOARD_SENHA no arquivo .env.")

# Caminho onde o script local envia o dashboard.html atualizado
CAMINHO_DASHBOARD = os.environ.get(
    "DASHBOARD_CAMINHO", os.path.expanduser("~/dashboard.html")
)

# Bloqueio contra tentativas de adivinhar a senha
MAX_TENTATIVAS = 10
JANELA_SEGUNDOS = 15 * 60
_falhas_por_ip = {}  # ip -> lista de horários das tentativas erradas


def _ip_cliente():
    # O PythonAnywhere fica atrás de um proxy, que informa o IP real aqui
    return request.headers.get("X-Real-IP") or request.remote_addr or "?"


def _falhas_recentes(ip):
    limite = time.time() - JANELA_SEGUNDOS
    recentes = [t for t in _falhas_por_ip.get(ip, []) if t > limite]
    if recentes:
        _falhas_por_ip[ip] = recentes
    else:
        _falhas_por_ip.pop(ip, None)
    return recentes


def _credenciais_validas(auth):
    # compare_digest evita ataques de tempo na comparação da senha
    return (
        auth is not None
        and hmac.compare_digest((auth.username or "").encode(), USUARIO.encode())
        and hmac.compare_digest((auth.password or "").encode(), SENHA.encode())
    )


@app.before_request
def forcar_https():
    # O proxy do PythonAnywhere informa o protocolo original neste cabeçalho
    if request.headers.get("X-Forwarded-Proto", "https") == "http":
        return redirect(request.url.replace("http://", "https://", 1), code=301)


@app.after_request
def cabecalhos_de_seguranca(resposta):
    resposta.headers["Strict-Transport-Security"] = "max-age=31536000"
    resposta.headers["Cache-Control"] = "no-store"
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["X-Frame-Options"] = "DENY"
    resposta.headers["Referrer-Policy"] = "no-referrer"
    resposta.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resposta


def autenticacao_necessaria(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        ip = _ip_cliente()
        if len(_falhas_recentes(ip)) >= MAX_TENTATIVAS:
            return Response("Muitas tentativas. Tente de novo em alguns minutos.", 429)

        auth = request.authorization
        if not _credenciais_validas(auth):
            # Só conta como falha quando uma senha foi de fato enviada (o
            # primeiro acesso sempre chega sem senha, antes do navegador pedir)
            if auth is not None:
                _falhas_por_ip.setdefault(ip, []).append(time.time())
            return Response(
                "Acesso restrito.", 401,
                {"WWW-Authenticate": 'Basic realm="Dashboard de Chamados"'},
            )

        _falhas_por_ip.pop(ip, None)
        return f(*args, **kwargs)
    return decorada


@app.route("/")
@autenticacao_necessaria
def dashboard():
    if not os.path.exists(CAMINHO_DASHBOARD):
        return "Dashboard ainda não foi publicado. Rode o script local primeiro.", 404

    with open(CAMINHO_DASHBOARD, "r", encoding="utf-8") as f:
        conteudo = f.read()

    return Response(conteudo, mimetype="text/html")


if __name__ == "__main__":
    app.run()
