# Nexo CRM

CRM de demonstração em Flask e SQLite para organizar clientes, catálogo e propostas comerciais. Cada conta mantém seus próprios registros. A interface usa templates Jinja, Tailwind CSS compilado e componentes CSS próprios; propostas são geradas em PDF.

> Este repositório é um exemplo de portfólio para execução local. Não publique uma instância com dados reais sem uma revisão de implantação e privacidade.

## Funcionalidades

- Cadastro de conta com e-mail, aceite de termos e senha com pelo menos 12 caracteres.
- Login, logout, sessão com duração limitada, proteção CSRF e limite para tentativas de senha.
- Clientes, produtos e serviços separados por conta.
- Orçamentos com itens, preço calculado no servidor, histórico, status, prioridade e download PDF.
- Migração automática que preserva o banco antigo e atribui registros legados ao administrador local já configurado.
- Layout responsivo com acesso por teclado e suporte à preferência de movimento reduzido.

## Tecnologias

- Python 3.10+, Flask, Flask-WTF, SQLite, Werkzeug e python-dotenv.
- Jinja e JavaScript sem framework no navegador.
- Tailwind CSS 3.4.17, compilado para `static/css/tailwind.css`.
- ReportLab para geração de PDF.

React/TypeScript não foram adicionados: a aplicação já usa renderização no servidor, e substituir o frontend não traria benefício suficiente para justificar uma segunda arquitetura e processo de build.

## Onboarding local

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

No Prompt de Comando (cmd.exe), a ativação equivalente é `.venv\\Scripts\\activate.bat`. Também é possível pular a ativação e executar `.venv\\Scripts\\python.exe app.py`.

### macOS ou Linux

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

O aplicativo escuta em `127.0.0.1` e abre `http://127.0.0.1:5000/login`. O CSS compilado está incluído no repositório, então não é necessário Node.js para executar o CRM. Não é necessário criar `.env`: `app.py` gera `config.py` privado e o banco local na primeira execução. Copie `.env.example` somente se precisar sobrescrever configurações e descomente apenas as variáveis necessárias.

Na primeira inicialização, o programa cria `config.py` local e `instance/crm.sqlite3`. O usuário administrador é `admin`; sua senha aleatória fica apenas em `config.py` e não é impressa nos logs. Mantenha esse arquivo privado. Para uma conta independente, selecione **Criar conta**.

## Configuração

Se precisar personalizar valores, copie `.env.example` para `.env` e descomente somente as variáveis que deseja definir:

```dotenv
# Opcional: descomente para sobrescrever a chave privada gerada localmente.
# SECRET_KEY=
# ADMIN_USERNAME=admin
# Opcional: deixe comentado para gerar uma senha administrativa aleatória.
# ADMIN_PASSWORD=
# DATABASE_PATH=instance/crm.sqlite3
# COMPANY_NAME=Nexo CRM
# APP_PORT=5000
# AUTO_OPEN_BROWSER=true
# COOKIE_SECURE=false
```

`SECRET_KEY` deve ser aleatória e mantida fora do Git. `COOKIE_SECURE` só deve ser ativada quando houver HTTPS. O arquivo `.env`, `config.py` e o banco local são ignorados pelo Git; `.env.example` não contém segredos e deixa as credenciais opcionais comentadas para evitar senhas de exemplo em uso.

O schema é aplicado automaticamente a cada inicialização. Migrações adicionam proprietário, snapshots, prioridade, aceite dos termos, limite de tentativas e tokens de sessão sem apagar registros. Os dados antigos sem proprietário ficam com o administrador local já configurado; novas contas não recebem dados anteriores.

## CSS do Tailwind

Node.js é necessário somente para alterar templates e recompilar o CSS:

```powershell
npm ci
npm run build:css
```

Para desenvolvimento com recompilação automática:

```powershell
npm run watch:css
```

## Testes

```powershell
python -m unittest discover -s tests -v
```

Os testes cobrem autenticação, CSRF, migração, cadastro, permissões entre contas, páginas de detalhes, catálogo e PDF usando bancos SQLite temporários.

## Verificações de segurança

As ferramentas de segurança ficam fora das dependências necessárias para executar o CRM. Para executar SAST localmente, instale as dependências de desenvolvimento e rode Bandit:

```powershell
python -m pip install -r requirements-dev.txt
python -m bandit -r app.py controllers models db.py pdf -ll
npm audit --audit-level=moderate
```

O GitHub Actions também roda `pip-audit` sobre dependências de runtime e desenvolvimento e Gitleaks sobre o histórico Git. O relatório de observabilidade registra que IDs/rotas não incluem corpo de formulário ou cookies. O CI semanal usa a base pública de advisories; nenhuma chave da aplicação é necessária.

## Verificações locais

Com o servidor em execução, abra `http://127.0.0.1:5000/health`. A resposta `{"status":"ok"}` indica que o processo respondeu e conseguiu executar uma consulta simples ao SQLite. A rota não retorna caminhos nem dados da aplicação.

Cada resposta inclui um cabeçalho `X-Request-ID`. Os eventos JSON no terminal usam o mesmo ID; consulte `docs/engineering/04-observability.md` para correlacionar uma resposta e seu log sem registrar dados de formulário.

```powershell
python -m pip check
git diff --check
```

`pip check` deve informar `No broken requirements found.`; `git diff --check` deve terminar sem apontar whitespace incorreto. Node.js é necessário apenas para recompilar Tailwind, não para executar o CRM.

## Segurança e limitações conhecidas

- O app vincula o servidor a `127.0.0.1`; não há suporte de produção, e-mail verificado, redefinição de senha, MFA ou backup automático.
- Cinco falhas de login em 15 minutos bloqueiam temporariamente novas tentativas daquele endereço IP. Como é um protótipo local, a limitação é persistida em SQLite e não substitui uma solução distribuída para servidor público.
- Um token rotativo no banco invalida sessões antigas quando há novo login ou logout. Cookies usam `HttpOnly` e `SameSite=Lax`; `Secure` depende de HTTPS.
- O código usa SQL parametrizado, escape padrão do Jinja, CSRF em formulários, validação no servidor e cabeçalhos de segurança. Isso reduz riscos comuns, mas não constitui auditoria de segurança independente.
- GitHub Actions verifica dependências Python/Node e roda Bandit e Gitleaks em push, pull request e semanalmente. A varredura automatizada não substitui revisão manual nem teste de invasão.
- A tela registra aceite da política de demonstração; ela não substitui termos legais revisados para uso comercial.
- Os exemplos do repositório são fictícios. Preserve `config.py`, `.env` e `instance/` localmente e não os anexe a issues ou commits.

## Demonstração

Para preencher uma base vazia com registros fictícios, execute:

```powershell
python scripts/seed_demo_data.py
```

Os registros de demonstração são adicionados somente à conta administrativa configurada. Para encerrar o servidor, pressione `Ctrl+C` no terminal.
