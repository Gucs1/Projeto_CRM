# Módulo 1 — Harness Engineering e Context Engineering

## Conceitos

**Prompt engineering** é escrever a instrução específica de uma tarefa. Por exemplo: “adicione prioridade ao orçamento e cubra a regra com testes”.

**Context engineering** é selecionar e organizar o conhecimento que o agente precisa antes de executar a tarefa: arquitetura, regras comerciais, limites do projeto e exemplos relevantes. Contexto útil reduz suposições; contexto excessivo torna mais difícil encontrar a regra certa.

**Harness engineering** é preparar o ambiente completo de trabalho do agente: contexto, instruções, ferramentas disponíveis, validações reproduzíveis e critérios de conclusão. O harness ajuda a tarefa a ser feita de maneira consistente e verificável, mesmo quando o prompt é curto.

Em resumo: o prompt diz **qual tarefa** executar; o contexto explica **onde e segundo quais regras**; o harness dá **meios e critérios para executar e conferir**.

## Como o CRM usa o contexto

1. `AGENTS.md` fornece regras curtas aplicáveis ao repositório inteiro e aponta para material mais específico.
2. `docs/architecture.md` mostra onde cada responsabilidade vive e como uma requisição percorre a aplicação.
3. `docs/business-rules.md` registra comportamentos comerciais atuais que não devem ser inferidos apenas pela interface.
4. `.agents/skills/crm-change/SKILL.md` descreve um fluxo reutilizável para mudanças funcionais no CRM.
5. Testes em `tests/` são exemplos executáveis e verificações de regressão; o comando padrão está em `AGENTS.md`.
6. Este documento reúne o mapa de leitura, as diferenças entre conceitos e um exercício para demonstrar o fluxo.

O agente deve ler apenas as regras relevantes à tarefa. Por exemplo, uma mudança no PDF requer consultar arquitetura, regras de snapshots/prioridade, a Skill, o gerador PDF e seus testes; não requer carregar todo o histórico do CRM.

## Fronteiras que preservam a arquitetura

- `controllers/`: HTTP, autenticação da ação e validação da entrada.
- `models/`: regras de persistência e consultas SQLite.
- `schema.sql` e `db.py`: estrutura inicial e migrações compatíveis com bancos existentes.
- `templates/` e `static/`: páginas Jinja, estilos e comportamento no navegador.
- `pdf/`: composição dos documentos PDF.
- `tests/`: verificações automatizadas, usando banco temporário quando necessário.

Uma alteração deve seguir a fronteira existente e receber validação no servidor. Dados de uma conta precisam continuar filtrados pelo `user_id`; mudanças de banco devem preservar os dados legados. `config.py`, `.env`, `instance/` e ambientes locais não são material de contexto para uma tarefa comum e não devem ser lidos ou commitados sem necessidade explícita.

## Fluxo de trabalho e critério de conclusão

1. Ler `AGENTS.md`, esta arquitetura e somente as regras de negócio pertinentes.
2. Descrever escopo, comportamento esperado, arquivos prováveis e riscos antes de editar.
3. Implementar a menor mudança coerente nas camadas existentes.
4. Acrescentar ou ajustar testes para regras novas e regressões relevantes.
5. Rodar `python -m unittest discover -s tests -v` e `git diff --check` quando aplicável.
6. Revisar o diff, confirmar que segredos/dados locais não foram incluídos e relatar verificações com seus resultados reais.
7. Parar no limite da fase aprovada e pedir autorização antes do módulo seguinte.

Uma tarefa está pronta quando o comportamento pedido existe, as regras relevantes estão cobertas, as validações executadas foram relatadas honestamente e o diff está limitado ao escopo autorizado.

## Decisões arquiteturais registradas

As decisões implementadas estão em `docs/engineering/adr/`:

- [ADR-0001 — Flask, SQLite e páginas Jinja para execução local](adr/0001-flask-sqlite-local.md)
- [ADR-0002 — Isolamento de dados por conta e preservação do banco legado](adr/0002-account-data-isolation.md)

ADRs registram o contexto, a decisão e suas consequências. Eles explicam por que o sistema atual tem esse formato; não substituem código, testes ou regras comerciais.

## Demonstração prática: prioridade do orçamento

Para uma tarefa como “adicionar prioridade à oportunidade”, um Coding Agent deve:

1. Consultar `docs/business-rules.md` para confirmar que orçamento é a oportunidade e que os níveis são Baixa, Média e Alta, com Média como padrão.
2. Consultar `docs/architecture.md` e a Skill para localizar persistência em `models/`, migração em `db.py`, interface em `templates/` e PDF em `pdf/`.
3. Planejar validação do valor no servidor e migração sem apagar orçamentos legados.
4. Cobrir criação, edição, listagem, PDF e migração com os testes existentes.
5. Executar a suíte e revisar o diff antes de declarar conclusão.

Esse exemplo foi implementado anteriormente no projeto; use-o como referência de processo, não como uma instrução para reaplicar a funcionalidade.

## Exercício

Peça ao Codex: “Quero permitir filtrar a lista de orçamentos por status. Antes de alterar arquivos, explique as regras e camadas que consultará, os arquivos que provavelmente mudam e os testes de regressão necessários. Não implemente ainda.”

### Critérios de resposta correta

- O agente consulta as regras comerciais, a arquitetura e a Skill antes de propor implementação.
- Identifica listagem em `controllers/quotes.py`, consulta em `models/quote.py`, interface em `templates/quotes/list.html` e testes em `tests/test_quotes.py`.
- Mantém o filtro limitado ao usuário autenticado e valida status no servidor.
- Propõe testes para cada status permitido, valor inválido, ausência de filtro e isolamento entre contas.
- Não altera arquivos antes de receber autorização para implementar.

## Comandos de validação

Na raiz do repositório, no PowerShell:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
git diff --check
```

Resultado esperado: a suíte informa `OK` e `git diff --check` não aponta erros de whitespace. Se um teste falhar, investigue a mensagem e o diff antes de concluir; não apresente falha como sucesso.

## Erros comuns

- **Colocar todas as regras em `AGENTS.md`:** instruções longas ficam difíceis de consultar. Mantenha nele o mapa e as regras essenciais; detalhe arquitetura e negócio em documentos próprios.
- **Confundir Skill com ferramenta:** Skill é um fluxo/documento reutilizável; ferramenta executa operações. Uma Skill pode orientar quando e como usar testes, mas não substitui o executor de testes.
- **Confundir o prompt com contexto:** uma solicitação bem escrita não informa sozinha a arquitetura local nem as regras escondidas em migrações e modelos.
- **Declarar validação sem executar:** relate o comando e o resultado observados; deixe explícito o que não foi possível testar.
- **Carregar arquivos locais sensíveis para “entender o projeto”:** use configuração de exemplo, schema e testes temporários; não exponha configuração privada nem banco real.

## Referências

- [AGENTS.md e instruções do repositório](../../../AGENTS.md)
- [Arquitetura](../architecture.md)
- [Regras de negócio](../business-rules.md)
- [Skill de mudanças no CRM](../../../.agents/skills/crm-change/SKILL.md)

