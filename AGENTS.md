# Orientações do repositório

## Contexto

- Este é um CRM local em Flask e SQLite. Orçamento/proposta é a oportunidade comercial; não crie uma entidade separada sem autorização.
- Leia `docs/architecture.md` para localizar responsabilidades e `docs/business-rules.md` antes de alterar comportamentos comerciais.
- Para entender o fluxo de trabalho dos agentes, diferenças entre harness/context/prompt e os ADRs, consulte `docs/engineering/01-harness-context.md`.
- Para mudanças de funcionalidades do CRM, siga a Skill `.agents/skills/crm-change/SKILL.md`.
- Não invente APIs, ferramentas ou dependências: confirme a implementação existente no código e na documentação antes de usá-las; proponha dependências novas com justificativa antes de instalá-las.
- Diferencie sugestões de implementação aprovada. Se o pedido deixar claro que é apenas planejamento ou exercício, não edite arquivos até receber autorização explícita.

## Trabalho e validação

- Respeite as fases autorizadas pelo usuário. Conclua apenas a fase atual e peça autorização explícita antes de começar a próxima.
- Explique o motivo de cada mudança funcional em linguagem direta e mantenha documentação/testes alinhados com o comportamento implementado.
- Preserve dados locais. Não leia, altere, imprima ou adicione ao Git `config.py`, `instance/crm.sqlite3`, `.venv` ou dados de clientes sem necessidade explícita.
- Mantenha as mudanças pequenas e compatíveis com os padrões existentes: Flask Blueprints, funções de persistência em `models`, templates Jinja e SQLite parametrizado.
- Alterações de banco devem preservar dados existentes e ser aplicadas de modo idempotente durante a inicialização, com cobertura de teste.
- Valide mudanças com `python -m unittest discover -s tests -v` a partir da raiz do repositório. No Windows, use o Python do ambiente virtual se necessário: `.venv\Scripts\python.exe`. Não declare validações que não foram executadas.
- Execute `git diff --check`, revise `git status` e faça commits separados conforme as fases autorizadas. Nunca use `git add .`.

## Prioridade de oportunidades

- Consulte a regra abaixo antes de alterar prioridades ou status.

## Contas e segurança

- Cadastro, validação e login ficam em `controllers/auth.py` e `models/user.py`; mantenha CSRF e validação também no servidor.
- Toda consulta de clientes, produtos e orçamentos deve receber o usuário autenticado e filtrar por `user_id`, inclusive detalhe, histórico, PDF e mutações. Cubra tentativa de acesso cruzado nos testes.
- Não vincule o servidor além de `127.0.0.1` sem uma solicitação específica e uma revisão de implantação; este exemplo não é preparado para exposição pública.

- Cada orçamento/proposta é uma oportunidade comercial. A prioridade implementada aceita Baixa, Média ou Alta e usa Média como padrão; confira `docs/business-rules.md` antes de alterar essa regra.

## Escopo e ferramentas

- Antes de alterar arquivos, identifique o comportamento solicitado, as camadas afetadas e os testes necessários.
- Prefira dependências e ferramentas que já existem no projeto. Não suponha que uma biblioteca, comando ou endpoint esteja disponível sem verificar.
- Não execute operações destrutivas nem acesse dados locais privados para tarefas que podem ser feitas com schema e bancos temporários.
- O onboarding não deve exigir Docker ou Node para executar o CRM; Tailwind já é entregue compilado. Preserve essa distinção em documentação e scripts.
- O CI roda testes em Python 3.10 e 3.13 e verifica o CSS compilado; mantenha os comandos e a matriz documentados em `docs/engineering/05-quality-cicd.md` alinhados ao workflow.
- Para mudanças de segurança, preserve o menor privilégio no CI, execute Bandit e testes de regressão, e não suprima achados sem validar e documentar a justificativa.
