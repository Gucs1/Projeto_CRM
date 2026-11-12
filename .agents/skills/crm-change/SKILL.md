---
name: crm-change
description: Use when planning or implementing a feature or behavior change in this Flask and SQLite CRM, especially database, quote, client, product, UI, or PDF work.
---

# Mudanças no CRM

Use esta sequência para manter o comportamento compreensível e verificável.

1. Leia `AGENTS.md`, `docs/architecture.md` e as regras relevantes de `docs/business-rules.md` antes de propor alterações.
2. Confirme o escopo da fase autorizada. Explique em português o que será mudado e por que cada mudança ajuda o usuário ou protege os dados.
3. Siga as fronteiras existentes: rota e validação HTTP em `controllers/`, regra/persistência em `models/`, estrutura SQLite em `schema.sql`/`db.py`, interface em `templates/`, PDF em `pdf/`.
4. Para mudanças de dados, use SQL parametrizado, transação e migração idempotente que preserve os registros existentes. Cubra schema novo e upgrade de banco legado com testes temporários.
5. Valide a entrada no servidor mesmo quando a interface também oferece validação. Proteja rotas e mutações com a autenticação e CSRF já existentes.
6. Adicione testes `unittest` para o caminho feliz, valores inválidos, acesso não autenticado e compatibilidade/migração quando aplicável. Execute `python -m unittest discover -s tests -v` e `git diff --check`.
7. Revise o diff e o status; não inclua `config.py`, `instance/`, ambientes virtuais nem dados de clientes. Faça commit apenas dos arquivos relacionados à fase autorizada.
8. Ao concluir uma fase, informe mudanças, motivos, testes e hash do commit. Pare e aguarde autorização explícita antes de iniciar a fase seguinte.

## Contas e isolamento de dados

Ao criar ou alterar rotas de clientes, produtos ou orçamentos, propague o ID do usuário autenticado até o modelo e filtre todas as consultas por esse ID. Inclua testes de acesso cruzado para listagem, detalhe, histórico, PDF e mutações. Não exponha o servidor fora do loopback sem solicitação e revisão específicas.

## Exemplo de aplicação

Ao adicionar prioridade à oportunidade, confirme que orçamento é a oportunidade do CRM, documente os níveis e o padrão, migre registros existentes sem apagá-los, valide valores no servidor e cubra criação, edição, listagem, PDF e migração com testes.
