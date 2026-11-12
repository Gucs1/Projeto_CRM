# Módulo 2 — Coding Agents, AGENTS.md e Skills

## 1. O que é um Coding Agent

Um Coding Agent é um agente de software que interpreta uma solicitação, consulta contexto, navega pelo repositório e usa ferramentas para analisar, alterar e validar código. Ele não conhece automaticamente as convenções privadas de cada projeto: precisa encontrar instruções, exemplos e critérios locais.

## 2. Como `AGENTS.md` funciona neste repositório

O Codex consulta `AGENTS.md` como instruções persistentes para o trabalho no repositório. Aqui, o arquivo na raiz dá regras gerais e aponta para arquitetura, regras comerciais, Skills e validações. Mantenha-o curto e acionável: uma regra detalhada de domínio pertence à documentação ou Skill correspondente.

Antes de uma mudança, confira as instruções aplicáveis ao diretório e à tarefa. Não assuma que um prompt substitui as regras de segurança, dados e arquitetura do projeto.

## 3. Instruções, Skills e ferramentas

| Elemento | Para que serve | Exemplo neste CRM |
| --- | --- | --- |
| Instrução | Regra persistente sobre como trabalhar | `AGENTS.md`: preservar dados e rodar testes |
| Skill | Procedimento especializado e reutilizável | `.agents/skills/crm-change/SKILL.md`: sequência para mudança funcional |
| Ferramenta | Ação que o agente pode executar | terminal para unittest, Git para diff e commits |
| Contexto | Informação necessária para decidir corretamente | arquitetura, regras comerciais, código e testes |
| Prompt | Pedido da tarefa atual | “planeje um filtro por status sem implementar” |

Uma Skill orienta o uso das ferramentas; não é uma dependência instalada nem executa testes por si só.

## 4. Regras de trabalho do agente

As instruções atualizadas em `AGENTS.md` e na Skill `crm-change` estabelecem que o agente deve:

- identificar camadas e testes relevantes antes de editar;
- distinguir análise/planejamento de autorização para implementar;
- confirmar APIs, comandos e dependências no projeto antes de assumir que existem;
- priorizar ferramentas já usadas e justificar dependências novas;
- preservar isolamento por `user_id`, CSRF, dados locais e migrações;
- relatar apenas verificações realmente executadas;
- parar no limite da fase aprovada.

## 5. Exemplo prático: planejar filtro de status

Pedido de treino:

> Quero permitir filtrar os orçamentos por status. Primeiro explique as regras, arquivos e testes necessários. Não implemente ainda.

Plano esperado:

1. Confirmar em `docs/business-rules.md` os status válidos: `Enviado`, `Aprovado`, `Recusado`.
2. Inspecionar `controllers/quotes.py`, `models/quote.py`, `templates/quotes/list.html` e `tests/test_quotes.py`.
3. Fazer o modelo filtrar com status permitido e sempre manter `user_id` na consulta.
4. Adicionar controle de filtro na listagem sem remover o comportamento atual quando o filtro estiver vazio.
5. Testar cada status, ausência de filtro, valor inválido e isolamento entre duas contas.
6. Não editar até receber autorização para implementação.

Esse exercício é apenas planejamento. O filtro ainda não foi implementado.

## 6. Como verificar se o agente seguiu as instruções

- Confira se ele consultou as regras e camadas corretas antes de propor a solução.
- Revise o diff para garantir que só os arquivos esperados foram alterados.
- Confirme que a consulta inclui o usuário autenticado e que há teste de acesso cruzado.
- Confira saída real de `python -m unittest discover -s tests -v` e `git diff --check`.
- Verifique `git status` para confirmar que configuração, banco, segredos e dados locais não foram adicionados.
- Compare a entrega com os critérios de conclusão da tarefa; testes aprovados não provam requisitos que os testes não cobrem.

## 7. Como reutilizar em outro projeto

1. Crie um `AGENTS.md` curto com arquitetura principal, limites de segurança, comandos válidos e critérios de conclusão.
2. Mantenha documentação de arquitetura e negócio em arquivos separados.
3. Crie uma Skill quando existir um fluxo especializado repetido, com etapas e verificações concretas.
4. Use comandos reais já presentes no projeto; não copie instruções de outra stack sem conferir.
5. Comece com um exercício de planejamento e revise a resposta antes de delegar mudanças maiores.

## 8. Comandos de validação

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
git diff --check
git status --short
```

Use esses comandos após mudanças de código. Para uma alteração puramente documental, revise links, arquivos apontados e diff; a suíte de aplicação não verifica a correção semântica de instruções.

## 9. Problemas comuns

- **`AGENTS.md` muito extenso:** regras essenciais ficam escondidas. Mantenha o mapa e mova detalhes para documentos especializados.
- **Skill genérica demais:** se não indicar arquivos, riscos e validações reais, não orienta a execução.
- **Agente inventa dependência ou endpoint:** peça para confirmar no repositório e justificar antes de instalar ou usar.
- **“Faça um plano” interpretado como autorização:** deixe explícito quando o pedido é apenas análise; as instruções do CRM também exigem distinguir plano de implementação.
- **Confiança cega nos testes:** teste passa somente o comportamento coberto; revise o diff e requisitos não automatizados.

## 10. Exercício

Peça ao Codex para planejar o filtro de status acima e avaliar a resposta usando a lista da seção 6. Para completar o exercício, a proposta não deve modificar arquivos, deve manter isolamento por conta e deve enumerar os casos de teste.

