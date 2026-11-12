# Orientações do repositório

## Contexto

- Este é um CRM local em Flask e SQLite. Orçamento/proposta é a oportunidade comercial; não crie uma entidade separada sem autorização.
- Leia `docs/architecture.md` para localizar responsabilidades e `docs/business-rules.md` antes de alterar comportamentos comerciais.
- Para entender o fluxo de trabalho dos agentes, diferenças entre harness/context/prompt e os ADRs, consulte `docs/engineering/01-harness-context.md`.
- Para mudanças de funcionalidades do CRM, siga a Skill `.agents/skills/crm-change/SKILL.md`.

## Trabalho e validação

- Respeite as fases autorizadas pelo usuário. Conclua apenas a fase atual e peça autorização explícita antes de começar a próxima.
- Explique o motivo de cada mudança funcional em linguagem direta e mantenha documentação/testes alinhados com o comportamento implementado.
- Preserve dados locais. Não leia, altere, imprima ou adicione ao Git `config.py`, `instance/crm.sqlite3`, `.venv` ou dados de clientes sem necessidade explícita.
- Mantenha as mudanças pequenas e compatíveis com os padrões existentes: Flask Blueprints, funções de persistência em `models`, templates Jinja e SQLite parametrizado.
- Alterações de banco devem preservar dados existentes e ser aplicadas de modo idempotente durante a inicialização, com cobertura de teste.
- Valide mudanças com `python -m unittest discover -s tests -v` a partir da raiz do repositório. No Windows, use o Python do ambiente virtual se necessário: `.venv\Scripts\python.exe`.
- Execute `git diff --check`, revise `git status` e faça commits separados conforme as fases autorizadas. Nunca use `git add .`.

## Prioridade de oportunidades

## Contas e segurança

- Cadastro, validação e login ficam em `controllers/auth.py` e `models/user.py`; mantenha CSRF e validação também no servidor.
- Toda consulta de clientes, produtos e orçamentos deve receber o usuário autenticado e filtrar por `user_id`, inclusive detalhe, histórico, PDF e mutações. Cubra tentativa de acesso cruzado nos testes.
- Não vincule o servidor além de `127.0.0.1` sem uma solicitação específica e uma revisão de implantação; este exemplo não é preparado para exposição pública.

- Cada orçamento/proposta é uma oportunidade comercial. A prioridade implementada aceita Baixa, Média ou Alta e usa Média como padrão; confira `docs/business-rules.md` antes de alterar essa regra.
