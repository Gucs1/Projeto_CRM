# Módulo 5 — Qualidade e CI/CD

## 1. Conceito

**Qualidade** é verificar que o comportamento esperado continua correto e que mudanças não introduzem regressões. **Integração contínua (CI)** automatiza essas verificações quando mudanças são enviadas ou propostas. **Entrega/implantação contínua (CD)** automatiza a distribuição do software; este módulo não configura deploy.

## 2. O que foi implementado

`.github/workflows/ci.yml` cria dois jobs em GitHub Actions:

1. **Python:** executa em Python 3.10 e 3.13, instala `requirements.txt`, roda `pip check` e a suíte `unittest`.
2. **Tailwind:** instala Node.js 22 e dependências travadas por `package-lock.json`, compila o CSS e falha se `static/css/tailwind.css` gerado diferir do arquivo commitado.

O workflow roda em `push`, `pull_request`, manualmente com `workflow_dispatch` e semanalmente. O token tem apenas `contents: read`; não há secrets, publicação ou deploy. Há timeout e cancelamento de runs anteriores da mesma referência. O Módulo 6 adiciona o job de verificações de segurança a esse workflow.

## 3. Por que esses checks

- A matriz Python testa a versão mínima declarada (3.10) e uma versão mais recente (3.13), cobrindo compatibilidade sem multiplicar excessivamente os runs.
- `pip check` detecta conflitos no conjunto instalado.
- `unittest` cobre autenticação, migrações, permissões por conta, orçamento e PDF usando SQLite temporário.
- A verificação de Tailwind impede que templates e CSS compilado fiquem dessincronizados.
- Não adicionei formatter, linter, cobertura ou scanner neste módulo: não havia configuração existente e ferramentas novas precisam de critérios de adoção próprios.

## 4. Como interpretar falhas

- **Falha no `pip install`:** confira versão Python suportada e metadados das dependências.
- **Falha no `pip check`:** há dependências instaladas com requisitos incompatíveis.
- **Falha no unittest:** veja nome do teste, traceback e execute localmente com `python -m unittest tests.test_quotes -v` (ajuste o módulo conforme o teste).
- **Falha no CSS gerado:** recompilar localmente com `npm ci` e `npm run build:css`; revisar e commitar a alteração de CSS se ela for intencional.
- **Workflow não iniciou:** confirme que a branch está no GitHub e que Actions estão habilitados para o repositório.

## 5. Como executar localmente

```powershell
python -m pip install -r requirements.txt
python -m pip check
python -m unittest discover -s tests -v
npm ci
npm run build:css
git diff --exit-code -- static/css/tailwind.css
```

O primeiro comando do Tailwind usa Node.js; os testes e app Python não precisam dele. No desenvolvimento cotidiano, execute a suíte e `pip check`; recompilar CSS só é necessário quando alterar templates/classes.

## 6. GitHub e credenciais

O repositório local não tem remoto Git configurado. O workflow foi adicionado como exemplo pronto para uso quando o projeto for enviado a um repositório GitHub; não foi enviado nem executado em um runner remoto. Antes de publicar, revise conteúdo e segredos locais. O workflow não recebe segredos nem concede permissão de escrita.

O GitHub documenta que `permissions` limita o `GITHUB_TOKEN`; este workflow usa somente leitura. As versões das actions seguem os exemplos oficiais atuais: `actions/checkout@v7`, `actions/setup-python@v7` e `actions/setup-node@v7`.

## 7. Limitações e próximos passos possíveis

- Não há deploy/CD, cobertura mínima definida, análise estática ou auditoria automática de dependências.
- O workflow não pôde ser executado remotamente porque não existe remoto configurado neste checkout.
- Se a cobertura crescer, estabeleça um objetivo de cobertura com base nos riscos do CRM antes de impor um percentual.
- Lint/formatação podem ser adicionados quando a equipe escolher convenções e corrigir o baseline.

## 8. Exercício

Faça uma alteração local em um teste ou template e examine quais jobs seriam afetados. Para uma mudança de lógica, rode a suíte; para uma classe Tailwind, rode `npm run build:css` e confirme o diff gerado. Explique por que o CSS compilado precisa ser commitado mesmo sem Node no runtime.

Critérios: saber ligar cada job ao tipo de alteração, interpretar a falha e reconhecer que o workflow ainda precisa de execução no GitHub após publicação.

## Referências oficiais

- [GitHub Actions — sintaxe de workflows e permissões](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- [Práticas de segurança para Actions](https://docs.github.com/en/actions/reference/security/secure-use)
- [actions/checkout](https://github.com/actions/checkout)
- [actions/setup-python](https://github.com/actions/setup-python)
- [actions/setup-node](https://github.com/actions/setup-node)
