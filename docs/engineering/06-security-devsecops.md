# Módulo 6 — Security Engineering e DevSecOps

## 1. Conceito

Security Engineering integra proteções ao desenho e à implementação. DevSecOps automatiza verificações de segurança junto ao ciclo de desenvolvimento. Nenhuma ferramenta sozinha prova que um sistema é seguro; cada uma detecta classes específicas de problemas.

## 2. Proteções já presentes no CRM

- Senhas persistidas como hash via Werkzeug; cadastro valida tamanho e confirmação.
- CSRF em formulários, validação no servidor, cookies HttpOnly/SameSite e sessão revogável.
- Consultas comerciais filtram por conta autenticada; testes cobrem acesso cruzado.
- SQL usa parâmetros para valores; migrações preservam dados e são testadas com bancos temporários.
- Configuração privada local, `.env`, banco e ferramentas virtuais são ignorados pelo Git.
- Flask escuta em `127.0.0.1` e debug permanece desativado; o projeto não é preparado para implantação pública.
- Logs evitam corpo, cookie, endereço IP e mensagens arbitrárias de exceções.

Esses controles reduzem riscos comuns, mas não fornecem recuperação de conta, MFA, e-mail verificado, backup automático ou operação pronta para produção.

## 3. Ferramentas adicionadas

- **Bandit 1.9.4:** análise estática Python baseada em AST. Fica em `requirements-dev.txt`, separada das dependências de runtime. O CI falha para achados médios/altos (`-ll`).
- **pip-audit:** compara dependências Python de desenvolvimento e runtime com advisories públicos no job GitHub.
- **npm audit:** verifica dependências do frontend com severidade moderada ou maior.
- **Gitleaks Action v3:** examina o histórico Git em busca de segredos commitados, usando checkout completo.

O workflow não precisa de segredo próprio. O token automático do GitHub tem somente permissão de leitura, e comentários/artefatos do Gitleaks estão desativados. Em contas pessoais, Gitleaks Action não requer chave de licença; organizações podem precisar configurar a licença gratuita indicada pelo projeto Gitleaks.

## 4. Achados analisados durante a implementação

Bandit identificou `urllib.request.urlopen` no abridor automático do navegador e SQL de migração que interpolava identificadores. O abridor agora valida HTTP, host `127.0.0.1` e ausência de credenciais antes da chamada; um teste cobre rejeição de URLs externas e userinfo. O único `# nosec B310` fica nessa linha, justificado pela validação imediatamente anterior.

As consultas de migração foram convertidas para SQLs constantes escolhidos por mapas locais. Os dados (`admin_id`) continuam parametrizados. Assim Bandit não precisa ignorar B608; os testes de migração verificam preservação dos dados.

Bandit reportou `No issues identified` para achados médios/altos após as mudanças. `npm audit` reportou zero vulnerabilidades. O pip-audit local não completou a consulta ao serviço remoto de advisories; portanto, não há resultado local aprovado para essa ferramenta. O job GitHub fará essa consulta quando o workflow rodar.

## 5. Como executar localmente

```powershell
python -m pip install -r requirements-dev.txt
python -m pip check
python -m bandit -r app.py controllers models db.py pdf -ll
npm audit --audit-level=moderate
python -m unittest discover -s tests -v
```

O `pip-audit` também pode ser executado com `python -m pip_audit -r requirements-dev.txt`, quando o serviço público de advisories estiver acessível. `pip-audit` detecta vulnerabilidades conhecidas por versão; não é SAST e não prova que o uso local de uma biblioteca seja seguro.

O Gitleaks CI examina o histórico completo. Localmente, se tiver o CLI instalado, execute `gitleaks git --redact` na raiz. Ao detectar um segredo já commitado, revogue/rotacione o segredo primeiro; apagar o arquivo num commit posterior não remove o valor do histórico.

## 6. Como interpretar os scanners

- **Bandit:** revise identificador, gravidade, confiança e fluxo real. Um padrão sinalizado pode ser falso positivo, mas só suprima regra pontual após validar o controle; explique o motivo ao lado do código.
- **pip-audit/npm audit:** identifique pacote, versão afetada e versão corrigida. Atualize as faixas/lock, rode os testes e não ignore advisory sem justificativa e prazo.
- **Gitleaks:** trate qualquer credencial real como comprometida; faça rotação e examine histórico/artefatos antes de considerar resolvido.
- **CI vermelho:** não desligue uma verificação para liberar o build. Reproduza localmente, corrija ou documente a exceção mínima com evidência.

## 7. Limitações

- Os scanners dependem de regras e feeds externos; podem gerar falsos positivos ou não conhecer uma vulnerabilidade nova.
- A auditoria `pip-audit` não foi concluída localmente por falta de resposta do serviço público. Nenhum resultado foi inventado.
- O checkout local não tem remoto GitHub, portanto os jobs de auditoria e Gitleaks ainda não rodaram em runner remoto.
- Bandit não cobre dependências, autenticação ponta a ponta, lógica comercial nem segurança operacional.
- O projeto permanece local e de demonstração; não se deve expô-lo à internet sem uma revisão de implantação.

## 8. Exercício

Rode Bandit, `npm audit` e a suíte de testes localmente. Depois revise o job `Security checks` em `.github/workflows/ci.yml` e explique o que cada etapa detecta, quais permissões recebe e por que uma vulnerabilidade corrigida no código não substitui a rotação de uma credencial que já foi exposta.

Critérios: diferenciar SAST, auditoria de dependências e secret scanning; interpretar resultados sem alegar cobertura total; manter o token do workflow read-only.

## Referências oficiais

- [Bandit — documentação e opções](https://github.com/PyCQA/bandit)
- [pip-audit — auditoria de dependências Python](https://github.com/pypa/pip-audit)
- [Gitleaks Action](https://github.com/gitleaks/gitleaks-action)
- [GitHub Actions — práticas de segurança](https://docs.github.com/en/actions/reference/security/secure-use)
