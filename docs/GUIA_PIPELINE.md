# Guia da Pipeline — Dashboard de Chamados

Como configurar, rodar e manter a pipeline que transforma a planilha de
chamados em um dashboard atualizado todo dia.

## Sumário

1. [Como funciona](#1-como-funciona)
2. [Configuração inicial (uma vez só)](#2-configuração-inicial-uma-vez-só)
3. [Rodar a pipeline](#3-rodar-a-pipeline)
4. [Agendar a execução diária](#4-agendar-a-execução-diária)
5. [Uso no dia a dia](#5-uso-no-dia-a-dia)
6. [Como conferir se deu certo](#6-como-conferir-se-deu-certo)
7. [Problemas comuns](#7-problemas-comuns)
8. [Segurança e GitHub](#8-segurança-e-github)
9. [Onde mudar cada coisa](#9-onde-mudar-cada-coisa)

---

## 1. Como funciona

```
Google Sheets                 Seu PC (python main.py)               Publicação
─────────────                 ───────────────────────               ──────────
Chamados - 08/2026 ─┐
Chamados - 09/2026 ─┼──► 1. lê as abas mensais
Chamados - 10/2026 ─┘    2. junta tudo e remove Ticket IDs repetidos
                         3. escreve na aba "Consolidado" ──────────► Google Sheets
                         4. gera o dashboard.html
                         5. envia para o Google Drive ─────────────► pasta restrita
                         6. envia para o PythonAnywhere ───────────► link com login
```

| Arquivo | Papel |
|---|---|
| `main.py` | Ponto de entrada: roda as 6 etapas acima, em ordem. |
| `config.py` | Configurações gerais (nome da planilha, padrão das abas). |
| `.env` | Segredos: token, IDs e senhas. **Nunca vai para o GitHub.** |
| `credentials.json` | Chave da conta de serviço do Google. **Nunca vai para o GitHub.** |
| `src/sheets.py` | Lê, consolida e escreve na planilha. |
| `src/dashboard.py` | Gera o `dashboard.html`. |
| `src/drive.py` | Atualiza o `dashboard.html` no Google Drive. |
| `src/hospedagem.py` | Publica o `dashboard.html` no PythonAnywhere. |
| `portal_flask_app.py` | Roda **no PythonAnywhere** e pede login antes de mostrar o dashboard. |
| `rodar_diario.bat` | Usado pelo Agendador de Tarefas do Windows. |
| `configurar_agendamento.ps1` | Configura o Agendador (seg-sex, 9h-17h, a cada 10 min) e o relógio do Windows. |
| `.estado_pipeline.json` | Criado sozinho: guarda a última alteração da planilha já processada. |

As etapas 5 e 6 são independentes: se uma falhar, a outra ainda é tentada.

---

## 2. Configuração inicial (uma vez só)

### 2.1. Python e dependências

1. Instale o Python 3.10 ou mais novo (https://www.python.org/downloads/).
   Na instalação, marque **"Add Python to PATH"**.
2. Abra o terminal na pasta do projeto e instale as dependências:
   ```
   pip install -r requirements.txt
   ```

### 2.2. Conta de serviço do Google

A conta de serviço é um "usuário robô" que o script usa para acessar a
planilha e o Drive.

1. Acesse https://console.cloud.google.com/ e crie um projeto (ou use um existente).
2. Em **APIs e Serviços > Biblioteca**, ative a **Google Sheets API** e a **Google Drive API**.
3. Em **APIs e Serviços > Credenciais > Criar Credenciais > Conta de Serviço**,
   crie uma conta (ex: `dashboard-chamados`). As etapas de permissão de projeto podem ser puladas.
4. Abra a conta criada, vá em **Chaves > Adicionar Chave > Criar nova chave > JSON**.
5. Renomeie o arquivo baixado para `credentials.json` e coloque na pasta do projeto.
6. Copie o **e-mail da conta de serviço** (campo `client_email` do JSON,
   algo como `dashboard-chamados@seu-projeto.iam.gserviceaccount.com`).

### 2.3. Compartilhar a planilha

1. Abra a planilha no navegador → **Compartilhar**.
2. Cole o e-mail da conta de serviço com permissão de **Editor**
   (precisa ser Editor porque o script escreve na aba "Consolidado").
3. Confira se o nome da planilha bate com `SPREADSHEET_NAME` no `.env`.

### 2.4. Pasta do Google Drive

1. Crie uma pasta no Drive (ex: "Dashboard Chamados - Interno").
2. Compartilhe com o e-mail da conta de serviço como **Editor**.
3. Em "Acesso geral", deixe **restrito ao domínio da empresa** (ou só às pessoas do time).
4. **Crie manualmente um arquivo vazio chamado `dashboard.html` dentro dela.**
   Contas de serviço não têm cota de armazenamento: elas só conseguem
   *atualizar* arquivos que já existem, nunca criar novos.
5. Copie o ID da pasta: é o trecho da URL depois de `/folders/`.
   Ex: `https://drive.google.com/drive/folders/1AbCdEf...` → `1AbCdEf...`

> O preview do Google Drive não mostra HTML funcionando, só o código. Para ver o
> dashboard pelo Drive, é preciso baixar o arquivo e abrir no navegador. Para um
> link direto, use o PythonAnywhere (próximo passo).

### 2.5. PythonAnywhere (link fixo com login) — opcional

Se não quiser usar, deixe `PYTHONANYWHERE_USERNAME` e `PYTHONANYWHERE_API_TOKEN`
em branco no `.env` e essa etapa será pulada.

1. Crie uma conta em https://www.pythonanywhere.com/.
2. Em **Account > API token**, gere um token (vai no `.env` local).
3. Na aba **Web**, crie um web app **Flask**. Anote a versão do Python escolhida.
4. Abra um console **Bash** e instale a dependência (troque `3.10` pela sua versão):
   ```bash
   pip3.10 install --user python-dotenv
   ```
5. Na pasta do `flask_app.py` (veja em **Web > Source code**, normalmente
   `/home/SEU_USUARIO/mysite/`), crie um arquivo `.env`:
   ```
   DASHBOARD_USUARIO=usuario_do_time
   DASHBOARD_SENHA='senha_do_time'
   DASHBOARD_CAMINHO=/home/SEU_USUARIO/dashboard.html
   ```
   Use aspas simples na senha se ela tiver `#`, espaços ou aspas.
6. Substitua todo o conteúdo do `flask_app.py` pelo `portal_flask_app.py` deste projeto.
7. Na aba **Web**, clique em **Reload**.

> Não execute o `flask_app.py` pelo botão **Run** ou pelo console: isso só sobe um
> servidor de teste local (`127.0.0.1:5000`). Quem serve o site de verdade é o
> web app, atualizado pelo botão **Reload**.

### 2.6. Arquivo `.env` local

1. Copie o `.env.example` para um arquivo chamado `.env`.
2. Preencha:

| Variável | O que é |
|---|---|
| `GOOGLE_CREDENTIALS_FILE` | Caminho do JSON da conta de serviço (padrão: `credentials.json`). |
| `SPREADSHEET_NAME` | Nome exato da planilha, como aparece no Google Drive. |
| `DRIVE_FOLDER_ID` | ID da pasta do Drive (passo 2.4). |
| `PYTHONANYWHERE_USERNAME` | Seu usuário do PythonAnywhere. |
| `PYTHONANYWHERE_API_TOKEN` | Token da API (passo 2.5). |
| `PYTHONANYWHERE_CAMINHO_REMOTO` | Onde o dashboard é salvo lá (ex: `/home/SEU_USUARIO/dashboard.html`). Precisa ser igual ao `DASHBOARD_CAMINHO` do `.env` do PythonAnywhere. |
| `DASHBOARD_USUARIO` / `DASHBOARD_SENHA` | Não são usados no seu PC, só ficam guardados aqui como referência para o `.env` do PythonAnywhere. |

---

## 3. Rodar a pipeline

Na pasta do projeto:

```
python main.py            # execução automática: respeita horário e só roda se a planilha mudou
python main.py --forcar   # roda tudo agora, sem checagens (use depois de mudar o código)
```

Sem `--forcar`, o script primeiro faz duas checagens rápidas:

1. **Horário:** só segue de segunda a sexta, das 9h às 17h de Campo Grande/MS.
   Fora disso, escreve `Fora do horário... Nada a fazer.` e termina.
2. **Alteração:** consulta no Google a data da última modificação da planilha
   (sem ler os dados) e compara com a guardada em `.estado_pipeline.json`.
   Se for igual, escreve `Planilha sem alterações. Nada a fazer.` e termina.

A aba "Consolidado" só é reescrita quando o conteúdo realmente mudou, para a
escrita do próprio script não contar como "alteração" na checagem seguinte.
Se algum envio falhar, o estado não é salvo e a próxima execução tenta de novo.

Saída esperada quando há alterações:

```
[2026-10-01 10:00:16] Iniciando consolidação...
  -> Lida: 'Chamados - 08/2026' (507 linhas)
  -> Lida: 'Chamados - 09/2026' (335 linhas)
  Diagnóstico: 842 linhas lidas ao todo -> 842 linhas após remover duplicados.
Dashboard HTML gerado em: dashboard.html
Dashboard atualizado no Google Drive (arquivo existente: ...).
Dashboard publicado no PythonAnywhere (200).
Concluído: 842 linhas consolidadas na aba 'Consolidado'.
```

O script termina com **código 0** se tudo deu certo e **código 1** se algum envio
falhou. Erros na leitura ou escrita da planilha interrompem a execução e mostram
o erro completo.

---

## 4. Agendar a execução automática

A tarefa roda **a cada 10 minutos, de segunda a sexta, das 9h às 17h**. Como o
script só processa algo quando a planilha mudou, o dashboard fica no máximo
~10 minutos atrás da planilha nesse horário.

Para configurar, abra o PowerShell **como administrador** e rode:

```
powershell -ExecutionPolicy Bypass -File C:\Dashboard_Chamados\configurar_agendamento.ps1
```

O script `configurar_agendamento.ps1`:

- ajusta o fuso do Windows para **Campo Grande/MS** ("(UTC-04:00) Cuiabá") e liga
  a sincronização automática do relógio;
- cria ou atualiza a tarefa **"Dashboard de Chamados"** no Agendador: seg-sex,
  a cada 10 min das 9h às 17h, **sem abrir janela**, com limite de 10 minutos
  por execução (uma execução travada não bloqueia as seguintes).

Para mudar o intervalo ou o horário, edite as variáveis no topo do script e
rode de novo. O horário também é checado pelo `main.py` (`HORA_INICIO`,
`HORA_FIM` e `DIAS_EXECUCAO` no `config.py`): mantenha os dois iguais.

Para testar agora: no Agendador, botão direito na tarefa → **Executar**, e
veja a última linha do `log_execucao.txt`.

> O nome `rodar_diario.bat` ficou do agendamento antigo (1x por dia). Ele
> continua sendo o arquivo usado pela tarefa.

Sobre o `rodar_diario.bat`:
- Se a pasta do projeto não for `C:\Dashboard_Chamados`, ajuste o caminho no `cd /d`.
- A saída de cada execução é acrescentada ao `log_execucao.txt`.
- Quando o log passa de ~1 MB, ele vira `log_execucao.old.txt` e um novo começa.
- Se a pipeline falhar, a tarefa aparece com resultado diferente de `0x0` no Agendador.

O PC precisa estar ligado (e com o usuário logado, dependendo de como a tarefa
foi criada) no horário agendado.

---

## 5. Uso no dia a dia

### Mês novo

Não precisa mexer no código. Basta criar a aba do mês na planilha seguindo o padrão:

```
Chamados - MM/AAAA        ex: Chamados - 11/2026
```

O padrão é definido por `SHEET_PATTERN` no `config.py`. Abas com outro nome
(incluindo a própria "Consolidado") são ignoradas.

### Estrutura das abas mensais

- A **primeira linha** é o cabeçalho.
- Colunas usadas pelo dashboard: `Ticket ID`, `Status`, `Sistema`,
  `Responsável`, `Dev Responsável`, `Descrição` e `Link TFS`. Os nomes precisam
  ser **exatamente** esses.
- Linhas **sem `Ticket ID`** são descartadas (são linhas vazias com formatação).
- Colunas sem cabeçalho são ignoradas.
- Status reconhecidos (sem diferenciar maiúsculas/minúsculas):
  - `Resolvido`
  - `Em andamento`
  - `Pendente`: faltando informação ou aguardando resposta do solicitante.

  Qualquer outro status conta como "Em Andamento" nos cartões.

### Ticket ID repetido

Se o mesmo `Ticket ID` aparece em mais de uma linha, fica só a ocorrência do
**mês mais recente**. O log avisa quais IDs estavam repetidos:

```
ATENÇÃO: 2 Ticket ID(s) aparecem em mais de uma linha: ['153146', '182708']
```

Vale corrigir esses casos na planilha.

### Aba "Consolidado"

É sobrescrita a cada execução. **Não edite nada nela à mão**: as alterações se
perdem na próxima rodada. Edite sempre as abas mensais.

### Usando o dashboard

- **Filtros na barra lateral:** mês, responsável, dev responsável, sistema e
  status. Eles se combinam (ex: setembro + um dev específico). O número ao lado
  de cada item é a quantidade de chamados considerando os outros filtros.
  **Limpar filtros** volta tudo para "Todos".
- **Link com filtros:** os filtros ficam salvos no endereço da página. Dá para
  recarregar (F5) ou mandar o link para alguém já filtrado.
- **Cartões:** total, resolvidos, em andamento, pendentes e taxa de resolução.
  Com um mês selecionado, mostram a variação em relação ao mês anterior
  (verde = melhorou, vermelho = piorou, cinza = neutro).
- **Barras por responsável, dev e sistema:** divididas por status.
- **Volume por Mês:** respeita os outros filtros, mas sempre mostra todos os
  meses, destacando o mês selecionado.
- **Chamados em aberto:** tabela com os chamados em andamento e pendentes,
  com busca e link para o TFS. Os mais antigos aparecem primeiro.
- **Celular:** a barra de filtros vai para o topo e a página rola.
- A data de "Atualizado em" (horário de Campo Grande) fica no rodapé da barra lateral.

---

## 6. Como conferir se deu certo

1. **Log:** abra o `log_execucao.txt` e veja se a última execução termina com
   `Concluído: ...` e sem linhas `ERRO`.
2. **Planilha:** a aba "Consolidado" tem o número de linhas informado no log.
3. **Drive:** a data de modificação do `dashboard.html` na pasta é de hoje.
4. **PythonAnywhere:** abra o link, faça login e confira o "Atualizado em".

---

## 7. Problemas comuns

| Mensagem / sintoma | Causa provável | Solução |
|---|---|---|
| `FileNotFoundError: credentials.json` | O arquivo não está na pasta ou o caminho no `.env` está errado. | Confira `GOOGLE_CREDENTIALS_FILE` no `.env`. |
| `SpreadsheetNotFound` | Nome errado ou planilha não compartilhada com a conta de serviço. | Confira `SPREADSHEET_NAME` no `.env` e o passo 2.3. |
| `Nenhuma aba encontrada com o padrão...` | Nenhuma aba segue `Chamados - MM/AAAA`. | Renomeie as abas ou ajuste `SHEET_PATTERN`. |
| `DRIVE_FOLDER_ID não configurado` | Falta o ID no `.env`. | Passo 2.4 e 2.6. |
| `O arquivo 'dashboard.html' ainda não existe na pasta do Drive` | A conta de serviço não pode criar arquivos. | Crie o `dashboard.html` vazio na pasta manualmente. |
| `HttpError 403` no Drive | Pasta não compartilhada com a conta de serviço como Editor. | Passo 2.4. |
| `Falha ao publicar no PythonAnywhere: 401` | Token inválido ou trocado. | Gere outro token e atualize o `.env`. |
| `Falha ao publicar no PythonAnywhere: 403/404` | Usuário ou caminho remoto errado. | Confira `PYTHONANYWHERE_USERNAME` e `PYTHONANYWHERE_CAMINHO_REMOTO`. |
| Timeout no PythonAnywhere | Sem internet ou serviço fora do ar. | Rode de novo mais tarde. O Drive é atualizado mesmo assim. |
| Site mostra "Something went wrong" | Erro no `flask_app.py`. | Veja o **Error log** na aba Web do PythonAnywhere. |
| Error log: `Defina DASHBOARD_USUARIO e DASHBOARD_SENHA` | O `.env` do PythonAnywhere não foi encontrado. | Ele precisa estar na mesma pasta do `flask_app.py`. |
| Error log: `No module named 'dotenv'` | Falta a dependência no PythonAnywhere. | Passo 2.5, item 4 (versão do `pip` = versão do web app). |
| Site mostra "Dashboard ainda não foi publicado" | Caminhos diferentes nos dois lados. | `DASHBOARD_CAMINHO` (lá) precisa ser igual a `PYTHONANYWHERE_CAMINHO_REMOTO` (aqui). |
| Agendador não roda / log não muda | `python` fora do PATH ou caminho do `.bat` errado. | Rode o `.bat` com dois cliques para ver o erro. Ajuste o `cd /d`. |
| Log só mostra `Planilha sem alterações` | Normal: ninguém editou a planilha desde a última atualização. | Para forçar: `python main.py --forcar`. |
| Log mostra `Fora do horário` em pleno expediente | Relógio ou fuso do Windows errado. | Rode o `configurar_agendamento.ps1` como administrador. |
| `Set-ScheduledTask : Acesso negado` | A tarefa foi criada como administrador. | Rode o PowerShell como administrador. |
| Mudei o código do dashboard e nada mudou | A planilha não foi alterada, então o script não regerou o HTML. | `python main.py --forcar`. |
| Nome duplicado nos filtros (ex: "joão" e "João") | Digitação diferente na planilha. | Padronize na planilha (uma lista suspensa ajuda). |

---

## 8. Segurança e GitHub

- **Nunca** vão para o GitHub: `.env`, `credentials.json`, `dashboard.html`
  (tem dados reais) e `log_execucao*.txt`. Todos já estão no `.gitignore`.
- Antes do primeiro commit, rode `git status` e confirme que nenhum deles aparece.
- O `.env.example` pode ir para o GitHub: ele só tem os nomes das variáveis.
- Se o token ou a senha vazarem, gere um token novo no PythonAnywhere e troque a
  senha no `.env` de lá (depois clique em **Reload**).
- Se o `credentials.json` vazar, apague a chave no Google Cloud
  (**Conta de serviço > Chaves**) e gere outra.

---

## 9. Onde mudar cada coisa

| Quero mudar... | Onde |
|---|---|
| Nome da planilha | `SPREADSHEET_NAME` no `.env` |
| Padrão do nome das abas | `SHEET_PATTERN` no `config.py` |
| Nome da aba de destino | `CONSOLIDATED_SHEET_NAME` no `config.py` |
| Pasta do Drive | `DRIVE_FOLDER_ID` no `.env` |
| Token / usuário do PythonAnywhere | `.env` local |
| Login e senha do dashboard | `.env` do PythonAnywhere + **Reload** |
| Horário / intervalo da execução | Variáveis no topo do `configurar_agendamento.ps1` **e** `HORA_INICIO` / `HORA_FIM` / `DIAS_EXECUCAO` no `config.py` |
| Cores, gráficos e cartões do dashboard | `src/dashboard.py` |
| Colunas usadas no dashboard | `COLUNAS_UTEIS` no `src/dashboard.py` |
