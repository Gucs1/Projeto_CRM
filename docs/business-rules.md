# Regras de negócio

Este documento registra o comportamento existente e as decisões aprovadas para a próxima mudança. A separação evita apresentar uma funcionalidade planejada como se já estivesse implementada.

## Comportamento atual

- Uma oportunidade comercial é representada por um orçamento/proposta; não existe entidade separada de oportunidade.
- Cada orçamento pertence a um cliente e contém um ou mais itens com quantidade, preço unitário e subtotal guardados como snapshots.
- O servidor recalcula o total a partir do catálogo; valores de total enviados pelo navegador não são confiáveis.
- Status válidos: `Enviado`, `Aprovado` e `Recusado`.
- Registros associados não podem ser excluídos quando a exclusão quebraria o histórico comercial.
- Rotas de CRM exigem sessão autenticada; formulários de alteração usam proteção CSRF.

## Decisão aprovada para prioridade

- Prioridade será um atributo do orçamento/oportunidade existente.
- Valores permitidos: `Baixa`, `Média` e `Alta`; novos registros e registros legados recebem `Média`, exceto quando outra opção for escolhida.
- O usuário escolhe a prioridade ao criar e pode alterá-la na página de detalhes.
- A prioridade é visível nas telas de listagem e detalhes e também na proposta PDF.
- A implementação deve validar os valores no servidor e preservar todos os orçamentos já cadastrados durante a migração.
- Esta regra está documentada como decisão, mas a funcionalidade só será implementada após autorização explícita para a fase correspondente.
