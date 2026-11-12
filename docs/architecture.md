# Arquitetura do CRM

## Visão geral

Aplicação web local de processo único: Flask atende a interface no endereço de loopback, SQLite guarda os registros e ReportLab gera propostas PDF em memória. Não há serviço remoto de aplicação ou banco.

## Caminho de uma requisição

1. `app.py` carrega a configuração local, inicializa o banco, registra os Blueprints, configura sessão, proteção CSRF e cabeçalhos de segurança.
2. `controllers/auth.py` autentica e cadastra contas. As outras rotas autenticam a ação, validam entrada HTTP e passam o usuário da sessão às funções de `models/`.
3. O modelo consulta ou atualiza SQLite por meio de `db.py`, usando transações e parâmetros SQL.
4. A resposta renderiza um template Jinja em `templates/` ou, para download de proposta, envia bytes produzidos por `pdf/generator.py`.

`GET /health` é uma verificação local mínima: confirma que o processo responde e que o SQLite executa `SELECT 1`. Retorna apenas `ok` ou `unavailable`, sem revelar o caminho do banco ou conteúdo dos registros.

## Pastas e responsabilidades

- `app.py`, `config.py`, `config.example.py`: construção da aplicação e configuração. `config.py` é local e privado.
- `db.py`, `schema.sql`: conexões, schema inicial, inicialização e migrações compatíveis com dados existentes.
- `controllers/`: autenticação e rotas Flask organizadas por área.
- `models/`: consultas e regras de persistência para usuários, clientes, produtos e orçamentos.
- `templates/`, `static/`: páginas Jinja, recursos de interface e CSS do Tailwind compilado. A compilação usa `tailwind.config.js`, `package.json` e gera `static/css/tailwind.css`.
- `pdf/`: composição de propostas PDF com ReportLab.
- `tests/`: testes `unittest`; cada teste que precisa de banco deve usar um SQLite temporário, sem tocar nos dados locais.
- `scripts/`: utilitários locais, como criação idempotente de dados demonstrativos.

## Contas e isolamento

O login aceita o administrador legado ou e-mail normalizado de uma conta criada pela tela de cadastro. Cada cliente, produto e orçamento tem `user_id`; consultas e alterações sempre filtram por esse identificador. A migração atribui dados existentes sem proprietário ao administrador local já configurado, nunca a novas contas, e cria guardas SQLite para manter os vínculos. Senhas ficam como hash, falhas de login são limitadas por endereço local e um token rotativo no banco permite invalidar sessões antigas. Configuração pode vir de `.env`; nunca versionar `.env` ou `config.py`. O aplicativo escuta apenas em `127.0.0.1`.

## Fluxo comercial atual

Cliente, prioridade e itens do catálogo são selecionados ao criar um orçamento. O modelo valida prioridade e itens, lê os preços vigentes, calcula o total no servidor e guarda snapshots do cliente e dos itens, preservando o que foi proposto mesmo após alterações no cadastro. A prioridade também pode ser alterada na página de detalhes. Status possíveis: Enviado, Aprovado e Recusado. A rota autenticada de PDF usa os snapshots e a prioridade do orçamento.

## Comandos locais

No PowerShell, na raiz do repositório:

```powershell
.\.venv\Scripts\python.exe app.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Se ainda não existir ambiente virtual, crie-o com `py -m venv .venv` e instale `requirements.txt`.
