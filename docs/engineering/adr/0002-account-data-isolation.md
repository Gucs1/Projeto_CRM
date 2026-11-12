# ADR-0002: Isolamento de dados por conta e preservação do banco legado

- **Estado:** aceito (comportamento atual)
- **Data:** 2026-11-12

## Contexto

O CRM passou de uma conta administrativa local para permitir cadastro de várias contas. Clientes, produtos e orçamentos contêm dados comerciais privados e não devem aparecer para outra conta.

## Decisão

Associar os registros comerciais ao `user_id` e exigir que as consultas e mutações recebam a conta autenticada. Na migração, registros existentes sem proprietário são atribuídos ao administrador local configurado. A migração preserva dados, e novas contas não recebem os dados legados.

## Consequências

- Consultas de lista, detalhe, histórico, PDF, edição e exclusão precisam manter o filtro por conta.
- Testes devem verificar acesso cruzado entre usuários, além do caminho feliz.
- Migrações de dados precisam ser compatíveis com o banco existente e cobrir o estado legado em testes temporários.
- A conta administradora e o banco locais continuam sendo dados privados; não devem ser incluídos em documentação ou commits.

