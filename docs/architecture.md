# Arquitetura do CRM

## Visão geral

Aplicação web local de processo único: Flask atende a interface no endereço de loopback, SQLite guarda os registros e ReportLab gera propostas PDF em memória. Não há serviço remoto de aplicação ou banco.

## Caminho de uma requisição

1. `app.py` carrega a configuração local, inicializa o banco, registra os Blueprints, configura sessão e proteção CSRF.
2. Uma rota em `controllers/` autentica a ação, valida entrada HTTP e chama funções do domínio/persistência em `models/`.
3. O modelo consulta ou atualiza SQLite por meio de `db.py`, usando transações e parâmetros SQL.
4. A resposta renderiza um template Jinja em `templates/` ou, para download de proposta, envia bytes produzidos por `pdf/generator.py`.

## Pastas e responsabilidades

- `app.py`, `config.py`, `config.example.py`: construção da aplicação e configuração. `config.py` é local e privado.
- `db.py`, `schema.sql`: conexões, schema inicial, inicialização e migrações compatíveis com dados existentes.
- `controllers/`: autenticação e rotas Flask organizadas por área.
- `models/`: consultas e regras de persistência para usuários, clientes, produtos e orçamentos.
- `templates/`, `static/`: páginas Jinja e recursos da interface. Tailwind é carregado via CDN.
- `pdf/`: composição de propostas PDF com ReportLab.
- `tests/`: testes `unittest`; cada teste que precisa de banco deve usar um SQLite temporário, sem tocar nos dados locais.
- `scripts/`: utilitários locais, como criação idempotente de dados demonstrativos.

## Fluxo comercial atual

Cliente, prioridade e itens do catálogo são selecionados ao criar um orçamento. O modelo valida prioridade e itens, lê os preços vigentes, calcula o total no servidor e guarda snapshots do cliente e dos itens, preservando o que foi proposto mesmo após alterações no cadastro. A prioridade também pode ser alterada na página de detalhes. Status possíveis: Enviado, Aprovado e Recusado. A rota autenticada de PDF usa os snapshots e a prioridade do orçamento.

## Comandos locais

No PowerShell, na raiz do repositório:

```powershell
.\.venv\Scripts\python.exe app.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Se ainda não existir ambiente virtual, crie-o com `py -m venv .venv` e instale `requirements.txt`.
