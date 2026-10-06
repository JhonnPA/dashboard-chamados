"""
Geração do dashboard HTML a partir do dataframe consolidado.

- Filtros na barra lateral (mês, responsável, dev, sistema e status), com a
  contagem de chamados em cada item, botão de limpar e filtros salvos no
  link (dá para recarregar a página ou compartilhar o link já filtrado).
- Cartões com comparação com o mês anterior (quando um mês está selecionado).
- Gráficos de responsável/dev/sistema em barras horizontais, divididas por status.
- Status "Pendente" (faltando informação / aguardando o solicitante) separado
  de "Em andamento": cartão, cor e barras próprias.
- Tabela dos chamados em aberto (em andamento + pendentes), com busca e
  link para o TFS.

Todos os gráficos são desenhados via JavaScript no navegador, então os
filtros recalculam tudo sem precisar rodar o script de novo.

O HTML/CSS/JS fica num template comum (não f-string), com marcadores
__ASSIM__ substituídos no final, para não precisar duplicar as chaves {}.
"""

import json

import config

COR_PRIMARIA = "#4F46E5"
COR_RESOLVIDO = "#10B981"
COR_ANDAMENTO = "#F59E0B"
COR_PENDENTE = "#0EA5E9"
COR_OUTROS = "#9CA3AF"

# Versão do plotly.js carregada pela CDN (o código JS abaixo usa a API 2.x).
# O SRI é a "impressão digital" do arquivo: se o conteúdo na CDN for
# alterado, o navegador se recusa a executá-lo. Ao trocar de versão,
# recalcule o hash (sha384 do arquivo, em base64).
PLOTLY_JS_URL = "https://cdn.plot.ly/plotly-2.32.0.min.js"
PLOTLY_JS_SRI = "sha384-7TVmlZWH60iKX5Uk7lSvQhjtcgw2tkFjuwLcXoRSR4zXTyWFJRm9aPAguMh7CIra"

COLUNAS_UTEIS = [
    "Ticket ID", "Status", "Sistema", "Responsável", "Dev Responsável",
    "Mes_Referencia", "Descrição", "Link TFS",
]
# Só entram no HTML para chamados não resolvidos (são os únicos exibidos na
# tabela) - evita expor descrições de todo o histórico sem necessidade.
COLUNAS_SO_ABERTOS = ["Descrição", "Link TFS"]


def _ordenar_mes_referencia(valores):
    def chave(v):
        try:
            mes, ano = v.split("/")
            return (int(ano), int(mes))
        except Exception:
            return (0, 0)

    return sorted(valores, key=chave)


def _json_para_script(dados):
    # Impede que um texto como "</script>" vindo da planilha feche a tag
    # <script> antes da hora e quebre (ou injete código na) página.
    return json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")


def gerar_dashboard_html(df, caminho_saida=None):
    caminho_saida = caminho_saida or config.DASHBOARD_HTML_FILE

    colunas_presentes = [c for c in COLUNAS_UTEIS if c in df.columns]
    df = df[colunas_presentes].copy()
    for col in colunas_presentes:
        df[col] = df[col].fillna("").astype(str).str.strip()

    if "Status" in df.columns:
        resolvidos = df["Status"].str.lower() == "resolvido"
        for col in COLUNAS_SO_ABERTOS:
            if col in df.columns:
                df.loc[resolvidos, col] = ""

    meses = []
    if "Mes_Referencia" in df.columns:
        meses = _ordenar_mes_referencia([m for m in df["Mes_Referencia"].unique() if m])

    substituicoes = {
        "__PLOTLY_JS_URL__": PLOTLY_JS_URL,
        "__PLOTLY_JS_SRI__": PLOTLY_JS_SRI,
        "__COR_PRIMARIA__": COR_PRIMARIA,
        "__COR_RESOLVIDO__": COR_RESOLVIDO,
        "__COR_ANDAMENTO__": COR_ANDAMENTO,
        "__COR_PENDENTE__": COR_PENDENTE,
        "__COR_OUTROS__": COR_OUTROS,
        "__ATUALIZADO_EM__": config.agora().strftime("%d/%m/%Y às %H:%M"),
        "__ORDEM_MESES__": _json_para_script(meses),
        # Por último: os dados podem conter qualquer texto, inclusive algo
        # parecido com os marcadores acima
        "__DADOS__": _json_para_script(df.to_dict(orient="records")),
    }
    pagina = TEMPLATE
    for marcador, valor in substituicoes.items():
        pagina = pagina.replace(marcador, valor)

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(pagina)

    print(f"Dashboard HTML gerado em: {caminho_saida}")


TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<meta name="referrer" content="no-referrer">
<!-- Segurança: a página só carrega o Plotly e a fonte, e não pode enviar
     dados para lugar nenhum (connect-src/img-src/form-action bloqueados),
     mesmo que algum script seja comprometido -->
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline' https://cdn.plot.ly; style-src 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src data: blob:; connect-src 'none'; form-action 'none'; base-uri 'none'">
<title>Dashboard de Chamados</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="__PLOTLY_JS_URL__" integrity="__PLOTLY_JS_SRI__" crossorigin="anonymous"></script>
<style>
  :root {
    --primaria: __COR_PRIMARIA__;
    --primaria-fundo: #EEF2FF;
    --primaria-borda: #C7D2FE;
    --resolvido: __COR_RESOLVIDO__;
    --andamento: __COR_ANDAMENTO__;
    --pendente: __COR_PENDENTE__;
    --texto: #1F2937;
    --texto-2: #6B7280;
    --texto-3: #9CA3AF;
    --borda: #E5E7EB;
    --fundo: #F3F4F6;
    --ruim: #DC2626;
    --sombra: 0 1px 3px rgba(0,0,0,0.06);
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; }
  body {
    font-family: 'Inter', -apple-system, sans-serif;
    background: var(--fundo); color: var(--texto);
    display: flex; overflow: hidden;
  }
  button:focus-visible, #busca:focus-visible { outline: 2px solid var(--primaria); outline-offset: 1px; }

  /* Sidebar com os filtros */
  .sidebar {
    width: clamp(180px, 16vw, 240px); flex-shrink: 0; background: white; border-right: 1px solid var(--borda);
    padding: 18px 14px; display: flex; flex-direction: column; gap: 16px;
    overflow-y: auto; height: 100vh;
  }
  .marca { font-weight: 700; font-size: 15px; line-height: 1.25; padding: 0 4px; }
  .sidebar-topo { display: flex; justify-content: space-between; align-items: center; padding: 0 4px; min-height: 24px; }
  .sidebar-topo .rotulo { font-size: 12px; font-weight: 700; color: var(--texto); }
  #limpar {
    font: inherit; font-size: 12px; font-weight: 600; color: var(--primaria); background: none;
    border: none; padding: 2px 4px; cursor: pointer; border-radius: 6px;
  }
  #limpar:hover { background: var(--primaria-fundo); }
  .filtro-label { text-transform: uppercase; font-size: 10.5px; font-weight: 700; color: var(--texto-3); letter-spacing: 0.05em; margin: 0 4px 6px; }
  .filtro-item {
    display: flex; justify-content: space-between; align-items: center; gap: 8px; width: 100%;
    font: inherit; text-align: left; background: none; border: none;
    padding: 6px 10px; border-radius: 8px; color: #4B5563; font-size: 13px; font-weight: 500;
    cursor: pointer; user-select: none; transition: background 0.15s; margin-bottom: 2px;
  }
  .filtro-item .nome { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .filtro-item .qtd { font-size: 11px; color: var(--texto-3); font-variant-numeric: tabular-nums; flex-shrink: 0; }
  .filtro-item:hover { background: var(--fundo); }
  .filtro-item.ativo { background: var(--primaria); color: white; }
  .filtro-item.ativo .qtd { color: rgba(255,255,255,0.8); }
  .sidebar-rodape { margin-top: auto; color: var(--texto-3); font-size: 11px; padding: 0 4px; }

  /* Conteúdo principal */
  .conteudo { flex: 1; min-width: 0; height: 100vh; overflow-y: auto; padding: 16px 22px 32px; }
  .topo { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
  .topo h1 { font-size: 22px; font-weight: 700; margin: 0; }
  .resumo { font-size: 12px; color: var(--texto-2); }

  /* Cartões */
  .cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 12px; }
  .card {
    background: white; border-radius: 12px; padding: 14px 18px; box-shadow: var(--sombra); min-width: 0;
    display: flex; flex-direction: column; justify-content: center; min-height: 96px;
  }
  .card .valor { font-size: clamp(22px, 2.1vw, 32px); font-weight: 700; line-height: 1.2; }
  .card .label { color: var(--texto-2); font-size: 13px; margin-top: 2px; }
  .card .delta { font-size: 12px; font-weight: 600; margin-top: 4px; min-height: 16px; color: var(--texto-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .delta .bom { color: var(--resolvido); }
  .delta .ruim { color: var(--ruim); }
  .delta .neutro { color: var(--texto-2); }
  .card.resolvido .valor { color: var(--resolvido); }
  .card.andamento .valor { color: var(--andamento); }
  .card.pendente .valor { color: var(--pendente); }
  .selo { display: inline-block; border-radius: 999px; padding: 1px 8px; font-size: 11.5px; font-weight: 600; white-space: nowrap; }
  .selo.andamento { background: #FEF3C7; color: #92400E; }
  .selo.pendente { background: #E0F2FE; color: #075985; }
  .selo.outro { background: var(--fundo); color: var(--texto-2); }
  .card.total .valor { color: var(--primaria); }

  /* Gráficos */
  .grid-principal {
    display: grid; grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(2, 1fr);
    gap: 12px; height: max(520px, calc(100vh - 210px));
  }
  .grafico-card {
    background: white; border-radius: 12px; padding: 6px; box-shadow: var(--sombra);
    overflow: hidden; min-height: 0; min-width: 0; display: flex; flex-direction: column;
  }
  .grafico-card.full { grid-column: span 2; }
  .grafico-card > div { flex: 1; min-height: 0; width: 100%; }

  /* Tabela de chamados em aberto */
  .tabela-card { background: white; border-radius: 12px; box-shadow: var(--sombra); margin-top: 12px; padding: 14px 16px; }
  .tabela-topo { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; }
  .tabela-topo h2 { font-size: 15px; margin: 0; }
  .tabela-topo h2 .qtd { background: #FEF3C7; color: #92400E; border-radius: 999px; padding: 2px 8px; font-size: 12px; margin-left: 6px; }
  #busca { font: inherit; font-size: 13px; padding: 7px 10px; border: 1px solid var(--borda); border-radius: 8px; width: min(320px, 100%); }
  .tabela-scroll { max-height: 60vh; overflow: auto; border: 1px solid var(--borda); border-radius: 8px; }
  table { border-collapse: collapse; width: 100%; font-size: 12.5px; min-width: 760px; }
  thead th {
    position: sticky; top: 0; background: #F9FAFB; text-align: left; font-weight: 600; color: var(--texto-2);
    padding: 8px 10px; border-bottom: 1px solid var(--borda); white-space: nowrap;
  }
  tbody td { padding: 7px 10px; border-bottom: 1px solid #F3F4F6; vertical-align: top; }
  tbody tr:hover { background: #F9FAFB; }
  td.ticket { font-variant-numeric: tabular-nums; white-space: nowrap; font-weight: 600; }
  td.nowrap { white-space: nowrap; }
  td a { color: var(--primaria); font-weight: 600; text-decoration: none; white-space: nowrap; }
  td a:hover { text-decoration: underline; }
  .tabela-vazia { padding: 24px; text-align: center; color: var(--texto-2); }

  /* Celular / telas estreitas: sidebar vira um bloco no topo, com os
     filtros lado a lado, e a página inteira rola */
  @media (max-width: 900px) {
    body { flex-direction: column; overflow: auto; height: auto; }
    .sidebar { width: 100%; height: auto; padding: 14px; border-right: none; border-bottom: 1px solid var(--borda); gap: 12px; }
    .lista-filtro { display: flex; flex-wrap: wrap; gap: 4px; }
    .filtro-item { width: auto; margin-bottom: 0; border: 1px solid var(--borda); }
    .filtro-item.ativo { border-color: var(--primaria); }
    .sidebar-rodape { margin-top: 0; }
    .conteudo { height: auto; overflow: visible; padding: 12px 12px 24px; }
    .cards { grid-template-columns: repeat(2, 1fr); gap: 10px; }
    .grid-principal { grid-template-columns: 1fr; grid-template-rows: none; height: auto; gap: 10px; }
    .grafico-card { height: 320px; }
    .grafico-card.full { grid-column: auto; }
  }
</style>
</head>
<body>

  <aside class="sidebar" aria-label="Filtros">
    <div class="marca">Dashboard de<br>Chamados</div>

    <div class="sidebar-topo">
      <span class="rotulo">Filtros</span>
      <button type="button" id="limpar" hidden>Limpar filtros</button>
    </div>

    <div><div class="filtro-label">Mês</div><div class="lista-filtro" id="f-mes"></div></div>
    <div><div class="filtro-label">Responsável</div><div class="lista-filtro" id="f-responsavel"></div></div>
    <div><div class="filtro-label">Dev Responsável</div><div class="lista-filtro" id="f-dev"></div></div>
    <div><div class="filtro-label">Sistema</div><div class="lista-filtro" id="f-sistema"></div></div>
    <div><div class="filtro-label">Status</div><div class="lista-filtro" id="f-status"></div></div>

    <div class="sidebar-rodape">Atualizado em<br>__ATUALIZADO_EM__</div>
  </aside>

  <main class="conteudo">

  <header class="topo">
    <h1>Visão consolidada</h1>
    <span class="resumo" id="dica-comparacao"></span>
  </header>

  <div class="cards">
    <div class="card total"><div class="valor" id="kpi-total">–</div><div class="label">Total de Chamados</div><div class="delta" id="delta-total"></div></div>
    <div class="card resolvido"><div class="valor" id="kpi-resolvidos">–</div><div class="label">Resolvidos</div><div class="delta" id="delta-resolvidos"></div></div>
    <div class="card andamento"><div class="valor" id="kpi-andamento">–</div><div class="label">Em Andamento</div><div class="delta" id="delta-andamento"></div></div>
    <div class="card pendente" title="Faltando informação ou aguardando resposta do solicitante"><div class="valor" id="kpi-pendentes">–</div><div class="label">Pendentes</div><div class="delta" id="delta-pendentes"></div></div>
    <div class="card"><div class="valor" id="kpi-taxa">–</div><div class="label">Taxa de Resolução</div><div class="delta" id="delta-taxa"></div></div>
  </div>

  <div class="grid-principal">
    <div class="grafico-card"><div id="grafico-status"></div></div>
    <div class="grafico-card"><div id="grafico-responsavel"></div></div>
    <div class="grafico-card"><div id="grafico-dev"></div></div>
    <div class="grafico-card"><div id="grafico-sistema"></div></div>
    <div class="grafico-card full"><div id="grafico-mensal"></div></div>
  </div>

  <section class="tabela-card">
    <div class="tabela-topo">
      <h2>Chamados em aberto<span class="qtd" id="qtd-abertos">0</span></h2>
      <input type="search" id="busca" placeholder="Buscar ticket, descrição, sistema, dev..." aria-label="Buscar chamados em aberto">
    </div>
    <div class="tabela-scroll">
      <table>
        <thead>
          <tr><th>Ticket</th><th>Status</th><th>Descrição</th><th>Sistema</th><th>Dev Responsável</th><th>Responsável</th><th>Mês</th><th>TFS</th></tr>
        </thead>
        <tbody id="tabela-corpo"></tbody>
      </table>
      <div class="tabela-vazia" id="tabela-vazia" hidden>Nenhum chamado em aberto com esses filtros.</div>
    </div>
  </section>

  </main>

<script>
const DADOS = __DADOS__;
const ORDEM_MESES = __ORDEM_MESES__;
const COR_PRIMARIA = "__COR_PRIMARIA__";
const COR_RESOLVIDO = "__COR_RESOLVIDO__";
const COR_ANDAMENTO = "__COR_ANDAMENTO__";
const COR_PENDENTE = "__COR_PENDENTE__";
const COR_OUTROS = "__COR_OUTROS__";

// Cada filtro: coluna dos dados, texto da opção "todos" e como ordenar as opções
const FILTROS_DEF = {
  mes:         { coluna: "Mes_Referencia",  todos: "Todos os meses", ordenar: "mes" },
  responsavel: { coluna: "Responsável",     todos: "Todos",          ordenar: "nome" },
  dev:         { coluna: "Dev Responsável", todos: "Todos",          ordenar: "nome" },
  sistema:     { coluna: "Sistema",         todos: "Todos",          ordenar: "nome" },
  status:      { coluna: "Status",          todos: "Todos",          ordenar: "nome" },
};
// "" = sem filtro
const FILTROS = { mes: "", responsavel: "", dev: "", sistema: "", status: "" };
const GRAFICOS = ["grafico-status", "grafico-responsavel", "grafico-dev", "grafico-sistema", "grafico-mensal"];

const FONTE = { family: "Inter, sans-serif", color: "#1F2937", size: 11 };
const CONFIG_BASE = { displayModeBar: false, responsive: true };

const normalizar = s => (s || "").toString().trim().toLowerCase();
const ehResolvido = d => normalizar(d["Status"]) === "resolvido";
const ehAndamento = d => normalizar(d["Status"]) === "em andamento";
// Pendente: faltando informação ou aguardando resposta do solicitante
const ehPendente = d => normalizar(d["Status"]) === "pendente";

function corDoStatus(nome) {
  const n = normalizar(nome);
  if (n === "resolvido") return COR_RESOLVIDO;
  if (n === "em andamento") return COR_ANDAMENTO;
  if (n === "pendente") return COR_PENDENTE;
  return COR_OUTROS;
}

function titulo(texto) {
  return { text: texto, font: { size: 14 } };
}

// trocas: substitui filtros pontualmente, ex: { mes: "" } ignora o mês
function filtrarDados(trocas) {
  const f = Object.assign({}, FILTROS, trocas || {});
  return DADOS.filter(d => Object.keys(FILTROS_DEF).every(k => !f[k] || d[FILTROS_DEF[k].coluna] === f[k]));
}

function metricas(dados) {
  const total = dados.length;
  const resolvidos = dados.filter(ehResolvido).length;
  const pendentes = dados.filter(ehPendente).length;
  return {
    total: total,
    resolvidos: resolvidos,
    pendentes: pendentes,
    // Qualquer outro status não resolvido conta como em andamento, para os
    // cartões sempre somarem o total
    andamento: total - resolvidos - pendentes,
    taxa: total ? Math.round((resolvidos / total) * 1000) / 10 : 0,
  };
}

// ---------- Filtros ----------

function itemFiltro(chave, valor, texto, qtd) {
  const botao = document.createElement("button");
  botao.type = "button";
  botao.className = "filtro-item" + (FILTROS[chave] === valor ? " ativo" : "");
  botao.dataset.chave = chave;
  botao.dataset.valor = valor;
  botao.title = texto;
  botao.setAttribute("aria-pressed", FILTROS[chave] === valor);
  const nome = document.createElement("span");
  nome.className = "nome";
  nome.textContent = texto;
  const contador = document.createElement("span");
  contador.className = "qtd";
  contador.textContent = qtd;
  botao.append(nome, contador);
  return botao;
}

// Remonta os itens de cada filtro com a contagem de chamados, considerando
// os OUTROS filtros ativos (ex: com um dev selecionado, os meses mostram
// quantos chamados aquele dev teve em cada mês). Itens sem chamados somem.
function atualizarListas() {
  Object.entries(FILTROS_DEF).forEach(([chave, def]) => {
    const base = filtrarDados({ [chave]: "" });
    const contagem = {};
    base.forEach(d => {
      const v = d[def.coluna];
      if (v) contagem[v] = (contagem[v] || 0) + 1;
    });

    const valores = def.ordenar === "mes"
      ? ORDEM_MESES.filter(m => m in contagem)
      : Object.keys(contagem).sort((a, b) => a.localeCompare(b, "pt-BR"));
    // Mantém o item selecionado visível mesmo que fique com 0 chamados
    if (FILTROS[chave] && !valores.includes(FILTROS[chave])) valores.push(FILTROS[chave]);

    const frag = document.createDocumentFragment();
    frag.appendChild(itemFiltro(chave, "", def.todos, base.length));
    valores.forEach(v => frag.appendChild(itemFiltro(chave, v, v, contagem[v] || 0)));
    document.getElementById("f-" + chave).replaceChildren(frag);
  });

  document.getElementById("limpar").hidden = !Object.values(FILTROS).some(Boolean);
}

function definirFiltro(chave, valor) {
  FILTROS[chave] = valor;
  salvarNoLink();
  aplicarFiltro();
}

// Guarda os filtros no endereço (#mes=09%2F2026&dev=...), para que recarregar
// a página ou compartilhar o link mantenha a seleção
function salvarNoLink() {
  const params = new URLSearchParams();
  Object.entries(FILTROS).forEach(([k, v]) => { if (v) params.set(k, v); });
  const hash = params.toString();
  try {
    history.replaceState(null, "", hash ? "#" + hash : location.pathname + location.search);
  } catch (e) { /* alguns navegadores bloqueiam em arquivos locais */ }
}

function lerDoLink() {
  const params = new URLSearchParams(location.hash.slice(1));
  Object.entries(FILTROS_DEF).forEach(([chave, def]) => {
    const v = params.get(chave);
    if (v && DADOS.some(d => d[def.coluna] === v)) FILTROS[chave] = v;
  });
}

// ---------- Cartões com comparação ----------

function mesAtualTexto() {
  const hoje = new Date();
  return String(hoje.getMonth() + 1).padStart(2, "0") + "/" + hoje.getFullYear();
}

// sobeEhBom: se um aumento é positivo (verde), negativo (vermelho) ou
// null quando não é nem bom nem ruim (cor neutra)
// emPontos: compara em pontos percentuais (taxa) em vez de variação %
function renderDelta(elId, atual, anterior, mesAnterior, sobeEhBom, emPontos) {
  const el = document.getElementById(elId);
  el.textContent = "";
  if (anterior === null) return;

  let diferenca, texto;
  if (emPontos) {
    diferenca = Math.round((atual - anterior) * 10) / 10;
    texto = Math.abs(diferenca).toLocaleString("pt-BR") + " p.p.";
  } else {
    if (anterior === 0) return;
    diferenca = Math.round(((atual - anterior) / anterior) * 100);
    texto = Math.abs(diferenca) + "%";
  }

  const seta = diferenca > 0 ? "▲ " : diferenca < 0 ? "▼ " : "= ";
  const classe = diferenca === 0 || sobeEhBom === null ? "neutro"
    : (diferenca > 0) === sobeEhBom ? "bom" : "ruim";

  const span = document.createElement("span");
  span.className = classe;
  span.textContent = seta + texto;
  el.appendChild(span);
  el.appendChild(document.createTextNode(" vs " + mesAnterior));
}

function atualizarCartoes(dados) {
  const atual = metricas(dados);
  document.getElementById("kpi-total").textContent = atual.total;
  document.getElementById("kpi-resolvidos").textContent = atual.resolvidos;
  document.getElementById("kpi-andamento").textContent = atual.andamento;
  document.getElementById("kpi-pendentes").textContent = atual.pendentes;
  document.getElementById("kpi-taxa").textContent = atual.taxa.toLocaleString("pt-BR") + "%";

  const idx = ORDEM_MESES.indexOf(FILTROS.mes);
  const mesAnterior = idx > 0 ? ORDEM_MESES[idx - 1] : null;
  const ant = mesAnterior ? metricas(filtrarDados({ mes: mesAnterior })) : null;

  // Volume de chamados não é "bom" nem "ruim": cor neutra
  renderDelta("delta-total", atual.total, ant ? ant.total : null, mesAnterior, null, false);
  renderDelta("delta-resolvidos", atual.resolvidos, ant ? ant.resolvidos : null, mesAnterior, true, false);
  renderDelta("delta-andamento", atual.andamento, ant ? ant.andamento : null, mesAnterior, false, false);
  // Pendências dependem do solicitante, não da equipe: cor neutra
  renderDelta("delta-pendentes", atual.pendentes, ant ? ant.pendentes : null, mesAnterior, null, false);
  renderDelta("delta-taxa", atual.taxa, ant ? ant.taxa : null, mesAnterior, true, true);

  const dica = document.getElementById("dica-comparacao");
  if (!FILTROS.mes) {
    dica.textContent = "Escolha um mês para comparar com o anterior";
  } else if (!mesAnterior) {
    dica.textContent = "Primeiro mês da série: sem comparação";
  } else if (FILTROS.mes === mesAtualTexto()) {
    dica.textContent = "Mês em andamento: comparação parcial com " + mesAnterior;
  } else {
    dica.textContent = "";
  }
}

// ---------- Gráficos ----------

function renderStatus(elId, dados) {
  const contagem = {};
  dados.forEach(d => {
    const s = (d["Status"] || "").trim();
    if (s) contagem[s] = (contagem[s] || 0) + 1;
  });
  const lista = Object.entries(contagem).sort((a, b) => b[1] - a[1]);
  Plotly.react(elId, [{
    labels: lista.map(l => l[0]),
    values: lista.map(l => l[1]),
    type: "pie", hole: 0.45, sort: false,
    marker: { colors: lista.map(([nome]) => corDoStatus(nome)) },
    textinfo: "percent", textfont: { size: 11 },
  }], {
    font: FONTE, paper_bgcolor: "rgba(0,0,0,0)", separators: ",.",
    title: titulo("Chamados por Status"),
    margin: { t: 36, l: 8, r: 8, b: 8 }, autosize: true,
    legend: { orientation: "h", y: -0.05, font: { size: 10 } },
  }, CONFIG_BASE);
}

function encurtar(texto, max) {
  return texto.length > max ? texto.slice(0, max - 1) + "…" : texto;
}

// Barras horizontais empilhadas por status, maior no topo
function renderBarraStatus(elId, dados, campo, textoTitulo) {
  const grupos = {};
  dados.forEach(d => {
    const chave = (d[campo] || "").toString().trim();
    if (!chave) return;
    const g = grupos[chave] || (grupos[chave] = { res: 0, and: 0, pen: 0, out: 0 });
    if (ehResolvido(d)) g.res++;
    else if (ehAndamento(d)) g.and++;
    else if (ehPendente(d)) g.pen++;
    else g.out++;
  });

  let lista = Object.entries(grupos)
    .map(([nome, g]) => ({ nome: nome, ...g, total: g.res + g.and + g.pen + g.out }))
    .sort((a, b) => b.total - a.total);

  // Segurança para quando houver muitas categorias: junta o resto em "Outros"
  const LIMITE = 10;
  if (lista.length > LIMITE) {
    const resto = lista.slice(LIMITE - 1);
    const soma = k => resto.reduce((s, x) => s + x[k], 0);
    lista = lista.slice(0, LIMITE - 1).concat([{
      nome: "Outros (" + resto.length + ")", res: soma("res"), and: soma("and"), pen: soma("pen"), out: soma("out"), total: soma("total"),
    }]);
  }

  const nomes = lista.map(x => encurtar(x.nome, 22));
  const hover = lista.map(x => x.nome);
  const barra = (nomeSerie, chave, cor) => ({
    type: "bar", orientation: "h", name: nomeSerie,
    y: nomes, x: lista.map(x => x[chave]), customdata: hover,
    marker: { color: cor },
    hovertemplate: "%{customdata}<br>" + nomeSerie + ": %{x}<extra></extra>",
  });

  const traces = [
    barra("Resolvido", "res", COR_RESOLVIDO),
    barra("Em andamento", "and", COR_ANDAMENTO),
  ];
  if (lista.some(x => x.pen > 0)) traces.push(barra("Pendente", "pen", COR_PENDENTE));
  if (lista.some(x => x.out > 0)) traces.push(barra("Outros status", "out", COR_OUTROS));

  // Total escrito no fim de cada barra
  traces.push({
    type: "scatter", mode: "text", y: nomes, x: lista.map(x => x.total),
    text: lista.map(x => " " + x.total), textposition: "middle right",
    textfont: { size: 10, color: "#374151" }, hoverinfo: "skip", showlegend: false, cliponaxis: false,
  });

  Plotly.react(elId, traces, {
    font: FONTE, plot_bgcolor: "white", paper_bgcolor: "rgba(0,0,0,0)",
    title: titulo(textoTitulo),
    // Com poucas categorias, mais espaço entre as barras evita barras gigantes
    barmode: "stack", bargap: lista.length < 5 ? 0.55 : 0.3, autosize: true, showlegend: false,
    margin: { t: 36, l: 8, r: 36, b: 8 },
    xaxis: { visible: false, rangemode: "tozero" },
    yaxis: { automargin: true, autorange: "reversed", tickfont: { size: 10 }, ticksuffix: " " },
  }, CONFIG_BASE);
}

function renderMensal(elId, dados) {
  const contagem = {};
  dados.forEach(d => {
    const mes = d["Mes_Referencia"];
    if (mes) contagem[mes] = (contagem[mes] || 0) + 1;
  });
  const meses = ORDEM_MESES.filter(m => m in contagem);
  const totais = meses.map(m => contagem[m]);

  Plotly.react(elId, [{
    x: meses, y: totais,
    type: "scatter", mode: "lines+markers+text",
    // Linha reta: a "spline" suavizada inventava picos entre os meses
    line: { shape: "linear", color: COR_PRIMARIA, width: 3 },
    marker: { size: meses.map(m => m === FILTROS.mes ? 12 : 7), color: COR_PRIMARIA },
    text: totais, textposition: "top center",
    textfont: { size: 10, color: "#1F2937" }, cliponaxis: false,
  }], {
    font: FONTE, plot_bgcolor: "white", paper_bgcolor: "rgba(0,0,0,0)",
    title: titulo("Volume de Chamados por Mês"), autosize: true,
    xaxis: { showgrid: false, tickfont: { size: 10 }, type: "category" },
    yaxis: { showgrid: true, gridcolor: "#F3F4F6", zeroline: false, tickfont: { size: 10 }, rangemode: "tozero" },
    margin: { t: 36, l: 32, r: 16, b: 32 },
  }, CONFIG_BASE);
}

// ---------- Tabela de chamados em aberto (em andamento + pendentes) ----------

function linkSeguro(url) {
  // Só aceita http(s): bloqueia "javascript:" e afins vindos da planilha
  return /^https?:\\/\\//i.test(url || "") ? url : "";
}

function renderTabela(dados) {
  const termo = normalizar(document.getElementById("busca").value);
  const posicaoMes = m => ORDEM_MESES.indexOf(m);

  const abertos = dados
    .filter(d => !ehResolvido(d))
    .filter(d => !termo || ["Ticket ID", "Descrição", "Sistema", "Dev Responsável", "Responsável", "Status"]
      .some(c => normalizar(d[c]).includes(termo)))
    .sort((a, b) =>
      posicaoMes(a["Mes_Referencia"]) - posicaoMes(b["Mes_Referencia"]) ||
      (parseInt(a["Ticket ID"], 10) || 0) - (parseInt(b["Ticket ID"], 10) || 0));

  document.getElementById("qtd-abertos").textContent = abertos.length;
  document.getElementById("tabela-vazia").hidden = abertos.length > 0;

  const corpo = document.getElementById("tabela-corpo");
  const frag = document.createDocumentFragment();
  abertos.forEach(d => {
    const tr = document.createElement("tr");
    const celula = (texto, classe) => {
      const td = document.createElement("td");
      td.textContent = texto || "";
      if (classe) td.className = classe;
      tr.appendChild(td);
      return td;
    };
    celula(d["Ticket ID"], "ticket");
    const selo = document.createElement("span");
    selo.className = "selo " + (ehPendente(d) ? "pendente" : ehAndamento(d) ? "andamento" : "outro");
    selo.textContent = d["Status"] || "Sem status";
    celula("").appendChild(selo);
    celula(d["Descrição"]);
    celula(d["Sistema"], "nowrap");
    celula(d["Dev Responsável"], "nowrap");
    celula(d["Responsável"], "nowrap");
    celula(d["Mes_Referencia"], "nowrap");
    const tdLink = celula("");
    const url = linkSeguro(d["Link TFS"]);
    if (url) {
      const a = document.createElement("a");
      a.href = url; a.target = "_blank"; a.rel = "noopener noreferrer";
      a.textContent = "Abrir ↗";
      tdLink.appendChild(a);
    }
    frag.appendChild(tr);
  });
  corpo.replaceChildren(frag);
}

// ---------- Orquestração ----------

function aplicarFiltro() {
  const dados = filtrarDados();
  atualizarListas();
  atualizarCartoes(dados);
  renderStatus("grafico-status", dados);
  renderBarraStatus("grafico-responsavel", dados, "Responsável", "Chamados por Responsável");
  renderBarraStatus("grafico-dev", dados, "Dev Responsável", "Chamados por Dev Responsável");
  renderBarraStatus("grafico-sistema", dados, "Sistema", "Chamados por Sistema");
  renderMensal("grafico-mensal", filtrarDados({ mes: "" }));
  renderTabela(dados);
}

// Um único "ouvinte" na sidebar, já que os itens são recriados a cada filtro
document.querySelector(".sidebar").addEventListener("click", e => {
  const item = e.target.closest(".filtro-item");
  if (item) definirFiltro(item.dataset.chave, item.dataset.valor);
});

document.getElementById("limpar").addEventListener("click", () => {
  Object.keys(FILTROS).forEach(k => FILTROS[k] = "");
  salvarNoLink();
  aplicarFiltro();
});

document.getElementById("busca").addEventListener("input", () => renderTabela(filtrarDados()));

// Garante o tamanho certo depois que a fonte e o layout terminam de carregar
window.addEventListener("load", () => GRAFICOS.forEach(id => Plotly.Plots.resize(id)));

lerDoLink();
aplicarFiltro();
</script>
</body>
</html>"""
