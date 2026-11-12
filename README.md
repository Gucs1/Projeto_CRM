# Nexo CRM de Orçamentos

Aplicação web local para administrar clientes, produtos e serviços, propostas comerciais e oportunidades. Foi construída em Flask e SQLite, com páginas renderizadas em Jinja, estilos Tailwind CSS e geração de PDF em ReportLab.

> **Uso pretendido:** demonstração e portfólio em ambiente local. O projeto não está preparado para hospedar publicamente ou tratar dados reais sem uma revisão de segurança, privacidade e operação.

## O que o sistema oferece

- **Contas e acesso:** cadastro de conta, login/logout, senhas armazenadas com hash, sessões limitadas, proteção CSRF, validação no servidor e limitação temporária de tentativas de login.
- **Separação entre contas:** cada usuário acessa seus próprios clientes, produtos, orçamentos, detalhes e PDFs.
- **Clientes:** cadastro, edição, exclusão permitida pelas regras do histórico, pesquisa e consulta do histórico de propostas.
- **Produtos e serviços:** catálogo com descrição e preço unitário; os valores são validados e recalculados no servidor.
- **Orçamentos/oportunidades:** seleção de cliente e múltiplos itens, quantidades, observações, total calculado no servidor, status (Enviado, Aprovado, Recusado) e prioridade (Baixa, Média, Alta). O padrão de prioridade é Média.
- **PDF:** proposta com dados da empresa configurados localmente, cliente, itens, data, status, prioridade e total.
- **Dashboard:** contagem de orçamentos por status e acesso às áreas do CRM.
- **Experiência de uso:** layout responsivo, navegação por teclado, respeito à preferência de movimento reduzido, mensagens de feedback e tela de autenticação com alternância entre entrar e criar conta.
- **Operação local:** inicialização do banco e migrações compatíveis com dados existentes; rota `/health` para checagem local; logs estruturados com identificador de requisição.

## Conceitos da palestra aplicados ao projeto

Este repositório também registra conceitos de engenharia de software que estudei em uma palestra e apliquei ao próprio CRM. A ideia foi transformar o aprendizado em práticas e código que possam ser consultados e reproduzidos:

- **Harness Engineering e Context Engineering:** preparei instruções, contexto do projeto e critérios de validação para que mudanças assistidas por Codex sigam as regras locais. `AGENTS.md` funciona como guia curto e aponta para a arquitetura e as regras de negócio.
- **Coding Agents e Skills:** a Skill `.agents/skills/crm-change/SKILL.md` descreve um fluxo repetível para implementar alterações. A prioridade Baixa/Média/Alta nos orçamentos foi usada como exercício concreto: a regra aparece na persistência, formulários, listagem, detalhe e PDF, com testes de criação, edição, validação e migração.
- **Arquitetura e regras explícitas:** `docs/architecture.md`, `docs/business-rules.md` e os ADRs registram como o Flask, SQLite, controllers, models, templates e PDFs se relacionam e por que certas decisões foram tomadas.
- **DevEx e onboarding:** o projeto roda localmente com Python e dependências instaladas por `requirements.txt`; Tailwind já vem compilado, então Node não é necessário para usar o CRM. Há instruções de inicialização, health check e script de dados demonstrativos.
- **Observabilidade:** cada requisição recebe `X-Request-ID` e gera logs JSON com campos permitidos para ajudar a investigar falhas sem incluir cookies, corpo de formulário ou dados pessoais nos logs.
- **Qualidade e CI:** testes `unittest`, verificação de dependências e conferência do CSS compilado são executados no GitHub Actions em versões definidas de Python. O workflow valida mudanças, mas não faz deploy.
- **Security Engineering e DevSecOps:** configuração e banco locais ficam fora do Git; o app usa CSRF, hash de senha, isolamento por conta, cabeçalhos de segurança e servidor limitado a `127.0.0.1`. O CI inclui Bandit, pip-audit, npm audit e Gitleaks para cobrir classes diferentes de risco.

Essas práticas ajudam a dar contexto, repetir verificações e perceber regressões. Elas não provam que o sistema é invulnerável nem o tornam pronto para produção. Os módulos, exemplos, decisões e limitações estão descritos em [`docs/engineering/`](docs/engineering/) e nos documentos ligados abaixo.
## Tecnologias

- Python 3.10 ou superior, Flask, Flask-WTF, SQLite, Werkzeug e python-dotenv.
- Templates Jinja e JavaScript sem framework.
- Tailwind CSS 3.4.17. O CSS compilado está versionado; Node.js só é necessário para reconstruí-lo.
- ReportLab para gerar documentos PDF.
- `unittest` para testes; Bandit, pip-audit, npm audit e Gitleaks nas verificações de qualidade/segurança configuradas.

## Requisitos

- Python 3.10+ (o CI está configurado para Python 3.10 e 3.13).
- Git para clonar o repositório e acompanhar alterações.
- Node.js 22 e npm apenas para recompilar o CSS ou executar as verificações do frontend.
- Não é necessário Docker, servidor externo ou conexão com banco remoto para executar localmente.

## Executar localmente

### Windows PowerShell

Na pasta do projeto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

### Windows Prompt de Comando (cmd.exe)

```bat
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python app.py
```

### macOS ou Linux

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Abra `http://127.0.0.1:5000`. O servidor fica restrito ao próprio computador por padrão; `Ctrl+C` encerra o processo.

## Primeira inicialização e conta

Na primeira execução, o aplicativo cria a configuração privada local `config.py`, inicializa `instance/crm.sqlite3`, aplica o schema/migrações e gera uma senha aleatória para o administrador local `admin`. A senha fica no `config.py` local e não deve ser compartilhada nem adicionada ao Git. Entre com essa conta ou use **Criar conta** para registrar uma conta independente.

Esses arquivos são dados locais ignorados pelo Git: não os apague se precisar preservar sua configuração ou banco. Os testes usam bancos temporários.

## Configuração opcional

O uso normal não exige configurar variáveis. Para sobrescrever configurações, copie `.env.example` para `.env` e descomente somente os valores desejados. Mantenha `.env` privado. Entre as opções estão `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `DATABASE_PATH`, `COMPANY_NAME`, `COMPANY_EMAIL`, `COMPANY_PHONE`, `COMPANY_ADDRESS`, `COMPANY_LOGO`, `APP_PORT`, `AUTO_OPEN_BROWSER` e `COOKIE_SECURE`.

- Use uma chave secreta forte e única se definir `SECRET_KEY`.
- Senhas de administrador configuradas manualmente devem ser fortes; não use valores de exemplo.
- Habilite `COOKIE_SECURE` somente quando cookies forem servidos por HTTPS. O servidor embutido do app é para desenvolvimento local.
- `config.example.py` é somente um modelo: substitua os placeholders antes de copiá-lo manualmente. No primeiro início, o próprio app gera `config.py` com valores aleatórios apropriados para uso local.

## Dados demonstrativos

Para inserir registros fictícios na conta administrativa local:

```powershell
python scripts/seed_demo_data.py
```

O script não deve ser usado como fonte de dados reais. O carregamento é idempotente para evitar duplicar a demonstração ao executá-lo novamente.

## Estrutura do projeto

```text
app.py                     Inicialização do Flask e configuração da aplicação
config.example.py          Modelo público; configuração real é local e ignorada
.env.example               Exemplo comentado de variáveis opcionais
db.py                      Conexão, inicialização e migrações SQLite
schema.sql                 Schema inicial do banco
controllers/               Rotas e validação de requisições
models/                    Consultas e regras de persistência
pdf/                       Composição e geração de propostas PDF
templates/                 Páginas e componentes Jinja
static/css/                CSS-fonte, CSS compilado e estilos do produto
static/js/                 Interações do navegador
static/img/                Recursos estáticos
scripts/                   Utilitários locais e dados demonstrativos
tests/                     Testes automatizados unittest
docs/                      Arquitetura, regras de negócio e decisões de engenharia
.agents/skills/             Fluxo reutilizável de mudanças no CRM
.github/workflows/          Verificações automatizadas do GitHub Actions
requirements.txt            Dependências para executar a aplicação
requirements-dev.txt        Dependências adicionais de análise de segurança
package.json                Ferramenta local de compilação Tailwind
```

## Desenvolvimento e validação

### Testes e verificações Python

Ative o ambiente virtual e rode:

```sh
python -m unittest discover -s tests -v
python -m pip check
```

A suíte cobre autenticação, CSRF, isolamento entre contas, migrações, catálogo, fluxo de orçamento, páginas de detalhe e PDFs.

### Recompilar Tailwind (opcional)

Instale Node.js 22 e então:

```sh
npm ci
npm run build:css
```

Para recompilar ao salvar templates/CSS durante o desenvolvimento: `npm run watch:css`.

### Análises de segurança locais

```sh
python -m pip install -r requirements-dev.txt
python -m bandit -r app.py controllers models db.py pdf -ll
npm audit --audit-level=moderate
```

O workflow em `.github/workflows/ci.yml` executa a suíte com Python 3.10 e 3.13, confere dependências, reconstrói o CSS, verifica dependências npm, executa Bandit e pip-audit e varre o histórico Git com Gitleaks. Essas ferramentas ajudam a encontrar problemas conhecidos; não equivalem a auditoria independente ou teste de invasão.

Com o servidor iniciado, `http://127.0.0.1:5000/health` deve responder `{"status":"ok"}` quando Flask e SQLite estiverem operacionais. Respostas incluem `X-Request-ID`; detalhes do formato de logs estão em `docs/engineering/04-observability.md`.

## Segurança, privacidade e limites

- Não comite nem compartilhe `config.py`, `.env`, `instance/`, bancos locais, PDFs gerados ou dados pessoais/comerciais. Verifique também o histórico Git antes de publicar.
- Este repositório não contém credenciais de produção. A senha do administrador é gerada localmente; nunca a publique em README, issue, captura de tela ou commit.
- O app está limitado a `127.0.0.1`; não é configuração de produção. Não o exponha diretamente à internet.
- Ainda faltam recursos operacionais para serviço público, como fluxo de redefinição/verificação de e-mail, MFA, backups e implantação com servidor WSGI/proxy configurado.
- A política/aceite apresentados no produto são demonstrativos, não aconselhamento jurídico nem termos comerciais revisados.
- Antes de publicar, rode o workflow de CI em GitHub e revise os arquivos e o histórico completos. O resultado local não substitui a varredura do Gitleaks no GitHub.

## Documentação adicional

- [`docs/architecture.md`](docs/architecture.md): arquitetura, fluxo de requisição e isolamento de dados.
- [`docs/business-rules.md`](docs/business-rules.md): status, prioridade e regras comerciais.
- [`docs/engineering/`](docs/engineering/): contexto de agentes, DevEx, observabilidade, CI e segurança.
- [`AGENTS.md`](AGENTS.md) e [Skill do CRM](.agents/skills/crm-change/SKILL.md): orientações para mudanças futuras assistidas por Codex.

## Licença

Nenhuma licença de código aberto foi definida neste repositório. Adicione uma licença explícita antes de permitir reutilização ou redistribuição sob termos específicos.
