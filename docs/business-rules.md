# Regras de negócio

Este documento registra o comportamento existente e as decisões aprovadas para a próxima mudança. A separação evita apresentar uma funcionalidade planejada como se já estivesse implementada.

## Comportamento atual

- Uma oportunidade comercial é representada por um orçamento/proposta; não existe entidade separada de oportunidade.
- Cada orçamento pertence a um cliente e contém um ou mais itens com quantidade, preço unitário e subtotal guardados como snapshots.
- O servidor recalcula o total a partir do catálogo; valores de total enviados pelo navegador não são confiáveis.
- Status válidos: `Enviado`, `Aprovado` e `Recusado`.
- Registros associados não podem ser excluídos quando a exclusão quebraria o histórico comercial.
- Rotas de CRM exigem sessão autenticada; formulários de alteração usam proteção CSRF.
- Contas novas usam e-mail normalizado para login e exigem senha de 12 a 128 caracteres e aceite registrado dos termos. O login legado do administrador continua aceitando o nome de usuário.
- Clientes, produtos e orçamentos são isolados por conta. Registros que já existiam antes do cadastro multiusuário são atribuídos ao administrador local durante migração, sem apagar dados.
- Este é um exemplo de execução local. Não há confirmação de e-mail nem controles de operação para exposição pública; a aplicação fica vinculada a `127.0.0.1`.
- Cinco falhas de login a partir do mesmo endereço em 15 minutos bloqueiam novas tentativas por esse endereço até a janela passar. Um novo login invalida o token de sessão anterior da mesma conta.

## Prioridade da oportunidade (implementada)

- Prioridade será um atributo do orçamento/oportunidade existente.
- Valores permitidos: `Baixa`, `Média` e `Alta`; novos registros e registros legados recebem `Média`, exceto quando outra opção for escolhida.
- O usuário escolhe a prioridade ao criar e pode alterá-la na página de detalhes.
- A prioridade é visível nas telas de listagem e detalhes e também na proposta PDF.
- A implementação deve validar os valores no servidor e preservar todos os orçamentos já cadastrados durante a migração.
- A interface usa etiquetas visuais consistentes para diferenciar os níveis; o PDF exibe prioridade junto da data e do status.
