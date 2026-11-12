# Orientações do repositório

## Contexto

- Este é um CRM local em Flask e SQLite. Orçamento/proposta é a oportunidade comercial; não crie uma entidade separada sem autorização.
- Leia `docs/architecture.md` para localizar responsabilidades e `docs/business-rules.md` antes de alterar comportamentos comerciais.
- Para mudanças de funcionalidades do CRM, siga a Skill `.agents/skills/crm-change/SKILL.md`.

## Trabalho e validação

- Respeite as fases autorizadas pelo usuário. Conclua apenas a fase atual e peça autorização explícita antes de começar a próxima.
- Explique o motivo de cada mudança funcional em linguagem direta e mantenha documentação/testes alinhados com o comportamento implementado.
- Preserve dados locais. Não leia, altere, imprima ou adicione ao Git `config.py`, `instance/crm.sqlite3`, `.venv` ou dados de clientes sem necessidade explícita.
- Mantenha as mudanças pequenas e compatíveis com os padrões existentes: Flask Blueprints, funções de persistência em `models`, templates Jinja e SQLite parametrizado.
- Alterações de banco devem preservar dados existentes e ser aplicadas de modo idempotente durante a inicialização, com cobertura de teste.
- Valide mudanças com `python -m unittest discover -s tests -v` a partir da raiz do repositório. No Windows, use o Python do ambiente virtual se necessário: `.venv\Scripts\python.exe`.
- Execute `git diff --check`, revise `git status` e faça commits separados conforme as fases autorizadas. Nunca use `git add .`.

## Fases já acordadas

- A próxima mudança funcional planejada é prioridade de oportunidade: Baixa, Média e Alta; padrão Média; seleção na criação e edição nos detalhes; exibição nas telas do CRM e no PDF. Só implemente após autorização explícita para essa fase.
